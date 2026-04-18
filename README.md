# KabuSys

日本株向け自動売買／リサーチ基盤の参照実装リポジトリです。  
売買実行エンジン・監視（Monitoring）・ポートフォリオ構築・ファクター計算・AI（ニュースセンチメント／レジーム判定）などを含むモジュール群で構成されています。

---

## プロジェクト概要

KabuSys は次のような責務を持つモジュール群から構成されます。

- ExecutionEngine（発注エンジン）:
  - 本番（kabuステーション連携）／ペーパートレード（MockBroker）に対応
  - 注文管理、リスク管理、リコンシリエーションを統合して実行セッションを管理
- Monitoring（監視）:
  - システム状態、データ鮮度、注文ログ、リスク指標を定期的に取得・永続化
  - Kill Switch により条件に応じて Execution を停止可能
- Portfolio（銘柄選定・配分）:
  - 候補選定、等金額／スコア加重、リスクベースの株数算出、セクター制約など
- Research（ファクター算出・特徴量解析）:
  - Momentum / Volatility / Value などのファクター計算、IC 計測、統計サマリー
- AI（ニュース NLP / レジーム判定）:
  - OpenAI を用いたニュースセンチメント計算、マクロセンチメントとETF MAを合成したレジーム判定
- Utils / Tools:
  - ログ設定、プロセス優先度設定、設定ウィザード・検証ツール、ペーパートレード検証レポートなど

主要スクリプトはパッケージモジュールとして起動できます（例: python -m kabusys.run_execution）。

---

## 主な機能一覧

- 起動／停止制御
  - data/stop_requested.flag や data/kill.flag を用いた外部停止シグナル
- DB 永続化
  - SQLite（監視・ペーパートレード）と DuckDB（分析）を利用
- 監視（Monitoring）
  - CPU/memory/disk、Execution プロセスヘルス、データ鮮度、注文レコードの監視
  - RiskMonitor によるドローダウン／ポジション上限監視、KillSwitch の発動
  - アラート経路抽象化（AlertManager）を介して LINE 等へ通知可能（設定に依存）
- Execution（ExecutionEngine）
  - ブローカー抽象化（実口座 / モック切替）
  - リスク管理（最大ポジション比率、利用率、サーキットブレーカー等）
- Portfolio construction
  - 候補選定・スコア正規化・配分（等分／スコア重み）・単元株丸め
- Research
  - DuckDB 接続を受けたファクター計算（momentum, volatility, value）
  - 将来リターン／IC 計算、統計サマリー
- AI
  - OpenAI（gpt-4o-mini など）を用いたニュースセンチメント（ai_scores テーブルへ保存）
  - ETF(1321) の MA とマクロニュースで日次レジーム判定を行い market_regime へ保存
- CLI ユーティリティ
  - 設定ウィザード（config_setup）、設定検証（validate_config）、ペーパートレード検証レポート（tools.paper_verification_report）

---

## セットアップ手順

前提:
- Python 3.9+ を推奨（実装で型アノテーション等が使用されています）
- SQLite は標準ライブラリ内
- ネットワーク接続（OpenAI 利用時）

1. リポジトリをクローン／展開
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - 必要最低限:
     - duckdb
     - psutil
     - openai（AI 機能を使う場合）
   - 開発・追加:
     - PyYAML（config ファイル検証に使用。必須ではない）
   - 例:
     - pip install duckdb psutil openai PyYAML
4. .env の準備
   - 簡易ウィザードで作成:
     - python -m kabusys.config_setup
   - 手動で .env を作る場合は .env.example を参考にしてください（存在する場合）。
   - 自動ロード:
     - モジュール kabusys.config はプロジェクトルートから .env/.env.local を自動読み込みします。
     - 自動読み込みを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
5. 環境変数の主な一覧（重要）
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - KABUSYS_ENV (development|paper_trading|live) — デフォルト: development
   - OPENAI_API_KEY (AI 機能使用時必須)
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト: data/monitoring.db)
   - PAPER_TRADING_SQLITE_PATH (ペーパートレード専用 DB。デフォルト: data/paper_trading.db)
   - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
   - LOG_DIR（ログ出力先、デフォルト: logs/）
   - MONITOR_POLL_INTERVAL（監視ポーリング間隔: 秒、デフォルト 60）
   - PID_FILE_PATH / KILL_FLAG_PATH 等は Settings クラスから参照できます。

