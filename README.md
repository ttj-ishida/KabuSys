# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買システム（KabuSys）のコアライブラリ群および起動スクリプトを含みます。  
README は日本語で、プロジェクト概要、機能、セットアップ、使い方、ディレクトリ構成を説明します。

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群で構成された自動売買システムです。

- 取引ロジック（シグナル→ポートフォリオ構築→発注）
- Execution エンジン（ブローカークライアントを通じた発注・ロジック実行）
- Monitoring（システム健全性・注文状態・リスク監視）
- Research（ファクター計算・特徴量解析）
- AI 補助（ニュースセンチメント評価、レジーム判定）
- Paper Trading（ペーパートレード用の分離 DB と検証ツール）

設計のポイント：
- 環境変数 / .env による設定管理（Settings クラス）
- DuckDB を用いた研究/分析データ、SQLite を監視・発注ログ用に使用
- OpenAI を用いたニュース NLP（任意）
- Monitoring と Execution はフラグファイルで停止/制御可能

---

## 主な機能一覧

- 設定管理
  - .env 自動読み込み（プロジェクトルートの .env / .env.local）
  - 設定ウィザード（対話式 .env 生成: `config_setup`）
  - 設定検証 CLI（`validate_config`）

- Execution（発注エンジン）
  - 本番 / ペーパートレードの切り替え（KABUSYS_ENV）
  - Risk Manager、Order Manager、Reconciler、ExecutionEngine の組み立て
  - 発注ログを SQLite に永続化、DuckDB へも出力可能
  - PID / stop フラグファイルを用いた制御

- Monitoring（監視）
  - システムリソース（CPU/MEM/DISK）、プロセス生存、データ鮮度を監視
  - 注文の滞留・約定異常検出
  - ドローダウン・ポジション数監視と Kill Switch（kill.flag 書き込み）
  - 監視ログの永続化（SQLite）

- Portfolio / Strategy
  - 銘柄選定、重み計算（等配分・スコア加重）
  - セクター制限、レジーム乗数の適用
  - 株数算出（単元丸め、リスクベース配分、利用可能現金に対するスケーリング）

- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB 上 SQL）
  - 将来リターン、IC 計算、統計サマリー

- AI（任意）
  - ニュースセンチメント評価（OpenAI）
  - 市場レジーム判定（ETF ma200 と LLM の組合せ）
  - OpenAI 呼び出しはリトライやフォールバック設計

- ツール
  - Paper Trading 検証レポート生成（`tools.paper_verification_report`）

---

## 前提条件 / 必要環境

- Python 3.9+
- 推奨パッケージ（一部は任意）
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（設定検証で YAML 検証を行う場合）
- ファイルシステムに書き込み可能な `data/`（デフォルト DB/フラグ場所）、`logs/`（ログ）

インストール例（pip）:
```bash
python -m pip install duckdb psutil openai PyYAML
```

注意: OpenAI を使用する機能を利用する場合は環境変数 `OPENAI_API_KEY` を設定してください。

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
   - 本 README の想定構成は `src/kabusys` 配下のモジュールがある状態です。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install -r requirements.txt
   - （requirements.txt が無い場合は上記の個別パッケージをインストール）

4. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - または `.env.example` を参考に `.env` を作成（プロジェクトルート）

5. 設定検証（起動前に推奨）
   - python -m kabusys.validate_config
   - 厳密モード（警告があると終了コード 1）:
     - python -m kabusys.validate_config --strict

6. データディレクトリの初期化
   - デフォルトの SQLite / DuckDB ファイルは `data/` 下に作成されます。
   - `logs/` ディレクトリの作成はログ設定が自動で行いますが、パーミッション確認を推奨。

---

## 主要環境変数（よく使うもの）

- 必須（起動前に設定）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境
  - KABUSYS_ENV: development | paper_trading | live (デフォルト: development)

- DB パス
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (ペーパートレード時の専用 DB、デフォルト: data/paper_trading.db)

- ログ
  - LOG_LEVEL (DEBUG/INFO/...)
  - LOG_DIR (デフォルト: logs/)

- AI
  - OPENAI_API_KEY

