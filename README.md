# KabuSys — 日本株自動売買システム

このリポジトリは日本株の自動売買とそれに付随する監視 / 研究 / ツール類を含む小規模なシステムです。  
以下はコードベースから作成した README です。各スクリプトは src/kabusys 以下に実装されています。

---

## プロジェクト概要

KabuSys は次の主要機能を持つ自動売買フレームワーク／補助ツール群です。

- 注文実行エンジン（ExecutionEngine: 実際のブローカーまたはペーパートレード用の Mock を利用）
- モニタリング（システム稼働・データ鮮度・注文状態・リスク監視）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制約など）
- 研究用モジュール（ファクター計算、特徴量解析、IC 計算）
- AI 補助（ニュースの NLP スコアリング、レジーム判定）
- 運用支援ツール（.env ウィザード、設定検証、ペーパートレード検証レポートなど）

設計方針の一部：
- DB（分析用）に DuckDB、運用ログ・監視に SQLite を使用
- 本番とペーパートレードを明確に分離（別 SQLite ファイル）
- OpenAI を用いた NLP 処理をサポート（API キーは環境変数で指定）
- 自動化スクリプトはモジュールとして実行可能（python -m kabusys.xxx）

---

## 機能一覧（主要コンポーネント）

- run_execution.py
  - ExecutionEngine の起動スクリプト
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、data/paper_trading.db を利用
  - 停止フラグ（data/stop_requested.flag）を見て安全停止
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
  - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔の上書き（デフォルト 60 秒）
  - 監視用 DB（SQLite）への永続化
- config_setup.py
  - .env の対話式ウィザード（初期作成/更新）