6. 初期 DB とディレクトリ
   - 初回実行時にデータディレクトリ（data）や logs は自動作成されますが、権限等で失敗する場合があるため事前に作成しておくと安全です。

---

## 使い方（主要スクリプト）

各スクリプトはパッケージモードで起動できます。プロジェクトルート（pyproject.toml / .git がある階層）で実行してください。

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 警告をエラー扱いにする: python -m kabusys.validate_config --strict

- 実行エンジン（ExecutionEngine）
  - 本番／ペーパー両対応。KABUSYS_ENV=paper_trading のときは MockBroker を使用し、PAPER_TRADING_SQLITE_PATH に書き込みます。
  - 起動:
    - python -m kabusys.run_execution
  - 停止:
    - data/stop_requested.flag を作成すると安全に停止します（スクリプトは起動時に stop flag をチェック）
    - Kill Switch（自動停止）: monitoring 側から data/kill.flag が書かれると ExecutionEngine は停止されます。

- 監視ループ（Monitoring）
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、デフォルト 60）。
  - 起動:
    - python -m kabusys.run_monitoring
  - 停止:
    - data/stop_requested.flag を作成または KeyboardInterrupt (Ctrl-C)
  - 備考:
    - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path（SQLITE_PATH）へ書き込みます。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数が優先されます）

- AI 機能（ニュース NLP / レジーム判定）
  - OPENAI_API_KEY が必要
  - ニューススコア付け:
    - 呼び出しはライブラリ API（kabusys.ai.score_news）として利用。CLI ラッパーは存在しません（スクリプトやバッチで呼び出して利用）。
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime を呼び出して market_regime に日次書き込みします。

---

## 実行時のファイル・フラグ

- data/
  - stop_requested.flag — スクリプト（run_execution/run_monitoring）の停止トリガ（存在を監視）
  - kill.flag — Kill Switch が発生した場合に書き込まれる（ExecutionEngine 停止用）
  - execution.pid — ExecutionEngine の PID を保持（engine 起動時に使用）
  - monitoring.db / paper_trading.db — SQLite DB（パスは環境変数で変更可能）
- logs/
  - 日次ローテートでアプリケーションログを保存（ファイル名: <app_name>.log）

---

## ディレクトリ構成

リポジトリの主要なファイル／ディレクトリ（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数・設定管理（.env 自動読み込み）
  - config_setup.py           — 対話式 .env ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード結果検証レポート生成
  - utils/
    - logging_setup.py        — 統一ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py        — SQLite 永続化レイヤ（テーブル初期化・CRUD）
    - monitoring_engine.py    — 複数 Monitor の統合ポーリング
    - system_monitor.py       — システム状態・データ鮮度監視
    - trade_monitor.py        — 注文ログ／滞留注文検出（省略されたが監視系に含まれる）
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — Kill Switch のフラグ書き込み
    - alert_manager.py        — アラート送信の抽象（LINE 等への通知を実装可能）
  - execution/
    - execution_engine.py     — 実行エンジン本体（EngineConfig 等）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py       — ブローカークライアント生成（Mock/Real 切替）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py             — ニュースを LLM でスコアリングして ai_scores に書込
    - regime_detector.py      — ETF MA + マクロニュースでレジーム判定
  - data/ (実行時に生成されることを想定)
  - logs/ (ログ保存ディレクトリ)

---

## 開発・運用上の注意

- .env は必ず管理下に入れず、機密情報（API トークン等）は適切に管理してください。
- KABUSYS_ENV=live の場合は設定内容（LINE 通知・KILL_FLAG_CLEAR_ON_START 等）に注意してください。validate_config の live 特有の警告を確認してください。
- Monitoring は SQLITE_PATH に監視ログを書きます。Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用する点に注意してください。
- AI 機能を使う場合は API レート制限・失敗に備えて実装側でリトライやフォールバックを設けていますが、運用側でも OPENAI_API_KEY の使用量を監視してください。
- プロセス優先度設定はプラットフォーム依存です。Linux/Windows に対応しますが権限不足や未サポート環境ではスキップされます（警告ログのみ）。

---

## よく使うコマンドまとめ

- .env 作成（対話式）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- Execution 起動
  - python -m kabusys.run_execution
- Monitoring 起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要に応じて、README に追記したい内容（例: API ドキュメント、設定サンプル、SQL スキーマの詳細、デプロイ手順等）を教えてください。README を拡張して詳しい手順やコード例を追加します。