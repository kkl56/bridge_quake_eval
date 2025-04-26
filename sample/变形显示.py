# 假设已进行静力/动力分析，提取位移
disp_scale = 10  # 位移放大系数
node_disps = np.array([ops.nodeDisp(n) for n in node_tags])
deformed_coords = node_coords + disp_scale * node_disps[:, :3]

# 绘制变形后的单元（绿色）
for conn in ele_conn:
    line = vtk.vtkLineSource()
    line.SetPoint1(deformed_coords[conn[0]-1])
    line.SetPoint2(deformed_coords[conn[1]-1])
    line.Update()

    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputConnection(line.GetOutputPort())

    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetColor(0, 1, 0)  # 绿色
    actor.GetProperty().SetLineWidth(3)
    renderer.AddActor(actor)