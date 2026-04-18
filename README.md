README
======

概要
----
KabuSys は日本株の自動売買／リサーチ基盤を想定した Python パッケージです。  
このリポジトリには以下の主要機能が含まれます。

- 実行エンジン（ExecutionEngine）の起動スクリプト（発注・リスク管理・約定処理などの統合）
- 監視サブシステム（System / Trade / Risk の監視、Kill Switch）
- ポートフォリオ構築、ポジションサイジング、セクター制限などの純粋関数群
- リサーチ用ファクター／特徴量計算（DuckDB を用いたオフライン計算）
- AI を用いたニュースセンチメント評価・市場レジーム判定（OpenAI 経由）
- 付帯ツール（.env 作成ウィザード、設定検証、ペーパートレード検証レポート等）

特徴
----
主な機能一覧（抜粋）:

- 実行（run_execution.py）
  - 本番 / ペーパートレード（KABUSYS_ENV=paper_trading）を区別
  - Broker クライアントを生成して ExecutionEngine を起動
  - 停止フラグ（data/stop_requested.flag）により安全停止
  - paper_trading 時は data/paper_trading.db に分離して記録

- 監視（run_monitoring.py / monitoring パッケージ）
  - SystemMonitor / TradeMonitor / RiskMonitor を定期実行
  - 監視ログを SQLite（data/monitoring.db: monitoring_db）に永続化
  - KillSwitch による停止シグナル生成（data/kill.flag）
  - MONITOR_POLL_INTERVAL でポーリング間隔を制御可能

- ポートフォリオ（portfolio パッケージ）
  - 候補選定、重み付け（等金額／スコア重み）、ポジションサイズ計算
  - セクターキャップ、レジーム乗数による調整

- リサーチ（research パッケージ）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - 将来リターン・IC 計算、統計サマリの提供

- AI（ai パッケージ）
  - ニュースセンチメントの LLM スコアリング（OpenAI）
  - マクロニュースを用いた市場レジーム判定（regime_detector）
  - LLM 呼び出しはリトライやレスポンス検証を備えた実装

- ユーティリティ
  - .env 対話式ウィザード（config_setup.py）
  - 起動前設定検証 CLI（validate_config.py）
  - ロギング設定ユーティリティ（utils/logging_setup.py）
  - プロセス優先度・CPU affinity ユーティリティ（utils/process_priority.py）
  - ペーパートレード検証レポート生成ツール（tools/paper_verification_report.py）

セットアップ
----------
1. 必須パッケージをインストール（例）
   - Python 3.9+ を想定
   - 主な依存: duckdb, psutil, openai, (PyYAML は設定検証で任意)
   - pip 例:
     pip install duckdb psutil openai

   ※ 実際の環境では requirements.txt / Poetry 等があればそちらを使用してください。

2. プロジェクトルートに .env を作成
   - 対話式ウィザード:
     python -m kabusys.config_setup
   - ウィザードで生成した .env は絶対に Git にコミットしないでください（シークレット含む）。

3. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合:
     python -m kabusys.validate_config --strict

4. データディレクトリ作成（.env に指定したパスに応じて）
   - デフォルトでは data/ に SQLite/DuckDB/フラグファイルを作成します。
   - ログは logs/ に出力（デフォルト）。環境変数 LOG_DIR で変更可能。

主要な環境変数（抜粋）
---------------------
必須（実運用時）:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

運用系:
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR — ログ保存ディレクトリ

DB / ファイルパス:
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 DB（paper_trading 用）
- PID_FILE_PATH — Execution 用 PID ファイルのパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）

AI:
- OPENAI_API_KEY — OpenAI API キー（ai.score_news / regime_detector で使用）

監視 / 動作制御:
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト: 60）※ run_monitoring で使用
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする（"1" で有効。production では "0" 推奨）
- PAPER_FILL_MODE — ペーパートレード時の約定挙動（instant/partial/never/reject）

