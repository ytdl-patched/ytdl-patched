all: lazy-extractors youtube-dl doc pypi-files
clean: clean-test clean-dist
clean-all: clean clean-cache
completions: completion-bash completion-fish completion-zsh
doc: README.md CONTRIBUTING.md issuetemplates supportedsites
ot: offlinetest
tar: youtube-dl.tar.gz

# Keep this list in sync with MANIFEST.in
# intended use: when building a source distribution,
# make pypi-files && python setup.py sdist
pypi-files: AUTHORS Changelog.md LICENSE README.md README.txt supportedsites completions youtube-dl.1 devscripts/* test/*

.PHONY: all clean install test tar pypi-files completions ot offlinetest codetest supportedsites

clean-test:
	rm -rf test/testdata/player-*.js tmp/ *.annotations.xml *.aria2 *.description *.dump *.frag \
	*.frag.aria2 *.frag.urls *.info.json *.live_chat.json *.part* *.unknown_video *.ytdl \
	*.3gp *.ape *.avi *.desktop *.flac *.flv *.jpeg *.jpg *.m4a *.m4v *.mhtml *.mkv *.mov *.mp3 \
	*.mp4 *.ogg *.opus *.png *.sbv *.srt *.swf *.swp *.ttml *.url *.vtt *.wav *.webloc *.webm *.webp \
	*.images
clean-dist:
	rm -rf yt-dlp.1.temp.md yt-dlp.1 README.txt MANIFEST build/ dist/ .coverage cover/ yt-dlp.tar.gz completions/ \
	yt_dlp/extractor/lazy_extractors.py *.spec CONTRIBUTING.md.tmp youtube-dl youtube-dl*.exe yt_dlp.egg-info/ AUTHORS .mailmap
clean-cache:
	find . \( -name "*.pyc" -o -name "*.class" \) -delete

lazy-extractors: yt_dlp/extractor/lazy_extractors.py

PREFIX ?= /usr/local
DESTDIR ?= .
BINDIR ?= $(PREFIX)/bin
MANDIR ?= $(PREFIX)/man
SHAREDIR ?= $(PREFIX)/share
PYTHON ?= /usr/bin/env python3

# set SYSCONFDIR to /etc if PREFIX=/usr or PREFIX=/usr/local
SYSCONFDIR = $(shell if [ $(PREFIX) = /usr -o $(PREFIX) = /usr/local ]; then echo /etc; else echo $(PREFIX)/etc; fi)

# set markdown input format to "markdown-smart" for pandoc version 2 and to "markdown" for pandoc prior to version 2
MARKDOWN = $(shell if [ `pandoc -v | head -n1 | cut -d" " -f2 | head -c1` = "2" ]; then echo markdown-smart; else echo markdown; fi)

install: lazy-extractors youtube-dl youtube-dl.1 completions
	install -Dm755 youtube-dl $(DESTDIR)$(BINDIR)/youtube-dl
	install -Dm644 youtube-dl.1 $(DESTDIR)$(MANDIR)/man1/youtube-dl.1
	install -Dm644 completions/bash/youtube-dl $(DESTDIR)$(SHAREDIR)/bash-completion/completions/youtube-dl
	install -Dm644 completions/zsh/_youtube-dl $(DESTDIR)$(SHAREDIR)/zsh/site-functions/_youtube-dl
	install -Dm644 completions/fish/youtube-dl.fish $(DESTDIR)$(SHAREDIR)/fish/vendor_completions.d/youtube-dl.fish

codetest:
	flake8 .

test:
	$(PYTHON) -m pytest
	$(MAKE) codetest

ot: offlinetest

offlinetest: codetest
	$(PYTHON) -m pytest -k "not download"

tar: youtube-dl.tar.gz

youtube-dl: yt_dlp/*.py yt_dlp/*/*.py yt_dlp/*/*/*.py devscripts/make_zipfile.py
	$(PYTHON) devscripts/make_zipfile.py "$(PYTHON)"

README.md: yt_dlp/*.py yt_dlp/*/*.py
	COLUMNS=80 $(PYTHON) yt_dlp/__main__.py --help | $(PYTHON) devscripts/make_readme.py

CONTRIBUTING.md: README.md
	$(PYTHON) devscripts/make_contributing.py README.md CONTRIBUTING.md

