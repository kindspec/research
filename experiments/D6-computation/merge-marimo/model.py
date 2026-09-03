import marimo
__generated_with = "0.24.0"
app = marimo.App()


@app.cell
def _():
    base = 100
    return (base,)


@app.cell
<<<<<<< HEAD
def _():
    alice_fee = 25
    return (alice_fee,)


@app.cell
def _(base, alice_fee):
    total = base + alice_fee
=======
def _(base):
    total = base + bob_fee
>>>>>>> bob
    print("TOTAL", total)
    return (total,)


@app.cell
def _():
    bob_fee = 40
    return (bob_fee,)


if __name__ == "__main__":
    app.run()
