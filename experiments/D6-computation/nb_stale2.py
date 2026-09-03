import marimo

__generated_with = "0.24.0"
app = marimo.App()


@app.cell
def _(rows, tax_rate):
    total = sum(r["qty"] * r["unit"] for r in rows) * (1 + tax_rate)
    print("TOTAL", total)
    return (total,)


@app.cell
def _():
    tax_rate = 0.13
    return (tax_rate,)


@app.cell
def _():
    rows = [{"qty": 10, "unit": 12.00}, {"qty": 20, "unit": 18.00}]
    return (rows,)


if __name__ == "__main__":
    app.run()