issuetemplates: devscripts/make_issue_template.py .github/ISSUE_TEMPLATE_tmpl/1_broken_site.yml .github/ISSUE_TEMPLATE_tmpl/2_site_support_request.yml .github/ISSUE_TEMPLATE_tmpl/3_site_feature_request.yml .github/ISSUE_TEMPLATE_tmpl/4_bug_report.yml .github/ISSUE_TEMPLATE_tmpl/5_feature_request.yml yt_dlp/version.py
	$(PYTHON) devscripts/make_issue_template.py .github/ISSUE_TEMPLATE_tmpl/1_broken_site.yml .github/ISSUE_TEMPLATE/1_broken_site.yml
	$(PYTHON) devscripts/make_issue_template.py .github/ISSUE_TEMPLATE_tmpl/2_site_support_request.yml .github/ISSUE_TEMPLATE/2_site_support_request.yml
	$(PYTHON) devscripts/make_issue_template.py .github/ISSUE_TEMPLATE_tmpl/3_site_feature_request.yml .github/ISSUE_TEMPLATE/3_site_feature_request.yml
	$(PYTHON) devscripts/make_issue_template.py .github/ISSUE_TEMPLATE_tmpl/4_bug_report.yml .github/ISSUE_TEMPLATE/4_bug_report.yml
	$(PYTHON) devscripts/make_issue_template.py .github/ISSUE_TEMPLATE_tmpl/5_feature_request.yml .github/ISSUE_TEMPLATE/5_feature_request.yml
	$(PYTHON) devscripts/make_issue_template.py .github/ISSUE_TEMPLATE_tmpl/6_question.yml .github/ISSUE_TEMPLATE/6_question.yml

supportedsites:
	$(PYTHON) devscripts/make_supportedsites.py docs/supportedsites.md

README.txt: README.md
	pandoc -f $(MARKDOWN) -t plain README.md -o README.txt

youtube-dl.1: README.md
	$(PYTHON) devscripts/prepare_manpage.py youtube-dl.1.temp.md
	pandoc -s -f $(MARKDOWN) -t man youtube-dl.1.temp.md -o youtube-dl.1
	rm -f youtube-dl.1.temp.md

completion-bash: yt_dlp/*.py yt_dlp/*/*.py devscripts/bash-completion.in
	$(PYTHON) devscripts/bash-completion.py

completion-zsh: yt_dlp/*.py yt_dlp/*/*.py devscripts/zsh-completion.in
	mkdir -p completions/zsh/
	$(PYTHON) devscripts/zsh-completion.py

completion-fish: yt_dlp/*.py yt_dlp/*/*.py devscripts/fish-completion.in
	mkdir -p completions/fish/
	$(PYTHON) devscripts/fish-completion.py

lazy-extractors: yt_dlp/extractor/lazy_extractors.py

_EXTRACTOR_FILES = $(shell find yt_dlp/extractor -iname '*.py' -and -not -iname 'lazy_extractors.py')
yt_dlp/extractor/lazy_extractors.py: devscripts/make_lazy_extractors.py devscripts/lazy_load_template.py $(_EXTRACTOR_FILES)
	$(PYTHON) devscripts/make_lazy_extractors.py $@

youtube-dl.tar.gz: all
	@tar -czf $(DESTDIR)/youtube-dl.tar.gz --transform "s|^|youtube-dl/|" --owner 0 --group 0 \
		--exclude '*.DS_Store' \
		--exclude '*.kate-swp' \
		--exclude '*.pyc' \
		--exclude '*.pyo' \
		--exclude '*~' \
		--exclude '__pycache__' \
		--exclude '.git' \
		-- \
		README.md supportedsites.md Changelog.md LICENSE \
		CONTRIBUTING.md Collaborators.md CONTRIBUTORS AUTHORS \
		Makefile MANIFEST.in youtube-dl.1 README.txt completions \
		setup.py setup.cfg youtube-dl yt_dlp requirements.txt \
		devscripts test tox.ini pytest.ini
	advdef -z -4 -i 30 youtube-dl.tar.gz

AUTHORS: .mailmap
	git shortlog -s -n | cut -f2 | sort > AUTHORS

.mailmap:
	git shortlog -s -e -n | awk '!(out[$$NF]++) { $$1="";sub(/^[ \t]+/,""); print}' > .mailmap
