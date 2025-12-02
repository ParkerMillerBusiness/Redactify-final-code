from core.pipeline import redact_text

if __name__ == "__main__":
    text = (
        "Patient John Doe visited St. Mary Hospital in Austin on 05/21/1984. "
        "Contact: john.doe@clinic.org, phone: (555) 123-4567. "
        "SSN: 123-45-6789. Card: 4111-1111-1111-1111."
    )

    redacted, spans = redact_text(text, "configs/policy.yaml", mode="placeholder")

    print("=== ORIGINAL ===")
    print(text)
    print("\n=== REDACTED ===")
    print(redacted)
    print("\n=== SPANS ===")
    for s in spans:
        print(
            f"{s.ent} ({s.source}) [{s.start}:{s.end}] "
            f"'{text[s.start:s.end]}' -> '{s.replacement}'"
        )
