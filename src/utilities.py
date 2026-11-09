
# -------------------------------------------------------
# Error Handling Classes and Functions
#-------------------------------------------------------

class StrictModeError(Exception):
    def __init__(self, message, details=None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self):
        base = f"StrictModeError: {self.message}"
        if self.details:
            return f"{base} | Details: {self.details}"
        return base

#-------------------------------------------------------
#  Format the error printing to be easy to read by humans
#-------------------------------------------------------
def print_strict_error(e: StrictModeError):
    print("\n=== STRICT MODE FAILURE ===")
    if e.step:
        print(f"Step: {e.step}")

    if e.missing_required_columns:
        print("\nMissing Required Columns:")
        for col in e.missing_required_columns:
            print(f"  - {col}")

    if e.missing_values:
        print("\nMissing Values:")
        for col in e.missing_values:
            print(f"  - {col}")

    if e.invalid_types:
        print("\nInvalid Types:")
        for col, msg in e.invalid_types.items():
            print(f"  - {col}: {msg}")

    if e.invalid_categories:
        print("\nInvalid Categories:")
        for col, cats in e.invalid_categories.items():
            print(f"  - {col}: {cats}")

    if e.out_of_range:
        print("\nOut-of-Range Values:")
        for col, msg in e.out_of_range.items():
            print(f"  - {col}: {msg}")

    if e.details:
        print("\nDetails:")
        if e.details:
                print(f"Step: {e.details}")

    print("\n===========================\n")