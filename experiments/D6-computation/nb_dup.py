import marimo
__generated_with = "0.24.0"
app = marimo.App()

@app.cell
def _():
    x = 1
    return (x,)

@app.cell
def _():
    x = 2
    return (x,)

@app.cell
def _(x):
    print("X IS", x)
    return

if __name__ == "__main__":
    app.run()
