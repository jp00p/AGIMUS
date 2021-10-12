from treys import Card, Evaluator, Deck

evaluator = Evaluator()
deck = Deck()

hand = deck.draw(5)
print(Card.print_pretty_cards(hand))
hand[1] = deck.draw(1)
print(Card.print_pretty_cards(hand))
score = evaluator.evaluate(hand, [])
p1_class = evaluator.get_rank_class(score)
print(evaluator.class_to_string(p1_class))