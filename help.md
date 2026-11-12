<!--
Guide shown in the app's Help window.
"## " starts a topic (its name appears in the left pane), "### " a subheading,
"1. " a numbered step, "- " a tip or bullet; any other line is a paragraph.
-->

## Getting started
Turn a folder of Markdown chapters into an audiobook (.m4b) with chapter markers that plays in Apple Books.

Setting up a book takes four steps, shown in the bar at the top: Book, Voice, Sound and Create. Click Next to move on, Back to go back, or click any step in the bar.

### Steps
1. Book: click New book, then Choose a book… (or Browse… in the Book section). Select the chapter .md files to narrate: press ⌘A to select them all, or ⌘-click to pick only some. Chapters you leave out are skipped, and the files stay where they are. Or select one EPUB, Word or PDF book to import it. The app lists the chapters it found. Type the Title and Author on the right; if Title is empty, the folder name is used. To give the book cover art in Books, click Choose… under Cover.
2. Voice: pick Kokoro or Chatterbox, then a voice. Michael is the default. Click Preview to hear the opening of chapter 1.
3. Sound: adjust the speed and pauses if you like, and preview again. The recommended settings suit most books.
4. Create: check the summary, then click Create audiobook. A progress screen shows each chapter as it finishes. After the last chapter it levels the volume and builds the audiobook file, and that is counted in the percentage too, so 100% means the book is ready to play. Click Cancel to stop; finished chapters and paragraphs are kept. The line at the bottom is the latest log message: click it to open the full log, and click it again to close it. The log folds away by itself when the audiobook is ready.
5. When it finishes, the app shows the finished book. The .m4b is saved in your audiobooks folder; click Show in Finder to see it. (That's Music › Audiobook Maker, or the out folder inside the app's folder if you have used it since before that change.)

### Tips
- On the Voice step, press ▶ on any voice card to hear it read the opening of chapter 1 without choosing it. Click the card to choose it.
- Kokoro renders an 18-minute chapter in about a minute. Chatterbox takes roughly an hour for the same chapter.
- Keep the app open while it renders. The Mac won't go to sleep on its own while an audiobook is being made, but closing a laptop's lid still puts it to sleep, so leave the lid open. If it stops partway, click Create audiobook again: finished chapters are skipped, and a half-finished chapter carries on from the paragraph where it stopped.
- Help and Settings are at the bottom of the library pane.
- A book you set up before opens on the Create step, with everything you chose. Click a row in the summary to change it.

## Library
The pane on the left lists your books: every chapters folder you've opened or imported, and any finished audiobook already in your audiobooks folder. The newest one you opened is at the top.

### Steps
1. Click a book to open it. A finished book opens on its Finished screen, where Play starts it; click Edit book at the bottom to change its voice or settings. Its voice, settings, title and cover come back as you left them.
2. Click New book, then Choose a book… to select chapter files or import an EPUB, Word or PDF book.
3. Hover over a book and click ⋯ to Show in Finder, Rename, Pin or Archive it.

### Tips
- Rename only changes the name in the library. The audiobook file is still named after the Title in the Book section.
- Voice previews have their own folding section below your books. Click one to play it.
- Pinned books stay at the top under Pinned. Archived books are tucked under Archived at the bottom; click it to see them, and use ⋯ > Unarchive to bring one back.
- The ‹ button at the top folds the pane away to make room. Click › to open it again.
- Settings and Help are at the bottom of the pane. Settings also opens with ⌘, (comma).
- You can't switch books while one is narrating. Wait for it to finish, or click Cancel.
- An audiobook found in your audiobooks folder opens on its Finished screen, since there are no chapters to edit.

## Listening
Finished audiobooks and voice previews play right in the app, in a bar that appears above the Create audiobook button.

### Steps
1. On a finished book, click Play. A voice preview plays by itself when it's ready; Play again replays it.
2. Use ⏮ and ⏭ to jump between chapters, ↺15 and 30↻ to go back 15 seconds or ahead 30, or drag the slider.
3. Pick a chapter from the menu under the title to jump straight to it.
4. Pick a speed on the right, from 0.75× to 2×. Voices keep their normal pitch.
5. Click × to stop and hide the bar.

