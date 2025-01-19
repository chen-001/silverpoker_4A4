from typing import List, Tuple, Optional, Dict

class Card:
    RANKS: Dict[str, int] = {
        '大王': 17, '小王': 16, '3': 15, '2': 14, 'A': 13, 'K': 12, 'Q': 11, 'J': 10,
        '10': 9, '9': 8, '8': 7, '7': 6, '6': 5, '5': 4, '4': 3
    }
    
    def __init__(self, card_str: str) -> None:
        self.card_str = card_str
        if card_str in ['大王', '小王']:
            self.suit: Optional[str] = None
            self.rank: str = card_str
        else:
            self.suit: str = card_str[0]  # 花色
            self.rank: str = card_str[1:]  # 点数
            
    def get_value(self) -> int:
        return self.RANKS[self.rank]
        
    def __lt__(self, other: 'Card') -> bool:
        return self.get_value() < other.get_value()
        
    def __str__(self) -> str:
        return self.card_str

class CardPattern:
    PATTERN_INVALID = 'invalid'  # 无效
    PATTERN_SINGLE = 'single'  # 单张
    PATTERN_PAIR = 'pair'  # 对子
    PATTERN_TRIPLE = 'triple'  # 炮（三张相同）
    PATTERN_BOMB = 'bomb'  # 炸弹（四张相同）
    PATTERN_DRAGON = 'dragon'  # 龙（顺子）
    PATTERN_DOUBLE_DRAGON = 'double_dragon'  # 双龙（连对）
    PATTERN_ROCKET = 'rocket'  # 火箭（两张4和一张A）
    PATTERN_DOUBLE_JOKER = 'double_joker'  # 双王
    PATTERN_TRIPLE_JOKER = 'triple_joker'  # 三王
    PATTERN_FOUR_JOKER = 'four_joker'  # 四王
    PATTERN_BIG_TRIPLE = 'big_triple'  # 大炮（五张相同）
    PATTERN_BIG_BOMB = 'big_bomb'  # 大炸弹（六张相同）
    PATTERN_HUGE_TRIPLE = 'huge_triple'  # 巨炮（七张相同）
    PATTERN_HUGE_BOMB = 'huge_bomb'  # 巨炸弹（八张相同）
    
    @staticmethod
    def get_pattern(cards: List[str]) -> Tuple[Optional[str], int]:
        """获取牌型和大小"""
        if not cards:
            return None, 0
            
        # 对牌进行排序
        sorted_cards = sorted(cards, key=lambda x: (CardPattern.get_card_value(x), x))
        
        # 获取点数列表
        values = [card if '王' in card else card[1:] for card in sorted_cards]
        
        # 火箭（两张4和一张A）
        if len(cards) == 3:
            four_count = sum(1 for c in cards if c.endswith('4'))
            ace_count = sum(1 for c in cards if c.endswith('A'))
            if four_count == 2 and ace_count == 1:
                return CardPattern.PATTERN_ROCKET, 1500
        
        # 四王（四张王牌，不区分大小王）
        if len(cards) == 4 and all('王' in card for card in cards):
            return CardPattern.PATTERN_FOUR_JOKER, 1300
            
        # 巨炸弹（八张相同）
        if len(cards) == 8 and len(set(values)) == 1 and not any('王' in card for card in cards):
            return CardPattern.PATTERN_HUGE_BOMB, CardPattern.get_card_value(values[0]) + 1100
        
        # 巨炮（七张相同）
        if len(cards) == 7 and len(set(values)) == 1 and not any('王' in card for card in cards):
            return CardPattern.PATTERN_HUGE_TRIPLE, CardPattern.get_card_value(values[0]) + 900
                
        # 三王（三张王牌，不区分大小王）
        if len(cards) == 3 and all('王' in card for card in cards):
            return CardPattern.PATTERN_TRIPLE_JOKER, 800
        
        # 大炸弹（六张相同）
        if len(cards) == 6 and len(set(values)) == 1 and not any('王' in card for card in cards):
            return CardPattern.PATTERN_BIG_BOMB, CardPattern.get_card_value(values[0]) + 600
        
        # 大炮（五张相同）
        if len(cards) == 5 and len(set(values)) == 1 and not any('王' in card for card in cards):
            return CardPattern.PATTERN_BIG_TRIPLE, CardPattern.get_card_value(values[0]) + 500
            
        # 双王（两张王牌，不区分大小王）
        if len(cards) == 2 and all('王' in card for card in cards):
            return CardPattern.PATTERN_DOUBLE_JOKER, 400

        # 炸弹（四张相同）
        if len(cards) == 4 and len(set(values)) == 1 and not any('王' in card for card in cards):
            return CardPattern.PATTERN_BOMB, CardPattern.get_card_value(values[0]) + 300
            
        # 炮（三张相同）
        if len(cards) == 3 and len(set(values)) == 1 and not any('王' in card for card in cards):
            print(f'values: {values}, values[0]: {values[0]}, CardPattern.get_card_value(values[0]): {CardPattern.get_card_value(values[0])}')
            return CardPattern.PATTERN_TRIPLE, CardPattern.get_card_value(values[0]) + 200
            
        # 对子（两张相同）
        if len(cards) == 2 and len(set(values)) == 1 and not any('王' in card for card in cards):
            return CardPattern.PATTERN_PAIR, CardPattern.get_card_value(values[0])
            
        # 单张
        if len(cards) == 1:
            return CardPattern.PATTERN_SINGLE, CardPattern.get_card_value(values[0])
            
        # 龙（顺子）
        if len(cards) >= 3 and not any('王' in card for card in cards):
            values = [CardPattern.get_card_value(card) for card in cards]
            values.sort()
            is_consecutive = all(values[i] + 1 == values[i + 1] for i in range(len(values) - 1))
            if is_consecutive:
                return CardPattern.PATTERN_DRAGON, max(values)
                
        # 双龙（连对）
        if len(cards) >= 6 and len(cards) % 2 == 0 and not any('王' in card for card in cards):
            values = [CardPattern.get_card_value(card) for card in cards]
            value_counts = {}
            for v in values:
                value_counts[v] = value_counts.get(v, 0) + 1
            if all(count == 2 for count in value_counts.values()):
                unique_values = sorted(value_counts.keys())
                is_consecutive = all(unique_values[i] + 1 == unique_values[i + 1] 
                                  for i in range(len(unique_values) - 1))
                if is_consecutive:
                    return CardPattern.PATTERN_DOUBLE_DRAGON, max(values)
                    
        return CardPattern.PATTERN_INVALID, 0
        
    @staticmethod
    def get_card_value(card: str) -> int:
        """获取牌的大小值"""
        if '王' in card:
            print(f'hahaha card: {card}')
            return 17 if card == '大王' else 16
        if len(card) == 2 and card!='10':
            value = card[1:]  # 去掉花色
        elif '10' in card:
            value = '10'
        else:
            value = card
        value_map = {
            '4': 3, '5': 4, '6': 5, '7': 6, '8': 7, '9': 8,
            '10': 9, 'J': 10, 'Q': 11, 'K': 12, 'A': 13, '2': 14, '3': 15
        }
        return value_map.get(str(value), 0)

    @staticmethod
    def can_beat(new_cards: List[str], last_cards: List[str]) -> bool:
        """判断新出的牌是否能打过上一手牌"""
        if not last_cards:
            return True
            
        new_pattern, new_value = CardPattern.get_pattern(new_cards)
        last_pattern, last_value = CardPattern.get_pattern(last_cards)
        print(f"new_pattern: {new_pattern}, new_value: {new_value}, last_pattern: {last_pattern}, last_value: {last_value}")
        
        if not new_pattern or new_pattern == CardPattern.PATTERN_INVALID:
            return False
            
        # 火箭不能打火箭
        if new_pattern == CardPattern.PATTERN_ROCKET:
            if last_pattern == CardPattern.PATTERN_ROCKET:
                new_suit=[card[0] for card in new_cards]
                last_suit=[card[0] for card in last_cards]
                if len(list(set(new_suit)))>1:
                    return False
                if len(list(set(last_suit)))>1 and len(list(set(new_suit)))==1:
                    return True
                if len(list(set(last_suit)))==1 and len(list(set(new_suit)))==1:
                    if new_suit=='♣️':
                        return False
                    if new_suit=='♠️' and last_suit=='♣️':
                        return True
                    if new_suit=='♦️' and last_suit in ['♠️','♣️']:
                        return True
                    if new_suit=='♥️' and last_suit in ['♠️','♦️','♣️']:
                        return True
                    return False
            return True
        
        # 四王可以打任何非火箭牌型
        if new_pattern == CardPattern.PATTERN_FOUR_JOKER:
            if last_pattern in CardPattern.PATTERN_ROCKET:
                return False
            return True
            
        # 巨炸弹可以打任何非火箭牌型
        if new_pattern == CardPattern.PATTERN_HUGE_BOMB:
            if last_pattern in [CardPattern.PATTERN_ROCKET, CardPattern.PATTERN_FOUR_JOKER]:
                return False
            if last_pattern == CardPattern.PATTERN_HUGE_BOMB:
                return new_value > last_value
            return True
            
        # 巨炮可以打任何非火箭、非四王、非巨炸弹牌型
        if new_pattern == CardPattern.PATTERN_HUGE_TRIPLE:
            if last_pattern in [CardPattern.PATTERN_ROCKET, CardPattern.PATTERN_FOUR_JOKER, CardPattern.PATTERN_HUGE_BOMB]:
                return False
            if last_pattern == CardPattern.PATTERN_HUGE_TRIPLE:
                return new_value > last_value
            return True
            
        # 三王可以打任何非火箭、非四王、非巨炸弹、非巨炮牌型
        if new_pattern == CardPattern.PATTERN_TRIPLE_JOKER:
            if last_pattern in [CardPattern.PATTERN_ROCKET, CardPattern.PATTERN_FOUR_JOKER, CardPattern.PATTERN_HUGE_BOMB,
                              CardPattern.PATTERN_HUGE_TRIPLE]:
                return False
            return True
            
        # 大炸弹可以打任何非火箭、非四王、非巨炸弹、非巨炮、非三王牌型
        if new_pattern == CardPattern.PATTERN_BIG_BOMB:
            if last_pattern in [CardPattern.PATTERN_ROCKET, CardPattern.PATTERN_FOUR_JOKER, CardPattern.PATTERN_HUGE_BOMB,
                              CardPattern.PATTERN_HUGE_TRIPLE, CardPattern.PATTERN_TRIPLE_JOKER]:
                return False
            if last_pattern == CardPattern.PATTERN_BIG_BOMB:
                return new_value > last_value
            return True
            
        # 大炮可以打任何非火箭、非四王、非巨炸弹、非巨炮、非三王、非大炸弹牌型
        if new_pattern == CardPattern.PATTERN_BIG_TRIPLE:
            if last_pattern in [CardPattern.PATTERN_ROCKET, CardPattern.PATTERN_FOUR_JOKER, CardPattern.PATTERN_HUGE_BOMB,
                              CardPattern.PATTERN_HUGE_TRIPLE, CardPattern.PATTERN_TRIPLE_JOKER,
                              CardPattern.PATTERN_BIG_BOMB]:
                return False
            if last_pattern == CardPattern.PATTERN_BIG_TRIPLE:
                return new_value > last_value
            return True
            
        # 双王可以打任何非火箭、非四王、非巨炸弹、非巨炮、非三王、非大炸弹、非大炮牌型
        if new_pattern == CardPattern.PATTERN_DOUBLE_JOKER:
            if last_pattern in [CardPattern.PATTERN_ROCKET, CardPattern.PATTERN_FOUR_JOKER, CardPattern.PATTERN_HUGE_BOMB,
                              CardPattern.PATTERN_HUGE_TRIPLE, CardPattern.PATTERN_TRIPLE_JOKER,
                              CardPattern.PATTERN_BIG_BOMB, CardPattern.PATTERN_BIG_TRIPLE]:
                return False
            return True
            
        # 炸弹可以打任何非特殊牌型
        if new_pattern == CardPattern.PATTERN_BOMB:
            if last_pattern in [CardPattern.PATTERN_ROCKET, CardPattern.PATTERN_FOUR_JOKER, CardPattern.PATTERN_HUGE_BOMB,
                              CardPattern.PATTERN_HUGE_TRIPLE, CardPattern.PATTERN_TRIPLE_JOKER,
                              CardPattern.PATTERN_BIG_BOMB, CardPattern.PATTERN_BIG_TRIPLE,
                              CardPattern.PATTERN_DOUBLE_JOKER]:
                return False
            if last_pattern == CardPattern.PATTERN_BOMB:
                return new_value > last_value
            return True
            
        # 炮可以打单张、对子、龙（但不能打双龙）
        if new_pattern == CardPattern.PATTERN_TRIPLE:
            if last_pattern in [CardPattern.PATTERN_ROCKET, CardPattern.PATTERN_FOUR_JOKER, CardPattern.PATTERN_HUGE_BOMB,
                              CardPattern.PATTERN_HUGE_TRIPLE, CardPattern.PATTERN_TRIPLE_JOKER,
                              CardPattern.PATTERN_BIG_BOMB, CardPattern.PATTERN_BIG_TRIPLE,
                              CardPattern.PATTERN_DOUBLE_JOKER, CardPattern.PATTERN_BOMB,
                              CardPattern.PATTERN_DOUBLE_DRAGON]:  # 不能打双龙
                return False
            if last_pattern == CardPattern.PATTERN_TRIPLE:
                return new_value > last_value
            # if last_pattern in [CardPattern.PATTERN_SINGLE, CardPattern.PATTERN_PAIR,
            #                   CardPattern.PATTERN_DRAGON]:  # 可以打单张、对子、龙
            #     return True
            return True
            
        # 双龙不能打炮，只能打同类型
        if new_pattern == CardPattern.PATTERN_DOUBLE_DRAGON:
            # if last_pattern == CardPattern.PATTERN_TRIPLE:  # 不能打炮
            #     return False
            if last_pattern == CardPattern.PATTERN_DOUBLE_DRAGON:
                return (new_value > last_value) and (len(new_cards) == len(last_cards))
            return False
            
        # 龙可以打单张、对子，但不能打炮
        if new_pattern == CardPattern.PATTERN_DRAGON:
            # if last_pattern == CardPattern.PATTERN_TRIPLE:  # 不能打炮
            #     return False
            if last_pattern == CardPattern.PATTERN_DRAGON:
                return new_value > last_value and len(new_cards) == len(last_cards)
            # if last_pattern in [CardPattern.PATTERN_SINGLE, CardPattern.PATTERN_PAIR]:
            #     return True
            return False
            
        # 对子可以打单张
        if new_pattern == CardPattern.PATTERN_PAIR:
            if last_pattern == CardPattern.PATTERN_PAIR:
                return new_value > last_value
            # if last_pattern == CardPattern.PATTERN_SINGLE:
            #     return True
            return False
            
        # 单张只能打单张
        if new_pattern == CardPattern.PATTERN_SINGLE:
            if last_pattern == CardPattern.PATTERN_SINGLE:
                return new_value > last_value
            return False
            
        return False
        
    @staticmethod
    def can_fork(card: str, player_cards: List[str]) -> bool:
        """检查玩家是否可以叉牌"""
        if not card:
            return False
        value = card[1:]
        # 统计玩家手牌中相同点数的牌数量
        count = sum(1 for c in player_cards if c[1:] == value)
        return count >= 2
        
    @staticmethod
    def can_hook(card: str, player_cards: List[str]) -> bool:
        """检查玩家是否可以勾牌"""
        if not card:
            return False
        value = card[1:]
        return any(c[1:] == value for c in player_cards)
        
    @staticmethod
    def sort_cards(cards: List[str]) -> List[str]:
        """对牌进行排序"""
        return sorted(cards, key=lambda x: (CardPattern.get_card_value(x), x))


