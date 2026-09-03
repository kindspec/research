import marimo
__generated_with = "0.24.0"
app = marimo.App()


@app.cell
def _():
    revenue = 1000
    return (revenue,)


@app.cell
def _():
    fee = 25
    return (fee,)


@app.cell
def _():
    fee = 40
    return (fee,)


@app.cell
def _(revenue):
    print("REVENUE", revenue)
    return


if __name__ == "__main__":
    app.run()
