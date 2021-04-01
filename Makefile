
TARGET 				:= pugbot

SRCDIR 				:= src
TARGETDIR 		:= target

PYTHON 				:= python

SOURCES       := $(wildcard $(SRCDIR)/*.py )
OBJECTS       := $(patsubst $(SRCDIR)/%,$(TARGETDIR)/%,$(SOURCES:.py=.py))


ALL: $(TARGET).pyz

$(TARGET).pyz: TEMPLATES RANKS $(OBJECTS)
	$(PYTHON) -m zipapp $(TARGETDIR) -p '/usr/bin/env python3' -m "server:main" -o $(TARGET).pyz

INSTALL:
	$(PYTHON) -m pip install -r requirements.txt -t $(TARGETDIR)

RANKS: ranks.json $(SRCDIR)/helper/rank_gen.py
	$(PYTHON) $(SRCDIR)/helper/rank_gen.py ranks.json $(SRCDIR)

TEMPLATES:
	cp -r templates $(TARGETDIR)/

$(TARGETDIR)/%.py: $(SRCDIR)/%.py
	cp $< $@

clean:
	rm $(TARGET).pyz
	rm -rf $(TARGETDIR)

.PHONY: RANKS INSTALL TEMPLATES clean
