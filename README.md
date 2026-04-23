KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株向けの自動売買（発注）／リサーチ／モニタリングを行うための Python コードベースです。
主な目的は以下です:

- 日次のファクタ計算・リサーチ（DuckDB を利用した時系列分析）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター上限適用）
- ExecutionEngine による注文発行（本番 / ペーパートレード分離）
- 監視（System / Trade / Risk）と Kill Switch による安全停止
- ニュースを用いた AI（OpenAI）ベースのスコアリングとレジーム判定
- ペーパートレード検証レポート生成ツール

特徴（機能一覧）
----------------
- 設定管理
  - .env 自動ロード（.env / .env.local）と Settings クラスによる一元管理
  - 対話式ウィザードで .env 作成（kabusys.config_setup）
  - 起動前検証 CLI（kabusys.validate_config）で必須環境・YAML 等をチェック

- 実行 / 発注
  - ExecutionEngine（別モジュール）を起動する run_execution スクリプト
  - KABUSYS_ENV=paper_trading で MockBroker を使用し paper_trading DB に完全分離
  - プロセス優先度設定・PID 管理・停止フラグ監視

- 監視
  - SystemMonitor / TradeMonitor / RiskMonitor を統合する MonitoringEngine
  - SQLite を用いた監視ログ永続化（monitoring_db）
  - Kill Switch（data/kill.flag）による ExecutionEngine の安全停止
  - run_monitoring スクリプトによる常駐ポーリング（MONITOR_POLL_INTERVAL で調整可能）

- ポートフォリオ構築
  - 候補選定（スコア順）・等配分／スコア加重配分
  - リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（リスクベース／等分配／スコア基準）、単元株で丸め、集計キャップ適用

- リサーチ
  - DuckDB を利用したファクター（Momentum / Volatility / Value）計算
  - 将来リターン・IC 計算・特徴量サマリ等のユーティリティ

- AI（OpenAI）
  - ニュース記事を LLM でセンチメント付与して ai_scores テーブルへ保存（news_nlp）
  - マクロニュース + ETF ma200 乖離で市場レジーム判定（regime_detector）
  - OpenAI API のリトライ、レスポンス検証、スコアクリップ等の安全策を実装

- ツール
  - ペーパートレード検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

セットアップ手順
----------------
1. リポジトリをクローン／チェックアウト

2. Python 環境準備
   - 推奨: Python 3.10+
   - 仮想環境作成・有効化（venv / conda 等）

3. 必要パッケージをインストール
   - 主要依存例:
     - duckdb
     - psutil
     - openai
     - (任意) PyYAML（config 検証を有効にするため）
   - 例:
     - pip install duckdb psutil openai pyyaml

4. 環境変数設定 (.env)
   - 対話式ウィザードを使用:
     - python -m kabusys.config_setup
   - あるいは .env を手動作成（.env.example を参照）
   - 主な環境変数（代表）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（モニタリング DB。デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB。デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE（instant / partial / never / reject。デフォルト: instant）
     - LOG_LEVEL（DEBUG/INFO/...。デフォルト: INFO）
     - KILL_FLAG_CLEAR_ON_START（0/1。デフォルト: 0）
     - OPENAI_API_KEY（AI 機能を使う場合に必須）

5. 設定検証（起動前推奨）
   - python -m kabusys.validate_config
   - 警告をエラー扱いにする場合: python -m kabusys.validate_config --strict

使い方（起動・ツール）
--------------------
- 監視プロセスを起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可（デフォルト 60 秒）
  - 監視は常に本番用 sqlite_path（Settings.sqlite_path）を使用

- 実行（Execution）エンジンを起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に完全分離して記録

- .env の作成・編集（ウィザード）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告があると exit code 1

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH の代替）

- AI 機能
  - OPENAI_API_KEY を設定しておくことで:
    - kabusys.ai.score_news（ニュースの銘柄別センチメントを ai_scores に保存）
    - kabusys.ai.regime_detector.score_regime（市場レジーム判定・保存）
  - これらはモジュール関数として呼び出せます。CLI 向けのスクリプトは別途用意してください。

停止・フラグ管理
-----------------
- execution の停止はフラグファイルによる制御:
  - data/stop_requested.flag（run_execution/run_monitoring が参照）
  - data/kill.flag（KillSwitch が書き込み、ExecutionEngine に停止を促す）
- PID ファイル:
  - data/execution.pid（ExecutionEngine 用、Settings.pid_file_path で変更可）
- KILL_FLAG_CLEAR_ON_START が 1 の場合、起動時に kill.flag を自動クリア（本番では 0 推奨）

ログ
----
- ログはルートロガーへ StreamHandler（stdout）と日次ローテーションファイルハンドラを設定
- デフォルトログディレクトリ: logs/
- ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で変更

注意点 / 補足
--------------
- Paper trading モードは本番 DB と完全分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- DuckDB は分析・時系列処理用のローカル DB として利用します（DUCKDB_PATH）。
- AI（OpenAI）呼び出しは外部 API 依存です。API キー、コスト、レート制限に注意してください。
- 一部の機能は PyYAML や openai SDK に依存します。validate_config の YAML 検証は PyYAML がないとスキップされます。
- process_priority（高優先度）や CPU affinity は psutil を通じて設定します。権限により失敗する場合がありますが、安全に警告でスキップされます。

ディレクトリ構成
----------------
（リポジトリルート / src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・Settings 管理（.env 自動ロードを含む）
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 起動前検証 CLI
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py       — ログ初期化ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — SQLite テーブル作成・永続化 API
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — （取引監視ロジック: 発注・約定の整合性等）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — Kill Switch 実装（flag ファイル）
    - alert_manager.py       — （アラート送信管理：LINE 等）
  - execution/               — ExecutionEngine / BrokerFactory / Order 管理等（発注ロジック）
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — ポジションサイズ計算（丸め・キャップ等）
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — Momentum / Volatility / Value ファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py            — ニュースセンチメント付与（OpenAI）
    - regime_detector.py     — レジーム判定（MA200 + macro sentiment）
  - monitoring scripts / tools
    - tools/paper_verification_report.py — ペーパートレード検証レポート生成

例: 起動シーケンス（開発環境）
--------------------------------
1. .env を作成（python -m kabusys.config_setup）
2. 設定検証（python -m kabusys.validate_config）
3. 監視プロセス起動（別ターミナル）
   - python -m kabusys.run_monitoring
4. Execution 起動（別プロセス）
   - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
5. ペーパー検証レポートを生成
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス / バージョン
-----------------------
- package version: __version__ = "0.1.0"（src/kabusys/__init__.py）
- ライセンス情報はリポジトリの LICENSE ファイルを参照してください（存在する場合）。

お問い合わせ / 追加情報
---------------------
- コードの各モジュールはドキュメント文字列（docstring）とコメントで設計方針・注意点を記載しています。実装の詳細や拡張は各ファイルを参照してください。
- OpenAI 関連のテストや CI を行う際は API 呼び出しをモックすることを推奨します（モジュール内に _call_openai_api の差し替えを想定する記述があります）。

以上。README の補足や特定ファイルの詳細説明が必要であれば教えてください。