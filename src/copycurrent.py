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


def gc(arg, fail=False):
    return mw.addonManager.getConfig(__name__).get(arg, fail)


def open_in_add_window(note, did):
    # Anki built in: see main.py
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

    addedCardWindow.deckChooser.setDeckName(deckname)
    addedCardWindow.modelChooser.models.setText(modelname)
    newnote = mw.col.newNote()
    newnote.fields = note.fields
    if gc("NoteIdFieldName", False):
        for f in newnote.keys():
            if f == gc("NoteIdFieldName"):
                newnote[f] = str(newnote.id)
    newnote.tags = note.tags
    addedCardWindow.editor.tags.setText("")
    addedCardWindow.editor.setNote(newnote)
    addedCardWindow.activateWindow()


def _on_open_in_add_window(editor):
    # did
    if isinstance(editor.parentWindow, AddCards):
        did = editor.parentWindow.deckChooser.selectedId()
    else:
        if editor.card.odid:
            did = editor.card.odid
        else:
            did = editor.card.did
    open_in_add_window(editor.note, did)
Editor._on_open_in_add_window = _on_open_in_add_window


def on_open_in_add_window(editor):
    editor.saveNow(editor._on_open_in_add_window)
Editor.on_open_in_add_window = on_open_in_add_window


# only in AddCards and EditCurrent and not in the Browser because it's defined
# for the Browser elsewhere
# For AddCards and EditCurrent I still want to use the Editor hook because
# there are not comparable ones for AddCards or EditCurrent
def onSetupShortcuts21(cuts, editor):
    if isinstance(editor.parentWindow, (AddCards, EditCurrent)):
        shortcut = gc('shortcut')
        added_shortcuts = [
            (shortcut,
                lambda: editor.on_open_in_add_window()),
        ]
        cuts.extend(added_shortcuts)
addHook("setupEditorShortcuts", onSetupShortcuts21)

###########################


def copy_from_reviewer():
    card = aqt.mw.reviewer.card
    if card.odid:
        did = card.odid
    else:
        did = card.did
    note = aqt.mw.col.getNote(card.nid)
    open_in_add_window(note, did)


def side_by_side():
    copy_from_reviewer()
    aqt.mw.onEditCurrent()


def EditorContextMenu(view, menu):
    a = menu.addAction('copy contents underlying note to add window')
    a.triggered.connect(lambda _, v=view.editor: on_open_in_add_window(v))


def ReviewerContextMenu(view, menu):
    a = menu.addAction('copy contents underlying note to add window')
    a.triggered.connect(lambda v=view: copy_from_reviewer())


def show_in_contextmenu_of_reviewer():
    """user config only available when profile is loaded"""
    if gc('context_menu__entry_for_copy_current_note__reviewer', False):
        addHook("AnkiWebView.contextMenuEvent", ReviewerContextMenu)
    if gc('context_menu__entry_for_copy_current_note__editor', False):
        addHook("EditorWebView.contextMenuEvent", EditorContextMenu)

addHook('profileLoaded', show_in_contextmenu_of_reviewer)


def reviewer_shortcuts_21(shortcuts):
    additions = (
        (gc("shortcut_side_by_side_from_reviewer"), side_by_side),
        (gc("shortcut_copy_note_thats_shown_in_the_reviewer"), copy_from_reviewer),
    )
    shortcuts += additions
addHook("reviewStateShortcuts", reviewer_shortcuts_21)


###########################

# allow to clone from the browser table (when you are not in the editor)
def _browser_on_open_in_add_window(browser):
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
        # must save current field
        open_in_add_window(note, did)


# allow to clone from the browser table (when you are not in the editor)
def browser_on_open_in_add_window(browser):
    browser.editor.saveNow(lambda b=browser: _browser_on_open_in_add_window(b))


def setupMenu(browser):
    global myaction
    myaction = QAction(browser)
    myaction.setText("Copy current note contents to add window")
    if gc("shortcut", False):
        myaction.setShortcut(QKeySequence(gc("shortcut")))
    myaction.triggered.connect(lambda: browser_on_open_in_add_window(browser))
    browser.form.menuEdit.addAction(myaction)
addHook("browser.setupMenus", setupMenu)


def add_to_table_context_menu(browser, menu):
    menu.addAction(myaction)
addHook("browser.onContextMenu", add_to_table_context_menu)
