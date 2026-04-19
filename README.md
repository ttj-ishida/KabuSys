# KabuSys

日本株自動売買システムの軽量コアライブラリ / 実行ユーティリティ群です。本リポジトリはトレード実行・監視・ポートフォリオ構築・リサーチ・AI アシスト（ニュース NLP / レジーム判定）などの主要コンポーネントを含みます。

> 注: この README は src/kabusys 以下のソースコードを基に作成しています。

## 概要

- 実行エンジン（ExecutionEngine）と監視ループ（Monitoring）を分離して運用できます。
- Paper Trading（ペーパートレード）モードをサポートし、本番 DB と分離して動作します。
- DuckDB を用いたリサーチ / ファクター計算、SQLite を用いた監視ログ永続化。
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメントと市場レジーム判定モジュールを内包（API キー必須）。
- 簡易的な Kill Switch（フラグファイル）、PID 管理、ログ日次ローテーション等を備えます。

## 主な機能一覧

- 実行（Execution）
  - BrokerClientFactory によるブローカークライアント解決（実口座 / モック切替）
  - OrderManager / RiskManager / Reconciler / ExecutionEngine（発注管理・リスク制御）
  - Paper Trading 時は専用 SQLite（data/paper_trading.db デフォルト）へ記録

- 監視（Monitoring）
  - SystemMonitor: CPU / メモリ / ディスク / プロセス状態 / データ鮮度
  - TradeMonitor: 注文滞留・約定異常等の検出（trade_logs 等）
  - RiskMonitor: ドローダウン監視・ポジション上限チェック
  - KillSwitch: 条件に応じて data/kill.flag を生成し ExecutionEngine に停止信号を送出
  - MonitoringEngine: 各モニターの統合およびアラート発行

- ポートフォリオ構築（純粋関数群）
  - 候補選定、重み計算（等金額 / スコア加重）、セクター制約、ポジションサイズ計算（lot 単位処理・aggregate cap）

- リサーチ / ファクター計算（DuckDB）
  - Momentum / Volatility / Value などファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- AI（OpenAI）
  - news_nlp: ニュース集合を LLM へ送り銘柄別センチメントを ai_scores に書き込み
  - regime_detector: ETF MA200 乖離 + マクロニュースセンチメントを組み合わせ市場レジームを判定

- ツール・ユーティリティ
  - 環境設定ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）
  - ロギング・プロセス優先度ユーティリティ等

## 必要条件（推奨）

- Python 3.10+
- 必要 Python パッケージ（代表例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証時に YAML を検査したい場合）
- 標準ライブラリ: sqlite3 等（Python 標準）

（requirements.txt は本コードからは提供されていません。使用する機能に応じて上記パッケージをインストールしてください。）

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

## セットアップ手順

1. リポジトリをクローン / 展開し、プロジェクトルートに移動します（.git または pyproject.toml が存在する場所がプロジェクトルートとして扱われます）。

2. 仮想環境を作成して依存パッケージをインストールします（上記参照）。

3. .env の作成（対話式ウィザード推奨）
```
python -m kabusys.config_setup
```
ウィザードはプロジェクトルートの .env を読み書きします。必須項目:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

4. 設定の検証
```
python -m kabusys.validate_config
# 警告も FAIL としたい場合:
python -m kabusys.validate_config --strict
```

5. データディレクトリ等の準備（自動作成される場合あり）
- デフォルト DB/ファイル:
  - DuckDB: data/kabusys.duckdb
  - SQLite (monitoring): data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db
  - PID / フラグ: data/execution.pid, data/kill.flag, data/stop_requested.flag
- ログ: logs/<app_name>.log（ログディレクトリは環境変数 LOG_DIR で変更可能）

## 使い方

- 監視ループの起動（プロジェクトルートで実行）
```
python -m kabusys.run_monitoring
```
- 監視ポーリング間隔は環境変数で上書き可能:
```
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```
- 実行エンジンの起動
```
python -m kabusys.run_execution
```
- Paper Trading モードで起動する場合:
  - .env で `KABUSYS_ENV=paper_trading` を設定するか環境変数で指定
  - この場合、MockBrokerClient が使われ、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録されます

- 停止方法
  - 実行ループを優雅に停止するにはプロジェクトルートの data/stop_requested.flag を作成します（監視ループ・実行ループはこのフラグを見て終了します）。
  - 実行エンジンを強制停止させたい・Kill Switch を発動させたい場合は data/kill.flag を作成します（KillSwitch は条件に応じて自動的に書き込みます）。

- Paper Trading 検証レポート生成
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB 指定:
python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
```

- OpenAI を使った機能
  - 環境変数 `OPENAI_API_KEY` をセットしてください（または関数呼び出し時に api_key を指定）。
  - news_nlp.score_news / regime_detector.score_regime は DuckDB 接続と日付を与えて使用します（ライブラリ API）。

## 環境変数（主なもの）

- KABUSYS_ENV: 実行環境 (development | paper_trading | live)（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定モード (instant|partial|never|reject)（デフォルト: instant）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログディレクトリ（デフォルト logs/）
- OPENAI_API_KEY: OpenAI API キー（AI 機能に必要）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒）（デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1）

.env 自動読み込み:
- プロジェクトルートの .env と .env.local を自動で読み込みます（OS 環境 > .env.local > .env）。自動読込を無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

## ログ

- setup_logging() により:
  - コンソール出力（stdout）
  - 日次ローテーションファイル出力 logs/<app_name>.log（30日保持）
- ログディレクトリは環境変数 LOG_DIR で上書き可能。

## データベースと永続化

- DuckDB: リサーチ・ファクターテーブル（prices_daily / raw_financials / raw_news など）
- SQLite (monitoring.db): system_status, trade_logs, positions, risk_logs, dashboard テーブルを保持
  - monitoring_db.init_monitoring_db() は起動時にテーブルを作成・マイグレーションを行います。
- Paper Trading 用 SQLite は環境に応じて分離（KABUSYS_ENV=paper_trading の場合、Execution は paper_sqlite_path を使用）。

## 開発者向けメモ

- 主要 CLI / スクリプト:
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config
  - python -m kabusys.run_monitoring
  - python -m kabusys.run_execution
  - python -m kabusys.tools.paper_verification_report
- ライブラリ的に使える主要モジュール:
  - kabusys.portfolio: 候補選定・重み・ポジションサイジング・リスク調整
  - kabusys.research: calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic 等
  - kabusys.ai: score_news（ニュース NLP）
  - kabusys.monitoring: MonitoringEngine 系
  - kabusys.utils: logging_setup / process_priority

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（.env 自動ロード含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py       — （該当ソース参照）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       — （アラートの発行ロジック）
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py

（上記は本リポジトリの主要ファイルを抜粋した一覧です。詳細はソースを参照してください。）

## 運用上の注意 / セーフガード

- KABUSYS_ENV=live の場合は本番扱いです。validate_config.py は live 時に警告を出します。LINE 通知の設定等を確認してください。
- Kill Switch（data/kill.flag）・stop flag（data/stop_requested.flag）を適切に管理してください。KILL_FLAG_CLEAR_ON_START を安易に 1 に設定すると本番で危険です。
- OpenAI API を利用する機能は API コストとレイテンシに注意してください。API キーは厳重に管理してください。
- Paper Trading 用 DB は本番 DB と分離してください（既定では分離されています）。

---

不明点や README に追加したい内容があれば教えてください。実行例や systemd / supervisor 用のサービスユニット例、より詳しい設定ファイルテンプレート（config/*.yaml）等も追記できます。