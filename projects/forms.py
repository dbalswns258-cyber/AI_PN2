from pathlib import Path
from django import forms
from .models import Project


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['name', 'client', 'trade', 'status', 'is_sample']


class UploadForm(forms.Form):
    file = forms.FileField(label='도면 또는 참고 자료 (DXF, PDF, PNG, JPG / 최대 10 MB)')
    previous = forms.UUIDField(label='이전 도면 버전 ID (새 도면이면 비워 두세요)', required=False)

    def clean_file(self):
        file = self.cleaned_data['file']
        if file.size > 10 * 1024 * 1024:
            raise forms.ValidationError('파일 크기는 10 MB 이하이어야 합니다.')
        extension = Path(file.name).suffix.lower()
        if extension not in ('.dxf', '.pdf', '.png', '.jpg', '.jpeg'):
            raise forms.ValidationError('DXF, PDF, PNG, JPG만 지원합니다. DWG는 AutoCAD에서 DXF로 별도 저장하세요.')
        head = file.read(32); file.seek(0)
        if not head:
            raise forms.ValidationError('빈 파일입니다.')
        signatures = {'.pdf': b'%PDF-', '.png': b'\x89PNG\r\n\x1a\n', '.jpg': b'\xff\xd8\xff', '.jpeg': b'\xff\xd8\xff'}
        if extension in signatures and not head.startswith(signatures[extension]):
            raise forms.ValidationError('파일 내용과 확장자가 다릅니다.')
        return file


class DecisionForm(forms.Form):
    revision = forms.IntegerField(widget=forms.HiddenInput)
    status = forms.ChoiceField(label='확인 상태', choices=[('pending', '미확정'), ('confirmed', '확정'), ('excluded', '제외')])
    system = forms.ChoiceField(label='계통', choices=[('', '미확정'), ('water', '급수')], required=False)
    diameter_mm = forms.DecimalField(label='호칭지름 (mm)', max_digits=8, decimal_places=3, min_value=0.001, max_value=10000, required=False)
    material = forms.CharField(label='재질 (모르면 비워 두세요)', max_length=100, required=False)
    floor = forms.CharField(label='층', max_length=100, required=False)
    zone = forms.CharField(label='구역', max_length=100, required=False)
    work_category = forms.ChoiceField(label='공사 구분', required=False, choices=[('', '미확정'), ('new', '신설'), ('existing', '기존'), ('demolition', '철거')])
    evidence = forms.CharField(label='확정·제외의 근거', widget=forms.Textarea(attrs={'rows': 3}), max_length=2000, required=False)


class RunForm(forms.Form):
    revision = forms.IntegerField(widget=forms.HiddenInput)
    unit = forms.ChoiceField(label='확인한 모델 공간 길이 단위', choices=[('', '직접 선택하세요'), ('mm', 'mm'), ('cm', 'cm'), ('m', 'm')])
    unit_evidence = forms.CharField(label='단위 확인 근거 (예: 기지 치수 5000과 객체 길이 비교)', max_length=1000)
    decimal_places = forms.TypedChoiceField(label='관경별 합계를 표시할 소수 자릿수', coerce=int,
                                           choices=[('', '직접 선택하세요')] + [(i, str(i)) for i in range(7)])
    rounding = forms.ChoiceField(label='관경별 합계 반올림 방법', choices=[('', '직접 선택하세요'),
                                ('ROUND_HALF_UP', '사사오입'), ('ROUND_HALF_EVEN', '정확한 중간값은 짝수 쪽'), ('ROUND_DOWN', '버림')])
    accept = forms.BooleanField(label='평면 직접 길이의 검토용 결과이며 입상·부속·할증·보온이 포함되지 않음을 확인합니다.')
