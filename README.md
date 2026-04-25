# KabuSys

日本株自動売買システムのライブラリ／起動スクリプト群。システム監視、Execution エンジン、ペーパートレード用モック、ファクター計算、ニュース NLP、ポートフォリオ構築などのユーティリティを提供します。

バージョン: 0.1.0

---

概要・目的、インストールや起動方法、主要機能、ディレクトリ構成などをこの README にまとめます。

## プロジェクト概要

KabuSys は日本株の自動売買を想定したコンポーネント群です。主な要素は以下です。

- ExecutionEngine（発注実行ロジック）とそれを補助する OrderManager / RiskManager 等
- Monitoring（システム稼働監視、トレード監視、リスク監視、Kill Switch）
- Portfolio / Position sizing（銘柄選定、重み計算、株数決定）
- Research（ファクター計算 / 特徴量探索 / IC 計算）
- AI モジュール（ニュース NLP による銘柄センチメント、レジーム検出）
- ユーティリティ（ログ設定、プロセス優先度設定、.env ウィザード、設定検証、レポート生成）

設計方針の例:
- 本番 DB とペーパートレード DB を分離
- ルックアヘッドバイアスを避ける（date.today() を直接参照しない設計）
- 外部 API 呼び出し（OpenAI など）は失敗時にフェイルセーフで継続

---

## 主な機能一覧

