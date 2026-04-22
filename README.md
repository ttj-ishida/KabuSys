KabuSys — 日本株自動売買システム（README）
=================================

概要
----
KabuSys は日本株向けの自動売買・研究・監視を想定した Python ライブラリ兼実行スクリプト群です。本リポジトリは以下の責務を持ちます。

- 注文実行エンジン（ExecutionEngine）の起動スクリプト
- システム／注文／リスク監視（Monitoring）の起動スクリプトと永続化層
- ペーパートレード用の検証ツール（レポート生成）
- ポートフォリオ構築（候補選定、重み算出、株数決定、セクター制限）
- リサーチ（ファクター計算、特徴量探索）
- AI を使ったニュース NLP / レジーム判定（OpenAI 使用）
- 設定ウィザード・検証ツール・ユーティリティ

特徴
----
- 明確に分離された「本番 / ペーパートレード」モード（KABUSYS_ENV）
- SQLite（監視・トレース）と DuckDB（分析）を併用するデータ構成
- OpenAI を用いたニュースセンチメント / 市場レジームスコア生成
- 監視エンジンによる Kill Switch（フラグファイル）連携とアラート発火可能設計
- ログをコンソール + 日次ローテートファイルに出力する統一的なログ設定ユーティリティ
- ポートフォリオ構築・ポジションサイズ計算の純粋関数群（テスト容易）

セットアップ手順
----------------
1. リポジトリをチェックアウト／クローンします。

2. Python 環境を用意（推奨: venv / pyenv）。

  例:
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip

3. 必要なパッケージをインストールします（最低限の依存を例示）。

   pip install duckdb psutil openai

   任意（YAML 検証など）:
   pip install pyyaml

   （プロジェクトの requirements.txt があればそれを使用してください）

4. ディレクトリ作成（初回のみ）:

   mkdir -p data logs

5. 環境変数設定
   - .env をプロジェクトルートに作成するのが簡単です。対話式ウィザードを利用できます（下記参照）。
   - 自動で .env を読み込む仕組みがあり、CWD に依存せずプロジェクトルートを探索して読み込みます。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI 機能利用時に必要）
- LOG_LEVEL（例: INFO、DEBUG）
- KILL_FLAG_CLEAR_ON_START（0/1、起動時に kill.flag を自動で消すか）

使い方
------

1. .env を対話式で作る
   python -m kabusys.config_setup

   ウィザードで入力後、.env ファイルを生成します。

2. 設定検証
   python -m kabusys.validate_config
   オプション: --strict をつけると警告も失敗扱いで exit 1 を返します。

3. ExecutionEngine（注文エンジン）を起動
   python -m kabusys.run_execution

   特記事項:
   - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録します（本番 DB と完全分離）。
   - 起動時、プロセス優先度を High に設定します（可能な場合）。
   - 起動前に data/stop_requested.flag が存在すると起動をスキップします。
   - 実行中に data/stop_requested.flag を置くとエンジンに停止指示を出します。
   - 実行プロセスの PID は data/execution.pid に書き込まれます（Engine 実装に依存）。

4. Monitoring（監視）を起動
   python -m kabusys.run_monitoring

   オプション／環境変数:
   - MONITOR_POLL_INTERVAL: ポーリング間隔（秒）。デフォルト 60 秒。1 未満・不正値はデフォルトにフォールバック。
   - 監視は実行環境に関係なく production の sqlite_path を使用して監視ログを記録します。
   - 停止はプロジェクトルート/data/stop_requested.flag を作成することで行います（存在検知でループ終了）。

5. Paper Trading 検証レポート生成
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   オプション:
   --from / --to を YYYY-MM-DD 形式で指定。--db で DB パスを上書き可能（環境変数 PAPER_TRADING_SQLITE_PATH でも可）。