### Tips
- Each book remembers where you stopped, even after you quit, and carries on from there next time you click Play.
- The speed you pick is kept for every book.
- ⏮ goes back to the start of the chapter; click it again within 3 seconds to go to the previous chapter.
- Playing barely uses the Mac, so you can listen while another book narrates.

## Deleting
Delete finished audiobooks and voice previews without leaving the app. Everything goes to the Trash, so you can get it back.

### Deleting a book
1. Hover over the book in the library and click ⋯ > Delete….
2. Delete always moves the book's audio to the Trash: the .m4b, its MP3 folder, its check report and its saved narration. The book leaves the library.
3. Tick "Also move the chapters folder to the Trash" to remove the chapter files too. Leave it unticked to keep them; you can open the folder again later with New book and narrate it again.
4. Click Move to Trash.

### Deleting previews
1. In the library, click Voice previews to open the list.
2. Click a preview to hear it. Hover over one and click 🗑 to delete it, or click Delete all previews under the list.

### Tips
- You can't delete while a book is narrating.
- Saved narration lets a book be rebuilt quickly, for example with a new cover. Once it's deleted, narrating the book again starts from scratch.

## Preparing chapters
How to write the chapter files so the book reads well.

### Steps
1. Put one chapter in each file, all in the same folder (not in subfolders). Markdown (.md) and plain text (.txt) files both work, saved from any text editor, including Notepad on Windows. A file called pronunciations.txt is never read as a chapter (see Pronunciations).
2. Start each file name with a two-digit number: 01, 02 … 10. Two digits keep chapter 10 from sorting before chapter 2.
3. Start each file with a heading, for example: # Chapter One — The Color of Almost Dark. It is read aloud at the start of the chapter, followed by a longer pause, and it becomes the chapter name in Books.
4. Separate paragraphs with a blank line. A short pause is added after each one.
5. To mark a scene break, put --- (or ***, or * * *) on a line of its own. It gives a 2-second pause.

### Adding a pause
- Type [pause] anywhere in the text for 1 second of silence at that spot, or [pause 3] for 3 seconds. Decimals work too: [pause 1.5].
- A [pause] inside a paragraph splits it there, so the voice stops and then carries on.
- On a line of its own, [pause 3] adds 3 seconds between two paragraphs.

### What gets left out
- Code blocks, images and HTML.
- Link addresses. The link's text is still read.
- Markdown symbols such as #, *, _, > and list markers. The words around them are read.

### Tips
- Lines inside one paragraph are joined together, so a list without blank lines is read as one paragraph. Put a blank line between items to get a pause after each.
- If a word is mispronounced, add it to the book's pronunciations (see Pronunciations) instead of changing the chapter.

## Importing a book
Turn an EPUB, Word (.docx) or PDF book into chapter files, instead of making the .md files by hand.

### Steps
1. Click New book, then Choose a book… (or Browse… in the Book section).
2. Select the book file.
3. The app makes a new folder next to it called "<book name> chapters", with one .md file per chapter, and opens it. An existing folder is never overwritten: a second import goes in "<book name> chapters (2)".
4. The title and author are filled in from the book, and the cover too when an EPUB has one.
5. Open the folder and look through the chapters before you narrate (see Tips).

### How chapters are found
- EPUB: each chapter file of the book, in reading order. The table of contents page is left out.
- Word: a new chapter starts at each Title or Heading 1 paragraph. Without those, at lines like "Chapter 3" or "Prologue".
- PDF: a new chapter starts at lines like "Chapter 3", "Part Two", "Prologue" or "Epilogue". Page numbers and running headers are removed, and words split with a hyphen at a line end are joined.
- Sections with fewer than 40 words, like a title page, are skipped.

### Tips
- Italics and bold are kept, and scene breaks become --- so they get a pause.
- Delete the files you don't want read, like a copyright page, acknowledgments or an excerpt from another book.
- PDF text is the hardest to recover. Check for paragraphs that were split or joined in the wrong place.
- A scanned PDF (pictures of pages) has no text to import. Use an EPUB or Word copy of the book instead.
- PDF import needs pypdf. If the log says to install it, open Terminal in the project folder and run: uv pip install --python .venv/bin/python pypdf
- Old .doc files and Pages files can't be imported. Open them in Word or Pages and export as .docx or EPUB first.

## Pronunciations
Fix how a name or word is said once for the whole book, without changing the chapters.

