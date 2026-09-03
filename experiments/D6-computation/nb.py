import marimo

__generated_with = "0.24.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    return (mo,)


@app.cell
def _():
    rows = [
        {"item": "widget", "qty": 10, "unit": 12.00},
        {"item": "gadget", "qty": 20, "unit": 18.00},
    ]
    return (rows,)


@app.cell
def _(rows):
    total = sum(r["qty"] * r["unit"] for r in rows)
    total
    return (total,)


if __name__ == "__main__":
    app.run()
