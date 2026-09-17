# -*- coding: utf-8 -*-
import json
import random
import argparse
import sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parent.parent
VOCAB_JSON = ROOT / 'knowledge' / 'cet4-bank' / '04-高频词汇与大纲词库' / 'cet4-core-vocab.json'

def get_word_batch(count=15):
    if not VOCAB_JSON.exists():
        print(f'Error: {VOCAB_JSON} not found.')
        return []
    with open(VOCAB_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)
    words = data.get('cet4CoreWords', [])
    return random.sample(words, min(count, len(words))) if words else []

def main():
    parser = argparse.ArgumentParser(description='Pick words for story reading')
    parser.add_argument('--count', type=int, default=15, help='Number of words')
    args = parser.parse_args()

    batch = get_word_batch(args.count)
    print('='*75)
    print(f'🎯 随机抽取的 {len(batch)} 个四级高频考点词（供情境短文创作/精读）：')
    print('='*75)
    word_list = []
    for idx, w in enumerate(batch, 1):
        word = w.get('word', '')
        phonetic = w.get('phonetic', '')
        defs = w.get('definitions', [])
        def_str = '；'.join([f"{d.get('pos','')} {d.get('def','')}" for d in defs])
        print(f'{idx:2d}. {word:<16} {phonetic:<16} {def_str}')
        word_list.append(word)
    
    words_str = ', '.join(word_list)
    print('\n💡 建议指令（直接发送给我即可自动生成下一篇量身定制的小故事）：')
    print('> 请用以下四级高频词编一个情节紧凑有趣的英文短故事（约 180 词，四级阅读难度），并在文中加粗单词，附上中文对照与核心词汇表：')
    print(f'> {words_str}')

if __name__ == '__main__':
    main()
