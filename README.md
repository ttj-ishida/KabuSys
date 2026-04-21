# KabuSys

日本株自動売買システム（開発版）

このリポジトリは、株価データの集計・ファクター計算・ポートフォリオ構築から、発注実行（実口座／ペーパートレード）・監視・アラート・AI を用いたニュースセンチメントや市場レジーム判定までを含む自動売買プラットフォームの一部です。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の機能群を備えています。

- DuckDB / SQLite を用いたデータ格納・分析基盤
- ファクター計算（モメンタム、ボラティリティ、バリュー 等）
- ポートフォリオ構築（候補選定、重み計算、リスク調整、ポジションサイズ算出）
- ExecutionEngine による発注処理（本番 / ペーパートレード切替）
- 監視モジュール（System / Trade / Risk）と Kill Switch（フラグファイルによる停止）
- ログ出力（コンソール + 日次ローテートファイル）
- OpenAI を使ったニュース NLP（センチメント）および市場レジーム判定ツール
- ユーティリティ：.env 対話式ウィザード、設定検証、ペーパートレード検証レポート 等

設計上、実際の発注・資金移動に関わる部分は環境（`KABUSYS_ENV`）によってペーパートレード用のモックや本番クライアントに切り替えられる仕組みです。

---

## 主な機能一覧

- 環境設定管理（`kabusys.config.Settings`）
  - 自動で `.env` / `.env.local` を読み込む（無効化可能）
- 対話式 .env 設定ウィザード（`kabusys.config_setup`）
- 設定検証 CLI（`kabusys.validate_config`）
- ExecutionEngine 起動スクリプト（`run_execution.py`）
  - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、`data/paper_trading.db` に記録
- Monitoring 起動スクリプト（`run_monitoring.py`）
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）
- 監視サブシステム
  - SystemMonitor（CPU / メモリ / ディスク / データ鮮度 / Execution プロセス監視）
  - TradeMonitor / RiskMonitor / MonitoringEngine / KillSwitch / AlertManager
  - 監視ログ永続化（SQLite 用ラッパー `MonitoringDB`）
- ポートフォリオ構築（等重/スコア重み、リスク調整、ポジションサイズ計算）
- 研究用モジュール（DuckDB 接続を受け取りファクター計算や特徴量探索）
- AI モジュール
  - `kabusys.ai.news_nlp.score_news`：ニュース記事のセンチメントを OpenAI で評価して DB に保存
  - `kabusys.ai.regime_detector.score_regime`：ETF を基にした MA とマクロ NLP を合成してレジーム判定
- ツール
  - Paper Trading 検証レポート生成（`kabusys.tools.paper_verification_report`）

---

## 動作前提・推奨

- Python 3.10+
  - （注）コードでの型ヒントや union 型（`X | Y`）を想定
- 必要な Python パッケージ（代表例）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config YAML の検証で任意）
- SQLite は標準ライブラリで利用可能
- ネットワーク（kabuステーション API、J-Quants、OpenAI 等）へのアクセスは環境に依存

仮想環境作成例:
- python -m venv .venv
- source .venv/bin/activate
- pip install duckdb psutil openai PyYAML

（requirements.txt が別途ある場合はそれを使用してください）

---

## セットアップ手順

1. リポジトリをクローンして Python 仮想環境を作成・有効化
2. 必要パッケージをインストール（上記参照）
3. 対話式ウィザードで .env を作成
   - python -m kabusys.config_setup
   - もしくはプロジェクトルートに `.env` を手動で作成
4. `.env` の必須項目を設定
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
   - OPENAI_API_KEY（AI 機能を使う場合）
   - そのほか、DUCKDB_PATH / SQLITE_PATH / LOG_LEVEL 等（任意）
5. 設定検証（起動前に推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）
6. データディレクトリやログディレクトリの作成は自動的に行われますが、権限等に注意してください

注意点:
- デフォルトで `.env` 自動読み込みが有効です。自動読み込みを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 本番（`KABUSYS_ENV=live`）では `KILL_FLAG_CLEAR_ON_START` を 1 にしないことを推奨します（安全上の理由）。

---

## 使い方（起動 / CLI）

基本的にモジュールとして起動できます（プロジェクトルートで実行することを想定）。

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine を起動（本番 / ペーパー共通スクリプト）
  - python -m kabusys.run_execution
  - 備考:
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、デフォルトで `data/paper_trading.db` に記録します。
    - 起動時に `data/stop_requested.flag` が存在する場合は起動をスキップします。
    - 実行中に同フラグが作られるとスレッド実行を停止します。
    - PID ファイル: デフォルト `data/execution.pid`（Settings.pid_file_path）

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書きできます（デフォルト 60 秒）
  - 監視は常に本番向けの sqlite_path を使用して監視ログを記録します（設定ファイルの env に依らず）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 環境変数 `PAPER_TRADING_SQLITE_PATH` を使って DB パスを指定できます（デフォルト `data/paper_trading.db`）

