# -*- coding: utf-8 -*-
from __future__ import unicode_literals


###############USER CONFIG#######################################
#config for 2.1 is set via the config dialog of 2.1
#config for 2.0 is set in the file config.json
####################END USER CONFIG##############################

"""
Copyright: (c) 2019 ijgnd
           (c) 2018 Glutanimate
           (c) Ankitects Pty Ltd and contributors
           (c) 2012–2017 Roland Sieker

License: GNU AGPLv3 <https://www.gnu.org/licenses/agpl.html>
"""

import aqt

from anki.hooks import addHook, runHook, wrap
from aqt import mw
from aqt.qt import *
from aqt.editcurrent import EditCurrent
from aqt.editor import Editor
from aqt.reviewer import Reviewer
from aqt.addcards import AddCards
from aqt.utils import tooltip

from .config import local_conf
from .consts import anki20


def open_in_add_window(note, did):
    #Anki built in: see main.py
    #    def onAddCard(self):
    #        aqt.dialogs.open("AddCards", self)
    # self is an instance of AnkiQt and in it's init this is set:  aqt.mw = self
    addedCardWindow = aqt.dialogs.open('AddCards', aqt.mw) 
    deck = mw.col.decks.get(did)
    deckname = deck['name']
    modelname = note.model()['name']

    # from  onModelChange
    m = mw.col.models.byName(modelname)
    mw.col.conf['curModel'] = m['id']
    cdeck = mw.col.decks.current()
    cdeck['mid'] = m['id']
    mw.col.decks.save(cdeck)
    runHook("currentModelChanged")  
    #mw.reset()
    
    if anki20:
        addedCardWindow.deckChooser.deck.setText(deckname)
    else:
        addedCardWindow.deckChooser.setDeckName(deckname)      
    
    addedCardWindow.modelChooser.models.setText(modelname)
    newnote = mw.col.newNote()

    newnote.fields = note.fields
    if local_conf.get("NoteIdFieldName",False):
        for f in newnote.keys():
            if f == local_conf["NoteIdFieldName"]:
                newnote[f] = str(newnote.id)
    newnote.tags = note.tags
    addedCardWindow.editor.tags.setText("")
    addedCardWindow.editor.setNote(newnote)
    addedCardWindow.activateWindow()


#This does not work: output to stdout is "ignored late blur"
def mysave21(editor):
    "Save unsaved edits - mod of editor.saveNow without callback"
    if not editor.note:
            # calling code may not expect the callback to fire immediately
        editor.mw.progress.timer(10, callback, False)
        return
    editor.saveTags()
    editor.web.eval("saveNow(true)")
    

def on_open_in_add_window(editor):   
    #must save current field
    if anki20:
        editor.saveNow()
    else:
        mysave21(editor)
    
    #did
    if isinstance(editor.parentWindow, AddCards):
        did = editor.parentWindow.deckChooser.selectedId()
    elif isinstance(editor.parentWindow, EditCurrent) and anki20:
        #Editcurrent.__init__ in anki.20 doesn't have this line: "self.editor.card = self.mw.reviewer.card"
        if editor.mw.reviewer.card.odid:
            did = editor.mw.reviewer.card.odid
        else:
            did = editor.mw.reviewer.card.did
    else:
        if editor.card.odid:
            did = editor.card.odid
        else:
            did = editor.card.did

    open_in_add_window(editor.note,did)
Editor.on_open_in_add_window = on_open_in_add_window



#only in AddCards and EditCurrent and not in the Browser because it's defined 
#for the Browser elsewhere
#For AddCards and EditCurrent I still want to use the Editor hook because 
#there are not comparable ones for AddCards or EditCurrent
def onSetupButtons20(editor):
    if isinstance(editor.parentWindow, (AddCards,EditCurrent)):
        shortcut = local_conf['shortcut']
        t = QShortcut(QKeySequence(shortcut), editor.parentWindow)
        t.activated.connect(lambda: editor.on_open_in_add_window())


def onSetupShortcuts21(cuts, editor):
    if isinstance(editor.parentWindow, (AddCards,EditCurrent)):
        shortcut = local_conf['shortcut']
        added_shortcuts = [
            (shortcut,
                lambda: editor.on_open_in_add_window()),
        ]
        cuts.extend(added_shortcuts)


if anki20:
    addHook("setupEditorButtons", onSetupButtons20)
else:
    addHook("setupEditorShortcuts", onSetupShortcuts21)

########################### 

def copy_currently_shown_note_from_reviewer():
    card = aqt.mw.reviewer.card
    if card.odid:
        did = card.odid
    else:
        did = card.did
    note = aqt.mw.col.getNote(card.nid)
    open_in_add_window(note,did)


def side_by_side():
    copy_currently_shown_note_from_reviewer()
    aqt.mw.onEditCurrent()


def addShortcuts20(self, evt):
    k = unicode(evt.text())
    if k == local_conf["shortcut_side_by_side_from_reviewer"]:
        side_by_side()
    if k == local_conf["shortcut_copy_note_thats_shown_in_the_reviewer"]:
        copy_currently_shown_note_from_reviewer()

def EditorContextMenu(view,menu):
    a = menu.addAction('copy contents underlying note to add window')
    a.triggered.connect(lambda _,v=view.editor: on_open_in_add_window(v))
def ReviewerContextMenu(view,menu):
    a = menu.addAction('copy contents underlying note to add window')
    a.triggered.connect(lambda v=view: copy_currently_shown_note_from_reviewer())
def show_in_contextmenu_of_reviewer():
    """user config only available when profile is loaded"""
    if local_conf.get('context_menu__entry_for_copy_current_note__reviewer',False):
        addHook("AnkiWebView.contextMenuEvent", ReviewerContextMenu)
    if local_conf.get('context_menu__entry_for_copy_current_note__editor',False):
        addHook("EditorWebView.contextMenuEvent", EditorContextMenu)

if anki20:
    Reviewer._keyHandler = wrap(Reviewer._keyHandler, addShortcuts20)
addHook('profileLoaded', show_in_contextmenu_of_reviewer)




def reviewer_shortcuts_21(shortcuts):
    additions = (
        (local_conf["shortcut_side_by_side_from_reviewer"], side_by_side),
        (local_conf["shortcut_copy_note_thats_shown_in_the_reviewer"], copy_currently_shown_note_from_reviewer),
    )
    shortcuts += additions
if not anki20:
    addHook("reviewStateShortcuts", reviewer_shortcuts_21)



###########################
#allow to clone from the browser table (when you are not in the editor)
def browser_on_open_in_add_window(browser):
    sel = browser.selectedCards()
    if len(sel) > 1:
        tooltip("two many cards selected. aborting")
    else:
        cid = sel[0]
        card = aqt.mw.col.getCard(cid)
        note = mw.col.getNote(card.nid)
        if card.odid:
            did = card.odid
        else:
            did = card.did
        #must save current field
        if anki20:
            browser.editor.saveNow()
        else:
            mysave21(browser.editor)
        open_in_add_window(note,card.did)


def setupMenu(browser):
    global myaction
    myaction = QAction(browser)
    myaction.setText("Copy current note contents to add window")
    if local_conf.get("shortcut",False):
        myaction.setShortcut(QKeySequence(local_conf["shortcut"]))
    myaction.triggered.connect(lambda : browser_on_open_in_add_window(browser))
    browser.form.menuEdit.addAction(myaction)
addHook("browser.setupMenus", setupMenu)


def add_to_table_context_menu(browser, menu):
    menu.addAction(myaction)


if not anki20:
    addHook("browser.onContextMenu", add_to_table_context_menu)
