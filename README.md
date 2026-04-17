# KabuSys

日本株自動売買システムのマイクロパッケージ群（ライブラリ + 実行スクリプト群）。

この README はコードベース（src/kabusys 以下）の概要、主要機能、セットアップ手順、使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買に関わる以下の機能を提供します。

- シグナル・ポートフォリオ構築（候補選定・重み付け・株数決定）
- 実行（ExecutionEngine）と注文管理（OrderRepository / OrderManager）
- 監視（System / Trade / Risk の監視、Kill Switch）
- 研究用モジュール（ファクター計算、特徴量解析）
- AI支援モジュール（ニュースのセンチメント評価、レジーム判定：OpenAI 使用）
- ユーティリティ（設定ウィザード、設定検証、レポート生成 等）

設計方針の一部：
- 本番/ペーパートレードを分離（KABUSYS_ENV による挙動切替）
- DuckDB を分析用 DB、SQLite を監視・発注ログ用に利用
- LLM 呼び出しはフェイルセーフ（失敗時は安全側フォールバック）

---

## 機能一覧（主なモジュール）

- 実行・監視
  - run_execution.py：ExecutionEngine 起動スクリプト（KABUSYS_ENV=paper_trading のときは MockBroker を使用）
  - run_monitoring.py：SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL により間隔を変更可能）
