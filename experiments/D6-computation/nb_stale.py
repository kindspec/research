import marimo

__generated_with = "0.24.0"
app = marimo.App(width="medium")


@app.cell
def _():
    tax_rate = 0.13
    return (tax_rate,)


@app.cell
def _():
    rows = [{"qty": 10, "unit": 12.00}, {"qty": 20, "unit": 18.00}]
    return (rows,)


@app.cell
def _(rows):
    # BODY references tax_rate but SIGNATURE does not list it.
    total = sum(r["qty"] * r["unit"] for r in rows) * (1 + tax_rate)
    print("TOTAL", total)
    return (total,)


if __name__ == "__main__":
    app.run()
