KabuSys — 日本株自動売買システム（README）
=================================

概要
----
KabuSys は日本株向けの自動売買・リサーチ・モニタリング用ライブラリ兼実行スクリプト群です。本リポジトリは以下の機能群を提供します。

- 注文実行エンジン（ExecutionEngine）とそれを起動する run_execution.py
- システム監視（Monitoring）と監視ループ起動スクリプト run_monitoring.py
- リスク監視・Kill Switch（条件を満たすと停止フラグを書く）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ算出）
- 研究用モジュール（ファクター計算・特徴量探索）
- AI モジュール（OpenAI を用いたニュースセンチメント / レジーム判定）
- 運用支援ツール（.env ウィザード、設定検証、ペーパートレード検証レポート等）

主要な設計方針：
- 本番とペーパートレードは DB を分離（PAPER_TRADING_SQLITE_PATH）
- 可能な限りフェイルセーフ（API 失敗やデータ欠損時に例外で止めない）
- ルックアヘッドバイアス防止（date.today() を直接参照しない設計）
- ログは統一的に設定（kabusys.utils.logging_setup）

主な機能一覧
--------------
- run_execution.py: ExecutionEngine を起動（KABUSYS_ENV に応じて MockBroker）
- run_monitoring.py: SystemMonitor を定期実行し監視ログを収集
- monitoring: system_monitor / trade_monitor / risk_monitor / kill_switch / monitoring_engine
- monitoring_db: SQLite に監視・ログ用テーブルを作成・永続化
- portfolio: 候補選定、重み計算、ポジションサイズ決定、セクターキャップ、レジーム乗数
- research: ファクター計算（momentum/value/volatility）、将来リターン、IC、統計サマリ
- ai: news_nlp（ニュースを LLM でスコア化）、regime_detector（市場レジーム判定）
- utils: logging_setup（統一ログ設定）、process_priority（優先度・CPU affinity 設定）
- config_setup.py: 対話式 .env 作成ウィザード
- validate_config.py: 起動前設定検証 CLI
- tools/paper_verification_report.py: ペーパートレード結果の検証レポート生成

前提・依存
-----------
- Python >= 3.10（型ヒント等に | 演算子を使用）
- 推奨ライブラリ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で任意）
- （実行環境で必要に応じて）kabuステーション API 等の設定

セットアップ手順
----------------

1. リポジトリをクローン / ワークツリーに入る

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   （requirements.txt がある場合はそれに従ってください）

4. .env の準備（2通り）
   - 対話式ウィザード（推奨）
     - python -m kabusys.config_setup
     - ウィザードは .env を生成します（.env は絶対に Git にコミットしないでください）
   - 手動で作成
     - .env.example を参考に必要な環境変数を設定

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告をエラー扱いにする場合は --strict を付与

6. OpenAI を使う機能を利用する場合
   - 環境変数 OPENAI_API_KEY を設定（または関数引数で渡す）
   - AI 機能（news_nlp / regime_detector）は API キーが必須

主要な環境変数（主なもの）
-------------------------
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 SQLite DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（PAPER_TRADING 用）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で使用）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、run_monitoring 用、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1、本番は 0 推奨）

使い方（CLI / スクリプト）
-------------------------

- .env を作成・更新（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（警告を失敗扱い）: python -m kabusys.validate_config --strict

- 監視サービスを起動
  - python -m kabusys.run_monitoring
  - 説明:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60）
    - run_monitoring は環境にかかわらず本番 sqlite_path を使用して監視 DB を初期化します
    - 停止: プロジェクトルート/data/stop_requested.flag を作成するとループを終了します

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - 説明:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録（本番 DB と完全分離）
    - 起動時に data/stop_requested.flag が既にある場合は起動をスキップ
    - 実行中に stop flag を検知すると engine.stop() を呼んで停止します
    - PID ファイル: data/execution.pid が使われます

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH

- AI 関連（プログラムから呼ぶ）
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key=None)  — OpenAI API キーは api_key か OPENAI_API_KEY 環境変数で指定

運用上のポイント・運用ファイル
-----------------------------
- ログ:
  - kabusys.utils.logging_setup.setup_logging により、stdout と logs/<app_name>.log（日次ローテーション、30日保持）へ出力します。
  - ログディレクトリは LOG_DIR 環境変数またはデフォルト logs/ を使います。

- Kill Switch / 停止フラグ:
  - KillSwitch は設定の閾値（ドローダウン超過、ポジション上限等）を満たすと data/kill.flag を書き込んで ExecutionEngine に停止シグナルを送ります。
  - run_monitoring/run_execution は data/stop_requested.flag を監視して停止します（運用側がフラグファイルを作って停止を要求するケース）。

- DB 初期化:
  - run_monitoring/run_execution は起動時に monitoring DB（SQLite）と DuckDB を接続し、必要テーブルを init_monitoring_db で作成します（冪等）。
  - ペーパートレードは PAPER_TRADING_SQLITE_PATH を用いて本番 DB と完全分離します。

ディレクトリ構成（主要ファイル）
------------------------------
以下はリポジトリ内の主要なモジュール／ファイル構造（抜粋）です:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数管理（.env の自動ロード含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度・CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — SQLite 監視テーブル定義・アクセス
    - system_monitor.py
    - trade_monitor.py       （実装あり）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       （アラート送信用）
  - execution/               — ExecutionEngine, OrderManager, BrokerFactory 等（発注系）
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
  - tools/
    - paper_verification_report.py

（上記は主なファイルのみ抜粋。詳細はソースを参照してください。）

よくある質問 / 注意事項
----------------------
- .env は絶対に Git にコミットしないでください（API キーやパスワードが含まれます）。
- KABUSYS_ENV=live の場合は本番動作になります。LINE 通知などの設定を必ず確認してください。
- run_monitoring は MONITOR_POLL_INTERVAL によりポーリング間隔を変更できますが、0 または負の値は無効（デフォルト 60 秒にフォールバックします）。
- OpenAI を利用する機能はネットワークや API 制限の影響を受けます。リトライやフォールバック処理は実装されていますが、運用時は API 利用量に注意してください。
- Python バージョンは 3.10 以降を推奨します（型ヒントの構文等）。

ライセンス・バージョン
----------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（現状: 0.1.0）。
- ライセンス情報がプロジェクトに含まれている場合はそれに従ってください。

サンプル運用フロー（例）
-----------------------
1. 仮想環境を作成・依存をインストール
2. python -m kabusys.config_setup で .env を生成
3. python -m kabusys.validate_config で検証
4. 監視をデーモンで起動: python -m kabusys.run_monitoring
5. 実行エンジンを起動: python -m kabusys.run_execution
6. 必要に応じて data/kill.flag や data/stop_requested.flag を使用して停止・保護

---
README の内容はソースコード（src/kabusys 以下）の現状に基づいて作成しています。実運用前に設定（特に API キーやパスワード、DB パス、KABUSYS_ENV）を十分に確認してください。質問や追記希望があれば教えてください。