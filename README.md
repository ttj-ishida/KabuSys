# KabuSys

日本株向けの自動売買システム（ライブラリ・ランタイムスクリプト群）の README。

以下はソースツリー（src/kabusys 配下）に基づく概要・セットアップ・使い方・ディレクトリ構成の説明です。

> 注意: 本リポジトリはモジュール群と起動用スクリプト群を含みます。実際に稼働させる前に .env の設定および validate を必ず実行してください。

---

目次
- プロジェクト概要
- 主な機能
- 前提・依存パッケージ
- セットアップ手順
- 環境変数 / .env
- 実行方法
- 停止 / Kill スイッチ
- ロギング / DB パス
- 開発・デバッグのヒント
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株自動売買に関するコンポーネント群（シグナル生成／ポートフォリオ構成／発注エンジン／監視・アラート／研究ツール／AI 補助）を提供する Python パッケージです。  
設計上、実際の発注は kabuステーション API を通じて行い、Paper Trading モードでは MockBroker を使って本番 DB と分離して検証できます。

主要なランタイムスクリプト:
- run_execution.py — 発注エンジン（ExecutionEngine）起動スクリプト
- run_monitoring.py — 監視ループ（SystemMonitor 等）起動スクリプト
- config_setup.py — .env を対話的に作成するウィザード
- validate_config.py — 起動前チェック（.env と config/*.yaml の検証）
- tools/paper_verification_report.py — ペーパートレード検証レポート生成

---

## 主な機能

- 発注エンジン（ExecutionEngine）: ブローカーインターフェース、注文管理、リスク管理、リコンサイル機能など
- モニタリング: システム状態（CPU/メモリ/ディスク）、データ鮮度、トレード履歴、リスク（ドローダウン、ポジション上限）監視
- Kill Switch: 条件に応じて停止フラグを書き込み、ExecutionEngine に安全停止を促す仕組み
- Paper Trading 分離: KABUSYS_ENV=paper_trading 時に MockBroker を使用し paper_trading.db に記録
- 研究モジュール: DuckDB 接続でファクター計算（モメンタム／ボラティリティ／バリュー）や特徴量探索を実行
- AI ユーティリティ: ニュース NLP（OpenAI を利用したセンチメント評価）と市場レジーム判定（LLM+価格データ）
- ユーティリティ: ロギング統一設定、プロセス優先度設定、.env の自動読み込み・ウィザード

---

## 前提・依存パッケージ

推奨 Python バージョン: 3.10+

主な依存（プロジェクトによって必要なものが異なります）:
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML (config/*.yaml の検証を行う場合)
- （その他、発注や DB 周りに依存するパッケージがある場合あり）

（requirements.txt があれば `pip install -r requirements.txt` を推奨します）

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存をインストール
   - pip install -r requirements.txt
   - ない場合は少なくとも次を入れる:
     - pip install duckdb psutil
     - pip install openai    # AI を使う場合
     - pip install pyyaml    # validate_config が YAML を検証する場合
4. .env を用意（下記参照）
   - 対話ウィザードを使う: python -m kabusys.config_setup
   - 手動: リポジトリ直下に `.env` を作成（.env.example を参考）

5. 設定検証
   - python -m kabusys.validate_config
   - 警告も厳格に扱いたい場合: python -m kabusys.validate_config --strict

6. DB 初期化
   - 監視用 SQLite（デフォルト `data/monitoring.db`）や DuckDB（`data/kabusys.duckdb`）は、run_* スクリプトが必要に応じてテーブルを初期化します（init_monitoring_db を通じて冪等的に作成）。

---

## 環境変数 / .env

自動読み込み順: OS 環境 > .env.local（上書き）> .env（未設定キーのみ）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須環境変数:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要な設定（一部、デフォルト値あり）
- KABUSYS_ENV: 実行環境（development / paper_trading / live） デフォルト: development
  - paper_trading: MockBroker を使用、DB 分離（PAPER_TRADING_SQLITE_PATH）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定動作（instant|partial|never|reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/…）
- LOG_DIR: ログ保存先（デフォルト logs/）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）
- その他: PID_FILE_PATH, KILL_FLAG_PATH, 各種閾値（CPU/MEM/DISK）

run_monitoring 固有:
- MONITOR_POLL_INTERVAL: 監視のポーリング間隔（秒、デフォルト 60）

---

## 実行方法

基本的にモジュールとして実行します（パッケージルートで実行してください）。

- 環境設定ウィザード（.env 作成）:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動:
  - python -m kabusys.run_execution
  - 動作: 起動時にプロセス優先度を high に設定、DB 接続（paper_trading のときは PAPER_TRADING_SQLITE_PATH を使用）、Broker を生成してエンジンをスレッドで起動します。
  - 起動前に data/stop_requested.flag が存在すると起動を中止します。
  - PID ファイル: data/execution.pid（デフォルト）

- Monitoring（監視ループ）起動:
  - python -m kabusys.run_monitoring
  - 動作: SystemMonitor のポーリングループを実行、MONITOR_POLL_INTERVAL で指定（またはデフォルト 60 秒）
  - 監視は常に本番 sqlite_path（SQLITE_PATH）を使用します（KABUSYS_ENV にかかわらず）

- Paper Trading 検証レポート生成:
  - python -m kabusys.tools.paper_verification_report
  - オプション例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - --db で DB パス指定（デフォルト: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）

- AI 系機能（プログラム的に呼び出す）:
  - kabusys.ai.score_news(conn, target_date, api_key=None) — raw_news を用いてニュースセンチメントを ai_scores に書き込む（OpenAI API が必要）
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None) — レジーム判定して market_regime テーブルへ書き込む

---

## 停止 / Kill スイッチ

- 全体停止（手動）:
  - `data/stop_requested.flag` を作成すると、run_monitoring と run_execution のループは検知して終了・停止します。
  - run_execution は起動時に既に stop フラグが立っていれば起動せずに終了します。

- Kill Switch（自動停止）:
  - 監視コンポーネントがリスク条件（ドローダウン超過、ポジション上限超過等）を検知すると `data/kill.flag` に理由を書き込みます（存在すれば再書き込みしない）。
  - ExecutionEngine は外部で kill.flag を検出して自身を安全停止する仕組みを備える（起動時の設定 KILL_FLAG_CLEAR_ON_START に注意）。

- kill.flag を消去する:
  - KillSwitch.clear() 相当、または手動で data/kill.flag を削除します。`KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に自動で消去されますが、本番では 0 を推奨します。

---

## ロギング / DB

- ログ:
  - setup_logging() により stdout ストリーム出力と日次ローテーションファイル（logs/<app_name>.log）を設定します。
  - 環境変数 LOG_DIR でログディレクトリを指定可能。
  - LOG_LEVEL で出力レベルを指定。

- DB:
  - DuckDB（デフォルト data/kabusys.duckdb）: 研究・価格テーブルなどの分析用
  - SQLite（監視）: data/monitoring.db（監視ログ、trade_logs、positions 等）
  - Paper trading 用 SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading 時に使用）
  - 監視テーブルの初期化は init_monitoring_db() により冪等的に行われます（run_* スクリプトが起動時に呼ぶ）

---

## 開発・デバッグのヒント

- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml がある場所）を基準に行われます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使って無効化できます。
- validate_config は YAML のパース確認やパスの存在チェックを行います。PyYAML がない場合は YAML 検証をスキップして警告が出ます。
- AI 関連（OpenAI）呼び出しはリトライ・バックオフの実装があります。API キーは OPENAI_API_KEY 環境変数で指定します。
- process priority や CPU affinity は utils/process_priority.py でプラットフォーム差分を吸収しています。実行開始直後に優先度を Hight に設定しますが、権限がない環境では警告が出ます。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 配下の主要モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/設定読み込みロジック
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py       — 監視用 DB（テーブル定義・永続化）
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — (トレード監視ロジック)
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 書き込み
    - monitoring_engine.py   — 各 Monitor を束ねる実行ループ
    - alert_manager.py       — （アラート送信管理、LINE 等）
  - execution/
    - execution_engine.py    — ExecutionEngine（コア）
    - order_manager.py       — 注文管理
    - order_repository.py    — 注文の永続化
    - reconciler.py          — 注文照合/リコンサイル
    - broker_factory.py      — Broker クライアント生成（Mock / 実ブローカー）
    - risk_manager.py        — 実行時リスク制御
  - portfolio/
    - portfolio_builder.py   — 候補選択・重み計算
    - position_sizing.py     — 株数算出・丸め・上限調整
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — モメンタム/ボラ/バリュー等のファクター計算
    - feature_exploration.py — 将来リターン/IC/統計サマリー等
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）による銘柄別スコアリング
    - regime_detector.py     — 市場レジーム判定（価格+LLM）
  - data/                    — デフォルトで使用される data ディレクトリ（logs, db 等）

---

以上が README 相当の説明です。実行時は必ず .env を作成し validate_config で確認してください。運用（live 環境）では kill.flag / KILL_FLAG_CLEAR_ON_START の設定に特に注意し、ログや DB のバックアップ・監査を行ってください。

必要であれば README に含める具体的な .env の例や各構成ファイル（config/*.yaml）の説明、運用フロー（起動順序・監視の運用手順）を追記します。どの情報を追加しますか？