- validate_config.py
  - .env と config/*.yaml を起動前に検証する CLI（--strict オプションあり）
- tools/paper_verification_report.py
  - ペーパートレードログ（SQLite）から検証レポートを生成
- portfolio/*
  - 銘柄選定、重み計算、リスク調整（セクター上限・レジーム乗数）、ポジションサイズ計算
- research/*
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 特徴量探索・IC（Information Coefficient）計算
- ai/*
  - news_nlp.py: OpenAI を用いたニュース記事の銘柄別センチメントスコアリング
  - regime_detector.py: マクロ＋ETF 指標から市場レジーム判定
- monitoring/*
  - monitoring_db.py: SQLite テーブル初期化 / 永続化ラッパー
  - system_monitor.py, trade_monitor.py, risk_monitor.py, monitoring_engine.py, kill_switch.py, alert_manager.py（アラート管理等）

ユーティリティ:
- utils/logging_setup.py: 統一的なロギング設定（コンソール + 日次ローテーション）
- utils/process_priority.py: プロセス優先度・CPU affinity の設定

---

## セットアップ手順（開発 / 実行）

前提
- Python 3.10 以上を推奨（typing の `X | Y` 構文等を使用）
- Git リポジトリのルートに `pyproject.toml` か `.git` があると自動で .env を探索します

1. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリをインストール
   - pip install duckdb psutil openai
   - ※ PyYAML は設定ファイル検証（validate_config）が YAML のパースを行う場合に必要: pip install pyyaml

   （プロジェクトに requirements.txt がない場合は上記を必要に応じて追加してください）

3. 環境変数設定（.env）
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - もしくは .env を手動作成（.env.example を参考）
   - 自動読み込みはデフォルトで ON。テストなどで無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合:
     - python -m kabusys.validate_config --strict

5. データディレクトリ作成（必要に応じて）
   - data/ や logs/ は自動作成されますが、権限や配置方針に応じて事前に準備してください。

---

## 主要な環境変数（要確認）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — default: development
  - paper_trading の場合、専用 SQLite（PAPER_TRADING_SQLITE_PATH）を利用
- OPENAI_API_KEY — AI 機能（news_nlp, regime_detector）で使用
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — paper_trading の約定挙動 (instant|partial|never|reject)
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- LOG_DIR — ログ出力ディレクトリ（default: logs）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START — 本番での自動 kill.flag クリア抑止の確認用（0/1）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — アラート通知（任意）

---

## 使い方（実行コマンド例）

- .env を作成・編集
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（デフォルト: .env の KABUSYS_ENV に従う）
  - python -m kabusys.run_execution
  - 注: 起動時に data/stop_requested.flag が存在すると起動せず終了します

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する場合:
    - export MONITOR_POLL_INTERVAL=30
    - python -m kabusys.run_monitoring

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 範囲指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI スコアリング / レジーム判定（プログラム API）
  - kabusys.ai.score_news(conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

- ログ設定
  - すべての起動スクリプトは kabusys.utils.logging_setup.setup_logging を使います
  - ログファイル: <LOG_DIR>/<app_name>.log（デフォルト: logs/<app_name>.log）

停止／kill フラグ
- 停止要求（外部から安全停止）:
  - data/stop_requested.flag を作成すると run_execution/run_monitoring は検知して停止
- Kill Switch（自動的に Execution を停止する条件が満たされた場合に作成）:
  - data/kill.flag が作成されると ExecutionEngine が停止シグナルとして扱います
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時にこのフラグを自動でクリアします（本番では注意）

---

## ディレクトリ構成（主要ファイル・モジュール）

（src/kabusys 以下を想定）

- __init__.py
- config.py
  - Settings クラス: 環境変数の解決・検証・便利プロパティを提供
- config_setup.py
  - .env 対話ウィザード
- validate_config.py
  - 起動前チェック CLI

- run_execution.py
  - ExecutionEngine 起動ラッパー
- run_monitoring.py
  - SystemMonitor ポーリングループ起動ラッパー

- utils/
  - logging_setup.py: ロギング統一設定
  - process_priority.py: 優先度設定 / CPU affinity
  - __init__.py

- monitoring/
  - monitoring_db.py: SQLite のスキーマ初期化 / 永続化ラッパー
  - system_monitor.py: システムモニタ（CPU / メモリ / データ鮮度 / 実行プロセス監視）
  - trade_monitor.py: 注文ログ監視（stale orders など）
  - risk_monitor.py: ドローダウン / ポジション上限監視
  - kill_switch.py: kill.flag 制御
  - monitoring_engine.py: 各 Monitor を束ねるエンジン
  - alert_manager.py: （アラート送信ロジック）

- execution/
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - broker_factory.py
  - reconciler.py
  - risk_manager.py
  - （実際の実装に依存するファイル群）

- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py

- research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py

- ai/
  - news_nlp.py
  - regime_detector.py
  - __init__.py

- data/
  - （デフォルトの DB 等は data/ に作成される: monitoring.db, paper_trading.db, kabusys.duckdb）
- logs/
  - （ログファイルが出力される）

---

## 開発上の注意点 / 運用メモ

- DuckDB は分析向けの高速クエリエンジンとして利用。テーブル名（prices_daily など）に依存するコードが多いです。
- Monitoring は監視 DB（SQLite）にログを書き、KillSwitch が条件を満たすと kill.flag を作ることで Execution を停止させます。kill.flag の取り扱いは慎重に行ってください（本番では自動クリア設定はオフ推奨）。
- AI 呼び出し（OpenAI）はレート制限や一時エラーに対してリトライ／フェイルセーフの実装がありますが、API キーとコスト管理は十分注意してください。
- ペーパートレード環境では本番 DB と明確に分離されています（PAPER_TRADING_SQLITE_PATH）。
- ロギングはデフォルトで stdout と日次ローテートファイル両方に出力します。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。

---

README はここまでです。必要であれば次の改善案を追加します：
- 実行フロー図（起動順序 / ファイルフラグの状態遷移）
- よくある運用手順（デプロイ手順、crontab / systemd サンプル）
- テストの実行方法や CI 設定例

ご希望があれば追加で作成します。