import tornado.ioloop
import tornado.web
import tornado.websocket
import json
from collections import defaultdict
import random
from typing import List, Dict, Optional, Tuple, Any, Set
from card_rules import CardPattern, Card

class GameRoom:
    def __init__(self, deck_count: int = 1) -> None:
        self.players: List[tornado.websocket.WebSocketHandler] = []  # 玩家列表
        self.current_player: Optional[tornado.websocket.WebSocketHandler] = None  # 当前玩家
        self.cards: List[str] = []  # 牌堆
        self.player_cards: Dict[tornado.websocket.WebSocketHandler, List[str]] = defaultdict(list)  # 玩家手牌
        self.game_started: bool = False
        self.last_cards: List[str] = []  # 上一次出的牌
        self.last_player: Optional[tornado.websocket.WebSocketHandler] = None  # 上一个出牌的玩家
        self.fork_enabled: bool = False  # 是否可以叉牌
        self.hook_enabled: bool = False  # 是否可以勾牌
        self.current_card: Optional[str] = None  # 当前可以叉或勾的牌
        self.hook_player: Optional[tornado.websocket.WebSocketHandler] = None  # 勾牌的玩家
        self.waiting_for_fork: bool = False  # 是否在等待叉牌
        self.waiting_for_hook: bool = False  # 是否在等待勾牌
        self.passed_players: List[tornado.websocket.WebSocketHandler] = []  # 已经过牌的玩家
        self.fork_player: Optional[tornado.websocket.WebSocketHandler] = None  # 叉牌的玩家
        self.deck_count: int = deck_count  # 牌组数量
        self.scores: Dict[tornado.websocket.WebSocketHandler, int] = defaultdict(int)  # 玩家分数
        self.finished_order: List[tornado.websocket.WebSocketHandler] = []  # 完成顺序
        self.player_names: Dict[tornado.websocket.WebSocketHandler, str] = {}  # 玩家名称
        self.is_giving_light: bool = False  # 是否处于给光状态
        self.last_empty_player: Optional[tornado.websocket.WebSocketHandler] = None  # 最后一个出完牌的玩家
        
    def add_player(self, player: tornado.websocket.WebSocketHandler) -> bool:
        if len(self.players) < 6 and not self.game_started:
            self.players.append(player)
            # 设置默认名称
            self.player_names[player] = f"玩家{len(self.players)}"
            return True
        return False
        
    def set_player_name(self, player: tornado.websocket.WebSocketHandler, name: str) -> bool:
        """设置玩家名称"""
        if player in self.players and len(name.strip()) > 0:
            self.player_names[player] = name.strip()
            return True
        return False
        
    def remove_player(self, player: tornado.websocket.WebSocketHandler) -> None:
        if player in self.players:
            self.players.remove(player)
            
    def start_game(self) -> bool:
        if len(self.players) >= 2:
            # 重置游戏状态
            self.current_player = None
            self.cards = []
            self.player_cards = defaultdict(list)
            self.last_cards = []
            self.last_player = None
            self.fork_enabled = False
            self.hook_enabled = False
            self.current_card = None
            self.hook_player = None
            self.waiting_for_fork = False
            self.waiting_for_hook = False
            self.passed_players = []
            self.fork_player = None
            self.is_giving_light = False
            self.last_empty_player = None
            self.finished_order = []

            # 先广播致谢消息给所有玩家
            for player in self.players:
                player.write_message({
                    'action': 'show_thanks',
                    'message': '六六让我致谢：感谢银姐及其爱人帮助测试bug 银姐祝各位玩家牌运🤙🤙🤙'
                })
            
            self.game_started = True
            self.init_cards()
            self.deal_cards()
            # 找到有红心4的玩家作为首家
            for player in self.players:
                if '♥4' in self.player_cards[player]:
                    self.current_player = player
                    break
            return True
        return False
            
    def init_cards(self) -> None:
        """初始化牌组"""
        # 初始化一副或两副牌
        all_cards = []
        for _ in range(self.deck_count):
            # 生成一副牌
            deck = []
            # 生成普通牌
            for suit in ['♠', '♥', '♣', '♦']:
                for rank in ['3', '2', 'A', 'K', 'Q', 'J', '10', '9', '8', '7', '6', '5', '4']:
                    deck.append(suit + rank)
            # 添加大小王
            deck.extend(['大王', '小王'])
            all_cards.extend(deck)
            
        # 洗牌
        random.shuffle(all_cards)
        self.cards = all_cards
        print(f"初始化了 {len(self.cards)} 张牌")
        
    def deal_cards(self) -> None:
        """发牌"""
        num_players = len(self.players)
        total_cards = len(self.cards)
        base_cards = total_cards // num_players  # 每人基础牌数
        remaining_cards = total_cards % num_players  # 余牌数量
        
        current_pos = 0  # 当前发牌位置
        for i, player in enumerate(self.players):
            # 计算这个玩家应得的牌数
            cards_for_this_player = base_cards + (1 if i < remaining_cards else 0)
            # 从当前位置取相应数量的牌
            self.player_cards[player] = self.cards[current_pos:current_pos + cards_for_this_player]
            current_pos += cards_for_this_player
            # 对玩家手牌排序
            self.player_cards[player] = [str(c) for c in CardPattern.sort_cards(self.player_cards[player])]
            
            # 识别所有火箭组合（两个4和一个A）
            all_rockets = []  # 存储所有找到的火箭组合
            fours = [card for card in self.player_cards[player] if card.endswith('4')]
            aces = [card for card in self.player_cards[player] if card.endswith('A')]
            
            # 尽可能多地组合火箭
            while len(fours) >= 2 and len(aces) >= 1:
                # 取出两个4和一个A组成火箭
                rocket_cards = fours[:2] + [aces[0]]
                all_rockets.append(rocket_cards)
                # 从剩余牌中移除已使用的牌
                fours = fours[2:]
                aces = aces[1:]
            
            if all_rockets:  # 如果找到了火箭
                # 从原手牌中移除所有火箭牌
                for rocket in all_rockets:
                    for card in rocket:
                        self.player_cards[player].remove(card)
                
                # 找到大王的位置（如果有的话）
                joker_index = -1
                for i, card in enumerate(self.player_cards[player]):
                    if card in ['大王', '小王']:
                        joker_index = i
                        # break
                
                # 将所有火箭牌按顺序插入到大王后面或列表末尾
                insert_pos = joker_index + 1 if joker_index != -1 else len(self.player_cards[player])
                for rocket in all_rockets:
                    self.player_cards[player][insert_pos:insert_pos] = rocket
                    insert_pos += 3  # 每个火箭有3张牌
            
    def play_cards(self, player: tornado.websocket.WebSocketHandler, cards: List[str]) -> Tuple[bool, str]:
        """玩家出牌"""
        print(f'play_cards: {player}, {cards}')
        if not self.game_started:
            return False, "游戏还没开始"
            
        # 如果正在等待叉牌或勾牌，允许符合条件的玩家操作
        if self.fork_enabled or self.waiting_for_hook:
            # 处理叉牌
            if self.fork_enabled and len(cards) == 2:
                # 叉牌时不检查是否轮到该玩家
                if player == self.current_player:
                    return False, "当前玩家不能叉自己的牌"
                if not (cards[0][1:] == cards[1][1:] == self.current_card[1:]):
                    return False, "叉牌必须是相同点数的对子"
                self.fork_enabled = False
                self.hook_enabled = True  # 叉牌后允许其他玩家勾牌
                self.waiting_for_hook = True  # 等待其他玩家勾牌
                self.current_card = cards[0]
                self.fork_player = player
                self.hook_player = None  # 清空勾牌玩家
                for card in cards:
                    self.player_cards[player].remove(card)
                self.passed_players.clear()  # 清空过牌记录
                return True, "叉牌成功，等待其他玩家勾牌"
            
            # 处理勾牌
            if self.hook_enabled and len(cards) == 1:
                # 勾牌时允许原始出牌玩家和其他玩家（除叉牌玩家）勾牌
                if player == self.fork_player:
                    return False, "叉牌玩家不能勾牌"
                if cards[0][1:] != self.current_card[1:]:
                    return False, "勾牌必须是相同点数"
                self.hook_enabled = False
                self.waiting_for_hook = False
                self.current_card = cards[0]
                self.hook_player = player
                self.player_cards[player].remove(cards[0])
                self.passed_players.clear()  # 清空过牌记录
                
                # 如果是2副牌，勾牌后可以继续叉牌
                if self.deck_count == 2:
                    # 检查是否有玩家可以叉牌
                    can_fork = False
                    for p in self.players:
                        if p != player and len(self.player_cards[p]) > 0 and self.can_fork(cards[0], self.player_cards[p]):
                            can_fork = True
                            break
                    
                    if can_fork:
                        self.fork_enabled = True
                        self.current_card = cards[0]  # 设置当前可以叉的牌
                        return True, "勾牌成功，等待其他玩家叉牌"
                    
                # 如果没有人可以叉牌，或者是1副牌，勾牌的玩家成为最大
                self.fork_enabled = False  # 确保关闭叉牌状态
                self.last_cards = []  # 清空上一手牌，允许出任意牌
                self.last_player = player  # 勾牌的玩家成为最大
                self.current_player = player  # 轮到勾牌玩家出牌
                self.current_card = None
                self.hook_player = None  # 清空勾牌玩家
                return True, "勾牌成功，现在可以出任意牌"
                
            # 在等待叉牌或勾牌时，不允许其他出牌操作
            return False, "当前只能叉牌或勾牌"
            
        # 普通出牌时检查是否轮到该玩家
        if player != self.current_player:
            return False, "还没有轮到你出牌"
            
        if not cards:
            return False, "请选择要出的牌"
            
        # 检查玩家是否有这些牌
        if not all(card in self.player_cards[player] for card in cards):
            return False, "你没有这些牌"
            
        # 如果是新的一轮（没有上一手牌），或者是上一个出牌的玩家，清空过牌记录
        if not self.last_cards or player == self.last_player:
            self.passed_players.clear()
            
        # 检查出牌是否符合规则
        print(f"last_cards: {self.last_cards}, cards: {cards}")
        
        # 在给光状态下，不需要检查是否能打过上一手牌
        if not self.is_giving_light:
            pattern = CardPattern.get_pattern(cards)
            if pattern[0] == CardPattern.PATTERN_INVALID:
                return False, "出牌不符合规则"
            
            if not CardPattern.can_beat(cards, self.last_cards):
                return False, "出牌不符合规则"
            
        # 出牌符合规则，先移除这些牌
        for card in cards:
            self.player_cards[player].remove(card)
            
        # 出牌成功时，如果玩家在passed_players中，将其移除
        if player in self.passed_players:
            self.passed_players.remove(player)
            
        # 更新游戏状态
        self.last_cards = cards
        self.last_player = player
        
        # 检查是否可以叉牌（只有出单张时才能叉牌）
        if len(cards) == 1:
            can_fork = False
            # 检查其他玩家是否可以叉牌
            for p in self.players:
                if p != player and len(self.player_cards[p]) > 0 and self.can_fork(cards[0], self.player_cards[p]):
                    can_fork = True
                    break
                    
            if can_fork:
                self.fork_enabled = True
                self.current_card = cards[0]
                self.is_giving_light = False  # 一旦有人出牌且可以被叉，给光状态就结束
                return True, "出牌成功，等待其他玩家叉牌"
            
        # 检查玩家是否已经出完牌（移到这里，确保在叉牌检查之后）
        if not self.player_cards[player]:
            # 记录完成顺序
            if player not in self.finished_order:
                self.finished_order.append(player)
                self.last_empty_player = player  # 记录最后一个出完牌的玩家
            
            # 检查是否只剩最后一个玩家有牌
            players_with_cards = [p for p in self.players if len(self.player_cards[p]) > 0]
            if len(players_with_cards) <= 1:
                # 如果最后一个玩家也出完了牌，确保他也被加入到完成顺序中
                if len(players_with_cards) == 0:
                    last_player = [p for p in self.players if p not in self.finished_order][0]
                    if last_player not in self.finished_order:
                        self.finished_order.append(last_player)
                return True, "游戏结束，玩家胜利！"
            
            # 如果没有人可以叉牌，轮到下一个玩家
            self.next_player()
            # 给光状态在玩家出牌后就结束
            if self.is_giving_light:
                self.is_giving_light = False
                return True, "出牌成功"
            return True, "出牌成功"
            
        # 如果没有人可以叉牌，轮到下一个玩家
        self.next_player()
        return True, "出牌成功"

    def can_fork(self, card: str, player_cards: List[str]) -> bool:
        """检查玩家是否可以叉牌"""
        # 统计玩家手牌中相同点数的牌的数量
        count = sum(1 for c in player_cards if c[1:] == card[1:])
        return count >= 2  # 需要至少两张相同点数的牌才能叉
        
    def pass_turn(self, player: tornado.websocket.WebSocketHandler) -> Tuple[bool, str]:
        """玩家选择过牌"""
        # 如果是等待叉牌或勾牌的状态
        if self.fork_enabled or self.waiting_for_hook:
            # 在叉勾阶段，过牌只是表示放弃叉勾的权利，不会立即轮到下家
            if player not in self.passed_players:
                self.passed_players.append(player)
                
                # 检查是否所有其他玩家都放弃了叉勾的权利
                other_players = [p for p in self.players if p != self.current_player]
                if self.fork_enabled:
                    # 自动将无牌可叉或没有手牌的玩家加入过牌列表
                    for p in other_players:
                        if p not in self.passed_players and (
                            len(self.player_cards[p]) == 0 or  # 没有手牌
                            not self.can_fork(self.current_card, self.player_cards[p])  # 无牌可叉
                        ):
                            self.passed_players.append(p)
                    
                    # 在叉牌阶段，只有所有其他玩家都放弃叉牌权利时，才进入下一阶段
                    # 只考虑还有手牌的玩家
                    active_players = [p for p in other_players if len(self.player_cards[p]) > 0]
                    all_passed = all(p in self.passed_players for p in active_players)
                    if all_passed:
                        # 所有玩家都放弃叉牌，结束叉牌阶段
                        self.fork_enabled = False
                        self.current_card = None
                        self.next_player()
                        self.passed_players.clear()
                        # 如果之前是给光状态，恢复给光状态
                        if self.is_giving_light:
                            return True, "给光状态：可以自由出牌"
                else:  # waiting_for_hook
                    # 在勾牌阶段，除了叉牌玩家外的所有玩家都需要表态
                    other_players = [p for p in other_players if p != self.fork_player and len(self.player_cards[p]) > 0]
                    all_passed = all(p in self.passed_players for p in other_players)
                    if all_passed:
                        # 所有玩家都放弃勾牌，轮到叉牌玩家出牌
                        self.waiting_for_hook = False
                        self.hook_enabled = False
                        self.current_player = self.fork_player
                        self.last_cards = []  # 清空上一手牌，允许出任意牌
                        self.hook_player = None  # 清空勾牌玩家
                        self.passed_players.clear()
            # 叉勾阶段的过牌不会立即轮到下家，只是记录放弃权利
            return True, "放弃叉勾权利"
            
        # 普通过牌阶段
        if player != self.current_player:
            return False, "还没有轮到你出牌"
            
        if not self.last_cards:
            return False, "第一手牌不能过"
            
        # 记录过牌并立即轮到下家
        if player not in self.passed_players:
            self.passed_players.append(player)
            
        # 普通过牌立即轮到下家
        self.next_player()
        
        # 检查是否进入给光状态
        if self.last_empty_player:
            # 获取还有手牌的玩家
            players_with_cards = [p for p in self.players if len(self.player_cards[p]) > 0]
            # 如果只剩最后一个玩家有牌，不进入给光状态
            if len(players_with_cards) == 1:
                # 直接结束游戏
                return True, "游戏结束"
            
            other_players = [p for p in self.players if p != self.last_empty_player and len(self.player_cards[p]) > 0]
            if all(p in self.passed_players for p in other_players):
                # 进入给光状态
                self.is_giving_light = True
                self.last_cards = []  # 清空上一手牌，允许自由出牌
                self.passed_players.clear()
                self.last_empty_player = None  # 清空最后出完牌的玩家，避免重复进入给光状态
                return True, "给光状态：可以自由出牌"
        
        # 如果所有其他玩家都过牌了，轮到最后出牌的玩家
        other_players = [p for p in self.players if p != self.last_player]
        if all(p in self.passed_players for p in other_players):
            self.current_player = self.last_player
            self.last_cards = []  # 清空上一手牌，允许出任意牌
            self.passed_players.clear()
            
        return True, "过牌成功"
        
    def next_player(self) -> None:
        """轮到下一个玩家"""
        current_index = self.players.index(self.current_player)
        next_index = current_index
        
        # 找到下一个还有牌的玩家
        while True:
            next_index = (next_index + 1) % len(self.players)
            # 如果转了一圈回到当前玩家，说明一轮结束了
            if next_index == current_index:
                self.passed_players.clear()
                self.last_cards = []
                break
            # 如果找到一个还有牌的玩家，就选择他
            if len(self.player_cards[self.players[next_index]]) > 0:
                self.current_player = self.players[next_index]
                break
            # 如果这个玩家已经出完牌了，自动将他加入过牌列表
            if self.players[next_index] not in self.passed_players:
                self.passed_players.append(self.players[next_index])
        
        # 如果下一个玩家就是上一个出牌的玩家，说明一轮结束了，清空过牌记录和上一手牌
        if self.current_player == self.last_player:
            self.passed_players.clear()
            self.last_cards = []
            
    def check_game_over(self) -> Tuple[bool, Optional[List[tornado.websocket.WebSocketHandler]]]:
        """检查游戏是否结束"""
        # 统计还有手牌的玩家
        players_with_cards = [p for p in self.players if len(self.player_cards[p]) > 0]
        # 如果只剩一个玩家有牌，或者只剩最后一个玩家有牌，游戏结束
        if len(players_with_cards) <= 1:
            # 找到失败者（最后一个还有牌的玩家）
            # 如果没有玩家有牌，说明是最后一个玩家刚刚出完，从finished_order中找出最后一个玩家
            if not players_with_cards:
                loser = self.finished_order[-1]
            else:
                loser = players_with_cards[0]
            
            # 扣分：剩余手牌数（如果是刚出完的玩家，扣0分）
            self.scores[loser] -= len(self.player_cards[loser])
            
            # 加分：按照完成顺序
            n = len(self.players)
            for i, player in enumerate(self.finished_order):
                self.scores[player] += (n - i - 1)
            
            # 标记游戏结束，但保留状态
            self.game_started = False
            
            return True, [p for p in self.players if p != loser]
        return False, None

    def broadcast_game_state(self) -> None:
        """广播游戏状态给所有玩家"""
        for player in self.players:
            # 构建上一手牌的显示信息
            last_cards_info = None
            if self.last_cards:
                last_player_name = self.player_names[self.last_player] if self.last_player else None
                last_cards_info = {
                    'cards': self.last_cards,
                    'player_name': last_player_name
                }
            
            # 构建叉牌信息
            fork_info = None
            if self.fork_player and not self.hook_player and not self.waiting_for_hook:
                fork_info = {
                    'cards': [self.current_card] * 2,
                    'player_name': self.player_names[self.fork_player]
                }
            
            # 构建勾牌信息
            hook_info = None
            if self.hook_player and not self.waiting_for_hook:
                hook_info = {
                    'cards': [self.current_card],
                    'player_name': self.player_names[self.hook_player]
                }
            
            player.write_message({
                'action': 'game_state',
                'cards': self.player_cards[player],
                'current_player': player == self.current_player,
                'last_cards': last_cards_info,
                'fork_info': fork_info,
                'hook_info': hook_info,
                'last_player': self.players.index(self.last_player) if self.last_player else None,
                'last_player_name': self.player_names[self.last_player] if self.last_player else None,
                'player_card_counts': {self.players.index(p): len(self.player_cards[p]) for p in self.players},
                'can_fork': self.fork_enabled and CardPattern.can_fork(self.current_card, self.player_cards[player]) if self.current_card else False,
                'can_hook': self.hook_enabled and CardPattern.can_hook(self.current_card, self.player_cards[player]) if self.current_card else False,
                'waiting_for_hook': self.waiting_for_hook,
                'passed_players': [self.players.index(p) for p in self.passed_players],
                'player_number': self.players.index(player),
                'scores': {self.players.index(p): self.scores[p] for p in self.players},
                'player_names': {self.players.index(p): self.player_names[p] for p in self.players},
                'can_pass': True,  # 始终允许玩家选择过牌
                'fork_player': self.players.index(self.fork_player) if self.fork_player else None,
                'hook_player': self.players.index(self.hook_player) if self.hook_player else None,
                'is_giving_light': self.is_giving_light  # 添加给光状态
            })

    def handle_pass(self, player: tornado.websocket.WebSocketHandler) -> Tuple[bool, str]:
        """处理玩家过牌"""
        success, message = self.pass_turn(player)
        if success:
            # 广播游戏状态
            self.broadcast_game_state()
        return success, message