- 設定管理
  - config_setup.py：.env を対話式に作成・更新するウィザード
  - validate_config.py：起動前に環境変数と config/*.yaml を検証する CLI
  - config.py：Settings クラス（環境変数読み取り、.env 自動ロード）
- 監視
  - monitoring/*.py：MonitoringDB（SQLite）、SystemMonitor、TradeMonitor、RiskMonitor、MonitoringEngine、KillSwitch、AlertManager（実装断片）
- ポートフォリオ構築
  - portfolio/*：候補選定、重み計算、セクター制限、ポジションサイズ計算
- 研究（research）
  - research/*：ファクター（モメンタム/ボラティリティ/バリュー）計算、特徴量探索、IC・統計サマリ
- AI（OpenAI）
  - ai/news_nlp.py：ニュース記事を LLM でセンチメント評価し ai_scores に書き込む
  - ai/regime_detector.py：MA とマクロニュースで市場レジーム判定（LLM 使用）
- ツール
  - tools/paper_verification_report.py：ペーパートレード検証レポート生成

---

## 前提・依存ライブラリ（代表）

実行するには以下パッケージが必要です（プロジェクト内に requirements.txt が無い場合、適宜インストールしてください）。

- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（validate_config の YAML 検証で使用、無くても動作はするが警告になる）

インストール例：
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

---

## 環境変数（主要なもの）

設定は .env / .env.local / OS 環境変数から読み込まれます。自動ロードはプロジェクトルート（.git または pyproject.toml）を検出した場合にのみ行われます。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須（最低限設定すべきもの）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

運用に関連する主要変数（デフォルト値は code 内の説明参照）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY: OpenAI を使用する機能で必要
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: アラート通知（任意）

ペーパートレード固有
- PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）

監視・制御
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 本番での Kill flag 自動クリア（1 で自動クリア、推奨は 0）
- KILL_FLAG_PATH / PID_FILE_PATH: フラグ・PID のパス（Settings で上書き可能）

---

## セットアップ手順（推奨ワークフロー）

1. リポジトリをクローンしてプロジェクトルートへ移動
2. 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate    # Windows: .venv\Scripts\activate
   ```
3. 依存ライブラリをインストール
   ```
   pip install duckdb psutil openai pyyaml
   ```
4. 対話式ウィザードで .env を作成（.env は決して Git にコミットしない）
   ```
   python -m kabusys.config_setup
   ```
   ウィザードの最後に `.env` に保存されます。必要に応じて `.env.local` を用いてローカル上書きを行ってください。

5. 設定を検証
   ```
   python -m kabusys.validate_config
   ```
   警告も失敗扱いにする場合は `--strict` を付けます。

6. DB ディレクトリ（data 等）が存在しない場合は作成しておくと安心です（自動作成される箇所もありますが念のため）。
   ```
   mkdir -p data
   ```

---

## 使い方

基本的にはモジュールとして起動します（プロジェクトのルートで実行）。

- 実行エンジン（ExecutionEngine）起動
  - ペーパートレード（.env に KABUSYS_ENV=paper_trading を設定）では MockBrokerClient を使用し、`data/paper_trading.db` に記録されます（本番 DB と分離）。
  ```
  python -m kabusys.run_execution
  ```
  起動時に `data/execution.pid` を作成したり、`data/stop_requested.flag` が存在する場合は起動を行わず終了します。停止は `data/stop_requested.flag` を作成するか、Kill Switch により `data/kill.flag` が書き込まれることで行います。

- 監視ループ起動
  - run_monitoring は SystemMonitor をポーリングし、MonitoringDB（sqlite）へログを残します。ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト: 60）。
  ```
  python -m kabusys.run_monitoring
  ```
  run_monitoring は環境にかかわらず Settings.sqlite_path を使用して監視 DB を接続します（監視データは常に指定された sqlite_path に記録されます）。停止は `data/stop_requested.flag` の作成で検知しループを終了します。

- 設定検証（起動前に推奨）
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ペーパートレード検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを明示する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI モジュール（ニューススコアリング / レジーム判定）
  これらは DuckDB 接続と OpenAI API キーが必要です。プログラムから呼び出す際は `OPENAI_API_KEY` を環境変数に設定するか、関数に `api_key` を渡してください。
  - ニューススコア:
    - 関数: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - レジーム判定:
    - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## 停止・制御の仕組み

- stop_requested.flag
  - run_monitoring.py と run_execution.py の両方で停止フラグを監視しています（パス: data/stop_requested.flag）。このファイルが存在すると起動中ループが検知して graceful に終了します。

- kill.flag（Kill Switch）
  - 監視側（KillSwitch）が条件を満たすと `KILL_FLAG_PATH`（デフォルト: data/kill.flag）へ理由を書き込みます。ExecutionEngine は kill.flag を検出して停止すべき（Settings.kill_flag_clear_on_start で起動時にクリアする挙動を制御）という運用設計です。

- PID ファイル
  - ExecutionEngine は起動時に PID を `data/execution.pid` に書きます。SystemMonitor は該当 PID の存否を確認してプロセス停止を検出します。

---

## DB とデータファイルについて

- DuckDB（分析用）
  - デフォルト: data/kabusys.duckdb（Settings.duckdb_path）
- SQLite（監視用）
  - デフォルト: data/monitoring.db（Settings.sqlite_path）
- Paper Trading SQLite
  - デフォルト: data/paper_trading.db（Settings.paper_sqlite_path）
- 監視用 DB（monitoring_db.init_monitoring_db）:
  - 起動時に必要なテーブルとインデックスを冪等的に作成します。マイグレーション（カラム追加）もコード内で扱われます。

---

## 主要な設定ファイル / CLI

- .env（env 設定ファイル）
  - config_setup により対話式で作成可能。例として以下のようなキーが含まれます（値は伏せる）:
    - JQUANTS_REFRESH_TOKEN=
    - KABU_API_PASSWORD=
    - KABU_API_BASE_URL=
    - DUCKDB_PATH=
    - SQLITE_PATH=
    - KABUSYS_ENV=
    - LOG_LEVEL=
    - KILL_FLAG_CLEAR_ON_START=

- config/*.yaml
  - validate_config は config ディレクトリの YAML ファイル存在と（PyYAML があれば）パース検証を行います。存在しない場合は警告を出します。

---

## ディレクトリ構成（概観: src/kabusys）

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - tools/
    - __init__.py
    - paper_verification_report.py
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
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (実装断片)
  - utils/
    - __init__.py
    - process_priority.py
  - execution/               # 発注関連（Repository / Engine / BrokerFactory 等、抜粋で存在）
  - data/ (ランタイムで作られるディレクトリ、DBやフラグファイルを配置)

（上記はリポジトリの主要ファイルを抜粋した一覧です）

---

## 運用上の注意点 / ベストプラクティス

- .env は絶対に Git にコミットしないでください。
- 本番（KABUSYS_ENV=live）の場合、LINE の通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を必ず確認してください。validate_config は live 環境時に追加警告を出します。
- OpenAI の利用はコストとレイテンシに注意。API 呼び出しはリトライ・バックオフやフェイルセーフを備えていますが、キー管理とレート制限に注意してください。
- ペーパートレード時は PAPER_TRADING_SQLITE_PATH を用いて本番 DB と完全に分離されます。デフォルトは data/paper_trading.db。
- run_monitoring は常に Settings.sqlite_path（監視 DB）を使用します。環境にかかわらず監視データは同一 DB に残る設計です。
- process priority / cpu affinity 設定は psutil の権限次第で失敗することがあります（警告ログでスキップされます）。

---

## 開発・テストのヒント

- validate_config.validate() をユニットテストから呼んで設定の整合性をチェックできます。
- monitoring_engine.MonitoringEngine.run_once() はテスト用に各 Monitor を一回だけ実行するユーティリティとして使えます。
- AI モジュールの外部呼び出しは _call_openai_api をモックしてテスト可能に設計されています。
- DuckDB 接続を使う関数は接続を引数で受け取るため、テスト用の一時 DB を渡して検証できます。

---

以上がこのコードベースの README 相当の概要です。追加で README に載せたい運用手順（例: systemd ユニットファイル、Docker 化、CI のセットアップ等）があれば、その目的に合わせたサンプルを作成します。必要であれば英語版 README も作成可能です。