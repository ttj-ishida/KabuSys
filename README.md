# KabuSys — README

日本株自動売買システムの一部を含む Python パッケージ（ドキュメント目的の抜粋）。この README はリポジトリ内のスクリプト・設定・主要モジュールに基づく簡易導入ガイドです。

---

## プロジェクト概要

KabuSys は日本株の自動売買・研究・監視を支援するツール群です。本リポジトリには以下の機能を提供するモジュールが含まれます（抜粋）：

- 実行エンジン起動スクリプト（ExecutionEngine 起動）
- 監視ループ（System / Trade / Risk モニタ）起動スクリプト
- 環境設定ウィザード（.env 生成）
- 設定検証 CLI
- Paper Trading の検証レポート生成ツール
- ポートフォリオ構築（銘柄選定・重み・ポジションサイズ計算）ライブラリ
- 研究用（ファクター計算・特徴量解析）モジュール
- ニュース NLP を用いた AI スコアリング / レジーム判定（OpenAI 連携）

設計の要点：
- 本番用 / ペーパートレード用 DB を分離（環境に依存）
- DuckDB（分析用） と SQLite（トランザクション／監視ログ）を併用
- .env による環境変数管理と対話式ウィザードを提供
- ログは stdout と日次ローテートファイルに出力

---

## 主な機能一覧

- run_execution.py
  - ExecutionEngine を起動。KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、paper_trading 用の SQLite に記録。
- run_monitoring.py
  - SystemMonitor のポーリングループを起動（デフォルト 60秒）。MONITOR_POLL_INTERVAL で間隔変更可。
- config_setup.py
  - .env の対話式作成・更新ウィザード。
- validate_config.py
  - .env や config/*.yaml の事前検証ツール。--strict モードあり。
- tools/paper_verification_report.py
  - Paper Trading の検証レポート生成（稼働率・注文成功率・レイテンシ等）。
- portfolio/*
  - 銘柄選定、重み付け、ポジションサイズ計算、セクター制限、レジーム乗数。
- research/*
  - ファクター計算（モメンタム／バリュー／ボラティリティ）や IC 計算など。
- ai/*
  - ニュース NLP によるセンチメントスコア計算、レジーム判定（OpenAI API を利用）。

---

## 必要条件（推奨）

- Python 3.10+
  - ソース中で「X | Y」型注釈等を使用しています。
- パッケージ（代表例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML の内容検証を行う場合）
- SQLite は標準ライブラリで使用

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```
（プロジェクトに requirements.txt がある場合はそちらを使用してください）

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を用意・有効化する。
2. 必要なパッケージをインストール（上記参照）。
3. .env を作成する（推奨: ウィザード使用）:
   ```bash
   python -m kabusys.config_setup
   ```
   ウィザードで入力した値はプロジェクトルートの `.env` に保存されます。`.env` は Git にコミットしないでください。
4. 設定を検証する:
   ```bash
   python -m kabusys.validate_config
   # 警告も失敗扱いにする場合
   python -m kabusys.validate_config --strict
   ```
5. 必要に応じて `data/` ディレクトリや `logs/` ディレクトリの作成権限を確認する。ログディレクトリはデフォルトで `logs/`、ログファイルは `logs/<app_name>.log`。

---

## 主要な環境変数（抜粋・デフォルト）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: （必須）J-Quants API トークン
- KABU_API_PASSWORD: （必須）kabuステーション API パスワード
- KABU_API_BASE_URL: デフォルト: http://localhost:18080/kabusapi
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）, デフォルト: INFO
- LOG_DIR: ログ保存ディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）

注意:
- run_monitoring は「環境にかかわらず」Settings.sqlite_path（本番 SQLite パス）を使用して監視テーブルに接続します。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_trading 用 SQLite を使用して本番 DB と隔離します。

---

## 使い方（コマンド例）

ルートで仮想環境を有効にした上で実行します。

- .env を対話式で作成
  ```bash
  python -m kabusys.config_setup
  ```

- 設定の事前検証
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 監視ループ起動（デフォルトポーリング 60 秒）
  ```bash
  python -m kabusys.run_monitoring
  # ポーリング間隔を変更する例（秒）
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- 実行エンジン起動
  ```bash
  # 開発/本番（デフォルト）
  python -m kabusys.run_execution

  # ペーパートレードで起動（MockBroker を使用）
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report \
    --from 2026-04-01 --to 2026-04-11
  # DB パスを手動指定する場合:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- ログ
  - stdout にも出力されます（StreamHandler）。
  - ファイルはデフォルト `logs/<app_name>.log`（TimedRotatingFileHandler・日次ローテーション、30日分保持）。

---

## 停止 / Kill Switch の取り扱い

- 実行の停止（Engine 停止）:
  - `data/stop_requested.flag` を作成すると run_execution / run_monitoring 側が検知して停止処理を行います（監視スクリプトでも利用）。
- Kill Switch:
  - `KillSwitch` はリスク監視で条件を満たした場合に `data/kill.flag` を書き込み、ExecutionEngine へ停止シグナルを送ります。
  - 本番では `KILL_FLAG_CLEAR_ON_START=0` を推奨（誤って自動でクリアしない設定）。

手動クリア:
```bash
rm data/kill.flag
rm data/stop_requested.flag
```

（config 内に `KILL_FLAG_CLEAR_ON_START` を 1 にする設定がある場合、起動時に自動でクリアされますが、本番では危険です）

---

## 注意事項 / 運用上のヒント

- 本番環境（KABUSYS_ENV=live）では LINE 通知等のアラート設定を確実に行ってください（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）。
- OpenAI を利用する機能（ニュース NLP / レジーム検出）は OPENAI_API_KEY が必要です。API 呼び出し時に失敗してもフォールバック処理が入る設計ですが、API 利用にはコストとレイテンシが伴います。
- logging のファイル出力に失敗するとコンソールのみ出力にフォールバックします。ディレクトリ作成権限を事前に確認してください。
- DuckDB と SQLite のパスは .env で変更可能です。バックアップ・永続化ポリシーを構築してください。

---

## ディレクトリ構成（抜粋）

以下は本パッケージ内の主なファイル一覧（簡略版）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - utils/
      - __init__.py
      - logging_setup.py
      - process_priority.py
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py (参照あり)
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py (参照あり)
    - execution/                 (主要モジュールは一部のみここで参照)
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - broker_factory.py
      - reconciler.py
      - risk_manager.py
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - data/                      (実行時に利用されるディレクトリ / ファイル)
      - monitoring.db (デフォルト: SQLITE_PATH)
      - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
      - kabusys.duckdb (DUCKDB_PATH)
      - kill.flag, stop_requested.flag, execution.pid
    - logs/                      (デフォルトのログ出力先)

（上記はリポジトリ内の一部ファイルを抜粋した構成です。実際のファイル・モジュールは更に存在する場合があります）

---

## よく使うコマンド一覧

- .env 作成
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- 実行エンジン起動
  - python -m kabusys.run_execution
- 監視ループ起動
  - python -m kabusys.run_monitoring
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

もし README の内容を実際の環境（依存関係の正確なバージョンや追加の実行オプション等）に合わせて調整したい場合、使用している環境や要望（例: requirements.txt の生成、systemd ユニットファイル例、Dockerfile など）を教えてください。追加でサンプルの systemd / Docker / CI 設定の雛形も作成できます。