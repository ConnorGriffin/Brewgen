from ortools.sat.python import cp_model


class VarArraySolutionPrinter(cp_model.CpSolverSolutionCallback):
    """Print intermediate solutions."""

    def __init__(self, variables):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self.__variables = variables
        self.__solution_count = 0

    def on_solution_callback(self):
        self.__solution_count += 1
        for v in self.__variables:
            print('%s=%i' % (v, self.Value(v)), end=' ')
        print()

    def solution_count(self):
        return self.__solution_count


model = cp_model.CpModel()

x = model.NewIntVar(0, 100, 'x')
x_below_range = model.NewBoolVar('x_below_range')
x_above_range = model.NewBoolVar('x_above_range')
x_mod_5 = model.NewIntVar(0, 4, 'x_mod_5')

y = model.NewIntVar(0, 100, 'y')
y_below_range = model.NewBoolVar('y_below_range')
y_above_range = model.NewBoolVar('y_above_range')
y_mod_5 = model.NewIntVar(0, 4, 'y_mod_5')

model.Add(x + y == 100)

model.AddModuloEquality(x_mod_5, x, 5)
model.Add(x >= 20).OnlyEnforceIf([x_below_range.Not(), x_above_range.Not()])
model.Add(x <= 80).OnlyEnforceIf([x_below_range.Not(), x_above_range.Not()])
model.Add(x < 20).OnlyEnforceIf(x_below_range)
model.Add(x > 80).OnlyEnforceIf(x_above_range)
model.Add(x_mod_5 == 0).OnlyEnforceIf(
    [x_below_range.Not(), x_above_range.Not()])

model.AddModuloEquality(y_mod_5, y, 5)
model.Add(y >= 20).OnlyEnforceIf([y_below_range.Not(), y_above_range.Not()])
model.Add(y <= 80).OnlyEnforceIf([y_below_range.Not(), y_above_range.Not()])
model.Add(y < 20).OnlyEnforceIf(y_below_range)
model.Add(y > 80).OnlyEnforceIf(y_above_range)
model.Add(y_mod_5 == 0).OnlyEnforceIf(
    [y_below_range.Not(), y_above_range.Not()])

# Create a solver and solve.
solver = cp_model.CpSolver()
solution_printer = VarArraySolutionPrinter(
    [x, y])
status = solver.SearchForAllSolutions(model, solution_printer)
print('Status = %s' % solver.StatusName(status))
print('Number of solutions found: %i' % solution_printer.solution_count())