- 環境設定ウィザード（.env 生成）: kabusys.config_setup
- 設定検証 CLI（.env と config/*.yaml をチェック）: kabusys.validate_config
- Execution 起動スクリプト: kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録
- Monitoring 起動スクリプト: kabusys.run_monitoring
  - モニタリングループ（ポーリング間隔は MONITOR_POLL_INTERVAL で上書き可能、デフォルト 60 秒）
- Monitoring コンポーネント
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager（通知管理）
  - SQLite ベースの永続化（monitoring_db）
- Portfolio 構築ユーティリティ
  - 候補選定、等重・スコア重み、セクター制限、レジーム乗数、ポジションサイズ計算
- Research（DuckDB を利用したファクター計算）
  - モメンタム・ボラティリティ・バリュー等の計算
  - 特徴量解析（forward returns, IC, summary）
- AI 機能
  - news_nlp: OpenAI によるニュースセンチメント取得（ai_scores へ書き込み）
  - regime_detector: MA とマクロニュースを合成して市場レジーム判定
- ツール
  - paper_verification_report: ペーパートレード結果の検証レポート生成

---

## セットアップ手順

前提:
- Python 3.10+（型ヒントに match などは使っていませんが、typing 記法を利用）
- SQLite は標準ライブラリで利用
- 外部ライブラリ例: duckdb, psutil, openai, PyYAML（validate 用）

1. リポジトリをクローン / 配布を展開
2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS) / .venv\Scripts\activate (Windows)
3. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai PyYAML
   - （プロジェクトで requirements.txt を用意している場合はそれを使用してください）
4. 初期設定（.env）の作成
   - インタラクティブに作成する:
     - python -m kabusys.config_setup
     - 質問に従って入力し、.env を生成します（.env は Git にコミットしないでください）
   - 自動ロード:
     - config モジュールはプロジェクトルートに .env /.env.local があれば自動で読み込みます（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）
5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱いになります
6. データディレクトリの作成
   - デフォルトの DB / ログ ディレクトリは以下:
     - data/kabusys.duckdb (DuckDB)
     - data/monitoring.db (SQLite, monitoring)
     - data/paper_trading.db (ペーパートレード用、paper_trading モード)
     - logs/ にログが出力されます
   - これらのパスは環境変数 DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, LOG_DIR で上書き可能

注意:
- 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（validate_config でチェックされます）
- OpenAI を使う機能を使用する場合: OPENAI_API_KEY を設定してください

例の最小 .env（実運用時は secret 系を適切に設定）:
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 起動 / 使い方

以下は代表的な実行コマンドです。パッケージは kabusys 配下にスクリプトモジュールとして置かれているため python -m で実行します。

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Execution エンジンを起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV 環境変数が paper_trading のときは MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します
    - 起動時に data/stop_requested.flag が既にあると起動せず終了します
    - data/execution.pid に PID を書き込む実装が呼び出し元により提供されます
    - プロセス優先度を "high" に設定します（set_process_priority）

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き（デフォルト 60 秒）
    - monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（monitoring DB は本番 DB を参照）
    - 監視ループは data/stop_requested.flag の存在で終了します

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH で指定

- AI / レジーム・ニュース処理
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime をアプリケーション内から呼び出し可能
  - OPENAI_API_KEY 環境変数を設定してください。API 呼び出しはリトライやフェイルセーフを備えています。

停止・Kill Switch
- Execution 停止シグナルは data/kill.flag を書き込むことで発行できます（KillSwitch が評価している場合に書き込まれます）
- run_monitoring / run_execution は data/stop_requested.flag が存在するとループを終了します（外部からの停止制御に利用）

ログ
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力されます（logs/ ディレクトリは自動作成を試みます）
- 環境変数 LOG_DIR でログディレクトリを変更可能
- LOG_LEVEL でログレベルを指定（DEBUG/INFO/WARNING/ERROR/CRITICAL）

---

## 主要設定項目（環境変数）

重要な環境変数の抜粋:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- OPENAI_API_KEY: OpenAI を使う場合に必要
- LOG_LEVEL: INFO（デフォルト）
- LOG_DIR: ログ出力先
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant | partial | never | reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（1=クリアする、0=しない）

---

## ディレクトリ構成 (主要ファイル)

以下は src/kabusys 以下の主要なモジュールとファイルの概観です（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / Settings 管理（.env 自動ロード）
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — Monitoring ポーリングループ起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - ai/
    - __init__.py
    - news_nlp.py              — ニュース NLP / OpenAI 呼び出しロジック
    - regime_detector.py       — レジーム判定（MA + マクロニュース）
  - monitoring/
    - monitoring_db.py         — SQLite スキーマ初期化 & 永続化層
    - system_monitor.py
    - trade_monitor.py         — (トレード監視ロジック)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py         — (通知管理、LINE 等)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py         — ログ設定ユーティリティ
    - process_priority.py      — プロセス優先度 / CPU affinity 設定
    - __init__.py

（注）実際のリポジトリにはさらに execution 関連のモジュール、data パイプラインや DB マスタ、strategy モジュール等が含まれる想定です。ここでは提供されたファイル群を中心に記載しています。

---

## 開発・デバッグのヒント

- .env を作成したらまず validate_config でチェックする
- Monitoring や Execution を単体で動作検証する際、ペーパートレードモード（KABUSYS_ENV=paper_trading）を使うと実際の発注を行いません
- ロギング設定は kabusys.utils.logging_setup.setup_logging を通じて統一されます。デバッグ時は LOG_LEVEL=DEBUG を設定すると詳細ログが得られます
- OpenAI 呼び出し部はリトライとパースの耐性を持っていますが、API キーやレート制限に注意してください
- DuckDB は分析・リサーチ用に使います。テーブルスキーマ（prices_daily / raw_financials / raw_news 等）に合わせてデータを準備してください

---

## ライセンス / 注意事項

- .env 等に API キーやパスワードを含める場合は決して Git にコミットしないでください
- 実際の発注ロジックを live 環境で動かす場合は十分なテストと安全対策（Kill Switch、LINE 通知など）を行ってください

---

README の内容や追加の CLI、例（docker-compose や systemd ユニットのサンプルなど）を追加したい場合は用途に合わせて追記します。必要があれば運用手順（systemd のサービス定義、ログローテーション設定、バックアップ方針など）のテンプレートも作成できます。