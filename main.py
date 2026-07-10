from orchestrator import Orchestrator


def main() -> None:
    orchestrator = Orchestrator()

    print("=" * 60)
    print("Asistentul AI al cofetariei")
    print("Scrie 'exit' pentru a inchide aplicatia.")
    print("=" * 60)

    while True:
        try:
            user_message = input("\nTu: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nAplicatia a fost inchisa.")
            break

        if user_message.lower() in {"exit", "quit", "stop"}:
            print("La revedere!")
            break

        if not user_message:
            print("Introdu o intrebare.")
            continue

        response = orchestrator.handle_message(user_message)

        print(f"\nAgent: {response}")


if __name__ == "__main__":
    main()