class GameHandler(tornado.websocket.WebSocketHandler):
    rooms: Dict[str, GameRoom] = {}  # 所有游戏房间
    
    def check_origin(self, origin: str) -> bool:
        return True
        
    def open(self) -> None:
        print("新玩家连接")
        
    def on_message(self, message: str) -> None:
        print(f"收到消息: {message}")
        try:
            data = json.loads(message)
            action = data.get('action')
            
            if action == 'create_room':
                deck_count = int(data.get('deck_count', 1))  # 确保转换为整数
                room_id = str(random.randint(1000, 9999))
                self.rooms[room_id] = GameRoom(deck_count)
                self.write_message({'action': 'room_created', 'room_id': room_id})
                print(f"创建房间成功: {room_id}")
                
            elif action == 'join_room':
                room_id = data.get('room_id')
                print(f"尝试加入房间: {room_id}")
                if room_id in self.rooms:
                    room = self.rooms[room_id]
                    if room.add_player(self):
                        self.current_room = room_id
                        print(f"玩家成功加入房间 {room_id}, 当前玩家数: {len(room.players)}")
                        self.write_message({'action': 'joined_room', 'success': True})
                        self.broadcast_room_state(room)
                    else:
                        print(f"加入房间失败: 房间已满或游戏已开始")
                        self.write_message({'action': 'joined_room', 'success': False, 'message': '房间已满或游戏已开始'})
                else:
                    print(f"加入房间失败: 房间 {room_id} 不存在")
                    self.write_message({'action': 'joined_room', 'success': False, 'message': '房间不存在'})
                    
            elif action == 'start_game':
                if hasattr(self, 'current_room'):
                    room = self.rooms[self.current_room]
                    if room.start_game():
                        self.broadcast_game_state(room)
                    else:
                        self.write_message({'action': 'error', 'message': '玩家数量不足'})
                        
            elif action == 'play_cards':
                if hasattr(self, 'current_room'):
                    room = self.rooms[self.current_room]
                    success, message = room.play_cards(self, data.get('cards', []))
                    if success:
                        # 先检查游戏是否结束
                        self.broadcast_game_state(room)
                        game_over, winners = room.check_game_over()
                        print(f"game_over: {game_over}, winners: {winners}")
                        if game_over:
                            # 先广播游戏结束消息
                            self.broadcast_game_over(room, winners)
                            # 然后再广播最终的游戏状态
                            self.broadcast_game_state(room)
                        else:
                            # 如果游戏没有结束，只广播当前状态
                            self.broadcast_game_state(room)
                    else:
                        self.write_message({'action': 'error', 'message': message})
                        
            elif action == 'pass':
                if hasattr(self, 'current_room'):
                    room = self.rooms[self.current_room]
                    success, message = room.handle_pass(self)
                    if success:
                        self.broadcast_game_state(room)
                    else:
                        self.write_message({'action': 'error', 'message': message})
                        
            elif action == 'change_name':
                if hasattr(self, 'current_room'):
                    room = self.rooms[self.current_room]
                    new_name = data.get('name', '').strip()
                    if room.set_player_name(self, new_name):
                        self.broadcast_game_state(room)
                    else:
                        self.write_message({'action': 'error', 'message': '修改名称失败'})
                        
            elif action == 'throw_brick':
                if hasattr(self, 'current_room'):
                    room = self.rooms[self.current_room]
                    from_player = data.get('from_player')
                    to_player = data.get('to_player')
                    # 广播扔砖头事件给房间内所有玩家
                    for player in room.players:
                        player.write_message({
                            'action': 'throw_brick',
                            'from_player': from_player,
                            'to_player': to_player
                        })
                        
            elif action == 'show_fire':
                if hasattr(self, 'current_room'):
                    room = self.rooms[self.current_room]
                    player_index = data.get('player_index')
                    # 广播火焰特效事件给房间内所有玩家
                    for player in room.players:
                        player.write_message({
                            'action': 'show_fire',
                            'player_index': player_index
                        })
                        
        except Exception as e:
            # print(f"处理消息出错: {e}")
            # self.write_message({'action': 'error', 'message': '服务器内部错误'})
            raise
            
    def broadcast_room_state(self, room: GameRoom) -> None:
        """广播房间状态"""
        for player in room.players:
            player.write_message({
                'action': 'room_state',
                'player_count': len(room.players)
            })
            
    def broadcast_game_state(self, room: GameRoom) -> None:
        """广播游戏状态"""
        room.broadcast_game_state()
        
    def broadcast_game_over(self, room: GameRoom, winners: List[tornado.websocket.WebSocketHandler]) -> None:
        """广播游戏结束"""
        loser = [p for p in room.players if p not in winners][0]
        for player in room.players:
            player.write_message({
                'action': 'game_over',
                'winners': [room.players.index(p) for p in winners],
                'loser': room.players.index(loser),
                'scores': {
                    'winners': [(room.players.index(p), room.scores[p], len(room.players) - room.finished_order.index(p) - 1) for p in winners],
                    'loser': (room.players.index(loser), room.scores[loser], -len(room.player_cards[loser]))
                },
                'player_names': {room.players.index(p): room.player_names[p] for p in room.players}
            })
            
    def on_close(self) -> None:
        if hasattr(self, 'current_room'):
            room = self.rooms[self.current_room]
            room.remove_player(self)
            if len(room.players) == 0:
                del self.rooms[self.current_room]
            else:
                self.broadcast_room_state(room)

class MainHandler(tornado.web.RequestHandler):
    def get(self) -> None:
        self.render("index.html")

def make_app() -> tornado.web.Application:
    return tornado.web.Application([
        (r"/", MainHandler),
        (r"/game", GameHandler),
    ],
    template_path="templates",
    static_path="static"
    )

if __name__ == "__main__":
    app = make_app()
    app.listen(address='0.0.0.0', port=8888)
    print("服务器启动在 http://localhost:8888")
    tornado.ioloop.IOLoop.current().start()
