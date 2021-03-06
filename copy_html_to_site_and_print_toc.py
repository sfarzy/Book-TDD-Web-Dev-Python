#!/usr/bin/env python

import os
import json
from lxml import html
import subprocess

CHAPTERS = [
    c.replace('.asciidoc', '.html')
    for c in json.loads(open('atlas.json').read())['files']
]
for tweak_chap in ['praise.html', 'part1.html', 'part2.html', 'part3.html']:
    CHAPTERS[CHAPTERS.index(tweak_chap)] = tweak_chap.replace('.', '.harry.')
CHAPTERS.remove('titlepage.html')
CHAPTERS.remove('copyright.html')
CHAPTERS.remove('toc.html')
CHAPTERS.remove('ix.html')
CHAPTERS.remove('author_bio.html')
CHAPTERS.remove('colo.html')


def make_chapters():
    for chapter in CHAPTERS:
        subprocess.check_call(['make', chapter], stdout=subprocess.PIPE)


def parse_chapters():
    for chapter in CHAPTERS:
        raw_html = open(chapter).read()
        yield chapter, html.fromstring(raw_html)


def get_chapter_info():
    chapter_info = {}
    appendix_numbers = list('ABCDEFGHIJKL')
    chapter_numbers = list(range(1, 100))
    part_numbers = list(range(1, 10))

    for chapter, parsed_html in parse_chapters():
        print('getting info from', chapter)

        if not parsed_html.cssselect('h2'):
            header = parsed_html.cssselect('h1')[0]
        else:
            header = parsed_html.cssselect('h2')[0]
        href_id = header.get('id')
        if href_id is None:
            href_id = parsed_html.cssselect('body')[0].get('id')
        subheaders = [h.get('id') for h in parsed_html.cssselect('h3')]

        chapter_title = header.text_content()
        chapter_title = chapter_title.replace('Appendix A: ', '')

        if chapter.startswith('chapter_'):
            chapter_no = chapter_numbers.pop(0)
            chapter_title = f'Chapter {chapter_no}: {chapter_title}'

        if chapter.startswith('appendix_'):
            appendix_no = appendix_numbers.pop(0)
            chapter_title = f'Appendix {appendix_no}: {chapter_title}'

        if chapter.startswith('part'):
            part_no = part_numbers.pop(0)
            chapter_title = f'Part {part_no}: {chapter_title}'

        if chapter.startswith('epilogue'):
            chapter_title = f'Epilogue: {chapter_title}'


        chapter_info[chapter] = href_id, chapter_title, subheaders

    return chapter_info


def fix_xrefs(contents, chapter, chapter_info):
    for other_chap in CHAPTERS:
        html_id, chapter_title, subheaders = chapter_info[other_chap]
        old_tag = f'href="#{html_id}"'
        new_tag = f'href="/book/{other_chap}"'
        if old_tag in contents:
            contents = contents.replace(old_tag, new_tag)
    return contents

def fix_title(contents, chapter, chapter_info):
    parsed = html.fromstring(contents)
    titles = parsed.cssselect('h2')
    if titles and titles[0].text.startswith('Appendix A'):
        title = titles[0]
        title.text = title.text.replace('Appendix A', chapter_info[chapter][1])
    return html.tostring(parsed)

def copy_chapters_across_fixing_xrefs(chapter_info, fixed_toc):
    comments_html = open('disqus_comments.html').read()
    buy_book_div = html.fromstring(open('buy_the_book_banner.html').read())
    analytics_div = html.fromstring(open('analytics.html').read())
    load_toc_script = open('load_toc.js').read()

    for chapter in CHAPTERS:
        old_contents = open(chapter).read()
        new_contents = fix_xrefs(old_contents, chapter, chapter_info)
        new_contents = fix_title(new_contents, chapter, chapter_info)
        parsed = html.fromstring(new_contents)
        body = parsed.cssselect('body')[0]
        if parsed.cssselect('#header'):
            head = parsed.cssselect('head')[0]
            head.append(html.fragment_fromstring('<script>' + load_toc_script + '</script>'))
            body.set('class', 'article toc2 toc-left')
        body.insert(0, buy_book_div)
        body.append(html.fromstring(
            comments_html.replace('CHAPTER_NAME', chapter.split('.')[0])
        ))
        body.append(analytics_div)
        fixed_contents = html.tostring(parsed)

        target = os.path.join('/home/harry/workspace/www.obeythetestinggoat.com/content/book', chapter)
        with open(target, 'w') as f:
            f.write(fixed_contents.decode('utf8'))
        toc = '/home/harry/workspace/www.obeythetestinggoat.com/content/book/toc.html'
        with open(toc, 'w') as f:
            f.write(html.tostring(fixed_toc).decode('utf8'))


def extract_toc_from_book():
    subprocess.check_call(['make', 'book.html'], stdout=subprocess.PIPE)
    parsed = html.fromstring(open('book.html').read())
    return parsed.cssselect('#toc')[0]



def fix_toc(toc, chapter_info):
    href_mappings = {}
    for chapter in CHAPTERS:
        html_id, chapter_title, subheaders = chapter_info[chapter]
        if html_id:
            href_mappings['#' + html_id] = f'/book/{chapter}'
        for subheader in subheaders:
            href_mappings['#' + subheader] = f'/book/{chapter}#{subheader}'

    def fix_link(href):
        if href in href_mappings:
            return href_mappings[href]
        else:
            return href

    toc.rewrite_links(fix_link)
    toc.set('class', 'toc2')
    return toc


def print_toc_md(chapter_info):
    for chapter in CHAPTERS:
        html_id, chapter_title, subheaders = chapter_info[chapter]
        print(f'* [{chapter_title}](/book/{chapter})')


def main():
    make_chapters()
    toc = extract_toc_from_book()
    chapter_info = get_chapter_info()
    fixed_toc = fix_toc(toc, chapter_info)
    copy_chapters_across_fixing_xrefs(chapter_info, fixed_toc)
    print_toc_md(chapter_info)


if __name__ == '__main__':
    main()
