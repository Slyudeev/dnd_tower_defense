class PlayerProfile:
    def __init__(self):
        self.total_souls = 150 
        self.perks = {
            "blessed_dice": True, 
            "unlocked_mage": False
        }

    def get_stat_bonus(self):
        return 2 if self.perks.get("blessed_dice") else 0

profile = PlayerProfile()