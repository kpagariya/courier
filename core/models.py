from django.db import models


class JobOpening(models.Model):
    """Model for career page job openings - manageable from admin without server restart"""
    title = models.CharField(max_length=200)
    location = models.CharField(max_length=100, default='Auckland')
    job_type = models.CharField(max_length=50, default='Full-time', 
                                 choices=[
                                     ('Full-time', 'Full-time'),
                                     ('Part-time', 'Part-time'),
                                     ('Contract', 'Contract'),
                                     ('Casual', 'Casual'),
                                 ])
    description = models.TextField()
    is_active = models.BooleanField(default=True, help_text='Uncheck to hide this job opening')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.location}"

