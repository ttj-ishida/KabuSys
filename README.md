KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買・研究・監視機能を持つ小規模なシステムです。  
主要コンポーネントには Execution（発注エンジン）、Monitoring（監視）、Research（ファクター計算）、
Portfolio Construction（銘柄選定・ポジションサイズ計算）、AI（ニュース NLP / レジーム判定）などがあります。

本 README ではプロジェクト概要、機能一覧、セットアップ手順、使い方、ディレクトリ構成を日本語で説明します。

1. プロジェクト概要
------------------
- 目的: 日本株の自動売買ワークフローを構成するエンジン群と運用補助ツール群を提供する。
- 構成:
  - ExecutionEngine: 発注・注文管理・リスク管理・約定整合などを担う（paper_trading モードあり）。
  - Monitoring: システム健全性・注文状況・リスクを定期監視し、必要時に Kill Switch を発動する。
  - Research: DuckDB 上の market & price データからファクター計算・特徴量解析を行う。
  - Portfolio: 候補選定、重み計算、ポジションサイズ決定、セクター制限等の純粋関数群。
  - AI: ニュース NLP（OpenAI を用いた銘柄センチメント）・市場レジーム判定。
  - Tools: ペーパートレード検証レポートなどのユーティリティスクリプト。
  - ユーティリティ: ログ設定、プロセス優先度設定、設定読み込み等。

2. 主な機能一覧
----------------
- 発注エンジン（ExecutionEngine）
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - ブローカークライアント抽象化（Mock を用意）
  - リスク管理（position limit、drawdown など）
  - order repository / reconciler / order manager を備える
- 監視（Monitoring）
  - CPU / メモリ / ディスク / プロセス存否の監視
  - 注文滞留・約定異常・リスクアラートの検出
  - Kill Switch：重大な条件で data/kill.flag を書き、Execution を停止
  - DB（SQLite）へ監視ログを永続化
- 研究（Research）
  - モメンタム・ボラティリティ・バリュー等のファクター計算（DuckDB 使用）
  - 将来リターン計算、IC（Information Coefficient）などの統計解析
- ポートフォリオ構築（Portfolio）
  - 候補選定、等配分・スコア配分、リスクベース配分
  - セクターキャップ適用、レジーム乗数
  - 株数算出（単元株丸め、aggregate cap のスケールダウン）
- AI（ニュース NLP / レジーム判定）
  - OpenAI API を用いたニュースセンチメント評価・銘柄毎スコアの DuckDB への書込み
  - ETF（1321）の MA とマクロニュースを組み合わせた日次レジーム判定
- ツール
  - .env 作成ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成スクリプト

