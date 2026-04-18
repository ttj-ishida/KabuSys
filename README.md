# KabuSys

日本株向け自動売買 / 研究基盤のモジュール群です。  
このリポジトリは発注エンジン、監視機構、ポートフォリオ構築、リサーチ、AI（ニュースセンチメント・レジーム判定）などの機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的としたコンポーネント群を含むパッケージです。

- ExecutionEngine（発注エンジン）: 実際のブローカー/モックを通じて注文を管理・発行
- Monitoring（監視）: システム稼働・データ鮮度・注文状況・リスクをポーリングしてログ・アラートを生成
- Portfolio（銘柄選定・配分）: 候補選定、重み付け、株数計算、セクター制約などの純関数群
- Research（ファクター計算 / 特徴量探索）: DuckDB 上の株価・財務データからファクターを計算
- AI（ニュース NLP / レジーム判定）: OpenAI API を用いたニュースのセンチメント付与・市場レジーム判定
- Tools（運用支援）: Paper Trading 検証レポートなど

設計方針として、DB（SQLite / DuckDB）を用いた永続化、環境変数ベースの設定、.env ウィザード・検証ツールを備えています。

---

## 主な機能一覧

- run_execution: ExecutionEngine を起動（KABUSYS_ENV により paper_trading モードで MockBroker を使用）
- run_monitoring: SystemMonitor を定期実行（MONITOR_POLL_INTERVAL で間隔変更可）
- config_setup: 対話式 .env 作成ウィザード（python -m kabusys.config_setup）
- validate_config: .env / config/*.yaml 等の設定検証 CLI
- tools.paper_verification_report: ペーパートレードの検証レポート生成
- portfolio: 候補選定・重み付け・ポジションサイズ計算・セクター制約・レジーム乗数
- research: ファクター計算（モメンタム、ボラティリティ、バリュー）、IC・統計量
- ai.news_nlp / ai.regime_detector: OpenAI を使ったニュースセンチメント・市場レジーム判定
- monitoring.monitoring_db: 監視用 SQLite スキーマ・読み書きラッパー
- utils.logging_setup: 統一ログ設定（コンソール + 日次ローテートファイル）
- utils.process_priority: プロセス優先度設定（Windows / POSIX 対応）

---

## 前提条件

- Python 3.9+
- 必要パッケージ（例）
  - duckdb
  - psutil
  - openai （AI 機能を使う場合）
  - PyYAML（config の YAML 検証を使いたい場合）
- ローカル DB / ファイル書込権限

インストール例（仮）:
pip install -r requirements.txt
（requirements.txt がある場合。無ければ各機能に応じて duckdb, psutil, openai 等をインストールしてください）

---

## セットアップ手順

1. リポジトリをクローン / 配置
2. 仮想環境作成・依存インストール
3. 対話式で .env を生成（推奨）
   - python -m kabusys.config_setup
   - これによりプロジェクトルートに `.env` が作成されます（出力先は引数で変更可）
4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いで exit(1) になります
5. DB ファイル（data ディレクトリ等）は自動で作成されることが多いですが、権限やパスを事前確認してください

重要な環境変数（最低限必須）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development | paper_trading | live、デフォルト: development）
- OPENAI_API_KEY（AI 機能を使う場合）

DB 関連（デフォルト）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading モード時）

ログ:
- デフォルトログディレクトリ: logs/
- LOG_LEVEL 環境変数でログレベル指定（DEBUG/INFO/WARNING/ERROR/CRITICAL）

.env 自動ロード:
- パッケージ import 時にプロジェクトルートが検出された場合、.env（次に .env.local）が自動読み込みされます
- 自動ロードを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 使い方（主要コマンド）

※ いずれもプロジェクトルートから実行する前提です。

- .env ウィザード作成（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- ExecutionEngine を起動（本番 / ペーパー）
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 SQLite に書き込む（設定により完全分離）
    - 起動時に data/stop_requested.flag が既に存在すると起動せずに終了
    - 停止は data/stop_requested.flag を作成することで実施
  - 実行中は data/execution.pid に PID を書きます

- Monitoring（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き（例: MONITOR_POLL_INTERVAL=30）
  - 監視は本番 sqlite_path を使用（KABUSYS_ENV に依らず）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH が優先されます）

- AI 関連（ライブラリ的に利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - OpenAI API キーは api_key 引数、または環境変数 OPENAI_API_KEY で指定
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## 環境変数の優先順位と .env ロード

優先順位:
- OS 環境変数 > .env.local > .env

自動ロードはプロジェクトルート（.git または pyproject.toml を探索）で行われ、見つからない場合は自動ロードをスキップします。

自動ロードを無効にする:
- export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 停止／Kill スイッチについて

- run_execution / run_monitoring は停止フラグ（data/stop_requested.flag）を監視します。フラグが検出されると慎重にシャットダウンします。
- kill_switch（data/kill.flag）:
  - 監視コンポーネントがリスク条件（ドローダウン閾値超過やポジション数上限）を検出した場合に kill.flag を書き、ExecutionEngine に停止を促します。
  - KillSwitch は冪等に動作し、既存 flag がある場合は再書き込みしません。
  - ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 が指定されていると自動でクリアされる可能性があるため、本番では 0 を推奨します。

---

## ログ

- setup_logging() により root logger が設定され、stdout（StreamHandler）と日次ローテートファイル（logs/<app_name>.log）へ出力されます。
- ログレベルは以下の優先順位で決定: 関数引数 level > 環境変数 LOG_LEVEL > デフォルト "INFO"
- デフォルトログディレクトリ: logs/（権限不足で作成できない場合はコンソールのみ出力）

---

## トラブルシューティング & 注意事項

- PyYAML がインストールされていない場合、validate_config は YAML 内容チェックをスキップして警告を出します。
- DuckDB のバージョンによっては executemany の空リスト等に制約があるため、コード内で互換性対策が施されています。
- AI 機能を使うには OPENAI_API_KEY が必要です。API 呼び出しはリトライ戦略があり、失敗時はフェイルセーフで処理をスキップまたはデフォルト値を使います（例: macro_sentiment=0.0）。
- process_priority の設定は psutil を用いています。権限によっては設定に失敗することがあります（警告ログが出ますが、処理は継続します）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュール構成（抜粋）です。

- kabusys/
  - __init__.py
  - config.py                — 環境変数/.env の読み込み・Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py (参照)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (参照)
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - data/                    — （実行時に使用されるファイル群: sqlite/duckdb/pid/flags 等）

（注）上記に示したファイルは本リポジトリに含まれる主要実装の一部です。その他 execution や data 周りの補助モジュール（broker_factory, execution_engine, order_manager, order_repository, reconciler, risk_manager 等）が参照されています。

---

## サンプル .env（例）

以下は最小限の例です（本番では .env を絶対に Git に乗せないでください）:

JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_station_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

---

## 開発・テストのヒント

- unit test では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットして環境読み込みを抑制できます。
- AI 呼び出し部分は _call_openai_api 関数を patch してモック化できます（news_nlp / regime_detector 共通で対応箇所あり）。
- DuckDB 接続を渡して pure function をテストすることで外部 API への依存を切り離せます（research, ai の一部設計はこれを想定しています）。

---

この README はコードベース内の主要機能と起動手順をまとめたものです。詳細な運用手順や設計ドキュメント（PortfolioConstruction.md 等）が別途ある場合はそちらも参照してください。質問や追加のドキュメント化希望があれば教えてください。