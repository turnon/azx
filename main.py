def main():
    print("Python REPL - Type 'exit' or 'quit' to exit")
    while True:
        try:
            user_input = input(">>> ")
            if user_input.lower() in ('exit', 'quit'):
                break
            
            # Evaluate and print result
            result = eval(user_input)
            print(result)
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
