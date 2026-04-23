# KabuSys — 日本株自動売買システム (README)

このリポジトリは日本株の自動売買システム「KabuSys」のコアライブラリ群です。  
本 README はプロジェクトの概要、主な機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は以下のような関数群・サービスを含む自動売買基盤です：

- 戦略用ファクター計算・研究機能（DuckDB を使用）
- ポートフォリオ構築・ポジションサイジングロジック（純粋関数）
- 実行エンジン（ExecutionEngine）とブローカークライアントの抽象化（paper/live 両対応）
- 監視サブシステム（System / Trade / Risk のモニタリング）と Kill Switch
- ニュースの NLP 処理（OpenAI を利用したセンチメント評価）と市場レジーム判定
- ユーティリティ（ログ設定・プロセス優先度設定 等）
- 各種 CLI ツール（環境設定ウィザード・設定検証・レポート生成 等）

設計方針として、計算ロジックは可能な限り副作用を持たない純粋関数に分離し、DBアクセスや外部 API 呼び出しは明示的に行う構成になっています。

---

## 主な機能一覧

- 環境設定管理
  - .env 読み込み（プロジェクトルートの .env / .env.local、自動ロード可）
  - 対話式設定ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）

- 実行 / 監視ランタイム
  - ExecutionEngine 起動スクリプト（run_execution.py）
    - KABUSYS_ENV=paper_trading 時は MockBroker を使用し paper DB に記録
  - Monitoring ポーリング（run_monitoring.py）
    - システム状態・注文状態・リスク監視、Kill Switch 評価・通知

- ポートフォリオ構築
  - 候補選定、重み計算（等配分 / スコア加重）
  - セクターキャップ適用、レジーム乗数
  - 株数決定（リスクベース・等配分）、単元株丸め、aggregate cap のスケーリング

- リサーチ / ファクター
  - Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- AI / ニュース処理
  - OpenAI を使ったニュースセンチメントスコアリング（ai.news_nlp）
  - マクロニュース + ETF MA による市場レジーム判定（ai.regime_detector）
  - API レート制御・リトライ・レスポンス検証を備えた安全設計

- ツール
  - Paper Trading 検証レポート生成（tools.paper_verification_report）

- ユーティリティ
  - 統一ログ設定（stdout + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定

---

## セットアップ手順

以下はローカル開発および簡易的な本番稼働準備の流れです。

1. Python 環境（推奨: 3.10+）を用意する。

2. 仮想環境作成・有効化（例）:
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```
     python -m venv .venv
     .venv\Scripts\activate
     ```

3. 必要パッケージをインストール（代表的な依存）:
   ```
   pip install duckdb psutil openai PyYAML
   ```
   ※ requirements.txt がある場合は `pip install -r requirements.txt` を使用してください。

