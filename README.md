README
======

概要
----
KabuSys は日本株の自動売買フレームワークです。本リポジトリは以下の主要機能を備えたモジュール群を含みます。

- 発注エンジン（ExecutionEngine）とブローカークライアントの抽象化（実残口座 / ペーパートレード対応）
- 監視サブシステム（System / Trade / Risk モニタ）と Kill Switch
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ算出）モジュール
- リサーチ（ファクター計算・特徴量解析）モジュール（DuckDB を使用）
- AI 支援モジュール（ニュース NLP によるセンチメント、レジーム検出） — OpenAI API 利用
- 各種ユーティリティ（設定ウィザード、設定検証、ログ設定、プロセス優先度設定、検証レポート生成）

主な機能
--------
- 実運用/検証・ペーパートレードの切り替え対応（KABUSYS_ENV）
- SQLite / DuckDB によるデータ永続化（監視ログ・発注履歴・分析データ）
- 監視ループ（ポーリング）とアラート / Kill Switch による安全停止
- ポートフォリオ構成の純粋関数実装（単体テスト容易）
- ニュースを LLM（OpenAI）でスコアリングし、レポート/レジーム判定に活用
- 設定ウィザード（.env 生成）と起動前検証 CLI

前提条件
--------
- Python 3.10 以降（型ヒントで | 演算子を使用）
- 以下の Python パッケージ（主要なもの）
  - duckdb
  - psutil
  - openai (AI 機能を利用する場合)
  - PyYAML（validate_config の YAML 検証機能を有効にする場合）
- SQLite（標準ライブラリ）およびファイルシステムアクセス

簡易インストール例
-----------------
1. リポジトリをクローンする
   - git clone <repo_url>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML

セットアップ手順
--------------
1. .env の作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - ウィザードは J-Quants / kabuAPI / DB パス /ログレベル 等の初期値入力を案内します。
   - 生成される .env はプロジェクトルートに書き込まれます（Git にコミットしないでください）。

2. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict オプションを付けると警告も失敗扱い（exit 1）になります。

3. データディレクトリ等の作成
   - デフォルトでは data/ および logs/ を使用します。必要に応じて作成済みであることを確認してください（logging_setup が自動的に作成します）。

主な環境変数（抜粋）
-------------------
- KABUSYS_ENV: 実行環境（development, paper_trading, live）デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI を使う機能で必要（ai.news_nlp / ai.regime_detector）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視）DB パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）（デフォルト: INFO）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、本番は 0 推奨）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60） — run_monitoring で参照

使い方（起動 / CLI）
-------------------
- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config [--strict]

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、データは data/paper_trading.db に格納されます。
  - 起動時に data/stop_requested.flag が存在すると起動を行いません。
  - 実行中は data/execution.pid にプロセスIDを書き込みます。

- 監視ループ起動（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 監視は .env の KABUSYS_ENV にかかわらず本番用の sqlite_path を使用します（監視ログは共通 DB に記録）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH 環境変数で指定可）

- AI / リサーチ関数の利用（プログラムから呼び出し）
  - 例: ニューススコアリング
    from kabusys.ai import score_news
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date, api_key="...")

注意点・運用メモ
--------------
- .env の自動ロード
  - プロジェクトルート（.git または pyproject.toml を探索）を基準に .env/.env.local を自動読み込みします。無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Kill Switch
  - kabusys.monitoring.kill_switch.KillSwitch がリスク条件を満たした場合、data/kill.flag を書き込み ExecutionEngine の停止を促します。KILL_FLAG_CLEAR_ON_START=1 にすると起動時に自動クリアされますが、本番では 0 推奨です。
- 監視 DB と発注 DB の分離
  - 実行エンジンは環境に応じて paper_trading 用の別 SQLite を使えます（settings.is_paper 判定）。
  - 監視コンポーネントは常に本番 sqlite_path を使用します（監視ログの一貫性確保のため）。
- ログ
  - デフォルトで logs/<app_name>.log（例: logs/execution.log, logs/monitoring.log）に日次ローテートで出力されます。ログディレクトリが作れない場合はコンソール出力のみになります。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py                     — パッケージ定義（version 等）
- config.py                       — Settings クラス（環境変数読み込み・.env 自動ロード）
- config_setup.py                 — .env 作成ウィザード（対話式）
- validate_config.py              — 起動前チェック CLI
- run_execution.py                — ExecutionEngine 起動スクリプト
- run_monitoring.py               — SystemMonitor ポーリング起動スクリプト

packages / サブモジュール
- ai/
  - news_nlp.py                   — ニュースの LLM センチメント評価（ai_scores 書込み）
  - regime_detector.py            — マーケットレジーム判定（MA + マクロセンチメント）
- monitoring/
  - monitoring_db.py              — SQLite 上の監視テーブル定義・ラッパ
  - system_monitor.py             — CPU/メモリ/ディスク/データ鮮度監視
  - trade_monitor.py              — （発注・約定）監視（滞留注文等）
  - risk_monitor.py               — ドローダウン・ポジション上限監視
  - kill_switch.py                — フラグファイル書込による停止制御
  - monitoring_engine.py          — 複数モニタの統合実行（テスト用 run_once / 本番 run）
- execution/
  - execution_engine.py           — ExecutionEngine（スレッド起動・セッション管理）
  - broker_factory.py             — BrokerClient の生成（本番 / モック分岐）
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py など
- portfolio/
  - portfolio_builder.py          — 候補選定・重み計算
  - position_sizing.py            — 株数算出・資金制約調整
  - risk_adjustment.py            — セクターキャップ・レジーム乗数
- research/
  - factor_research.py            — Momentum/Value/Volatility 等のファクター計算（DuckDB）
  - feature_exploration.py        — forward returns / IC / summary 統計
- data/
  - pipeline.py (参照されるユーティリティ; prices_daily などの取得)
- tools/
  - paper_verification_report.py  — Paper Trading の検証レポート生成スクリプト
- utils/
  - logging_setup.py              — 統一的なログ設定ユーティリティ
  - process_priority.py           — プロセス優先度 / CPU affinity 設定ユーティリティ

例: 最小 .env（参考）
--------------------
# .env の一例（実運用では機密値を必ず secret として管理）
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
# OpenAI を使う場合
OPENAI_API_KEY=sk-...

開発・テストのヒント
--------------------
- 各モジュールは純粋関数（副作用を持たない）で実装された部分が多く、ユニットテストが書きやすく設計されています（portfolio, research 等）。
- OpenAI 呼び出し部分は _call_openai_api をテスト時にモック差し替えしやすい設計です。
- validate_config の YAML チェックは PyYAML がない場合はスキップされます。

ライセンス・貢献
----------------
本 README はコードベースから抽出した情報に基づく簡易ドキュメントです。詳細な設計書（PortfolioConstruction.md 等）がプロジェクト内に存在する想定です。問題の報告や提案は Issue / PR を通じて行ってください。

以上。必要であれば、各コマンドの出力例や .env の詳しい項目説明、Docker 化手順などの追加ドキュメントを作成します。どの情報を優先的に追記しますか？