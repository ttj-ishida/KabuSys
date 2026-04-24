# KabuSys

日本株自動売買システムのリポジトリ（ライブラリ／起動スクリプト群）。  
この README は、プロジェクトの概要、主要機能、セットアップ手順、使い方、およびディレクトリ構成を説明します。

---

目次
- プロジェクト概要
- 機能一覧
- 必要条件・依存関係
- セットアップ手順
- 主要な使い方（コマンド例）
- 主要環境変数
- 実行時のファイル / フラグ
- ディレクトリ構成（主要ファイルの説明）
- 開発者向けメモ

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システム向けユーティリティとコンポーネント群です。  
主な目的は次の通りです。

- シグナル→銘柄選定→ポジションサイジング→発注を支援するライブラリ
- 実行エンジン（ExecutionEngine）とそれを監視する Monitoring コンポーネント
- Paper Trading 用の検証ツール（履歴保存／レポート生成）
- AI（OpenAI）を使ったニュースセンチメント評価・市場レジーム判定モジュール
- 開発用 CLI（.env ウィザード、設定検証）

設計方針として、DB（DuckDB/SQLite）をデータ層に利用し、本番 DB とペーパートレード DB を分離できる設計、LLM 呼び出しはリトライやフォールバックを備えた堅牢な実装がされています。

---

## 機能一覧

