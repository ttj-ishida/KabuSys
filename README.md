# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買プラットフォーム（KabuSys）の実装です。戦略・ポートフォリオ構築、発注エンジン、監視、研究用ユーティリティ、AI（ニュースセンチメント / レジーム判定）などのモジュールで構成されています。

注意: README はコードベースから自動生成した概要です。実運用前に `.env` の内容や各種設定を十分に確認してください。

---

## 概要

- 戦略（ファクター計算・特徴量解析）とポートフォリオ構築（銘柄選定・重み付け・株数算出）を行う研究/運用モジュール
- ExecutionEngine による発注・リスク管理・注文調整（paper_trading モードではモックブローカーで完全分離）
- 監視モジュール（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager）によるプロセス・データ鮮度・注文状況・ドローダウン監視
- AI モジュール（OpenAI を使ったニュースセンチメント / マクロセンチメント → レジーム判定）
- DuckDB（分析用）と SQLite（監視・発注履歴等）の併用
- ユーティリティツール（環境設定ウィザード、設定検証、Paper Trading 検証レポート生成 等）

主要な実行モード:
- development: ローカル開発用（発注なし）
- paper_trading: ペーパートレード（MockBrokerClient を使用、専用 DB に記録）
- live: 本番（実際に発注）

---

## 主な機能一覧

- 設定管理
  - .env 自動読み込み（プロジェクトルートの `.env` / `.env.local`）
  - インタラクティブな設定ウィザード（`kabusys.config_setup`）
  - 起動前の設定検証 CLI（`kabusys.validate_config`）
- 発注・実行
  - ExecutionEngine（発注、リスク管理、order manager、reconciler 等）
  - Paper trading 用に発注ログを分離（`PAPER_TRADING_SQLITE_PATH`）
- 監視・Kill Switch
  - SystemMonitor: CPU/メモリ/ディスク、プロセス存在確認、データ鮮度チェック
  - TradeMonitor: 滞留注文、約定異常価格検出
  - RiskMonitor: ドローダウン、ポジション上限のチェック
  - KillSwitch: 条件に応じて `data/kill.flag` を書き込み ExecutionEngine を停止
  - MonitoringEngine: 上記をまとめてポーリング実行、アラート通知連携
- ポートフォリオ構築
  - 銘柄選定、等重・スコア加重、リスクベースの株数算出、セクター制限、レジーム乗数
- 研究
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC 計算、統計サマリー、ランク付けユーティリティ
- AI（OpenAI）
  - ニュース記事を銘柄ごとに集約してセンチメント (−1.0〜1.0) を算出して ai_scores に保存
  - マクロニュース + ETF MA を用いた日次レジーム判定（bull/neutral/bear）
- ツール
  - Paper Trading 検証レポート生成（稼働率、注文成功率、レイテンシ等の評価）

---

## 前提（推奨） / 依存関係

必須:
- Python 3.9+（実際の互換性はプロジェクトポリシーに依存）
- pip

推奨（コードで使用されている外部モジュール）:
- duckdb
- psutil
- openai
- PyYAML（config 検証で任意）
その他: 標準ライブラリの sqlite3 等

インストール例（仮）:
- 仮想環境作成:
  - python -m venv .venv
  - source .venv/bin/activate（Windows は .venv\Scripts\activate）
- 必要パッケージをインストール:
  - pip install duckdb psutil openai pyyaml

（requirements.txt があるなら `pip install -r requirements.txt` を使用してください）

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化する。
2. 依存パッケージをインストールする（上記参照）。
3. 環境変数の設定
   - インタラクティブウィザード（推奨）:
     - python -m kabusys.config_setup
     - これでプロジェクトルートに `.env` が生成されます（絶対に Git にコミットしないでください）
   - 手動の場合は `.env` に必要値を設定:
     - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
     - 推奨: KABUSYS_ENV（development|paper_trading|live）、DUCKDB_PATH、SQLITE_PATH、OPENAI_API_KEY（AI機能を使う場合）
     - その他: LOG_LEVEL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID, PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH など
4. 起動前検証:
   - python -m kabusys.validate_config
   - 問題がある場合は出力に従って修正してください
5. データディレクトリ:
   - デフォルトでは `data/` に DB や PID / flag ファイルが作成されます。必要に応じてパスを `.env` で変更してください。

---

## 使い方（主要スクリプト／コマンド）

