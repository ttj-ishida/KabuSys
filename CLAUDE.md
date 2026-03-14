# KabuSys (日本株自動売買システム) - Developer Guide

本ファイルは、KabuSys（日本株自動売買システム）の開発に参画するAIアシスタントおよび開発者のためのガイドラインです。
このファイルには、プロジェクトのアーキテクチャ、ディレクトリ構造、ドキュメントの配置、今後の開発方針とGit運用ルールが記載されています。

## 📂 Directory Structure (Current & Planned)

現在の設計ドキュメント構造と、開発開始に向けて予定されるディレクトリ構造です。

```text
KabuSys/
├── documents/                  # すべての設計仕様書および運用手順書の格納場所
│   ├── 00_Architecture/        # システム全体構成・インフラ要件・ステートマシンの定義
│   ├── 01_Data/                # 市場データ・ニュース・DB基盤の仕様とスキーマ (DataSchema等)
│   ├── 02_Strategy/            # 売買戦略モデル、ポートフォリオ構築、ユニバース定義
│   ├── 03_AI_Model/            # ニュースNLPや市場レジーム判定などのAIモデル仕様
│   ├── 04_Execution/           # 執行系・発注制御 (OrderStateMachine)・通信仕様
│   ├── 05_Backtest/            # バックテストおよびフォワードテストのフレームワーク定義
│   ├── 06_RiskManagement/      # 資金管理・リスク上限ルール（AI影響度は最大10%など）
│   ├── 07_Research/            # 新規ファクターやAIモデルの開発・分析用隔離環境
│   ├── 08_Operations/          # 監視 (Monitoring)・障害復旧・Trading Runbook などの運用仕様
│   ├── 09_Deployment/          # デプロイメントアーキテクチャ（単一Windowsノード構成）
│   ├── 10_Runtime/             # 実行時アーキテクチャやジョブスケジュール定義
│   └── Archive/                # 旧設計資料や参考資料の退避場所
├── src/                        # (予定) プロダクションコード本体
├── tests/                      # (予定) 単体テスト・結合テストコード
├── notebooks/                  # (予定) Research・Jupyter Notebook 用のディレクトリ
├── data/                       # (予定) SQLite/DuckDBのファイルやParquetなどローカルのデータストア
└── config/                     # (予定) 環境設定・APIキー設定などのコンフィグファイル群
```

## 📄 Documentation Reference

本システムの根幹は**「データ駆動(Data Driven)」**および**「Single Windows Node（1台のWindowsPCで完結する構成）」**です。
開発を開始するにあたり、以下の設計ドキュメント・アーキテクチャ仕様を常に念頭に置いてください。

1. **`documents/00_Architecture/SystemArchitecture_統合案.md`**
   - システム全体を俯瞰するための起点ドキュメント。
   - 物理分離（LinuxとWindows分割）ではなく、プロセス分離・スケジュール分離で安全性を担保する設計方針を確認すること。
2. **`documents/01_Data/DataPlatform.md` & `DataSchema.md`**
   - 扱うすべてのデータ構造定義。データの品質と冪等性（Idempotency）、トレーサビリティの確保方法が記載されている。
3. **`documents/06_RiskManagement/RiskManagement.md`**
   - 本システムの「最後の砦」となるリスク管理ルール。あらゆる実装判断において、このドキュメントの許容リスク（ドローダウン上限、AIオーバーレイ上限＝10%など）に違反しないよう配慮する。
4. **`documents/08_Operations/Monitoring.md`**
   - 初期運用(Phase 1)向けとして、まずは `SQLite` + `Streamlit` による軽量な監視基盤構築を目指す方針を遵守する。

## 💻 Development Workflow

実装フェーズ（Pythonコーディング等）においては以下を標準とします。

- **Language / Environment**: Python 3.10以降推奨, Windows OS (API制限等により必須)
- **Database**: 分析用には `DuckDB` (+ Parquet)、軽量トランザクション・監視ログ用には `SQLite`
- **Code Rules (Recommended)**:
  - PEP 8 に準拠。`black`, `isort`, `flake8` (または `ruff`) を用いてフォーマットとLintを徹底する。
  - 型ヒント(Type hints)を積極的に活用し、`mypy`等での静的解析を前提とした堅牢な実装を心がける。

## 🌿 Git & Repository Workflow

- **Branching Strategy**: シンプルな GitHub Flow または Git Flow をベースとする。
  - `main`: 本番稼働可能（Production Ready）なコード。
  - `develop`: 日々の機能開発を統合していくブランチ。
  - `feature/*`: 新規モジュールや機能の開発を行うブランチ。
  - `fix/*` / `hotfix/*`: バグ修正を行うブランチ。
- **Commit Messages**: Conventional Commits 形式を推奨（例: `feat: add signal queue processing`, `fix: correct typo in DD limit`）。
- **Pull Request / Merge**: 重要な変更は、テストに合格したうえで `develop` もしくは `main` にマージすること。

## ⚙️ Architecture Constraints (Must Follow)

AIアシスタントや開発者がコードを生成・修正する際は、以下の制約を**絶対に破らないこと**：

1. **Look-ahead Bias（未来情報参照の禁止）**: バックテストと本番システムはロジックを共通化し、分析時において「未来のデータ」を誤って参照しないよう、現在時刻（Simulated Time）の注入機構を設けること。
2. **AIは直接発注しない**: AIやLLMはあくまでセンチメント分析などのスコア生成に留め、最終的な取引判断は `Strategy` 層を経由し、ルールベースにマッピングされた上で執行（Execute）されること。
3. **Idempotency（冪等な発注キュー）**: `signal_queue` を利用したPull型の実行アーキテクチャを遵守し、クラッシュ復旧時などに同じ発注が重複して実行される事故（二重発注）を確実に防ぐこと。
