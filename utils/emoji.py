"""Emoji catalog for the chat UI."""
EMOJIS = {"常用": ["😀","😂","😍","😎","😭","😡","👍","👏","🙏","🎉","❤️"], "动物": ["🐶","🐱","🐼","🐯","🦊"], "食物": ["🍎","🍕","🍔","🍜","🍰","☕"]}
def all_emojis(): return [item for group in EMOJIS.values() for item in group]
