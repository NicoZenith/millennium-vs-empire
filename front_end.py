from back_end import calculate_odds

if __name__ == "__main__":
    millennium_file = input("Enter the path to the millennium JSON file: ")
    empire_file = input("Enter the path to the Empire JSON file: ")
    try:
        odds = calculate_odds("examples/"+millennium_file, "examples/"+empire_file)
        print(f"The odds that the Millennium Falcon reaches Endor in time are: {odds:.2f}%")
    except Exception as e:
        print(f"Error: {e}")