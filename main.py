import json

import genanki

from cedict_utils.cedict import CedictParser
from xpinyin import Pinyin

CEDICT_PATH           = "./data/cedict_ts.u8"
CSS_PATH              = "style.css"
DECOMPOSITION_PATH    = "./data/outlier_decomp.json"
LOACH_WORD_ORDER_PATH = "./data/loach_word_order.json"
OUTPUT_PATH           = "cc.apkg"

BACK_FMT = '''\
<div class="container">
    {{FrontSide}}
    <div class="reading">{{Pinyin}}</div>
    <div class="decomposition">{{Decomposition}}</div>
    <div class="pleco_deeplink"><a href="{{Pleco Deeplink}}">go to pleco</a></div>
    </br>
    <div id="meaning_button"><button onclick="showMeaning()">show meaning</button></div>
    <div class="meaning" id="meaning">{{Meaning}}</div>
</div>
<script>
function showMeaning() {
    var button_el = document.getElementById("meaning_button");
    button_el.style.display = "none";
    var meaning_el = document.getElementById("meaning");
    meaning_el.style.display = "block";
}
</script>
'''


def main():
    # load dictionary to use for translation
    print("loading CC-CEDICT")
    cedict_parser = CedictParser()
    cedict_parser.read_file(CEDICT_PATH)
    cedict_entries = cedict_parser.parse()
    char_lookup = {x.simplified: x for x in cedict_entries}

    print("loading loach word order")
    with open(LOACH_WORD_ORDER_PATH, encoding="utf8") as f:
        loach_word_order = json.load(f)

    print("loading css")
    with open(CSS_PATH, encoding="utf8") as f:
        css = f.read()

    print("loading character decompositions")
    with open(DECOMPOSITION_PATH, encoding="utf8") as f:
        decomp_lookup = json.load(f)

    # set up anki data structures
    my_deck = genanki.Deck(1548502343, "cc")
    my_model = genanki.Model(
        1177587192,
        "cc model",
        fields=[
            {"name": "Character"},
            {"name": "Pinyin"},
            {"name": "Decomposition"},
            {"name": "Pleco Deeplink"},
            {"name": "Meaning"}
        ],
        templates=[
            {
                "name": "default",
                "qfmt": '<div class="chinese">{{Character}}</div>',
                "afmt": BACK_FMT,
            },
        ],
        css=css
    )

    def gen_char_colour_pinyins(char, n=2):
        raw_pinyins = [x.split(" ") for x in xp.get_pinyins(char, splitter=" ", tone_marks="marks", n=n)]
        # colourize pinyin
        number_pinyins = [x.split(" ") for x in xp.get_pinyins(char, splitter=" ", tone_marks="numbers", n=n)]
        pinyins = []
        for number_pinyin, raw_pinyin in zip(number_pinyins, raw_pinyins):
            pinyin = []
            for number_word, word in zip(number_pinyin, raw_pinyin):
                tone_number = number_word[-1]
                if not tone_number.isnumeric():
                    tone_number = "5"
                pinyin.append('<span class="tone' + tone_number + '">' + word + '</span>')
            pinyins.append(" ".join(pinyin))
        return pinyins

    xp = Pinyin()
    for i, character in enumerate(loach_word_order):
        pinyin = ", ".join(gen_char_colour_pinyins(character))

        # find meanings
        try:
            cedict_entry = char_lookup[character]
            meanings = cedict_entry.meanings[:min(len(cedict_entry.meanings), 4)]
        except KeyError:
            meanings = ""

        # find the decomposition
        def dfs_decomp(curr_char):
            decomp_output = []
            if curr_char not in decomp_lookup:
                return decomp_output
            curr_char_decomp = decomp_lookup[curr_char]

            if curr_char_decomp:
                decomp_output.append("<ul>")
            for char in curr_char_decomp:
                decomp_output.append("<li>")
                decomp_output.append(char + " (" + ", ".join(gen_char_colour_pinyins(char)) + ")")
                decomp_output.append("</li>")
                decomp_output.extend(dfs_decomp(char))
            if curr_char_decomp:
                decomp_output.append("</ul>")
            return decomp_output

        decomp = []
        decomp.append("<ul>")
        for sub_char in list(character):
            decomp.append("<li>" + sub_char + "</li>")
            decomp.extend(dfs_decomp(sub_char))
        decomp.append("</ul>")

        # create deeplink to navigate to pleco
        pleco_deeplink = "plecoapi://x-callback-url/df?hw=" + character + "&sec=dict&x-source=anki&x-success=anki%3A%2F%2F"

        # generate anki card
        my_note = genanki.Note(
            model=my_model,
            fields=[character, pinyin, "".join(decomp), pleco_deeplink, "\n</br>".join(meanings)],
            guid=genanki.guid_for(character)
        )
        my_deck.add_note(my_note)

        if i % 100 == 0:
            print(str(round(((i + 1) / len(loach_word_order)) * 100)) + "%: ", character)

    print("writing output file")
    genanki.Package(my_deck).write_to_file(OUTPUT_PATH)
    print("done!")

if __name__ == "__main__":
    main()
