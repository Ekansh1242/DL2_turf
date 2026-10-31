# Held-out synthetic test evaluation

Balanced synthetic dataset v2; disjoint template families; recurring entity values; not evidence of real-user generalization

| Model | Intent macro F1 | Entity micro F1 | Complete request accuracy |
|---|---:|---:|---:|
| bilstm | 0.8626 | 0.9997 | 0.8700 |
| rules | 0.8495 | 1.0000 | 0.8567 |

Full precision/recall/F1, field accuracies, strict span matches, and every error: evaluation.json.
Confusion matrices: *_confusion_matrix.csv. Rows are actual labels, columns predicted.
Field accuracy includes absent fields. Complete request accuracy requires correct intent and every exact entity span.
Checkpoint chosen by validation loss only. Test data is used only after training.
