"""Seed file to make sample data for db."""
# EXAMPLE SETUP
# from models import Department, Employee, Project, EmployeeProject, db
# from app import app

# # Create all tables
# db.drop_all()
# db.create_all()


# EXAMPLE
# EmployeeProject.query.delete()
# Employee.query.delete()
# Department.query.delete()
# Project.query.delete()

# # Add sample employees and departments
# df = Department(dept_code='fin', dept_name='Finance', phone='555-1000')
# dl = Department(dept_code='legal', dept_name='Legal', phone='555-2222')
# dm = Department(dept_code='mktg', dept_name='Marketing', phone='555-9999')

# leonard = Employee(name='Leonard', dept=dl)
# liz = Employee(name='Liz', dept=dl)
# maggie = Employee(name='Maggie', state='DC', dept=dm)
# nadine = Employee(name='Nadine')

# db.session.add_all([df, dl, dm, leonard, liz, maggie, nadine])
# db.session.commit()

# pc = Project(proj_code='car', proj_name='Design Car',
#              assignments=[EmployeeProject(emp_id=liz.id, role='Chair'),
#                           EmployeeProject(emp_id=maggie.id)])
# ps = Project(proj_code='server', proj_name='Deploy Server',
#              assignments=[EmployeeProject(emp_id=liz.id),
#                           EmployeeProject(emp_id=leonard.id, role='Auditor')])

# db.session.add_all([ps, pc])
# db.session.commit()