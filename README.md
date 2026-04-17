# KabuSys

日本株自動売買システム（ライブラリ / 実行スクリプト群）

このリポジトリは、システム監視、発注実行、ペーパートレード検証、ファクター/リサーチ、AI ニューススコアリング等を含む自動売買プラットフォームの実装群を含みます。各コンポーネントはできるだけサイドエフェクトを抑え、テスト可能性と本番/ペーパー分離を意識して設計されています。

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 環境変数（.env）/ 重要設定
- 使い方（主要コマンド）
- 停止 / Kill Switch / フラグファイル
- ディレクトリ構成（主なファイル説明）
- 注意事項

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の領域を含むモジュール群です。

- 発注実行エンジン（ExecutionEngine）と注文管理
- 監視（System / Trade / Risk）のポーリングループ
- Kill Switch（条件に応じたエンジン停止）
- ポートフォリオ構築（候補選定・重み付け・株数算出）
- リサーチ（ファクター計算 / 将来リターン / IC 等）
- AI を用いたニュースセンチメント（OpenAI を利用）
- ペーパートレード用の検証レポート生成ツール
- 設定ウィザードおよび設定検証 CLI

設計方針として、発注や本番 DB へのアクセスは環境に依存し、paper_trading モードでは本番 DB と明確に分離されます。

---

## 主な機能

- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading のときは MockBroker を使用し、paper_trading 専用 SQLite DB に記録
  - プロセス優先度（High）に設定
  - execution.pid の管理、stop flag による終了制御

- Monitoring（run_monitoring.py / MonitoringEngine）
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせたポーリング
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）
  - 監視情報は SQLite（monitoring.db）に永続化

- Kill Switch
  - リスク閾値（ドローダウン、ポジション上限）到達で data/kill.flag を書き込み、ExecutionEngine を停止

- Portfolio（選定・重み付け・ポジションサイズ決定）
  - 等配分、スコア加重、リスクベース算出
  - セクター制限・レジーム乗数による調整

- Research（DuckDB を使ったファクター計算）
  - Momentum / Volatility / Value 等のファクター計算
  - forward returns, IC, factor summary など

- AI（ニュース NLP / レジーム判定）
  - OpenAI（gpt-4o-mini 指定）でニュースをまとめて銘柄ごとに -1.0〜1.0 のスコア化
  - マクロニュース + ETF ma200 を合成して市場レジーム判定
  - API 呼び出しはリトライやフェイルセーフを考慮（失敗時は安全なフォールバック）

