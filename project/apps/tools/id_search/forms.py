from django import forms
from django.core.validators import RegexValidator
from django.utils.safestring import mark_safe

class GeneIDSearchForm(forms.Form):
    gene_ids = forms.CharField(
        label='基因ID',
        widget=forms.Textarea(attrs={
            'rows': 5,
            'placeholder': '输入一个或多个基因ID，用逗号或换行分隔',
            'class': 'form-control'
        }),
        help_text='例如: Ghe01G16580, Ghe01G04430'
    )
class BlastpForm(forms.Form):
    sequence = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 10,
            'placeholder': '>OptionalHeader\nMAVSE... 或直接输入蛋白质序列'
        }),
        label='Protein Sequence (FASTA or raw sequence)',
        required=False,
        error_messages={'required': ''}
    )
    
    evalue = forms.FloatField(
        initial=0.001,
        label='E-value Threshold',
        required=False,
        error_messages={'required': ''}
    )


    max_hits = forms.IntegerField(
        required=False,
        initial=20,
        min_value=1,
        max_value=1000,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
        }),
        label="Maximum Results"
    )

    ALGORITHM_CHOICES = [
        ('blastp', 'BLASTp (标准蛋白质比对)'),
        ('phiblast', 'PHI-BLAST (模式匹配)'),
    ]
    algorithm = forms.ChoiceField(
        choices=ALGORITHM_CHOICES,
        initial='blastp',
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Algorithm"
    )

    def clean_sequence(self):
        """预处理序列数据：移除空格/空行，提取纯序列"""
        raw_seq = self.cleaned_data['sequence'].strip()

        if raw_seq.startswith('>'):
            lines = [line.strip() for line in raw_seq.split('\n') if line.strip()]
            sequence = ''.join(lines[1:])
        else:
            sequence = ''.join(raw_seq.split())
            
        if len(sequence) < 10:
            raise forms.ValidationError("序列太短（至少10个氨基酸）")
        if not sequence.isalpha():
            raise forms.ValidationError("包含非字母字符")
            
        return sequence.upper()