4. .env を作成する:
   - 対話式ウィザードを使う:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは手動で `.env` を作成（例）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_token
     KABU_API_PASSWORD=your_kabu_password
     KABUSYS_ENV=development
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO
     KILL_FLAG_CLEAR_ON_START=0
     ```
   - 自動ロードはデフォルトで有効。環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます。

5. 設定検証（推奨）:
   ```
   python -m kabusys.validate_config
   ```
   警告を FAIL としたい場合は `--strict` を付けます。

6. データディレクトリ・ログディレクトリ等は必要に応じて作成されます（logging_setup が自動作成を試みます）。

---

## 使い方（起動・運用）

基本的な起動コマンド例:

- 実行エンジン（ExecutionEngine）起動
  - 通常起動（paper/live は KABUSYS_ENV に依存）:
    ```
    python -m kabusys.run_execution
    ```
  - ペーパートレードでは `KABUSYS_ENV=paper_trading` を設定すると MockBroker を使用し、デフォルトで `data/paper_trading.db` に記録します。

- 監視プロセス起動（SystemMonitor のポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）。
  - 監視は本番 sqlite_path（`SQLITE_PATH`）を常に使用します（環境に依らない）。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - `--db` で DB パスを指定できます。環境変数 `PAPER_TRADING_SQLITE_PATH` も利用可能。

停止・Kill フロー:

- 停止フラグ（外部プロセスからの優雅な停止）
  - 各ランナーはプロジェクトの `data/stop_requested.flag` ファイルを監視しています。存在すると監視ループ/エンジンは停止処理を行います。
- Kill Switch（監視から ExecutionEngine 停止指示）
  - 監視コンポーネントは条件に応じて `data/kill.flag` を書き込みます（KillSwitch）。
  - ExecutionEngine 側は起動時に `KILL_FLAG_CLEAR_ON_START` 設定で kill.flag の自動クリア挙動を制御できます（0: クリアしない / 1: クリアする（開発用））。
  - 本番では自動クリアを無効化することを推奨します。

ログ:
- デフォルトで stdout に出力され、ファイルは `logs/<app_name>.log`（日次ローテーション）に出力されます。
- ログレベルは `LOG_LEVEL` 環境変数で制御できます（DEBUG/INFO/WARNING/ERROR/CRITICAL）。

OpenAI / 外部 API:
- AI 機能を使うには `OPENAI_API_KEY` を設定してください。(ai.news_nlp, ai.regime_detector)
- J-Quants / kabuステーション など外部 API 用のトークンは `.env` で設定します（必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。

環境変数の主な一覧（抜粋）:
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live
- OPENAI_API_KEY (AI 機能使用時に必須)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用, デフォルト: data/paper_trading.db)
- LOG_LEVEL (デフォルト: INFO)
- MONITOR_POLL_INTERVAL (監視ポーリング間隔秒, デフォルト: 60)
- KILL_FLAG_CLEAR_ON_START (0/1)

---

## 開発時のヒント / 注意点

- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml を基準）を探索して行います。テストで自動読み込みを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB を使うリサーチ関数群（research/*）は大量データを効率的に処理するよう設計されています。ローカルでのテスト用には小さなテーブルを用意して動作確認してください。
- OpenAI 呼び出しはリトライ・バックオフを実装していますが、API 利用料・レートには注意してください。
- 本番（live）モードでは Kill Switch や LINE 通知など安全ガードの設定を十分に整備してください（LINE_TOKEN 等）。

---

## ディレクトリ構成

リポジトリの主要ファイル / 主要パッケージ（抜粋）:

- src/kabusys/
  - __init__.py
  - __version__ = "0.1.0"
  - config.py                — 環境変数 / Settings 管理（.env 自動ロード等）
  - config_setup.py          — 対話式 .env 作成ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI）によるスコアリング
    - regime_detector.py      — 市場レジーム判定
    - __init__.py
  - research/
    - factor_research.py      — Momentum/Volatility/Value 等の計算
    - feature_exploration.py  — 将来リターン / IC / 統計サマリー
    - __init__.py
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 株数算出・スケーリング
    - risk_adjustment.py      — セクターキャップ・レジーム乗数
    - __init__.py
  - monitoring/
    - monitoring_db.py        — SQLite テーブル初期化・永続化 API
    - system_monitor.py       — システム状態 / データ鮮度監視
    - trade_monitor.py        — （注文監視ロジック）
    - risk_monitor.py         — ドローダウン / ポジション上限監視
    - kill_switch.py          — kill.flag 書込みロジック
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - alert_manager.py        — （通知マネージャー）
  - execution/
    - execution_engine.py     — ExecutionEngine 本体（起動/セッション管理）
    - broker_factory.py       — ブローカークライアント生成
    - order_manager.py
    - reconciler.py
    - risk_manager.py
    - order_repository.py
  - utils/
    - logging_setup.py        — ルートロギング初期化（stdout + file）
    - process_priority.py     — プロセス優先度 / CPU affinity
    - __init__.py
  - data/ (実行時に使用するデータファイル)
    - monitoring.db (デフォルト SQLITE_PATH)
    - kabusys.duckdb (デフォルト DUCKDB_PATH)
    - paper_trading.db (paper_trading 用)

※ 上記は主要ファイルの抜粋です。細かな実装ファイルはソースツリーを参照してください。

---

## 付録：よく使うコマンドまとめ

- .env を対話式に作る:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン起動:
  ```
  python -m kabusys.run_execution
  ```

- 監視プロセス起動:
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- Paper Trading レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

ご不明点や追加で README に含めたい情報（例：実際の ExecutionEngine の構成図、LINE 通知設定手順、データベーススキーマの詳細な説明など）があれば教えてください。必要に応じて README を拡張します。