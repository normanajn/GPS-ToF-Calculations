# Build the technical note.  Tables come from reports/nova.json via scripts/make_note_tables.py.
all: tables nova-tof-note.pdf
tables:
	cd ../.. && python3 scripts/make_note_tables.py
nova-tof-note.pdf: nova-tof-note.tex references.bib generated/*.tex figures/*.pdf
	latexmk -pdf -interaction=nonstopmode -halt-on-error nova-tof-note
clean:
	latexmk -C nova-tof-note
.PHONY: all tables clean