- AI 関連（プログラム呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続（duckdb.connect(...)）を渡し、`OPENAI_API_KEY` を設定するか `api_key` を渡して使用します。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 同様に API キーが必要（失敗時はフォールバックロジックあり）

ログ:
- デフォルトのログ出力先: logs/
- 例: logs/execution.log, logs/monitoring.log
- ログはコンソール（stdout）と日次ローテーションファイルに出力されます

停止・Kill Switch:
- `data/kill.flag` を作成すると ExecutionEngine に対して停止シグナルを送る Kill Switch が有効化されます（監視側が検出して書き込む仕組み）。
- `data/stop_requested.flag` を監視スクリプト / 実行スクリプトは監視しており、存在するとループを止めます。
- Kill Switch を手動で削除する場合はファイルを削除してください（`kabusys.monitoring.kill_switch.KillSwitch.clear()` を利用することもできます）。

---

## 重要な環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- DUCKDB_PATH — デフォルト data/kabusys.duckdb
- SQLITE_PATH — デフォルト data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 DB（paper_trading 時）
- LOG_LEVEL — デフォルト INFO
- OPENAI_API_KEY — AI 機能を使う場合に必要
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリア（1 にすると自動クリア、デフォルト 0）

例（.env の一部）:
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
OPENAI_API_KEY=sk-...

---

## ディレクトリ構成

（プロジェクトルート /src/kabusys 配下の主なファイル／モジュール）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定ハンドリング（自動 .env 読込）
  - config_setup.py          — 対話式 .env ウィザード
  - validate_config.py       — 起動前検証ツール
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - risk_adjustment.py      — セクターキャップ、レジーム乗数
    - position_sizing.py      — 発注株数計算・スケールダウンロジック
    - __init__.py
  - research/
    - factor_research.py      — ファクター計算（Momentum / Volatility / Value）
    - feature_exploration.py  — 将来リターン・IC・統計サマリー
    - __init__.py
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI）による銘柄毎センチメント
    - regime_detector.py      — 市場レジーム判定（ETF MA + マクロ NLP）
    - __init__.py
  - monitoring/
    - monitoring_db.py        — SQLite テーブル定義 & MonitoringDB
    - system_monitor.py       — CPU/メモリ/ディスク/データ鮮度監視
    - trade_monitor.py        — (存在) 注文監視関連（ファイル内参照）
    - risk_monitor.py         — ドローダウン / ポジション数監視
    - kill_switch.py          — kill.flag 管理
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - alert_manager.py        — (存在) 通知管理
  - utils/
    - logging_setup.py        — 共通ロギング設定
    - process_priority.py     — プロセス優先度 / CPU affinity 設定
    - __init__.py
  - data/                    — デフォルトで使われるデータファイル（logs, DB 等を想定）
  - その他 (execution/*, data/* など) — 発注周り、ブローカーファクトリ、リポジトリ等（コードベースに依存）

（上記は主要なファイルを抜粋したものです。詳細はソースを参照してください。）

---

## 運用のヒント・注意点

- 本番（live）運用前に必ず `python -m kabusys.validate_config` で設定検証を行ってください。
- `KILL_FLAG_CLEAR_ON_START=1` は開発時のみ推奨。本番で設定すると Kill Switch が誤ってクリアされる恐れがあります。
- OpenAI を使う処理（ニュース NLP / レジーム判定）は API コストやレートリミットに注意してください。API 呼び出しはリトライ・フォールバックを備えていますが、鍵の管理は慎重に行ってください。
- データベースファイル（DuckDB / SQLite）のバックアップ・ローテーションを運用設計に含めてください。
- ログディレクトリ作成に失敗するとコンソールのみの出力になります。エラーメッセージを確認してください。

---

## 開発者向けメモ

- 主要なビジネスロジックは純粋関数（portfolio/* や research/*）として実装されており、ユニットテストが書きやすい設計です。
- DuckDB を使った分析系関数は接続オブジェクトを引数で受け取り、テスト時は in-memory DB や fixture を用いることが可能です。
- OpenAI 呼び出し部は `_call_openai_api` 等をモック可能な実装にしています（ユニットテストで差し替えやすい）。

---

README はここまでです。さらに README に追記したい内容（運用手順の詳細、systemd サービス定義例、Docker 化、CI/テスト方法など）があれば教えてください。必要に応じて具体的なコマンド例や systemd ユニットファイルのサンプルも用意します。