### Steps
1. Choose the chapters folder.
2. On the Book step, click Edit list… under the chapters. A file called pronunciations.txt opens in TextEdit. It is created in the chapters folder the first time.
3. Add one word per line, then the way it should sound: Saoirse = Seer-sha
4. Save the file in TextEdit (⌘S).
5. Click Preview, or Create audiobook. The Edit list button shows how many words the list fixes.

### Tips
- Capitalization doesn't matter: Kai = Kye also changes KAI and kai.
- Only whole words are replaced, so Kai doesn't change Kairo.
- Phrases work too: New York = Noo Yawk. Longer phrases are matched first.
- Spell the sound with ordinary words and hyphens. Try a few spellings with Preview until it sounds right.
- Lines starting with # are notes and are ignored.
- Only chapters that use a word you changed are rendered again.
- The list belongs to the book, so each chapters folder has its own.

## Kokoro voices
Kokoro is fast, free and gives exactly the same result every time, so the preview is what the whole book will sound like.

### Reading the voice names
- The first letter is the accent: a = American, b = British.
- The second letter is f for female or m for male.
- So am_michael is an American male voice and bf_emma is a British female voice.

### Steps
1. Click a voice in the Voice list. Use the search box and the US/UK and Female/Male filters to narrow it down.
2. Click Preview. The sample plays when it is ready.
3. Try a few. Good narrators to start with: am_michael, am_fenrir, bm_george, bm_lewis, af_heart and bf_emma.
4. Adjust Speed if you like. 0.95 is recommended; 0.9 gives a slower, more relaxed read.

### Tips
- Samples are saved in the samples folder. Previewing the same voice again replaces its sample.
- Each voice keeps its own rendered chapters, so switching back to a voice you already used reuses its finished chapters.

## Voice blending
Blending mixes two Kokoro voices into one new voice, like mixing two paint colors. That one voice reads the whole book; the two voices never take turns.

### Steps
1. On the Voice step, click the main voice. It is marked Narrator.
2. On the Sound step, under Blend with a second voice, click Choose a voice…. The Voice step opens: click a second voice. It is marked Blend.
3. Click Preview and listen.
4. To go back to a single voice, click Remove under Blend with a second voice on the Sound step.

### Tips
- Pronunciation follows the main voice. am_michael blended with bm_george has American pronunciation with some of George's tone.
- Blending a male and a female voice gives a more neutral-sounding voice.
- A blend is a good way to get a narrator that doesn't sound like every other Kokoro audiobook.

## Character voices
Read dialogue in different voices: one per character if you like, with the narrator reading everything else. It's optional; with it off, the whole book is read in one voice.

### Steps
1. Choose Kokoro and pick the narrator's voice as usual (and a blend if you like).
2. On the Sound step, under Character voices, click Set up cast…
3. Turn on the switch at the top right of the Character voices window.
4. Pick an Other dialogue voice. It reads characters without their own voice, and lines whose speaker couldn't be worked out. Leave it on Narrator's voice to read those in the narrator's voice.
5. In the list of characters found in the book, pick a voice for each one you want to stand out.
6. Click Done, then Preview to hear chapter 1 with the cast.

### How speakers are found
- A name next to the quote with a speech word: “Late,” Mara said. / “Late,” said Mara. / Mara asked, “Why?”
- One speaker per paragraph: once one quote in a paragraph is attributed, the paragraph's other quotes go to the same character.
- An action beat with one known character: Mara frowned. “Flooded since when?”
- A back-and-forth between two characters: a line with no clue goes to whichever of the two didn't speak last, and a line that names one of them (“I can count, Torvan.”) goes to the other one. A paragraph of narration ends the back-and-forth.
- Lines like “Fine,” she said, or someone said, can't be worked out, so they use the Other dialogue voice. Expect roughly half of a typical chapter's lines to be attributed this way; tag the ones that matter.

### Fixing a wrong guess
- Put the character's name in curly brackets right before the opening quote mark: {Mara} “Fine,” she said.
- Put {Name} at the very start of a paragraph to give all of that paragraph's quotes to that character.
- The brackets are never read aloud, and they are ignored when character voices are off.
- Click Who said what in the Cast window for a list of every line of dialogue and who it went to, chapter by chapter. It opens in TextEdit.

