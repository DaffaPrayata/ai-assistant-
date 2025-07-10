# mio/ascii_art.py
import random

ART_LIST = [
    r"""
      ／＞　 フ
     | 　_　_| 
   ／` ミ＿xノ 
  /　　　　 |
 /　 ヽ　　 ﾉ
│　　|　|　|
／￣|　　 |　|　|
(￣ヽ＿_ヽ_)__)
＼二)
    """,
    r"""
 (｡♥‿♥｡)
 [Anime Girl Says Hello!]
    """,
    r"""
（＾・ω・＾❁） Hai Daffa~!
    """,
]

def get_random_ascii():
    return random.choice(ART_LIST)
