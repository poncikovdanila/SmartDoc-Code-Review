"""Образец Python-кода, оформленного по PEP 8."""


def calculate_sum(numbers):
    """Возвращает сумму чисел в переданной последовательности."""
    total = 0
    for value in numbers:
        total = total + value
    return total


if __name__ == "__main__":
    print(calculate_sum([1, 2, 3, 4, 5]))
