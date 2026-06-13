import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import models, transforms
import os
import sys

print("Script started...")

# Add the current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    print("Testing imports...")
    try:
        from utils.data_loader import get_data_loaders
        print("✓ data_loader imported successfully")
        return get_data_loaders
    except Exception as e:
        print(f"✗ Failed to import data_loader: {e}")
        return None

def train_model(num_epochs=10, model_save_path='models/receipt_forgery_model.pth'):
    print(f"Training function called. Epochs: {num_epochs}")
    
    # Create models directory
    os.makedirs('models', exist_ok=True)
    print("Models directory created")
    
    # Load data
    print("Loading data...")
    get_data_loaders = test_imports()
    if get_data_loaders is None:
        print("Cannot proceed without data_loader")
        return
    
    try:
        train_loader, val_loader, test_loader = get_data_loaders()
        print(f"Data loaded successfully! Train batches: {len(train_loader)}")
    except Exception as e:
        print(f"Error loading data: {e}")
        return
    
    # Use pre-trained ResNet
    print("Creating model...")
    model = models.resnet18(pretrained=True)
    num_features = model.fc.in_features
    model.fc = nn.Linear(num_features, 2)
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = model.to(device)
    
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    
    print(f"Training on {device}")
    print(f"Starting training for {num_epochs} epochs...")
    
    best_accuracy = 0.0
    
    for epoch in range(num_epochs):
        # Training phase
        model.train()
        running_loss = 0.0
        correct = 0
        total = 0
        
        for batch_idx, (images, labels) in enumerate(train_loader):
            images, labels = images.to(device), labels.to(device)
            
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            
            running_loss += loss.item()
            _, predicted = torch.max(outputs.data, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
            
            if batch_idx % 10 == 0:
                print(f"  Batch {batch_idx}/{len(train_loader)}, Loss: {loss.item():.4f}")
        
        train_accuracy = 100 * correct / total
        
        # Validation phase
        model.eval()
        val_correct = 0
        val_total = 0
        
        with torch.no_grad():
            for images, labels in val_loader:
                images, labels = images.to(device), labels.to(device)
                outputs = model(images)
                _, predicted = torch.max(outputs.data, 1)
                val_total += labels.size(0)
                val_correct += (predicted == labels).sum().item()
        
        val_accuracy = 100 * val_correct / val_total
        
        print(f'Epoch [{epoch+1}/{num_epochs}], Loss: {running_loss/len(train_loader):.4f}, '
              f'Train Acc: {train_accuracy:.2f}%, Val Acc: {val_accuracy:.2f}%')
        
        # Save best model
        if val_accuracy > best_accuracy:
            best_accuracy = val_accuracy
            torch.save(model.state_dict(), model_save_path)
            print(f"  → Saved best model with accuracy {best_accuracy:.2f}%")
    
    print(f"Training complete! Best validation accuracy: {best_accuracy:.2f}%")

if __name__ == "__main__":
    print("="*50)
    print("RECEIPT FORGERY DETECTOR - TRAINING SCRIPT")
    print("="*50)
    train_model(num_epochs=10)
    print("Script finished!")