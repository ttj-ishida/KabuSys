# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ用 README（日本語）

注意: この README は src/ 以下のコードから構成・挙動を抜粋してまとめたものです。実運用前に必ず `python -m kabusys.validate_config` で設定検証を実施してください。

---

## プロジェクト概要

KabuSys は日本株の自動売買・研究・監視を支援する Python ベースのシステムです。  
主要な機能群は以下を含みます。

- 実行エンジン（ExecutionEngine）：注文発行・リスク管理・リコンシリエーション
- 監視（Monitoring）：システム健全性・注文ログ・リスク監視・Kill Switch
- ポートフォリオ構築（Portfolio）：候補選定・重み計算・ポジションサイズ計算
- リサーチ（Research）：ファクター計算・特徴量探索・IC 計測
- AI モジュール：ニュース NLP による銘柄センチメント、レジーム判定（OpenAI）
- 運用用ツール：.env ウィザード、設定検証、ペーパートレード検証レポート 等

設計方針として、実行系とリサーチ系を分離し、DB（SQLite / DuckDB）を通じてデータ永続化／分析を行います。Paper Trading（ペーパートレード）は本番 DB と分離して動作します。

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py：ExecutionEngine の起動（KABUSYS_ENV による paper/live 切替）
  - run_monitoring.py：SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定可）