### Tips
- Character voices work with Kokoro only.
- Changing one character's voice only narrates that character's lines again.
- Character-voice and one-voice renders are kept separately, so switching between them doesn't narrate anything again once both have been made.
- The same person can appear twice in the list, for example Bren and Old Bren. Give both the same voice.
- The cast is saved with the book.

## Chatterbox
Chatterbox sounds more expressive than Kokoro and can copy any voice from a short clip. It is much slower, and it occasionally skips or garbles a sentence.

### Steps
1. Click Chatterbox at the top of the Voice section.
2. For the voice, leave Built-in voice selected, click a saved clip in the list, click Browse… to choose a clip, or click Record… to record one (see Recording a voice).
3. Click Preview. It takes a minute or two.
4. Read along with the text while the sample plays and listen for skipped words. If you hear any, lower Temperature and preview again.
5. Click Create audiobook. Leave the Mac plugged in: a whole book can take many hours.

### Checking for skipped words
- With Check for skipped words turned on (below the voice clips), a speech-to-text model called Whisper listens to each paragraph as soon as Chatterbox narrates it and compares what it hears with the text.
- If words are missing, or extra words were added, the paragraph is narrated again, up to 3 tries in all. The best try is kept, and the log says what happened.
- Paragraphs that are still wrong after 3 tries are listed in a check report, a text file in your audiobooks folder named after the book. It shows the text and what Whisper heard. Listen to those spots, and click Redo on the chapter if you want a new take.
- The report covers the whole book, not just the last run. A paragraph leaves it when it is narrated again and passes.
- A name Whisper hears a little differently, or a word respelled in Pronunciations, doesn't count as a mistake.
- Only paragraphs narrated with the check turned on are checked. Chapters made earlier aren't checked until they are narrated again.
- The check needs faster-whisper. If the log says to install it, open Terminal in the project folder and run: uv pip install --python .venv/bin/python faster-whisper
- The first check downloads Whisper, about 480 MB. Checking adds a few seconds per paragraph, which is small next to Chatterbox's own time.
- Kokoro doesn't skip words, so Kokoro books are never checked.

