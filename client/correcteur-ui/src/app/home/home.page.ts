import { Component } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { IonicModule } from '@ionic/angular';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-home',
  templateUrl: './home.page.html',
  styleUrls: ['./home.page.scss'],
  standalone: true,
  imports: [IonicModule, FormsModule]
})
export class HomePage {
  text: string = '';
  result: any = null;
  isLoading: boolean = false; // État de chargement

  constructor(private http: HttpClient) {}

  correctText() {
    if (!this.text.trim()) return;

    this.isLoading = true;
    this.result = null;

    // Appel au backend Node.js
    this.http.post('http://localhost:5050/correct', { text: this.text })
      .subscribe({
        next: (res) => {
          this.result = res;
          this.isLoading = false;
        },
        error: (err) => {
          console.error('Erreur Backend:', err);
          alert("Impossible de contacter le serveur de correction.");
          this.isLoading = false;
        }
      });
  }
}