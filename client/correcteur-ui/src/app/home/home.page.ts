import { Component } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { IonicModule } from '@ionic/angular';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { addIcons } from 'ionicons';
import { sparkles, documentTextOutline, checkmarkCircle, alertCircleOutline } from 'ionicons/icons';

@Component({
  selector: 'app-home',
  templateUrl: './home.page.html',
  styleUrls: ['./home.page.scss'],
  standalone: true,
  imports: [IonicModule, FormsModule, CommonModule]
})
export class HomePage {
  text: string = '';
  result: any = null;
  isLoading: boolean = false;

  constructor(private http: HttpClient) {
    addIcons({ sparkles, documentTextOutline, checkmarkCircle, alertCircleOutline });
  }

  correctText() {
    if (!this.text.trim()) return;

    this.isLoading = true;
    this.result = null;

    this.http.post('http://localhost:5050/correct', { text: this.text })
      .subscribe({
        next: (res: any) => {
          this.result = res;
          this.isLoading = false;
        },
        error: (err) => {
          console.error('Erreur Backend:', err);
          this.isLoading = false;
        }
      });
  }
}