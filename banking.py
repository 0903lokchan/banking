# Write your code here
import random
import sqlite3
from typing import Union

IIN = "400000"


class App:
    def __init__(self, db_file: str):
        super().__init__()
        self.db_conn = None
        self.current_user = None
        self.ui = UI(self)

        self.init_db(db_file)
        self.create_tables()

    def run(self):
        self.ui.main_menu()

    # Database manipulation functions
    def init_db(self, db_file: str):
        self.db_conn = self.connect_db(db_file)
        self.create_tables()

    @staticmethod
    def connect_db(db_file: str):
        """
        create database connection to db_file
        :return: Connection object or None
        """
        connection = None
        open(db_file, mode='w').close()

        try:
            connection = sqlite3.connect(db_file)
        except Exception as e:
            print(e)
        return connection

    def create_tables(self):
        """ create a table with the connection and provided statement
        """
        sql_create_card_table = ('''CREATE TABLE IF NOT EXISTS card (
                         id integer PRIMARY KEY, 
                         number text, 
                         pin text, 
                         balance integer DEFAULT 0);''')
        self.execute_sql(sql_create_card_table, query=False)

    def execute_sql(self, sql_statement: Union[str, list], query: bool):
        """execute the supplied statement to the provided sql connection and commit.
        :param sql_statement: SQL statement to execute
        :param query: whether a response is expected
        :return: True if successfully executed otherwise False"""
        sql_param = None
        if isinstance(sql_statement, list):
            sql_param = sql_statement[1]
            sql_statement = sql_statement[0]
        try:
            cursor = self.db_conn.cursor()
            if sql_param:
                cursor.execute(sql_statement, sql_param)
            else:
                cursor.execute(sql_statement)
            self.db_conn.commit()
            return cursor.fetchall() if query else True
        except Exception as e:
            print('Error occurred executing following SQL statement:' + sql_statement)
            print(e)
        return False

    # App functions

    def get_balance(self, account: str):
        """return the account balance of provided account number, returns None if account doesn't exist, default currently selected account
        :param account: account number to check, default current account"""
        sql_check_balance = ['SELECT balance FROM card WHERE number = ?', [account, ]]
        response = self.execute_sql(sql_check_balance, query=True)
        if len(response) != 0:
            return response[0][0]
        return None

    def handle_check_balance(self):
        """return the account balance of provided account number, default currently selected account"""
        account = self.current_user
        balance = self.get_balance(account)
        print(f"Balance: {balance}")

    def handle_add_income(self):
        add_amount = int(self.ui.get_input('Enter income:'))
        account = self.current_user
        if self.modify_income(add_amount, account):
            print('Income was added!')
        else:
            print('An error occurred adding income.')

    def handle_close_account(self):
        if self.close_account():
            print('The account has been closed!')
            self.handle_log_out()
        else:
            print('The account was not closed.')

    def handle_do_transfer(self):
        print('Transfer')
        target = self.ui.get_input('Enter card number')
        if not self._validate_card(target):
            print('Probably you made a mistake in the card number. Please try again!')
        elif self.get_balance(target) is None:
            print('Such a card does not exist.')
        else:
            amount = int(self.ui.get_input('Enter how much money you want to transfer:'))
            if amount > self.get_balance(self.current_user):
                print('Not enough money!')
            else:
                return True if self.transfer(target, amount) else False

    def handle_log_out(self):
        self.log_out()

    def modify_income(self, amount: int, target_account: str = 'current'):
        """add to the balance of the logged in user
        :param amount: amount to modify, positive to add, negative to subtract
        :param target_account: target account to modify, default current account"""
        if target_account == 'current':
            target_account = self.current_user
        old_balance = self.get_balance(target_account)
        new_balance = old_balance + amount
        sql_add_income = ['UPDATE card SET balance = ? WHERE number = ?', [new_balance, target_account]]

        if self.execute_sql(sql_add_income, query=False):
            return True
        return False

    def transfer(self, target_account: str, amount: int):
        """transfer an amount of balance to the target account
        :param target_account: The target account number to transfer to
        :param amount: The amount of balance to transfer"""
        return self.modify_income(-amount) and self.modify_income(amount, target_account)

    def close_account(self):
        """delete all record of the current account from the database"""
        sql_close_account = ['DELETE FROM card WHERE number = ?', [self.current_user]]
        self.execute_sql(sql_close_account, query=False)

    def log_out(self):
        """Clear current user data"""
        self.current_user = None

    def _validate_card(self, card_number: str) -> bool:
        return card_number[-1] == self._calculate_checksum(card_number[0:-1])

    @staticmethod
    def _calculate_checksum(number: str) -> str:
        checksum_counter = 0
        for i, d in enumerate(number):
            d = int(d)
            if i % 2 == 0:
                d *= 2
            if d > 9:
                d -= 9
            checksum_counter += d
        return "0" if (checksum_counter % 10 == 0) else str(10 - checksum_counter % 10)

    def create_account(self):
        """create a new bank account with randomly generated card number and pin"""

        sql_create_card_entry = '''INSERT INTO card(number, pin) VALUES (?, ?)'''

        # generate 9 random digits as customer account number
        customer_number = str(random.randint(0, 10**9-1))
        customer_number = '0'*(9-len(customer_number)) + customer_number

        incomplete_account: str = IIN + customer_number

        checksum = self._calculate_checksum(incomplete_account)
        new_account = incomplete_account + checksum

        # check if account exists
        if self.get_balance(new_account):
            return

        # generate random password
        password = ""
        for i in range(4):
            password += str(random.randint(0, 9))

        # save account into database
        cursor = self.db_conn.cursor()
        cursor.execute(sql_create_card_entry, (new_account, password))
        self.db_conn.commit()

        # print account details
        print(f"""
Your card has been created
Your card number:
{new_account}
Your card PIN:
{password}""")

        return

    def login(self):
        """
        Prompts for card number and PIN and tries to match detail in database. If match log user in.
        :return: boolean True if successful login, False if errors
        """
        card_number = self.ui.get_input("Enter your card number:")
        pin = self.ui.get_input("Enter your PIN:")

        cursor = self.db_conn.cursor()
        user = cursor.execute("SELECT * FROM card WHERE number == ?", [card_number, ]).fetchone()
        if not user:
            print("Wrong card number or PIN!")
            return False

        user_pin = user[2]
        if user_pin == pin:
            self.current_user = card_number
            print("You have successfully logged in!")
            self.ui.logged_in_menu()
            return True
        else:
            print("Wrong card number or PIN!")
            return False


