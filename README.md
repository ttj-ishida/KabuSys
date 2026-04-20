KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株自動売買システム「KabuSys」のコアライブラリです。  
戦略／ポートフォリオ構築、発注エンジン、監視、AI を用いたニュース解析やレジーム判定、
研究用ユーティリティを含みます。

本 README はローカルでのセットアップ、主な機能、実行方法、ディレクトリ構成の概要を日本語でまとめたものです。

目次
-
- プロジェクト概要
- 主な機能
- 前提（依存パッケージ）
- セットアップ手順
- 実行例（使い方）
- 環境変数 / .env の主要項目
- 停止・Kill Switch の仕組み
- ディレクトリ構成

プロジェクト概要
-
KabuSys は以下の主要コンポーネントから構成されています。

- ExecutionEngine: ブローカーとのやり取り、発注管理、リスク管理、約定整合（reconciler）を担う。
- Monitoring: システム稼働状況・データ鮮度・注文の健全性・リスクを監視し、必要に応じてアラート送信や Kill Switch（停止フラグ）を発動する。
- Portfolio: 銘柄選定、重み算出、株数算出（単元株丸め）、セクター制限・レジーム乗数などの純粋関数群。
- Research: DuckDB の市場データを用いたファクター計算・特徴量解析ユーティリティ。
- AI モジュール: ニュースのセンチメント解析（OpenAI）や市場レジーム判定。
- ツール: 環境設定ウィザード、設定検証、ペーパートレード検証レポート生成など。