- Monitoring
  - MONITOR_POLL_INTERVAL （秒。run_monitoring のポーリング間隔、デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START （本番での自動クリアは危険: デフォルト 0）

- Paper trading
  - PAPER_FILL_MODE: instant | partial | never | reject

---

## 使い方（起動・コマンド）

主要なモジュールはパッケージモジュールとして起動できます。プロジェクトルート（`src` の親）で実行してください。

- 設定ウィザード（対話式 .env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- ExecutionEngine を起動（実働 / ペーパートレード切替は KABUSYS_ENV で）
  - python -m kabusys.run_execution
  - 実行中は `data/execution.pid` を作成し、停止は `data/stop_requested.flag` を作成することで通知

- Monitoring を起動（監視ループ）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で秒単位に変更可能（デフォルト 60）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH

- AI / リサーチ機能は API を呼び出す関数群として提供（ライブラリ利用）
  - ニューススコアリング: kabusys.ai.score_news（DuckDB 接続と日付を渡す）
  - レジーム判定: kabusys.ai.regime_detector.score_regime

ログや停止フラグ:
- 停止フラグ（強制停止シグナル）: data/kill.flag（KillSwitch）
- 停止要求（run_execution/run_monitoring の外部停止）: data/stop_requested.flag
- PID ファイル: data/execution.pid

注意:
- Monitoring は Settings にかかわらず監視用の sqlite_path（デフォルト data/monitoring.db）を使用します。
- ExecutionEngine は KABUSYS_ENV=paper_trading のとき PAPER_TRADING_SQLITE_PATH を使用して本番 DB と完全分離します。

---

## 主要スクリプト / エントリポイント一覧

- python -m kabusys.config_setup
- python -m kabusys.validate_config
- python -m kabusys.run_execution
- python -m kabusys.run_monitoring
- python -m kabusys.tools.paper_verification_report

--- 

## ディレクトリ構成（抜粋）

リポジトリ内の主要なパッケージ構成（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                — 環境変数・Settings 管理（.env 自動ロード含む）
  - config_setup.py          — 対話式 .env ウィザード
  - validate_config.py       — 設定検証 CLI

  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト

  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ

  - monitoring/
    - monitoring_db.py       — 監視用 SQLite 永続化層（テーブル初期化・CRUD）
    - system_monitor.py      — システム状態 / データ鮮度監視
    - trade_monitor.py       — 注文系の監視（※実装ファイルあり）
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — kill.flag の書き込み / 管理
    - monitoring_engine.py   — 各 monitor を束ねるポーリングエンジン
    - alert_manager.py       — アラート送信（LINE 等）（※実装ファイルあり）

  - execution/
    - execution_engine.py    — ExecutionEngine 実装（セッション管理）
    - broker_factory.py      — ブローカークライアント生成
    - order_manager.py       — 注文管理
    - order_repository.py    — 注文永続化
    - reconciler.py          — ブローカーとの突合せ
    - risk_manager.py        — 発注前リスクチェック

  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - risk_adjustment.py     — セクター制限・レジーム乗数
    - position_sizing.py     — 株数決定ロジック

  - research/
    - factor_research.py     — Momentum/Value/Volatility の計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー

  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI を使ったセンチメント）
    - regime_detector.py     — レジーム判定（MA200 + LLM）

  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート出力

- data/                      — デフォルト DB / フラグ / PID（実行時に作成）
- logs/                      — ログ出力（デフォルト、日次ローテーション）

---

## 開発メモ / 注意点

- 設定ファイル（.env）は絶対にバージョン管理に含めないこと（機密情報を含む）。
- 本番（KABUSYS_ENV=live）では `KILL_FLAG_CLEAR_ON_START` を `0` に設定することを推奨。
- OpenAI 等外部 API は失敗時にフォールバック設計が入っているが、API キー未設定では該当機能は動作しません。
- `psutil` を用いてプロセス優先度や CPU affinity を設定しますが、権限により設定できない場合は warning が出ます。
- DuckDB / SQLite のスキーマはコード内で必要に応じてマイグレーション（ALTER）処理があります。

---

ご不明点や README の追加項目の希望があれば教えてください。必要に応じてセットアップ手順や実行例（systemd サービス定義や Dockerfile など）を追記できます。