- ツール
  - config_setup: 対話式 .env 作成ウィザード
  - validate_config: .env や config/*.yaml の事前検証 CLI
  - paper_verification_report: ペーパートレード結果の検証レポート生成

---

## セットアップ手順

1. Python の仮想環境を作る（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要ライブラリをインストール
   - 最低限推奨パッケージ（本リポジトリに requirements.txt は含まれていないため適宜インストールしてください）：
     - psutil
     - duckdb
     - openai
     - requests
     - PyYAML（config の YAML 検証を行う場合）
   - 例:
     - pip install psutil duckdb openai requests PyYAML

3. .env の準備
   - 対話式ウィザードで生成（推奨）:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に手動で作成してください。
   - 自動ロードはデフォルトで有効（プロジェクトルートに .env / .env.local があれば読み込み）。テストで無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 設定検証
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合:
     - python -m kabusys.validate_config --strict

5. データディレクトリ
   - デフォルトで使用するパス:
     - DuckDB: data/kabusys.duckdb
     - Monitoring SQLite: data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
   - 必要に応じて .env の `DUCKDB_PATH`, `SQLITE_PATH`, `PAPER_TRADING_SQLITE_PATH` を設定してください。

---

## 環境変数（主なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用
  - KABU_API_PASSWORD: kabuステーション API パスワード

- 実行モード
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）

- DB / ファイルパス
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、default: data/paper_trading.db)
  - PID_FILE_PATH (default: data/execution.pid)
  - KILL_FLAG_PATH (default: data/kill.flag)
  - KILL_FLAG_CLEAR_ON_START (0/1) — 起動時に kill.flag を自動でクリアするか（本番では 0 推奨）

- Paper Trading 動作
  - PAPER_FILL_MODE: instant | partial | never | reject（default: instant）

- ログ / モニタリング
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、run_monitoring で使用。デフォルト 60）

- OpenAI
  - OPENAI_API_KEY: AI モジュール（news_nlp / regime_detector）で使用

- LINE 通知（任意）
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID

その他の設定は config/*.yaml を参照してください（存在する場合は validate_config でチェックされます）。

---

## 使い方（主要なコマンド）

- 設定ウィザード（対話式で .env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード（警告も失敗扱い）:
    - python -m kabusys.validate_config --strict

- ExecutionEngine 起動（発注エンジン）
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合、MockBroker を使用し data/paper_trading.db に記録（本番 DB と分離）
    - 実行前に data 直下の stop/kill フラグ（data/stop_requested.flag, data/kill.flag）があると起動しない / 即時停止
    - プロセス優先度を high に設定し execution.pid を管理

- Monitoring 起動（監視ポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更（秒）
  - 監視は本番用 sqlite_path を環境に関わらず使用します（監視ログの一元化）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - デフォルト DB は PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI スコアリング（プログラム上での使用）
  - ニューススコアリング: kabusys.ai.score_news（DuckDB 接続・target_date・api_key を渡す）
  - レジーム判定: kabusys.ai.regime_detector.score_regime（同様に使用）
  - OpenAI API キー（OPENAI_API_KEY）を設定すること。失敗時は安全フォールバックが働きますが、API キーは必須関数もあります。

---

## 停止 / Kill Switch / フラグファイル

- ExecutionEngine の停止信号はファイルベース（data/stop_requested.flag または data/kill.flag）で実装されています。
  - run_execution / run_monitoring は起動前に stop フラグをチェックし、ループ中も定期的に確認して安全に停止します。
  - KillSwitch（監視側）は一定の条件（ドローダウン超過、ポジション数超過等）で data/kill.flag を書き込み、実行エンジンを停止させます。
  - kill.flag を自動クリアする挙動は KILL_FLAG_CLEAR_ON_START を 1 にすると起動時にクリアされます（本番では 0 推奨）。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数 / Settings 管理（.env 自動ロードロジック）
  - config_setup.py — 対話式 .env 生成ウィザード
  - validate_config.py — 設定検証 CLI

  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト

  - execution/ — 発注関連（Engine, BrokerFactory, OrderManager 等）
    - execution_engine.py, broker_factory.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, order_record.py など（詳細は該当ファイルを参照）

  - monitoring/
    - monitoring_db.py — SQLite による監視ログ永続化層（テーブル生成・CRUD）
    - system_monitor.py — システム / データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — Kill Switch 実装
    - monitoring_engine.py — 複数モニタの調整とポーリングループ
    - alert_manager.py — LINE Push 通知ユーティリティ

  - portfolio/
    - portfolio_builder.py — 候補選定、重み計算
    - position_sizing.py — 株数算出・アロケーションロジック
    - risk_adjustment.py — セクター制限・レジーム乗数

  - research/
    - factor_research.py — Momentum / Volatility / Value 等
    - feature_exploration.py — forward returns / IC / 統計サマリー

  - ai/
    - news_nlp.py — ニュースを OpenAI でスコアリングして ai_scores に書き込む
    - regime_detector.py — マクロ + ETF MA200 を使ったレジーム判定

  - tools/
    - paper_verification_report.py — ペーパートレードの検証レポート生成ツール

  - utils/
    - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ

- data/（実行時に使用するファイル、デフォルトパス）
  - kabusys.duckdb
  - monitoring.db
  - paper_trading.db
  - execution.pid
  - kill.flag / stop_requested.flag

---

## 注意事項 / 運用メモ

- 本番環境（KABUSYS_ENV=live）では .env の設定を十分に確認してください（validate_config の警告を確認）。
- .env は機密情報を含むため絶対に Git にコミットしないでください（config_setup も README に注意書きを出します）。
- Process priority / CPU affinity の設定には OS 権限が必要な場合があります（psutil を利用）。権限がない場合は警告を出してスキップされます。
- OpenAI 呼び出しはコストとレート制限があるため、API キーの管理と呼び出し頻度に注意してください。
- DuckDB / SQLite のファイルパスは .env で変更可能。Paper trading は本番と DB を分離するため、必ず PAPER_TRADING_SQLITE_PATH を確認してください。
- monitoring は本番 sqlite_path を使って監視ログを記録します。監視だけで本番 DB に影響を与えることは基本的にありませんが、運用時は権限やパスに注意してください。

---

もし README に追記してほしい詳細（例えば各設定ファイルのサンプル、発注ワークフロー図、CI / デプロイ手順など）があれば教えてください。必要に応じて具体的な .env.example も作成できます。