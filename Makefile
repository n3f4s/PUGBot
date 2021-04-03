
TARGET 				:= pugbot

SRCDIR 				:= src
TARGETDIR 		:= target

PYTHON 				:= python

SOURCES       := $(wildcard $(SRCDIR)/*.py )
OBJECTS       := $(patsubst $(SRCDIR)/%,$(TARGETDIR)/%,$(SOURCES:.py=.py))


ALL: $(TARGET).pyz

$(TARGET).pyz: TEMPLATES ASSETS RANKS $(OBJECTS)
	@echo "Generating file" $(TARGET).pyz
	@$(PYTHON) -m zipapp $(TARGETDIR) -p '/usr/bin/env python3' -o $(TARGET).pyz

run: $(TARGET).pyz
	@echo "Running" $(TARGET).pyz
	@$(PYTHON) $(TARGET).pyz

INSTALL:
	@echo "Installing dependencies"
	@$(PYTHON) -m pip install -r requirements.txt -t $(TARGETDIR)

RANKS: ranks.json $(SRCDIR)/helper/rank_gen.py
	@echo "Generating rank files"
	@$(PYTHON) $(SRCDIR)/helper/rank_gen.py ranks.json $(SRCDIR)

TEMPLATES:
	@echo "Copying templates"
	@cp -r templates $(TARGETDIR)/

ASSETS:
	@echo "Copying assets"
	@cp -r assets $(TARGETDIR)/

$(TARGETDIR)/%.py: $(SRCDIR)/%.py
	@echo "Copying source files"
	cp $< $@

clean:
	rm $(TARGET).pyz
	rm -rf $(TARGETDIR)

.PHONY: RANKS INSTALL TEMPLATES clean
