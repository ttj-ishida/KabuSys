# KabuSys WebManual

`documents/WebManual` は、KabuSys を使い始める人向けの入口です。  
設計メモではなく、実際の導入と運用で読む順番を優先して並べています。

---

## 最初に読む順番

1. [A_Overview.md](./A_Overview.md)  
   KabuSys の全体像と、どの運用フローで使うかを把握するための概要です。
2. [B_CoreSetup.md](./B_CoreSetup.md)  
   `Core` の初期セットアップ、`.env`、DB、Task Scheduler の確認手順です。
3. [C_Backtest.md](./C_Backtest.md)  
   過去データで戦略を検証するバックテストの実行手順です。
4. [C_PaperTrading.md](./C_PaperTrading.md)  
   実資金を使う前に `paper_trading` で検証するための手順です。
5. [C_1WeekPaperChecklist.md](./C_1WeekPaperChecklist.md)  
   最初の 1 week を `paper_trading` で回すときの運用チェックリストです。
6. [D_LiveOperation.md](./D_LiveOperation.md)  
   本番運用に入った後の日次運用手順です。
7. [E_FailureRecovery.md](./E_FailureRecovery.md)  
   障害時、異常時、復旧時の確認手順です。

---

## 補足

- この WebManual は運用者向けの導線に絞っています。
- 管理情報や配置方針は [MAPPING.md](./MAPPING.md) と [INDEX_DESIGN.md](./INDEX_DESIGN.md) に分離しています。
- 迷った場合は [A_Overview.md](./A_Overview.md) に戻ってください。