- 設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config [--strict]
- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 動作モードは `KABUSYS_ENV` 環境変数で制御:
    - paper_trading の場合は MockBroker を使用し、`PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）にデータを記録
- 監視ポーリング起動（監視ループ）
  - python -m kabusys.run_monitoring
  - ポーリング間隔: 環境変数 `MONITOR_POLL_INTERVAL`（秒、デフォルト 60）
  - 監視は本番 sqlite_path（`SQLITE_PATH`）を利用（環境に依存せず本番監視 DB を使用）
- 停止方法
  - 監視 / 実行ループを外部から確実に停止するにはプロジェクトルートの `data/stop_requested.flag` を作成（両スクリプトはこれを検知して安全終了）
  - ExecutionEngine を即時停止させるための Kill Switch は `data/kill.flag`（KillSwitch によって作成） — ExecutionEngine 起動時に `KILL_FLAG_CLEAR_ON_START` を 1 にしていると起動時に自動クリアされる（本番では 0 推奨）
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 `PAPER_TRADING_SQLITE_PATH` または `data/paper_trading.db`
- AI 機能（ニューススコア / レジーム）
  - OPENAI_API_KEY を設定しておくと、`kabusys.ai.news_nlp.score_news` や `kabusys.ai.regime_detector.score_regime` を呼び出して ai_scores / market_regime に書き込めます
  - 実行はコード内から呼び出す想定（スケジューラや起動フローに組み込む）

---

## 主要設定項目（環境変数）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

運用関連:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
- OPENAI_API_KEY: OpenAI を利用する場合に必要

DB / パス:
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- PID_FILE_PATH（実行エンジン PID ファイル、デフォルト: data/execution.pid）
- KILL_FLAG_PATH（kill.flag のパス、デフォルト: data/kill.flag）

監視関連:
- MONITOR_POLL_INTERVAL（秒、デフォルト 60）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT（監視しきい値）

Paper / Mock ブローカー:
- PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）

その他:
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（1 = クリア、0 = クリアしない。開発のみでの利用推奨）

---

## ディレクトリ構成（コードから抽出）

以下は主要なファイル・モジュールの概要です（src/kabusys を想定）:

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / 設定読み込みロジック（.env 自動読み込み含む）と Settings クラス
  - config_setup.py — 対話式 .env 作成ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor のポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - ai/
    - news_nlp.py — ニュース記事の LLM によるセンチメント算出と ai_scores 書き込み
    - regime_detector.py — ETF MA + マクロセンチメントから市場レジーム判定
  - monitoring/
    - monitoring_db.py — SQLite ベースの監視 DB 初期化 / 永続化層
    - monitoring_engine.py — MonitoringEngine（各 Monitor を束ねる）
    - system_monitor.py — CPU / メモリ / データ鮮度 / プロセスチェック
    - trade_monitor.py — 滞留注文・約定異常検出
    - risk_monitor.py — ドローダウンおよびポジション上限監視
    - kill_switch.py — Kill Switch（kill.flag 書き込み）
    - alert_manager.py — アラート通知管理（※ファイル末尾に続いている実装）
  - execution/ (概念的に存在)
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py, order_record.py など — 発注・リスク管理・リポジトリ
  - portfolio/
    - portfolio_builder.py — 候補選定、等重/スコア重み
    - position_sizing.py — 株数算出、aggregation cap、lot rounding
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン、IC、サマリー等
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - tools/ — ユーティリティスクリプト群

（実際のリポジトリにはさらにモジュール・補助ファイルが含まれる場合があります）

---

## 運用上の注意・補足

- paper_trading モードは「本番 DB と完全に分離」される設計です（`PAPER_TRADING_SQLITE_PATH` を使用）。
- Monitoring は環境にかかわらず監視用 SQLite（`SQLITE_PATH`）を使用します（監視ログは本番 DB に保存される想定）。
- OpenAI を利用する機能は API キーと外部コストを伴うため、テスト環境では API を呼ばない設計・モック化を推奨します。テスト時は該当関数の差し替え（patch）を利用可能。
- プロセス優先度 / CPU affinity の設定は OS に依存します。`psutil` の権限により失敗する場合はログに警告が出力されます。
- DB の初期化（monitoring DB 等）は idempotent（複数回実行しても安全）に実装されています。既存スキーマにカラムを追加する軽微なマイグレーション処理も含まれています。
- kill.flag / stop_requested.flag / execution.pid といったファイルベースの制御を採用しています。CI / デプロイ環境での取り扱いに注意してください。

---

もし README に追加してほしい内容（例: 実際のコマンド例、デプロイ手順、CI 設定、より詳細なディレクトリツリー、サンプル .env.example）や、特定モジュールの詳しい説明が必要であれば教えてください。