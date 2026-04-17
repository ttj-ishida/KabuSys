# KabuSys

日本株向け自動売買システム（ライブラリ / 実行スクリプト群）

このリポジトリは、取引エンジン（ExecutionEngine）、監視/アラート、ポートフォリオ構築、ファクター計算、LLM を使ったニュース解析などを含むモジュール群で構成されています。用途に応じて本番（live）・ペーパートレード（paper_trading）・開発（development）モードで実行できます。

## 概要

主な目的は次のとおりです。

- 銘柄選定・ポジションサイズ計算（portfolio モジュール）
- バックエンドのデータ処理・ファクター計算（research モジュール／DuckDB）
- 実際の注文送信を担う ExecutionEngine（execution モジュール）
  - KABUSYS_ENV=paper_trading の場合はモックブローカーを使用し、本番 DB と分離して `data/paper_trading.db` に記録します
- 監視・リスク監視（monitoring モジュール）と LINE への通知（AlertManager）
- ニュース NLP / レジーム判定（AI モジュール）で OpenAI API を利用
- 設定ウィザード・検証ツールやペーパートレード検証レポートのユーティリティ

## 機能一覧

- 設定管理
  - .env 自動ロード（プロジェクトルートの .env / .env.local）
  - 対話式の `.env` 作成ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
- 実行
  - ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - Monitoring 起動スクリプト（python -m kabusys.run_monitoring）
- 監視（monitoring）
  - システム状態（CPU/MEM/DISK、プロセス存在チェック）
  - 注文滞留・約定異常価格監視
  - ドローダウン・ポジション上限監視（Kill Switch で Execution を停止）
  - LINE 通知（AlertManager）
- ポートフォリオ構築（portfolio）
  - 候補選定、等比率/スコア比率の重み計算、ポジションサイズ計算（lot 単位丸め・集約キャップ）
  - セクター上限適用、レジーム乗数
- 研究（research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB を想定）
  - 将来リターン・IC 計算、ファクター統計
- AI（ai）
  - ニュースセンチメントのスコアリング（OpenAI）
  - 市場レジーム判定（MA + マクロニュース LLM）
- ユーティリティ
  - ペーパートレード検証レポート（python -m kabusys.tools.paper_verification_report）

## 前提・依存関係

必須（実行する機能により異なる）：

- Python 3.10+
- duckdb
- psutil
- requests
- openai（AI 機能を使う場合）
- PyYAML（設定 YAML 内容検証を行う場合、オプション）

インストール例（仮）:

pip install -r requirements.txt

（requirements.txt がない場合は個別に duckdb psutil requests openai をインストールしてください）

## セットアップ手順

1. レポジトリをクローンしてプロジェクトルートへ移動

2. 仮想環境の作成・パッケージのインストール（例）

   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb psutil requests openai

3. .env の作成

- 対話式ウィザードを推奨:

  python -m kabusys.config_setup

  ウィザードは .env（デフォルトはプロジェクトルート）を生成します。生成後は設定検証を行ってください。

- 手動で作成する場合（最低限必要な環境変数）:

  JQUANTS_REFRESH_TOKEN=...
  KABU_API_PASSWORD=...
  KABUSYS_ENV=development   # development | paper_trading | live
  DUCKDB_PATH=data/kabusys.duckdb
  SQLITE_PATH=data/monitoring.db
  LOG_LEVEL=INFO
  # OpenAI を利用する場合:
  OPENAI_API_KEY=...

4. 設定検証

  python -m kabusys.validate_config

  --strict フラグを付けると警告も失敗扱いになります。

5. 必要に応じて data ディレクトリ作成（DB の親ディレクトリなど）

  mkdir -p data

6. DuckDB / SQLite の初期化は起動スクリプト側で行われます（必要なテーブルは init_monitoring_db で作成されます）。

## 使い方

基本的にモジュールはパッケージとして実行できます。

- 実行エンジン（ExecutionEngine）を起動

  python -m kabusys.run_execution

  挙動:
  - Settings に基づいて DB へ接続します (paper_trading の場合は専用 DB を使用)
  - プロセス優先度を high に設定し、ExecutionEngine を別スレッドで実行します
  - プロジェクトルート/data/stop_requested.flag が存在すると起動を抑制または実行中に停止します

