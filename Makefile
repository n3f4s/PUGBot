
TARGET 				:= pugbot

SRCDIR 				:= src
TARGETDIR 		:= pugbot

PYTHON 				:= python

SOURCES       := $(wildcard $(SRCDIR)/*.py )
OBJECTS       := $(patsubst $(SRCDIR)/%,$(TARGETDIR)/%,$(SOURCES:.py=.py))


ALL: $(TARGET).pyz

$(TARGET).pyz: INSTALL RANKS $(OBJECTS)
	$(PYTHON) -m zipapp $(TARGETDIR) -p '/usr/bin/env python3' -m "server:main"
# -o pugbot.pyz

INSTALL:
	$(PYTHON) -m pip install -r requirements.txt -t $(TARGETDIR)

RANKS: ranks.json $(SRCDIR)/helper/rank_gen.py
	$(PYTHON) $(SRCDIR)/helper/rank_gen.py ranks.json $(SRCDIR)

$(TARGETDIR)/%.py: $(SRCDIR)/%.py
	cp $< $@

.PHONY: RANKS INSTALL