3. セットアップ手順
-------------------
前提: Python 3.9+（ソース冒頭の __future__ 指示などから互換性の高いバージョンを想定）。  
主要依存（例）:
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config/*.yaml の内容検証を行う場合に必要）

例: 仮想環境作成と依存インストール
- python -m venv .venv
- source .venv/bin/activate  （Windows: .venv\Scripts\activate）
- pip install -U pip
- pip install duckdb psutil openai

.env の初期作成
- 対話式ウィザードで .env を作る:
  - python -m kabusys.config_setup
  - これにより .env がプロジェクトルートに生成される（.env は絶対に Git にコミットしないでください）
- 自動読み込み:
  - 実行時、KabuSys は自動でプロジェクトルートの .env を読み込みます。
  - 読み込み優先順: OS 環境変数 > .env.local > .env
  - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

必須環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN （必須）
- KABU_API_PASSWORD （必須）
- OPENAI_API_KEY （AI 機能を利用する際に必須）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（デフォルト: INFO）
- LOG_DIR（デフォルト: logs/）

設定検証
- python -m kabusys.validate_config
- 警告もエラー扱いにする場合:
  - python -m kabusys.validate_config --strict

4. 使い方（起動・主要コマンド）
------------------------------

起動スクリプト（モジュールとして実行可能）
- Monitoring を開始:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き可能（デフォルト 60 秒）。
  - 停止条件: プロジェクト data/stop_requested.flag を作成するとループが終了します（このフラグファイルは run_monitoring が監視）。
- Execution（発注エンジン）を開始:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録され、本番 DB と分離されます。
  - 起動時に data/stop_requested.flag が既に存在する場合は起動せず終了します。
  - 実行中に data/stop_requested.flag を作成すると Engine を停止します。
  - 実行中は実行 PID を data/execution.pid に書きます。

ログ
- setup_logging(app_name="...") により logs/<app_name>.log に日次ローテーションで出力します（30日分保持）。
- コンソール出力は stdout を使用します。

Kill Switch / 停止フラグ
- 監視側（KillSwitch）は条件を満たすと data/kill.flag を書き込み、Execution 側がその存在を検知して安全停止します。
- 実行停止フラグ: data/stop_requested.flag（run_monitoring/run_execution が監視する stop フラグ）
- Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動クリアします（本番では 0 推奨）

AI 関連
- ニュース NLP（kabusys.ai.news_nlp）/ レジーム判定（kabusys.ai.regime_detector）は OpenAI API を利用します。
- OPENAI_API_KEY 環境変数か、関数呼び出し時の api_key 引数でキーを与えてください。
- API 呼び出しは retry/backoff を実装しており、失敗時はフェイルセーフでスコア 0 を用いる等の挙動があります。

ツール
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または環境変数 PAPER_TRADING_SQLITE_PATH を用いて DB パスを指定できます。

5. ディレクトリ構成（主要ファイル）
-----------------------------------
以下は src/kabusys 以下の主要ファイルと目的の概観です。

- kabusys/
  - __init__.py                — パッケージ定義（__version__）
  - config.py                  — 環境変数・設定読み込み（.env 自動ロードロジック、Settings クラス）
  - config_setup.py            — .env 作成ウィザード（対話式）
  - validate_config.py         — 起動前の設定検証 CLI
  - run_monitoring.py          — Monitoring ポーリングループ起動スクリプト
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py         — ログ設定ユーティリティ（共通）
    - process_priority.py      — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py         — SQLite 監視 DB の初期化・永続化 API
    - system_monitor.py        — システム状態・データ鮮度監視
    - trade_monitor.py         — （ソース内にあり）発注ログ監視等（コードベースに存在）
    - risk_monitor.py          — ドローダウン・ポジション上限監視
    - kill_switch.py           — kill.flag 管理（書き込み・クリア）
    - monitoring_engine.py     — 各 Monitor を束ねてポーリング
    - alert_manager.py         — （ソース内にあり）通知管理
  - execution/
    - execution_engine.py      — ExecutionEngine 本体（セッション実行）
    - order_manager.py         — 注文管理
    - order_repository.py      — DB レイヤ
    - reconciler.py            — 注文整合（取り消し/補正等）
    - broker_factory.py        — ブローカークライアント生成（Mock 含む）
    - risk_manager.py          — 発注時のリスク判定
  - data/                      — （実行時に作られる想定）DB / flag / pid 等を置く場所
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading 用)
    - kabusys.duckdb (デフォルト)
    - kill.flag / stop_requested.flag / execution.pid
  - research/
    - factor_research.py       — モメンタム/ボラ/バリュー等ファクター計算（DuckDB）
    - feature_exploration.py   — IC/統計解析
  - portfolio/
    - portfolio_builder.py     — 候補選定・重み計算
    - position_sizing.py       — 発注株数計算（単元丸め・aggregate cap）
    - risk_adjustment.py       — セクターキャップ・レジーム乗数
  - ai/
    - news_nlp.py              — ニュースを LLM で評価し ai_scores に書込む
    - regime_detector.py       — 市場レジーム判定（MA + マクロニュース）
  - tools/
    - paper_verification_report.py — Paper Trading レポート生成

6. 運用上の注意 / ベストプラクティス
------------------------------------
- .env を絶対にリポジトリにコミットしないこと（config_setup にも注意書きあり）。
- 本番環境では KABUSYS_ENV=live を設定する前に validate_config で全項目を検証する。
- Kill Switch の扱い:
  - 本番では KILL_FLAG_CLEAR_ON_START=0 を推奨（自動クリアは危険）。
  - kill.flag が書かれると Execution の実行を止める仕組みがあるため、意図しないフラグ操作に注意する。
- Paper Trading:
  - KABUSYS_ENV=paper_trading にすると paper_sqlite_path を用いて DB を分離します（本番 DB と完全分離）。
- ログディレクトリのパーミッションに注意。ログ出力に失敗するとコンソールのみでの出力になります。

7. 追加情報 / トラブルシューティング
--------------------------------------
- DuckDB / SQLite のデータベースパスは env で簡単に変更可能（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）。
- PyYAML がインストールされていると validate_config で config/*.yaml のパース検証を実施します。インストールがない場合は YAML の検証はスキップされます。
- OpenAI の呼び出しはリトライ・バックオフを採用していますが、API キーやネットワークの問題で失敗する場合があります。AI 機能は失敗時にフェイルセーフ（0 相当）で継続する設計です。

8. 開発・拡張ポイント（参考）
------------------------------
- position_sizing: lot_size を銘柄毎にサポートする拡張がコメントに示唆されています。
- AI モジュールでは JSON Mode を使用し、堅牢なレスポンス検証の実装があります。テストは _call_openai_api のモックで行う想定です。
- monitoring_db はスキーママイグレーション（カラム追加）ロジックを含んでいます。

以上がこのコードベースの概要と使い方です。実行前に python -m kabusys.config_setup → python -m kabusys.validate_config を実行し、環境変数と DB パス、OpenAI キー等が正しく設定されていることを確認してください。必要があれば README に追加したいトピック（例: 各モジュール API の詳細ドキュメント、CI/テスト実行方法、Docker 化手順など）を教えてください。