- 監視ループを起動

  python -m kabusys.run_monitoring

  環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト 60 秒）。
  監視は本番 sqlite_path を使用（KABUSYS_ENV に依存せず本番 DB を参照します）。

- ペーパートレード検証レポート

  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  オプション --db で PAPER_TRADING_SQLITE_PATH を上書き可能。

- .env 作成ウィザード

  python -m kabusys.config_setup

- 設定検証

  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

AI 関連（OpenAI を使う機能）:

- ニューススコアリング（ai.news_nlp.score_news）やレジーム判定（ai.regime_detector.score_regime）を使う場合は OPENAI_API_KEY を環境変数に設定してください。これらの関数は DuckDB 接続と target_date を受け取って処理を行います。

停止・Kill スイッチ:

- 実行プロセスを外部から停止させたい場合:
  - プロジェクトの data/stop_requested.flag を作成すると run_monitoring / run_execution のループが検知して終了します（run scripts は stop_requested.flag をチェック）。
  - KillSwitch（監視の判定により）data/kill.flag を生成すると ExecutionEngine に停止シグナルを送ります（Settings.kill_flag_path を使用）。Kill flag を手動で削除する場合は data/kill.flag を削除してください。

プロセス優先度:

- 起動時に set_process_priority("high") が試行されます。psutil が必要で、権限がないと警告が出ます（スキップされます）。

環境変数の主要一覧（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db) — paper_trading 用
- PAPER_FILL_MODE: instant | partial | never | reject (paper_trading の挙動制御)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- OPENAI_API_KEY（AI 機能用）
- MONITOR_POLL_INTERVAL（監視ポーリング秒数、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START など（Settings で参照）

例: 監視ポーリング間隔を 30 秒にする

export MONITOR_POLL_INTERVAL=30
python -m kabusys.run_monitoring

例: ペーパートレードで Execution を起動（.env で KABUSYS_ENV=paper_trading を設定）

python -m kabusys.run_execution

## ディレクトリ構成

主要ファイル／ディレクトリの概略:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込み・Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - utils/
    - process_priority.py    — psutil を使った優先度 / affinity 設定
  - execution/               — Execution 関連（エンジン、ブローカーファクトリ等）
  - monitoring/
    - monitoring_db.py       — SQLite テーブル作成 / MonitoringDB ラッパ
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
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

- data/                     — デフォルトの DB / PID / flag が置かれる場所（手動で作成推奨）
  - monitoring.db (SQLite)
  - kabusys.duckdb (DuckDB)
  - paper_trading.db (paper_trading 用 SQLite)
  - execution.pid
  - stop_requested.flag
  - kill.flag

（上記はソースツリーの一部抜粋です。細かい実装ファイルは各サブパッケージ内に存在します。）

## よくあるトラブルシューティング

- .env が読み込まれない／値が見つからない
  - プロジェクトルートが識別できない場合（.git や pyproject.toml がない）自動ロードをスキップします。config_setup で .env を作成するか環境変数を手動で設定してください。
  - 自動ロードを無効化している場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を確認。

- DuckDB / SQLite のパスの親ディレクトリがない
  - validate_config で警告が出ます。`mkdir -p $(dirname <path>)` で作成してください。起動時に自動作成される場合もありますが事前作成を推奨します。

- OpenAI 呼び出しが失敗する / API キーがない
  - OPENAI_API_KEY を設定してください。AI 機能は API のレート制限・失敗に対してリトライ・フォールバックを行いますが、完全に失敗する場合もあります。

- プロセスを安全に停止したい
  - data/stop_requested.flag を作成すると run_* スクリプトが検知して終了します。
  - 監視側による停止（KillSwitch）は data/kill.flag を書き込みます。kill.flag は削除して再起動してください。

## 開発向けメモ

- 多くのモジュールは外部 DB（DuckDB）や外部 API に依存します。ユニットテストではモック（依存注入）を使う設計になっています。
- AI 関連の OpenAI 呼び出し部はテストしやすく分離されており、内部の _call_openai_api をパッチすることでテスト可能です。
- monitoring_db.init_monitoring_db は冪等で、既存 DB に対する小さなスキーママイグレーション（列追加）処理も実装されています。

---

README の内容に不足や、特定の操作手順（デプロイ手順、Docker 化、systemd サービス化など）を追加したい場合は用途を教えてください。必要な例やコマンドを追記します。