主な機能
-
- 環境設定ウィザード（対話式 .env 作成）：kabusys.config_setup
- 設定検証 CLI（.env / config/*.yaml の検査）：kabusys.validate_config
- 実運用用 ExecutionEngine 起動スクリプト：run_execution.py
  - KABUSYS_ENV=paper_trading では MockBroker を使用し paper_trading DB に分離保存
- 監視ポーリングループ起動スクリプト：run_monitoring.py
  - MONITOR_POLL_INTERVAL で間隔を調整可能（デフォルト 60 秒）
  - 監視は環境に関わらず本番 sqlite_path を使用（監視用 DB は一元管理）
- 監視データ永続化（SQLite）：monitoring_db.py（テーブル初期化・読み書き API）
- リスク監視（ドローダウン、ポジション上限等）と Kill Switch（data/kill.flag）
- ニュース NLP（OpenAI）による銘柄別センチメント付与（ai.news_nlp）
- Regime Detector（AI + ETF ma200 で市場レジーム判定）
- ポートフォリオ構築：候補選定・等比重/スコア加重・ポジションサイズ計算・セクターキャップ
- 研究用ファクター計算（momentum/value/volatility）と特徴量解析
- Paper Trading 検証レポート生成ツール（tools/paper_verification_report.py）

前提（依存パッケージ）
-
主な外部依存（代表例）:
- python >=3.9（型アノテーション等を前提）
- duckdb
- psutil
- openai
- PyYAML（config ファイルの検証で任意）
- sqlite3（標準ライブラリ）
実際の導入では requirements.txt を用意して pip install -r で管理してください（本リポジトリには付属していないため、下記例を参照）。

セットアップ手順（ローカル開発向け）
-
1. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール（最低限）
   - pip install duckdb psutil openai PyYAML

   （必要に応じて他の依存を追加してください）

3. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは手動でプロジェクトルートに .env を作成（.env.example を参照）

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります:
     - python -m kabusys.validate_config --strict

5. データディレクトリ / ログディレクトリの作成
   - デフォルトでは data/ と logs/ にファイルを書きます。必要に応じて環境変数でパスを上書きしてください。

使い方（実行例）
-
1. 環境変数の例（.env）
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - KABUSYS_ENV=development|paper_trading|live
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   - LOG_LEVEL=INFO
   - OPENAI_API_KEY=...   （AI 機能を使う場合必須）
   - LOG_DIR=logs

2. 監視（Monitoring）を起動
   - 簡易起動（プロジェクトルートで）:
     - python -m kabusys.run_monitoring
   - ポーリング間隔を変更する:
     - export MONITOR_POLL_INTERVAL=30
     - python -m kabusys.run_monitoring
   - 監視プロセスは data/stop_requested.flag を検知するとループを抜けて終了します。

   ※ run_monitoring は監視用に settings.sqlite_path（SQLITE_PATH）を常に使用します（KABUSYS_ENV に関わらず）。

3. ExecutionEngine を起動（発注エンジン）
   - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading のときは MockBroker を使い、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録され、本番 DB と完全に分離されます。
   - 実行中は PID を data/execution.pid に書きます。停止は data/stop_requested.flag を作成して監視プロセス経由で停止させるか、Kill Switch によって data/kill.flag が作成される場合があります。

4. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report
   - 期間を指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB パスを明示:
     - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

5. AI 機能（ニュース NLP / レジーム検出）
   - OPENAI_API_KEY が必要です。呼び出しはライブラリ関数経由で行います（自動で CLI から実行するスクリプトは付属していませんが、score_news / score_regime を呼んで DB に書き込み可能です）。

主要な環境変数（サマリ）
-
- KABUSYS_ENV: 実行環境（development / paper_trading / live）; Settings.env による検証あり
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ出力ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒。run_monitoring で使用。デフォルト 60）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリアするか（1=クリア、0=クリアしない。production では 0 推奨）

停止・Kill Switch の仕組み
-
- stop_requested.flag（data/stop_requested.flag）
  - run_monitoring.py / run_execution.py はこのファイルが存在することを検知すると優雅に終了します（運用管理用の停止フラグ）。
- kill.flag（Settings.kill_flag_path / デフォルト data/kill.flag）
  - Monitoring の KillSwitch がリスク閾値超過（大きなドローダウン等）を検出したときに作成され、ExecutionEngine に停止シグナルを与えます。
  - ExecutionEngine は起動時に kill.flag を自動クリアする挙動を制御する環境変数 KILL_FLAG_CLEAR_ON_START に従います（production では自動クリアを無効にすることを推奨）。

ログ
-
- ログは標準出力（stdout）とファイル（TimedRotatingFileHandler）両方へ出力されます。
- デフォルトログディレクトリ: logs/
- 各アプリケーション（execution, monitoring 等）は logs/<app_name>.log に日次ローテートで書き込みます。
- ロギング設定は kabusys.utils.logging_setup.setup_logging で統一的に行われます。

注意点 / 運用上の留意事項
-
- run_monitoring は監視用 DB（SQLITE_PATH）を常に使用します。監視データは環境に関係なく一元化される想定です。
- run_execution は KABUSYS_ENV=paper_trading の場合に発注を分離します（紙上検証用）。
- AI を使う機能は API レート制限・失敗を考慮したリトライ・フォールバック実装がありますが、API キーやコスト管理に注意してください。
- DB スキーマのマイグレーション（monitoring_db.init_monitoring_db）は冪等に設計されています。既存 DB にないカラム追加等の互換処理も含まれます。
- .env は絶対にリポジトリへコミットしないでください（config_setup でも注意書きあり）。

ディレクトリ構成（抜粋）
-
- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数読み込み / Settings クラス
    - config_setup.py          — .env 対話式ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — Monitoring ポーリングスクリプト
    - execution/               — Execution エンジン関連モジュール（broker_factory 等）
    - monitoring/
      - monitoring_db.py       — SQLite 永続化層
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
      - news_nlp.py
      - regime_detector.py
    - utils/
      - logging_setup.py
      - process_priority.py
    - tools/
      - paper_verification_report.py
      - __init__.py

補足（開発者向け）
-
- config.py はプロジェクトルート（.git or pyproject.toml）を基に .env 自動読込を行います。自動読込を無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を 1 に設定してください。
- logging_setup は既存ハンドラをクリアしてから再設定するため、複数回呼んでも二重出力にならない設計です。
- process_priority は Windows / POSIX の差分を吸収するユーティリティを提供します（psutil を利用）。

問題報告 / コントリビュート
-
- バグ報告や改善案は issue を作成してください。プルリクエストは歓迎しますが、.env 等の秘密情報は含めないでください。

以上がこのコードベースの主要な説明です。運用や拡張に関する具体的な質問（例: ExecutionEngine の設定を変更したい、AI スコアの出力形式を調整したい 等）があれば、目的に合わせて README の追補や使用例を追加します。