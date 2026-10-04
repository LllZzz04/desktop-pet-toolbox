# 本地射频计算

在统一输入框输入并按 Enter，`rf` / `/rf` 均可，`rf help` 显示示例。RF 命令不发送模型 API，错误直接显示本地提示，成功进入记录并可收藏。

## 串联元件 Q

`rf q 6GHz 1nH 2ohm`，或 `rf q f=6GHz L=1nH Rs=2ohm`。

输入频率、一个串联电感 / 电容、该频率的有效串联损耗电阻 Rs。参数顺序可交换。

- `ω = 2πf`
- 电感：`Q = ωLs/Rs`
- 电容：`Q = 1/(ωCsRs)`

例子按公式应约为 `18.849556`；电容例子为 `rf q 6GHz 700fF 2ohm`。Rs 应是目标频率的损耗电阻，直流电阻不能表达全部高频损耗；单个元件 Q 不等于完整谐振回路的加载 Q。参考 [Analog Devices AN-280](https://www.analog.com/media/en/technical-documentation/application-notes/294542582256114777959693992461771205an280.pdf)。

## 精确串并联转换

`rf rp 6GHz 1nH Q=20`；亦可用 `rf rp 6GHz 1nH 2ohm` 从 Rs 求 Q。需要频率、一个串联元件值、Q / Rs 其中之一。

- `Q = |X|/Rs`
- `Rp = Rs(1+Q²)`
- 电感：`Lp = Ls(1+1/Q²)`
- 电容：`Cp = Cs/(1+1/Q²)`

第一个例子按公式应约为 `Rs = 1.88496 Ω`、`Rp = 755.867 Ω`、`Lp = 1.0025 nH`，显示会取有效位数。这是指定频率下的精确等效，输入 L/C 解释为串联元件，未使用高 Q 近似。参考 [Analog Devices RF 阻抗匹配计算](https://www.analog.com/en/resources/technical-articles/radio-frequency-impedance-matching-calculations-and-simulations.html)。

## VCO FoM

`rf fom 6GHz 1MHz -120dBc/Hz 10mW`，或 `rf fom f0=6GHz df=1MHz pn=-120dBc/Hz p=10mW`。

依次为载波 f₀、测量偏移 Δf、该偏移处相噪 PN、直流功耗 Pdc：

`FoM = PN − 20log₁₀(f₀/Δf) + 10log₁₀(Pdc/1mW)`

例子按公式应约为 `−185.56303 dBc/Hz`，同时显示反号结果以便比较其他符号惯例。负值表示下越小越好。未加入调谐范围 / 面积修正。参考原始论文 [A 60 GHz Class-C Wide Tuning Range Two-Core VCO…](https://pmc.ncbi.nlm.nih.gov/articles/PMC11820980/) 中的负值公式和参数定义。

## 单位与边界

频率 / 电感 / 电容沿用现有单位；电阻新增 `ohm / Ohm / Ω`、`mohm / mΩ`、`kohm / kOhm / kΩ`、`Mohm / MOhm / MΩ`；功率新增 `uW / mW / W`。µ / μ 可代替 u。单位大小写有意义，尤其 m 与 M。

也支持 `2000 ohm to kohm`、`10 mW to W`。RF 参数 SI 值需为正数且在 1e−30～1e30；相噪限制为 −1000～0 dBc/Hz，偏移必须小于载波。拒绝非有限、重复量纲和不完整参数，只使用格式解析及数学函数，不使用 eval。

模块位于 `app/calculator/rf_calc.py`，无界面、存储或网络依赖。以上数值是手动核对参考，本次没有执行计算器测试。
