# KabuSys

日本株向けの自動売買・リサーチ基盤の一部を抜粋した実装です。  
このリポジトリには、環境設定ウィザード、設定検証、ExecutionEngine / Monitoring の起動スクリプト、ファクター計算・ポートフォリオ構築・ポジションサイジング、AI を使ったニュースセンチメント評価、監視／アラート周りの実装などが含まれます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は、日本株の自動売買システムのコンポーネント群です。本実装は以下の役割を持つモジュール群を提供します。

- 環境変数の管理（.env 自動読み込み / ウィザード）
- 設定検証 CLI（.env と config/*.yaml の基本チェック）
- ExecutionEngine（発注ロジック、ブローカ抽象化、リスク管理等）起動スクリプト
- Monitoring（プロセス監視、データ鮮度、注文滞留や約定異常検出、Kill Switch）起動スクリプト
- ポートフォリオ構築（候補選定、重み付け）、ポジションサイズ計算、セクターキャップ等の純粋関数群
- Research（ファクター計算、将来リターン、IC 計算など）
- AI モジュール（OpenAI を使ったニュースセンチメント評価・市場レジーム判定）
- ペーパートレード検証レポート生成ツール

設計方針の一部:
- DuckDB / SQLite を用いたデータ処理・永続化
- 実行環境（development / paper_trading / live）による挙動切替
- フェイルセーフ：API 失敗やデータ不足時は安全側にフォールバック
- 可能な限り副作用を避ける純粋関数設計の採用箇所あり

---

## 主な機能一覧

- 環境設定ウィザード: python -m kabusys.config_setup（.env の対話式作成）
- 設定検証: python -m kabusys.validate_config（必須環境変数 / ファイル存在 / YAML パース確認 等）
- Execution 起動: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し paper_trading 用 SQLite に記録（本番 DB と分離）
  - 停止フラグ（data/stop_requested.flag）や kill.flag による停止機構
- Monitoring 起動: python -m kabusys.run_monitoring
  - システム監視（CPU / メモリ / ディスク / プロセス PID チェック）
  - 注文監視（滞留注文・約定異常）
  - リスク監視（ドローダウン、ポジション上限）
  - LINE によるアラート送信（AlertManager）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔調整
- AI: kabusys.ai.score_news / kabusys.ai.regime_detector
  - OpenAI（gpt-4o-mini 想定）を利用したニューススコアリング・レジーム判定
- Research: ファクター計算（momentum/value/volatility）、forward returns、IC、統計要約
- ポートフォリオ: 候補選定、重み計算（等金額・スコア加重）、ポジションサイズ算出、セクター上限・レジーム乗数
- ツール: Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）

---

## 必要条件（推奨）

- Python 3.9+
- SQLite（標準ライブラリで利用可）
- DuckDB Python パッケージ
- psutil
- requests
- openai パッケージ（AI 機能を使う場合）
- PyYAML（設定 YAML の内容検証を有効にしたい場合）

依存パッケージはプロジェクト側で requirements.txt があればそれを使ってください。ない場合は最低限以下をインストールしてください（例）:

pip install duckdb psutil requests openai

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install -r requirements.txt  （requirements.txt がある場合）
   - または最低限:
     - pip install duckdb psutil requests openai PyYAML

3. 環境変数（.env）を作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - あるいは .env を手動で作成（例）:
     JQUANTS_REFRESH_TOKEN=your_token_here
     KABU_API_PASSWORD=your_password_here
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO
     OPENAI_API_KEY=sk-...

   注意: 実運用（KABUSYS_ENV=live）時は機密情報の管理に注意し、.env を絶対に Git へコミットしないでください。

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにしたい場合:
     - python -m kabusys.validate_config --strict

5. DB 初期化
   - run_execution / run_monitoring が起動時に必要なテーブルを作成します（init_monitoring_db/マイグレーションを含む）。
   - duckdb ファイルの親ディレクトリや data ディレクトリを事前に作成しておくと良い:
     - mkdir -p data

---

## 使い方

基本的な実行コマンド:

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い

- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用
    - 実行中は execution.pid（デフォルト data/execution.pid）を用いてプロセス監視
    - 起動前に data/stop_requested.flag が存在すると起動せず終了
    - 停止は data/stop_requested.flag を作成すると検出して停止

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を変更可能（デフォルト: 60）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - run_monitoring は monitoring 用 SQLite（settings.sqlite_path）に対してテーブル作成（冪等）を行います
  - 監視処理は MonitoringEngine を使い、各モニターを定期実行してアラートや kill.flag 作成を行います

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

停止・Kill 機構:
- data/stop_requested.flag
  - run_execution / run_monitoring のループはこのファイルを検出すると終了します（外部からの優雅な停止要求用）。
- data/kill.flag
  - Monitoring の KillSwitch が危険条件を検出した場合に作成され、ExecutionEngine に停止シグナルを送る用途で使われます。
  - ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していると自動でクリアされます（本番環境では 0 推奨）。

注意点 / トラブルシューティング:
- OpenAI を使うモジュール（news_nlp / regime_detector）は OPENAI_API_KEY の設定が必須です。未設定だと ValueError を送出します。
- psutil によるプロセス優先度設定は権限やプラットフォーム依存です。アクセス拒否が発生する場合は警告が出てスキップされます。
- DuckDB による SQL 実行時はテーブルが存在しないと sqlite3.OperationalError 等が発生しますが、多くの箇所で例外を捕捉してフォールバックする実装があります。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）から行われます。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 主要な環境変数（要点）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

よく使う / 重要:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading: ブローカーはモックを使用し DB は分離される
  - live: 実際に発注が行われるため注意が必要
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper trading 用 SQLite（デフォルト data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager の送信先
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant | partial | never | reject）

---

## ディレクトリ構成

以下は主要ファイル・ディレクトリの抜粋です（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数・設定管理（.env 自動ロード / Settings クラス）
  - config_setup.py                — .env 対話式ウィザード
  - validate_config.py             — 設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — Monitoring 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading 検証レポート
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュースセンチメント評価（OpenAI）
    - regime_detector.py            — 市場レジーム判定（MA + マクロセンチメント）
  - research/
    - __init__.py
    - factor_research.py            — Momentum / Value / Volatility ファクター
    - feature_exploration.py        — 将来リターン・IC・統計サマリ等
  - portfolio/
    - __init__.py
    - portfolio_builder.py          — 候補選定・重み計算
    - risk_adjustment.py            — セクターキャップ・レジーム乗数
    - position_sizing.py            — 株数決定・投下資金スケーリング
  - monitoring/
    - monitoring_db.py              — SQLite 永続化層・Migration
    - system_monitor.py             — システム監視（CPU/メモリ/データ鮮度/PID）
    - trade_monitor.py              — 注文滞留・約定異常検出
    - risk_monitor.py               — ドローダウン・ポジション数監視
    - kill_switch.py                — kill.flag 操作
    - alert_manager.py              — LINE Push によるアラート
    - monitoring_engine.py          — 各 Monitor を束ねるエンジン
  - utils/
    - __init__.py
    - process_priority.py           — プロセス優先度 / CPU affinity 設定ユーティリティ
  - execution/                      — ExecutionEngine 関連（省略された詳細実装ファイルを想定）
  - data/                           — データ関連（DuckDB / SQLite / マスタ等、実データ格納想定）

---

## 開発者向けメモ

- 多くのモジュールは DuckDB 接続や sqlite3.Connection を引数で受け取り、テストがしやすい設計になっています。
- AI 部分は外部 API を呼ぶため、ユニットテスト時は _call_openai_api をモック化してください（各モジュールの docstring に記載）。
- MonitoringDB はマイグレーションロジックを含み、既存 DB に列がなければ追加する仕組みがあります（安全に運用可能）。
- 設定ファイル（config/*.yaml）の内容検証は PyYAML がインストールされていると行われます。開発時は PyYAML を入れておくと便利です。

---

必要であれば README に「起動例」「.env のサンプル」「よくあるエラーと対処法」等の追加情報を追記します。どの情報を詳しく載せたいか教えてください。