- 設定管理
  - config_setup.py：対話式 .env 作成ウィザード
  - validate_config.py：環境変数・config/*.yaml の事前検証 CLI（--strict 有り）
- 監視・Kill Switch
  - system_monitor, trade_monitor, risk_monitor を組み合わせる MonitoringEngine
  - data/kill.flag による ExecutionEngine 停止（KillSwitch）
- ポートフォリオ構築
  - 候補選定（select_candidates）
  - 等配分・スコア加重（calc_equal_weights, calc_score_weights）
  - ポジションサイズ計算（calc_position_sizes）
  - セクターキャップ・レジーム乗数（apply_sector_cap, calc_regime_multiplier）
- リサーチ
  - ファクター計算（momentum, volatility, value）
  - 将来リターン、IC 計算、統計サマリー
- AI（OpenAI）
  - ニュースセンチメント付与（news_nlp.score_news）
  - 市場レジーム判定（regime_detector.score_regime）
- 解析ツール
  - tools/paper_verification_report.py：ペーパートレード結果の検証レポート生成

---

## 前提条件 / 依存ライブラリ

主な依存（必須・推奨）：
- Python 3.9+
- duckdb
- psutil
- openai（AI 関連機能を使用する場合）
- PyYAML（validate_config の YAML 検証で使用、未インストールでも動作するが検証はスキップされます）

インストール例（pip）:
pip install duckdb psutil openai PyYAML

※ その他の一般的なライブラリ（sqlite3 等）は標準ライブラリで提供されます。

---

## セットアップ手順

1. リポジトリをクローン / 展開
2. 仮想環境を作成して依存をインストール
   - python -m venv .venv
   - source .venv/bin/activate
   - pip install -r requirements.txt  （requirements.txt がある場合）
   - もしくは上の個別インストール
3. .env の準備
   - 対話式で作成:
     python -m kabusys.config_setup
   - もしくは .env.example を参考に手動作成（.env は Git 管理に含めないこと）
4. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 警告も FAIL にしたい場合は --strict
5. 必要な初期ディレクトリを作成（ログ・data 等）
   - mkdir -p data logs

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: 実行環境 {development, paper_trading, live}（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite のパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（paper 環境で使用、デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- LOG_DIR: ログ出力ディレクトリ（デフォルト: logs）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
- PAPER_FILL_MODE: paper_trading 時のモック約定モード（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリア（0/1、デフォルト 0）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- PID_FILE_PATH: Execution の PID ファイルパス（デフォルト: data/execution.pid）

設定は OS 環境変数、.env.local、.env の順で読み込まれます（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

---

## 起動と使い方

リポジトリのルートから実行します。いずれも setup_logging を使うため logs ディレクトリがあるとログファイルが出力されます。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告で失敗扱い）: python -m kabusys.validate_config --strict

- ExecutionEngine（実行エンジン）起動
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録します。production / live では本番 sqlite_path を使用。
    - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
    - 実行中に stop flag（data/stop_requested.flag）を作ると走っているエンジンを停止します。
    - PID ファイル: data/execution.pid（Settings.pid_file_path により上書き可）
    - プロセス優先度を "high" に設定しようとします（権限により失敗する場合あり）

- Monitoring（SystemMonitor）起動
  - python -m kabusys.run_monitoring
  - 動作:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で指定（デフォルト 60）
    - 監視は本番 sqlite_path を使用（環境にかかわらず）
    - data/stop_requested.flag を検知するとループを抜けて終了
    - プロセス優先度を "high" に設定しようとします

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 関連（ライブラリ呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - OpenAI API キーは api_key 引数か OPENAI_API_KEY 環境変数で指定
    - DuckDB 接続（conn）を受け取ります
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## 停止 / Kill Switch の仕組み

- 手動停止（Execution 停止指示）
  - data/kill.flag に理由テキストを書き込むことで ExecutionEngine に停止を指示できます（KillSwitch）。
  - run_execution および ExecutionEngine は kill.flag / stop_requested.flag の存在を確認して停止します。
- run_* スクリプト停止
  - data/stop_requested.flag が存在すると run_monitoring / run_execution の起動ループが終了します（デプロイ運用でプロセスを安全に止めるためのフラグ）。
- 設定 KILL_FLAG_CLEAR_ON_START=1 を設定すると Execution 起動時に既存の kill.flag を自動でクリアします（本番環境では危険なのでデフォルトは 0）。

---

## ログ

- ログは stdout とファイルの両方に出力されます（utils.logging_setup）。
- デフォルトログディレクトリ: logs/
- ファイルログ名: <app_name>.log（例: logs/execution.log, logs/monitoring.log）
- 日次ローテーション、バックアップ保持 30 日
- ログレベルは環境変数 LOG_LEVEL（または setup_logging の引数）で制御

---

## 開発者向けメモ・注意点

- DB マイグレーションは簡易（monitoring_db.init_monitoring_db 内のスクリプト）で実施され、既存スキーマに列が無ければ ALTER TABLE で追加する処理があります。
- モジュールは外部状態（datetime.today() 等）を参照しない設計を心がけており、テストしやすく作られています（AI モジュール等）。
- OpenAI 呼び出しはリトライ・バックオフ処理を持ち、失敗時は安全側（0 値）で処理を続行する実装になっています。
- Paper Trading は本番 DB と分離されるため、ペーパートレード用 DB を別に設定してください。

---

## ディレクトリ構成（抜粋）

リポジトリの主なファイル / ディレクトリ（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / Settings 管理
  - config_setup.py            — .env 対話ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py         — ロギング設定ユーティリティ
    - process_priority.py      — プロセス優先度 / cpu affinity
  - execution/                  — 実行エンジン関連（broker_factory, execution_engine, order_manager,...）
  - monitoring/
    - monitoring_db.py         — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py               — ニュース NLP / OpenAI 呼び出し
    - regime_detector.py       — 市場レジーム判定
  - data/                       — 実行時生成されるファイル（data/*.db, kill.flag, execution.pid など）
  - tools/
    - paper_verification_report.py

（上記は抜粋です。実際のリポジトリにはさらに多くのモジュールと実装ファイルがあります。）

---

## よく使うコマンドまとめ

- 対話式 .env 作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- Execution 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - python -m kabusys.run_monitoring
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

---

この README はコードベースの主要な使い方・設定をまとめたものです。運用に入る前に必ず .env を正しく設定し、validate_config によるチェック、テスト環境での動作検証を行ってください。質問や補足があれば教えてください。