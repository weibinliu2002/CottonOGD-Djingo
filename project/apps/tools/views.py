from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json
import subprocess
from django.views import View


@method_decorator(csrf_exempt, name='dispatch')
class PrimerDesignAPIView(View):
    def post(self, request, format=None):
        try:
            data = json.loads(request.body.decode('utf-8'))
            sequence = data.get('sequence', '')
            if not sequence:
                return Response({'error': 'No sequence provided'}, status=400)
            
            # 调用Primer3Plus进行引物设计
            cmd = f"primer3_core -s {sequence} -o primer3_output.txt"
            subprocess.run(cmd, shell=True, check=True)
            
            with open('primer3_output.txt', 'r') as f:
                primer3_output = f.read()
            
            return Response({'primer3_output': primer3_output})
        except Exception as e:
            return Response({'error': str(e)}, status=500)