6. AI 機能
   - OpenAI API を使う機能（ニュース NLP / レジーム判定）は OPENAI_API_KEY を設定してください。
   - 例: kabusys.ai.score_news(conn, target_date, api_key=...)
   - エラー時はフォールバック動作（部分スコアリング・スコア 0.0 等）を行う設計です。

7. ライブラリとしての利用（例）
   - ポートフォリオ構築:
     from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes
   - リサーチ:
     from kabusys.research import calc_momentum, calc_volatility, calc_value
   - AI:
     from kabusys.ai import score_news

運用上の注意
-------------
- KABUSYS_ENV=live の場合は本番向けの設定や API トークンの管理に十分注意してください。validate_config は live 時に追加警告を出します（LINE の通知設定等）。
- .env は絶対に Git にコミットしないでください（config_setup のヘッダにも同様の注意あり）。
- monitoring の Kill Switch は data/kill.flag によって ExecutionEngine の停止を誘発します。KILL_FLAG_CLEAR_ON_START=1 を本番で設定すると危険なので注意してください。
- ログは logs/<app_name>.log に日次ローテートで保存されます。ログディレクトリ作成に失敗した場合はコンソールのみで動作します。

ディレクトリ構成（主要ファイル）
----------------------------
（src/kabusys 以下を想定）

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定読み込みロジック（.env 自動読み込み含む）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring の簡易起動スクリプト
  - monitoring/
    - monitoring_db.py        — SQLite 監視 DB スキーマ & ラッパー
    - system_monitor.py       — システム／データ鮮度チェック
    - trade_monitor.py        — （注文監視ロジック）※（実装ファイルあり）
    - risk_monitor.py         — ドローダウン・ポジション数監視
    - kill_switch.py          — kill.flag の書き込み・評価
    - monitoring_engine.py    — 複数 Monitor を束ねるエンジン
    - alert_manager.py        — 通知（LINE 等）管理（※実装ファイルあり）
  - execution/                — ExecutionEngine・OrderManager 等（本体実装）
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 株数算出・配分・aggregate cap
    - risk_adjustment.py      — セクター上限・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py      — Momentum/Value/Volatility 等のファクター計算
    - feature_exploration.py  — 将来リターン・IC/統計関数
    - __init__.py
  - ai/
    - news_nlp.py             — ニュースを OpenAI でスコア化して ai_scores に書き込む
    - regime_detector.py      — マクロ + ma200 でレジーム判定
    - __init__.py
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - utils/
    - logging_setup.py        — 共通ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定
    - __init__.py

テスト・開発
-------------
- 各モジュールは依存注入（DB 接続・ DuckDB 接続・API クライアント等）で設計されているため、ユニットテストではモックが容易に利用できます。
- OpenAI 呼び出しや外部 API を行う関数は内部で別関数へ委譲されており、unittest.mock などで差し替え可能です（コード内にその旨のコメントあり）。

トラブルシューティング
-----------------------
- .env を読み込んでほしくないテスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- MONITOR_POLL_INTERVAL に 0 や負の値を設定すると無効値としてデフォルト 60 秒が使われます（警告ログ）。
- OpenAI API のエラーはリトライやフェイルセーフが組み込まれていますが、API キー・レート制限・ネットワーク状態を確認してください。
- DuckDB / SQLite のパスの親ディレクトリが存在しない場合は validate_config で警告が出ます。必要なら先にディレクトリを作成してください。

付録: よく使うコマンド例
-----------------------
- .env ウィザード:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 実行エンジン起動（バックグラウンド等は OS 側で管理）:
  python -m kabusys.run_execution

- 監視プロセス起動:
  python -m kabusys.run_monitoring
  環境変数で interval を変更: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- ペーパートレード検証レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

最後に
-----
この README はリポジトリ内のモジュール実装（docstring やコード）から要点を抜粋してまとめたものです。より詳細な挙動や設定は各モジュールのソースコードの docstring を参照してください。もし README の補足や特定コマンドの使い方を追記してほしい箇所があれば教えてください。