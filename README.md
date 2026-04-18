KabuSys
======

日本株向け自動売買システムのコアライブラリ群（リポジトリ内スクリプト・モジュール群）の簡易 README です。  
この README はソースコード（src/kabusys 以下）を基に作成しています。

概要
----
KabuSys は日本株の自動売買・研究・監視に必要なコンポーネントを備えたライブラリ/ツール群です。  
主な役割は次のとおりです。

- ExecutionEngine（発注エンジン）: 発注・注文管理・リスク管理を行う（本番 / ペーパートレード対応）
- Monitoring（監視）: システム状態・注文・リスクを定期ポーリングしてログ/アラートを生成
- Portfolio（ポートフォリオ構築）: 候補選定、重み計算、ポジションサイズ算出
- Research（研究）: ファクター計算、将来リターン・IC・統計解析
- AI モジュール: ニュースの NLP によるセンチメント（OpenAI を利用）、市場レジーム判定
- ユーティリティ: ロギング設定、プロセス優先度設定、設定ファイル生成/検証など

主な機能一覧
--------------
- 環境設定ウィザード（.env の対話式作成 / 更新）: kabusys.config_setup.run_wizard
- 設定検証 CLI: kabusys.validate_config（.env と config/*.yaml の基本チェック）
- Execution 起動スクリプト: run_execution.py（KABUSYS_ENV により paper_trading を分離）
- Monitoring 起動スクリプト: run_monitoring.py（SystemMonitor を定期実行）
- 監視データ永続化（SQLite）と監視ロジック（system/trade/risk/kill-switch）
- ポートフォリオ構築: 候補選定、等重/スコア重み、ポジションサイズ（単元株調整、資金割当）
- 研究用ファクター計算（DuckDB 経由、prices_daily/raw_financials テーブル参照）
- Paper Trading 検証レポート生成 CLI: tools.paper_verification_report
- OpenAI 連携: ニュース NLP（ai.news_nlp）、レジーム検出（ai.regime_detector）

セットアップ手順
----------------
以下はローカルで動かすための基本手順例です。

1. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - 主要依存: duckdb, psutil, openai
   - 追加（任意）: PyYAML（config yaml のパース検証に使用）
   例:
     pip install duckdb psutil openai pyyaml

   ※ requirements.txt は本リポジトリに含まれていないため、実行環境に応じて必要なパッケージを追加してください。

3. プロジェクトルートに data/ と logs/ を作成（自動生成されることもあります）
   - mkdir -p data logs

4. .env を作成
   - 対話式で作成する場合:
     python -m kabusys.config_setup
   - 手動で作成する場合は .env.example を参考に必要な値を設定してください。

5. 設定の検証
   - python -m kabusys.validate_config
   - 警告も FAIL 扱いにする場合: python -m kabusys.validate_config --strict

必須環境変数（主要）
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）

代表的な任意 / デフォルト項目
- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
- DUCKDB_PATH: duckdb ファイルパス。デフォルト: data/kabusys.duckdb
- SQLITE_PATH: 監視用 SQLite（monitoring）デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading の場合に使用）
- LOG_LEVEL: ログレベル（INFO 等）
- LOG_DIR: ログ保存ディレクトリ（デフォルト: logs）
- OPENAI_API_KEY: OpenAI を使う機能（ai.news_nlp / ai.regime_detector）で必要

重要な挙動（運用ノート）
- .env 自動ロード:
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）を自動検出し、.env/.env.local を読み込みます。
  - 自動ロードを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- Kill Switch:
  - data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります（KillSwitch モジュール）。
  - 設定 KILL_FLAG_CLEAR_ON_START によって起動時に自動クリアするか制御できます（本番は 0 推奨）。
- 停止フラグ:
  - run_monitoring.py / run_execution.py は data/stop_requested.flag を監視して安全に停止します。

使い方（主要コマンド）
--------------------

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Execution（発注エンジン）起動
  - python -m kabusys.run_execution
  - 備考: KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB に書き込みます。
  - 実行中に data/stop_requested.flag を作成すると安全に停止します。

- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト: 60）
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視テーブルを管理します。

- Paper Trading 検証レポート（CLI）
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    --from YYYY-MM-DD, --to YYYY-MM-DD, --db PATH
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI モジュールの利用（プログラムから）
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key=None) — OpenAI API キーが必要（api_key 引数または OPENAI_API_KEY 環境変数）

ログ
---
- ログはデフォルトで stdout (StreamHandler) とファイル出力（logs/<app_name>.log）に出力されます。  
- ログディレクトリは環境変数 LOG_DIR で上書き可能。ログレベルは LOG_LEVEL。

ディレクトリ構成（主なファイル）
------------------------------
以下は src/kabusys 以下の主要モジュール/ファイルの抜粋構成です（完全版ではありません）。

- kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定取得ロジック
  - config_setup.py                — .env 対話式ウィザード
  - validate_config.py             — 設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — Monitoring 起動スクリプト

  - utils/
    - logging_setup.py             — ログ設定ユーティリティ
    - process_priority.py          — プロセス優先度 / CPU affinity 設定
  - execution/                      — 発注エンジン関連（Engine / OrderManager 等）
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - monitoring/
    - monitoring_db.py             — SQLite 永続化レイヤ
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
    - news_nlp.py                   — ニュース NLP（OpenAI）
    - regime_detector.py            — 市場レジーム判定（OpenAI）
  - data/ (モジュール未表示)        — パイプライン / データアクセス層（DuckDB を利用）
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート生成 CLI

注意点・運用上のヒント
--------------------
- DB/ログディレクトリ:
  - デフォルトは data/ と logs/。これらは適切な場所に作成・バックアップを行ってください。
- 本番起動時のチェック:
  - KABUSYS_ENV=live の場合は validate_config の警告を必ず確認してください（LINE 通知などの設定漏れがないか）。
- OpenAI / 外部 API:
  - OpenAI を使う機能は API キー（OPENAI_API_KEY）が必須。API 呼び出し時はレートやエラーに対してリトライ実装がありますが、運用上の監視が必要です。
- Kill Switch / Stop フラグ:
  - 運用で安全に停止したい場合は data/stop_requested.flag（run_* の停止用）や data/kill.flag（実行系への強制停止）を活用します。
  - KILL_FLAG_CLEAR_ON_START を誤って 1 にすると本番で自動クリアされるため注意してください。

開発・拡張
----------
- DuckDB を使った研究向けクエリ群（research/*.py）は、prices_daily や raw_financials テーブルのスキーマに依存します。テーブル準備やデータ投入は別途パイプラインで実施してください。
- Portfolio / Position Sizing 関数群は純粋関数として設計されており、単体テストが書きやすくなっています。ユニットテストの追加を推奨します。
- AI モジュールは外部 API 呼び出し部分（_call_openai_api 等）を差し替え可能に設計されており、テスト時はモックを利用してください。

ライセンス・バージョン
---------------------
- パッケージバージョン: kabusys.__version__ = "0.1.0"
- ライセンス情報はリポジトリのトップレベルファイルを参照してください（本 README にはライセンスファイルを含めていません）。

付録: よく使うコマンド例
----------------------
- .env を作る（対話式）:
  python -m kabusys.config_setup

- 設定確認:
  python -m kabusys.validate_config

- 監視を起動（デフォルトポーリング 60s）:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Execution を起動:
  python -m kabusys.run_execution

- Paper Trading 検証レポート（2026-04-01〜2026-04-11）:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

最後に
-----
この README はリポジトリ内のソース（src/kabusys 以下）を元に要点を整理したものです。実際のデプロイや運用では、各 config/*.yaml、運用監視（外部モニタ・アラート）、バックアップ、テスト戦略を詳細に設計してください。もし README をプロジェクトの README.md として整備する場合、環境ごとの起動例や systemd / supervisor 用の unit ファイルのサンプル、requirements.txt や CI 設定を追記することを推奨します。