### Tips
- The first use downloads the model, about 3 GB. The Creating screen shows how far along it is. To download it ahead of time, use Download all voices in Settings (see Voices and storage).
- Each run comes out slightly different, even with the same settings.
- Chatterbox marks everything it makes with an inaudible watermark (Resemble AI's Perth). You can't hear it, but software can detect that the audio was made by AI. Kokoro adds no watermark.
- If it stops partway, click Create audiobook again. Finished chapters, and the finished paragraphs of the chapter it was on, are kept.
- To get a new take of one chapter, click Redo next to it in the chapter list.

## Recording a voice
Record a short clip of a voice for Chatterbox to copy, such as your own narrator voice.

### Steps
1. Click Chatterbox at the top of the Voice section.
2. Click Record…, then Start recording. The timer counts down from 12 seconds.
3. Start reading right away. The passage to read is shown in the window, and the bar under the timer moves as the microphone hears you.
4. Recording stops after 12 seconds, or click Stop to end it early. At least 5 seconds of speech is needed.
5. Type a name for the voice and click Save voice. If the name is already taken, click Replace voice to overwrite it, or type another name. Cancel throws the new recording away.
6. The new recording is added to the Voice clip list and selected. Click Preview to hear Chatterbox read with it.

### Tips
- Record in a quiet room, about a hand's width from the microphone.
- Read at the pace and in the tone you want for the book. Chatterbox copies both.
- Chatterbox only uses the first 10 seconds. The silence before and after your speech is trimmed automatically.
- Recordings are saved in the voices folder. To reuse one later, click it in the Voice clip list (saved voices appear there), or click Browse… to pick any audio file.
- The first time, macOS asks to let Audiobook Maker use the microphone. Click Allow.

## Settings explained
What each slider does, and the recommended values that Reset restores.

### Kokoro
- Speed (0.5 to 2.0, recommended 0.95): how fast the voice reads.
- Blend with (recommended None): mixes in a second voice. See Voice blending.

### Chatterbox
- Exaggeration (0.25 to 2.0, recommended 0.5): how emotional and dramatic the reading is. Higher values also read faster.
- Pacing (0 to 1, recommended 0.3): lower values give a slower, more deliberate read. At 0 it stops copying the clip's accent.
- Temperature (0.3 to 1.5, recommended 0.6): lower values are more consistent with fewer slips; higher values are livelier but skip or garble more often.

### Pauses
- Paragraph pause (recommended 0.6 seconds): silence after each paragraph.
- Heading pause (recommended 1.2 seconds): silence after a chapter heading.
- Scene breaks (---) always get 2 seconds, and [pause] tags add their own silence. See Preparing chapters.

### Tips
- Change one setting at a time and preview, so you can hear what it did.
- If Chatterbox rushes at high Exaggeration, lower Pacing to slow it back down.
- Changing a voice setting narrates every chapter again on the next Create audiobook. Changing only a pause doesn't: the chapters are put back together from the saved narration in seconds.
- Reset to recommended, on the Sound step, changes only the sliders. It doesn't change the book, voice, blend or voice clip.
- Each book remembers its own voice, settings, title, author and cover (see Updating a book). Reset changes only the book that is open.

## Updating a book
Fix or rewrite a chapter without rendering the whole book again.

### Steps
1. Edit the chapter's .md file and save it.
2. Open the app. It reopens the last book with the voice and settings it was made with, so you don't need to set anything.
3. Click Create audiobook. Unchanged chapters show "already rendered, skipping". In the edited chapter, only the paragraphs you changed are narrated again; the rest are reused. Then the .m4b is rebuilt.
4. In Books, remove the old copy of the audiobook, then double-click the new .m4b in your audiobooks folder.
5. Sync your iPhone again (see iPhone & Books).

### What the app remembers
- Each book's voice (or voice clip), blend, character voices, every slider, the skipped-word check, title, author and cover are saved in a file called audiobook-settings.json in its chapters folder.
- They are saved when you click Preview or Create audiobook, when you switch to another chapters folder, and when you quit.
- Choosing a chapters folder loads what was saved with it. A book that was never saved keeps the current voice and settings, with an empty title, author and cover.
- When the app opens, it reopens the last chapters folder you used.
- If a saved voice clip or cover image was moved or deleted, the log says so and it is left out.

### Redoing a chapter
1. In the chapter list in the Book section, click Redo next to the chapter.
2. That chapter is narrated again from the start, and the .m4b is rebuilt. Other chapters are kept.

- Redo only appears on chapters already made with the current voice and settings. A new or edited chapter, or a chapter after you change the voice or a setting, has no Redo until Create audiobook makes it.
- With Chatterbox, each redo is a new take, so use it when a chapter has a skipped or garbled sentence.
- With Kokoro, a redo sounds exactly the same, because Kokoro gives the same result every time.

### Changing the cover, title or author
- Pick a new Cover image (or change Title or Author) and click Create audiobook again. Every chapter shows "already rendered, skipping", so only the .m4b file is rebuilt, which takes seconds. The voice model isn't even loaded when nothing needs narrating.
- Square images work best: Books shows audiobook covers as squares. 1400 × 1400 pixels or larger looks sharp.

### What makes chapters render again
- Editing a chapter: only the paragraphs you changed.
- Changing the pronunciations: only the chapters that use a word you added or changed.
- Changing the voice, blend or a voice setting: every chapter.
- Changing a pause: nothing is narrated again. The chapters are put back together from the saved paragraphs, which takes seconds.
- Clicking Redo: that chapter.
- Re-recording or replacing the voice clip: every chapter.
- Inserting or renumbering chapter files: the chapters whose position changed.

### Tips
- Narration is saved in the build folder, one folder per book and voice, with each paragraph saved separately.
- After each Create audiobook, narration the book no longer uses (old versions of edited paragraphs, old settings) is deleted automatically. The log says how much space was freed.
- Other voices you tried are kept, so switching back reuses them. To free that space too, delete the build folder; the next Create audiobook then narrates everything again.

## Volume and MP3 export
Every chapter is levelled to the same volume, and you can also save the book as one MP3 per chapter.

### Even volume
- Before the .m4b is built, each chapter is set to the same loudness: about -20 dB on average, with peaks kept below -3 dB. That's within what audiobook stores such as ACX (Audible) ask for, and it means no chapter is noticeably louder or quieter than the next.
- This happens automatically. A levelled copy of each chapter is kept in the build folder, so it is only redone for chapters that change.

### Exporting MP3s
1. Create the audiobook as usual.
2. On the finished screen, click Export MP3s.
3. The MP3s go in a folder in out named after the book, with (MP3) at the end. Click Show in Finder to see it, next to the .m4b. It has one MP3 per chapter: 01 - Chapter title.mp3, and so on.

### Tips
- The MP3s are 44.1 kHz, 192 kbps, mono, with ¾ of a second of silence at the start and 2 seconds at the end. That's the file format ACX and most other audiobook stores ask for.
- Exporting reuses the finished chapters, so it doesn't narrate anything again and takes about as long as building the .m4b.
- Each export replaces the MP3s in that folder, so renamed or removed chapters don't leave old files behind.
- Stores have their own rules about AI narration. ACX asks you to contact them before submitting it; check each store's rules before uploading.

## iPhone & Books
iCloud doesn't sync audiobooks you add yourself, so copy the book to your iPhone with Finder.

### Steps
1. Connect your iPhone to the Mac with a cable and unlock it. If asked, tap Trust.
2. Open Finder and click your iPhone in the sidebar under Locations.
3. Click the Audiobooks tab (not Books).
4. Check Sync audiobooks onto your iPhone, then choose All audiobooks or select yours.
5. Click Apply or Sync. The book appears in Books on the iPhone under Library → Audiobooks.

### Tips
- Turn on "Show this iPhone when on Wi-Fi" in Finder's General tab to sync later without the cable.
- After updating the book, sync again so the new version replaces the old one.
- Alternative: install BookPlayer (free) from the App Store, AirDrop the .m4b to your iPhone and open it in BookPlayer. It keeps the chapters.

## Gentle mode
Narrating works the Mac's chip hard for a long time. A MacBook Air has no fan, so it gets warm, slows itself down to cool off, and other apps can feel laggy. Gentle mode, in Settings at the bottom of the library pane (or ⌘,), trades some speed for a cooler, more responsive Mac.

### What it does
- The voice uses 2 of the Mac's 4 fast cores instead of all of them, which leaves room for everything else. Whisper, the skipped-word check, does the same.
- Narrating is marked as background work, so macOS gives the apps you are using the CPU first.
- After every 5 minutes of narrating, the app rests for 1 minute so the chip can cool down. The log says when it rests. Cancel works during a rest too.

### How much slower
- Kokoro takes about a third longer.
- A rest only comes before narrating a new paragraph, so rebuilding a finished book, for example with a new cover, never waits.
- Chatterbox does most of its work on the graphics chip, so fewer cores barely slow it. The rests add about a fifth.
- Gentle mode doesn't change how the narration sounds, so turning it on or off never makes chapters render again.

### Tips
- Gentle mode is on unless you turn it off. The app remembers your choice for every book. A change applies from the next preview or audiobook, not to one already running.
- For the fastest render, turn it off and leave the Mac alone, for example overnight.
- Keep the Mac on a hard, flat surface, not a bed or your lap, and plugged in.
- Quitting heavy apps such as browsers with many tabs helps more than anything else.

## Voices and storage
Download every voice ahead of time, see how much room the voices take, and free it up. Open Settings at the bottom of the library pane (or ⌘,).

### Steps
1. Under Voices and storage, each row says whether it is downloaded and how much room it takes: Kokoro voices, Chatterbox, the skipped-word check (Whisper) and the narration cache.
2. Click Download all voices to fetch everything that is missing, with a progress bar. All of it together is about 4 GB. Click Cancel to stop; what finished is kept, and the next download carries on from there.
3. To free up room, click Delete on a row. A deleted voice downloads again the next time you use it.

### Tips
- Downloading stops if you close Settings. Finished files are kept.
- The narration cache holds every narrated paragraph, so changing a finished book (a new cover, a redone chapter) doesn't narrate it all again. Deleting it keeps your audiobooks, but the next change to a book narrates the whole book again.
- The voices are kept in Hugging Face's folder (~/.cache/huggingface), which stays if you remove the app. Delete them here first if you are removing the app.

## Privacy
- No account, no sign-in and no tracking. Your books, recordings and audiobooks never leave this computer.
- The app fetches the voices from Hugging Face, the first time each is used. Hugging Face's own usage reporting is turned off.
- Once a day it asks GitHub whether a new version of the app is out. The request carries nothing about you or your books, and nothing is downloaded or installed. Turn it off in Settings, under Check for updates.
- Copy details in Settings, for bug reports, includes the app's version and your system but not your name or your files.

## Updates
When a new version is out, **Version … is out** appears at the bottom of the library, and in Settings under About. Click it to open the download page. The new version is free too: open the .dmg and drag Audiobook Maker into Applications to replace the old one. Your books, settings and voices stay.

The app checks once a day. **Check now** in Settings checks straight away, and the switch beside Check for updates turns the daily check off.

## Keyboard
The main actions have keyboard shortcuts. On Windows, use Ctrl where it says ⌘.

- **⌘Return**: next step, or Create audiobook on the last step.
- **⌘[**: back a step.
- **⌘1 to ⌘4**: go to Book, Voice, Sound or Create.
- **⌘F**: search the voices.
- **⌘N**: new book.
- **⌘L**: open or close the library.
- **⌘,**: Settings.
- **⌘/**: this guide.
- **Space**: play or pause the player (when the cursor isn't in a text box).
- **Esc**: close Settings, this guide and other small windows.

### Easier reading
- **Larger text** in Settings, under Display, draws everything a little bigger. The window grows to fit, so it suits a screen bigger than a 13-inch laptop's.
- All text meets the WCAG AA contrast level against its background.
- VoiceOver can't read the app's window yet, because the toolkit it's built with doesn't support it.

## Windows
This guide is written for a Mac. On Windows everything works the same way, with these differences.

### Names that differ
- Use Ctrl where the guide says ⌘: Ctrl+A selects every chapter, and Ctrl+, opens Settings.
- Show in Finder is called Show in Explorer.
- Text files (pronunciations.txt, Who said what) open in Notepad instead of TextEdit.
- Books doesn't exist on Windows. Play the .m4b in the app, or in an audiobook app such as VLC, or export MP3s.

### Setting up
1. Install Python 3.11 from python.org, and uv (see docs.astral.sh/uv).
2. Install FFmpeg: in PowerShell, run winget install Gyan.FFmpeg
3. In PowerShell, in the project folder, run: uv venv --python 3.11 .venv
4. Then run: uv pip install --python .venv\Scripts\python.exe -r requirements.txt
5. Double-click Audiobook Maker.bat to start the app.

### Tips
- With an NVIDIA graphics card, Chatterbox uses it automatically and runs much faster.
- Gentle mode still uses fewer cores and rests, but can't lower the app's priority as it does on a Mac.

### Recording is silent, or "Didn't catch 5 seconds of speech"
1. Open System Settings → Privacy & Security → Microphone.
2. Turn on Audiobook Maker (or Terminal, if you started the app from Terminal).
3. Quit and reopen the app, then record again.

### Chatterbox skipped or garbled words
1. Make sure Check for skipped words is on (see Chatterbox), and look at the check report in your audiobooks folder.
2. Lower Temperature to about 0.5 and preview.
3. To redo one chapter without changing settings, click Redo next to it in the chapter list (see Updating a book).

### "hasn't been downloaded yet"
- Each Kokoro voice, Chatterbox's model and Whisper download the first time they are used, so that first use needs the internet. Connect once and try again; after that they work offline.
- To make every voice work offline, open Settings and click Download all voices while you're online.
- Character voices count too: a character's voice that has never been used before has to download.

### "No chapter files found"
- The chapters folder must contain the .md or .txt files directly, not inside subfolders.

### "FFmpeg is needed"
- FFmpeg is a free program the app uses to even out the volume, join the chapters into one audiobook and play it. The app checks for it before narrating, so you never lose hours of work to a missing FFmpeg.
- On a Mac, install it with Homebrew: open Terminal, run brew install ffmpeg, then open the app again.

### A word is pronounced wrong
- Add it to the book's pronunciations (see Pronunciations), then create the audiobook again. Only the chapters that use the word are rendered again.

### macOS won't open the app
- The app isn't signed with a paid Apple developer account, so the first time, macOS says it can't check it. Click Done, then open System Settings → Privacy & Security, scroll down to Security and click Open Anyway next to Audiobook Maker. After that it opens normally.

### Something else went wrong
- The line at the bottom of the main window shows the latest message. Click it to open or close the full log. Errors open the full log automatically.
- Full details are saved in a log file. To find it, open Settings and click Show log. On a Mac it is in your Library/Logs/Audiobook Maker folder, and the Console app can open it.
- When you report a problem, open Settings, click Copy details and paste them into your message. They give the app's version and your system, without your name.
