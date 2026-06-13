import os
from PIL import Image
import torch
from torch.utils.data import Dataset
import pandas as pd

class ReceiptForgeryDataset(Dataset):
    def __init__(self, data_dir, split='train', transform=None):
        self.data_dir = os.path.join(data_dir, split)
        self.transform = transform
        
        # Load labels from text file
        label_file = os.path.join(data_dir, f'{split}.txt')
        self.samples = []
        
        with open(label_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    parts = line.split()
                    if len(parts) >= 2:
                        img_name = parts[0]
                        label = int(parts[1])
                        self.samples.append((img_name, label))
        
        print(f"Loaded {len(self.samples)} samples from {split} set")
    
    def __len__(self):
        return len(self.samples)
    
    def __getitem__(self, idx):
        img_name, label = self.samples[idx]
        img_path = os.path.join(self.data_dir, img_name)
        
        try:
            image = Image.open(img_path).convert('RGB')
            if self.transform:
                image = self.transform(image)
            return image, torch.tensor(label, dtype=torch.long)
        except Exception as e:
            print(f"Error loading {img_path}: {e}")
            # Return a dummy image if error
            dummy = torch.zeros(3, 224, 224)
            return dummy, torch.tensor(0, dtype=torch.long)

def get_data_loaders(data_dir='data/findit2', batch_size=32):
    from torchvision import transforms
    
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    
    train_dataset = ReceiptForgeryDataset(data_dir, 'train', transform)
    val_dataset = ReceiptForgeryDataset(data_dir, 'val', transform)
    test_dataset = ReceiptForgeryDataset(data_dir, 'test', transform)
    
    train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = torch.utils.data.DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    test_loader = torch.utils.data.DataLoader(test_dataset, batch_size=batch_size, shuffle=False)
    
    return train_loader, val_loader, test_loader