- 環境設定ウィザード（対話式 .env 生成）: kabusys.config_setup
- 設定検証 CLI（.env / config/*.yaml のチェック）: kabusys.validate_config
- ExecutionEngine 起動スクリプト（本番 / paper_trading 切替）: run_execution.py
- Monitoring ポーリング（System / Trade / Risk の監視）: run_monitoring.py
- Kill Switch（フラグファイルによる ExecutionEngine 強制停止）
- Monitoring DB（SQLite）ラッパー: monitoring_db.py
- Paper Trading 検証レポート生成ツール: kabusys.tools.paper_verification_report
- ポートフォリオ構築ユーティリティ（候補選定、重み計算、サイズ計算、セクター制限）
- リサーチ（DuckDB を使ったファクター計算、特徴量解析、IC 計算）
- AI モジュール（ニュース NLP -> ai_scores、レジーム判定 -> market_regime）
- Logging / プロセス優先度・CPU affinity ユーティリティ

---

## 必要条件・依存関係

- Python 3.9+
- 必須パッケージ（例）:
  - duckdb
  - psutil
  - openai
- 追加で便利なパッケージ:
  - PyYAML（config/*.yaml の検証に使用。インストールしていない場合は検証をスキップ）
- 標準ライブラリ: sqlite3, logging, threading, pathlib, datetime 等

（実際のプロジェクトでは requirements.txt / pyproject.toml を参照してください）

例:
pip install duckdb psutil openai PyYAML

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置

2. 仮想環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存関係をインストール
   pip install -r requirements.txt
   （requirements.txt がない場合は上記必須パッケージを個別にインストール）

4. .env の作成（対話式ウィザード）
   python -m kabusys.config_setup
   ウィザードは .env（デフォルトはプロジェクトルート/.env）を生成します。
   もしくは既存の .env ファイルを編集してください。

5. 設定検証
   python -m kabusys.validate_config
   必須項目が不足していないか確認します。--strict を付けると警告も失敗扱いになります。

6. DB の初期化
   - monitoring 用 SQLite の初期化は run_monitoring / run_execution 実行時に自動で行われます（init_monitoring_db）。
   - DuckDB ファイル（デフォルト data/kabusys.duckdb）は適宜準備してください（データ投入は別途）。

---

## 主要な使い方（コマンド例）

- 環境ウィザード（.env の作成・更新）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- ExecutionEngine を起動
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録します。
  - 起動時に data/stop_requested.flag が存在すると起動を行わず終了します。

- Monitoring を起動（ポーリング）
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60）
  - モニタは実行環境に関わらず本番 sqlite_path を参照して監視ログを書きます。

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report
  期間指定:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  DB 指定:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI ニューススコアリング（ライブラリ関数）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - OpenAI API キーは引数または環境変数 OPENAI_API_KEY を使用

- 市場レジーム判定（ライブラリ関数）
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## 主要環境変数

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: 実行環境。development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring）SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の売買成立モード（instant / partial / never / reject）
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）
- LOG_DIR: ログディレクトリ（デフォルト logs/）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで利用）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知に使用（任意）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1。既定 0）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると自動 .env ロードを無効化（テスト用）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

.env ウィザードで上記の多くを設定できます。

---

## 実行時のファイル / フラグ

- データ / フラグディレクトリ（デフォルト）
  - data/monitoring.db         — 監視用 SQLite（Settings.sqlite_path）
  - data/paper_trading.db      — Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）
  - data/kabusys.duckdb        — DuckDB（DUCKDB_PATH）
  - data/kill.flag             — Kill Switch（ExecutionEngine を停止させる合図）
  - data/stop_requested.flag   — run_execution/run_monitoring の停止トリガ（起動スクリプトが参照）
  - data/execution.pid         — ExecutionEngine の PID（起動スクリプトで使用）

- ログ
  - デフォルト: logs/<app_name>.log（app_name は "execution" / "monitoring" など）
  - setup_logging は stdout と日次ローテーションファイルハンドラを設定します

---

## ディレクトリ構成（主要ファイルの説明）

（リポジトリの src/kabusys 配下を想定）

- kabusys/
  - __init__.py
  - config.py
    - Settings クラス: 環境変数読み取り・検証、デフォルト値
    - 自動 .env ロード機能（プロジェクトルートの .env / .env.local）
  - config_setup.py
    - 対話式 .env ウィザード（python -m kabusys.config_setup）
  - validate_config.py
    - 起動前検証 CLI（必須 env / YAML / パス等のチェック）
  - run_execution.py
    - ExecutionEngine 起動スクリプト（KABUSYS_ENV により paper_trading を切替）
  - run_monitoring.py
    - SystemMonitor のポーリング起動スクリプト
  - utils/
    - logging_setup.py — 共通のログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite 用永続化レイヤ（テーブル作成 / CRUD）
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py — 注文の滞留／異常チェック（参照用）
    - risk_monitor.py — ドローダウン・ポジション数の監視
    - kill_switch.py — kill.flag の書き込み / 解除
    - monitoring_engine.py — 各モニタを束ねるポーリングエンジン
    - alert_manager.py — アラート送信ロジック（LINE 等への通知を想定）
  - execution/
    - execution_engine.py — ExecutionEngine の本体（発注ループ等）
    - broker_factory.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py
  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み付け
    - position_sizing.py — 株数計算（リスク制約・lot 単位）
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — momentum / volatility / value などのファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン計算 / IC / 統計サマリ
  - ai/
    - news_nlp.py — raw_news を OpenAI で評価して ai_scores に書き込む
    - regime_detector.py — ETF + マクロニュースを合成して market_regime を算出
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポートを作成する CLI

---

## 開発者向けメモ / 注意点

- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を基準）から行われます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Settings では KABUSYS_ENV の値チェックや PAPER_FILL_MODE の検証などを行います。無効な値は ValueError を発生させます。
- run_execution は paper_trading モード時に paper_sqlite_path を使って DB を分離します。本番 DB と混ざらないよう注意してください。
- Monitoring は監視用 DB（sqlite_path）に常に書き込みます（環境に関係なく本番のパスを用いる点に注意）。
- OpenAI API を利用する機能（news_nlp / regime_detector）は API キー（OPENAI_API_KEY）を必要とします。API 呼び出し時はリトライや JSON 検証が組み込まれており、失敗時はフェイルセーフ（スコア 0.0 等）で続行します。
- ログは stdout とファイルの両方に出力されます。ログディレクトリの作成に失敗した場合は標準出力のみで継続します。
- kill.flag / stop_requested.flag による制御が存在します。特に本番環境では kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は危険なのでデフォルト 0 を推奨します。

---

この README はコードベースから抽出した主要な情報をまとめたものです。実行やデプロイ前に必ず python -m kabusys.validate_config を実行し、.env を正しくセットしてください。必要があれば README に環境固有の運用手順（systemd ユニット、コンテナ設定、DB 初期ロードなど）を追記してください。