class UI:
    def __init__(self, app_instance):
        self.app = app_instance

    @staticmethod
    def get_input(string=""):
        user_input = input(string)
        user_input = user_input.strip()
        return user_input

    def main_menu(self):
        dict_key_function_main = {"1": self.app.create_account, "2": self.app.login}

        while True:
            print("""
1. Create an account
2. Log into account
0. Exit
            """)
            user_input = self.get_input()
            if user_input == '0':
                print('Bye!')
                exit()
            elif user_input in dict_key_function_main.keys():
                dict_key_function_main[user_input]()
            else:
                print("Please input the corresponding number of options eg.1")

    def logged_in_menu(self):
        instance = self.app
        dict_key_function_logged_in = {'1': instance.handle_check_balance, '2': instance.handle_add_income,
                                       '3': instance.handle_do_transfer, '4': instance.handle_close_account,
                                       '5': instance.handle_log_out}

        while instance.current_user:
            print("""
1. Balance
2. Add income
3. Do transfer
4.Close account
5.Log out
0. Exit""")
            user_input = self.get_input()
            if user_input == '0':
                print('Bye!')
                exit()
            elif user_input in dict_key_function_logged_in.keys():
                dict_key_function_logged_in[user_input]()
            else:
                print("Please input the corresponding number of options eg.1")


if __name__ == "__main__":
    db_file_path = 'card.s3db'
    app = App(db_file=db_file_path)
    app.run()