使い方
------
基本的なコマンド例:

- .env を作る（対話式）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 監視プロセスを起動
  python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き（秒）
  - 監視は .env の KABUSYS_ENV にかかわらず sqlite_path（本番パス）を使用して永続化します
  - 停止: プロジェクトルート/data/stop_requested.flag を作成するとループが終了します

- 実行エンジン（ExecutionEngine）を起動
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します
  - 停止: data/stop_requested.flag を作成すると実行エンジンに停止信号を送れます

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite パスを指定可能（優先度: --db > 環境変数 > デフォルト data/paper_trading.db）

- ライブラリ関数（スクリプトから呼ぶ）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - research や portfolio の関数群は duckdb 接続やパラメータを渡して利用可能

停止フラグ / Kill Switch
----------------------
- Execution の安全停止: data/stop_requested.flag を作成すると run_execution が検知してエンジンを停止します。
- Kill Switch（自動停止判定）: モニタリング側で条件（ドローダウン超過など）が満たされた場合 data/kill.flag に理由を書き込み、運用側でこれを検知して手動確認後にクリアできます。
- Kill flag の自動クリアは .env の KILL_FLAG_CLEAR_ON_START を "1" にすることで（本番では推奨しません）。

ログ
----
- ログはデフォルトで logs/ にアプリ別ファイル（例: logs/execution.log, logs/monitoring.log）として日次ローテーションで保存されます。
- ログ出力は stdout とファイルの両方に行われます（utils/logging_setup.py を参照）。
- LOG_LEVEL 環境変数で詳細度を制御します。

ディレクトリ構成（主要ファイル）
------------------------------
リポジトリの主要構成（src/kabusys 配下を抜粋）:

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / 設定読み込みロジック
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 起動前チェック CLI
  - run_execution.py        — 実行エンジン起動スクリプト
  - run_monitoring.py       — 監視ループ起動スクリプト

  - ai/
    - news_nlp.py           — ニュースを LLM でスコア化するロジック
    - regime_detector.py    — 市場レジーム判定（LLM + MA）
    - __init__.py

  - monitoring/
    - monitoring_db.py      — SQLite スキーマと永続化層
    - system_monitor.py     — CPU/メモリ/データ鮮度監視
    - trade_monitor.py      — （略）※トレード監視ロジック（ファイル内未表示部分）
    - risk_monitor.py       — ドローダウン・ポジション上限監視
    - kill_switch.py        — kill.flag 書き込みユーティリティ
    - monitoring_engine.py  — Monitor を束ねるエンジン
    - alert_manager.py      — （略：アラート送信ロジック）

  - execution/
    - execution_engine.py   — （実行エンジン本体）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py

  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py

  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py

  - monitoring/ (上記)
  - tools/
    - paper_verification_report.py
    - __init__.py

  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py

補足 / 運用メモ
--------------
- DuckDB / SQLite のパスは .env で設定してください（デフォルトは data/ 以下）。
- ペーパートレードと本番は DB を物理的に分離する設計です（PAPER_TRADING_SQLITE_PATH）。
- LLM（OpenAI）を使う機能は API キーやレートの設定に注意して運用してください。API 呼び出しはリトライやフォールバック（失敗時の安全値）を入れた実装になっていますが、実行時のコスト管理は必要です。
- 本番稼働時は KABUSYS_ENV=live を設定し、validate_config の警告を注意深く確認してください。

ライセンス / バージョン
---------------------
- パッケージバージョン: src/kabusys/__init__.py の __version__ を参照（例: 0.1.0）
- ライセンス情報はリポジトリの LICENSE ファイル等をご確認ください（本リポジトリ例では省略）。

問い合わせ / 開発
-----------------
- 開発者向け: .env の自動ロードはデフォルトで有効です。テスト時などに無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- より詳細な実装や各モジュールの使い方はソース内の docstring / コメントを参照してください。