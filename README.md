KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株の自動売買 / 研究 / 監視を行うための小規模なフレームワークです。本リポジトリは以下の機能群を含みます。

- 注文実行エンジン（ExecutionEngine）と発注管理（paper/live 切替対応）
- 監視（System / Trade / Risk）と Kill Switch（フラグファイルによる緊急停止）
- ポートフォリオ構築（候補選定・重み計算・株数算出・セクター制約など）
- リサーチ用ファクター計算・特徴量解析（DuckDB ベース）
- AI 支援モジュール（ニュースセンチメントの LLM 評価、レジーム判定）
- 環境設定ウィザード・設定検証ツール・ペーパートレード検証レポート

主な設計方針
- 本番・ペーパートレードを明確に分離（KABUSYS_ENV による切替）
- DuckDB を分析用 DB、SQLite を監視 / 注文ログ用 DB に使用
- .env による設定管理（自動読み込み・ウィザードあり）
- OpenAI 連携は明示的な API キー指定が必要（環境変数 OPENAI_API_KEY）

機能一覧
--------
- config_setup: 対話式ウィザードで .env ファイルを作成 / 更新
- validate_config: .env や config/*.yaml の設定チェック（--strict オプションあり）
- run_execution: ExecutionEngine を起動（KABUSYS_ENV に応じて実際発注 or Mock）
- run_monitoring: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定可能）
- monitoring: system／trade／risk の監視、ダッシュボード更新、kill.flag による停止判定
- portfolio: 候補選定、重み計算、リスク調整、ポジションサイズ計算
- research: DuckDB 上でファクター（Momentum/Value/Volatility 等）や将来リターン、IC 等を計算
- ai: news_nlp（ニュースセンチメントを OpenAI で評価して ai_scores へ書込）、regime_detector（市場レジーム判定）
- tools.paper_verification_report: ペーパートレードの検証レポート生成

前提 / 必要ソフトウェア
--------------------
- Python 3.9+
- 必要な Python パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML の検証を行う場合）
- SQLite（標準ライブラリで利用）
- ネットワーク接続（OpenAI / 外部 API を使う場合）

（実際の環境では requirements.txt を用意して pip install -r で管理することを推奨します）

セットアップ手順
----------------

1. リポジトリをクローン / 展開
   - プロジェクトルート（pyproject.toml/.git がある場所）を確認してください。

2. Python 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール
   - 例:
     pip install duckdb psutil openai PyYAML

4. .env の作成
   - 対話式ウィザードを使う:
     python -m kabusys.config_setup
   - または手動で .env を作成（.env.example を参照）
   - 重要: .env をリポジトリにコミットしないこと

5. 設定検証
   - python -m kabusys.validate_config
   - 本番前は --strict を付けて警告を FAIL 扱いにできます:
     python -m kabusys.validate_config --strict

6. DB 初期化
   - 実行スクリプト（run_execution / run_monitoring）が初回起動時に必要なテーブルを作成します。
   - DuckDB / SQLite のファイルパスは .env の DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH 等で指定できます。

環境変数（主なもの）
-------------------
主な環境変数（必須 / 主要）:
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: execution モード（development / paper_trading / live。デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 時）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant|partial|never|reject）

詳しいキー一覧は kabusys.config.Settings のプロパティを参照してください。

使い方（主要コマンド）
--------------------

- .env 設定ウィザード
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  - 本番（設定で KABUSYS_ENV=live）
    python -m kabusys.run_execution
  - ペーパートレード（KABUSYS_ENV=paper_trading を .env に設定）
    python -m kabusys.run_execution
  - 実装上の挙動:
    - paper_trading の場合、MockBrokerClient を用い data/paper_trading.db に記録して本番 DB と分離します。
    - 実行中に data/stop_requested.flag や data/kill.flag を用いて外部からの停止を検知できます。

- Monitoring 起動
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60）
  - 監視は常に本番用 sqlite_path を使用（環境に依存せず監視 DB は単一ファイルに集約）

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - 環境変数 PAPER_TRADING_SQLITE_PATH または --db オプションで DB を指定可能

- AI 関連（ライブラリ関数）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - raw_news / news_symbols を読み、OpenAI API でスコアを生成して ai_scores に書き込み
    - api_key 引数または環境変数 OPENAI_API_KEY が必要
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF 1321 の MA200 乖離＋マクロニュースでレジーム判定し market_regime に書き込み

停止 / Kill Switch
------------------
- Kill Switch（自動停止）:
  - kabusys.monitoring.kill_switch が RiskMonitor の結果等を元に data/kill.flag を書き込みます。
  - ExecutionEngine は起動時 / ループ中に kill.flag / stop_requested.flag の存在をチェックして停止します。
- 手動停止フラグ:
  - data/stop_requested.flag を作成すると run_execution/run_monitoring のループは終了します。
  - data/kill.flag は KillSwitch が生成するファイル（ExecutionEngine の停止を意図）。

ログ
----
- ロギングは kabusys.utils.logging_setup.setup_logging で統一的に設定されます。
- デフォルトでは stdout と日次ローテートされたファイル（logs/<app_name>.log）に出力されます。
- ログディレクトリは LOG_DIR 環境変数または引数で指定可能。存在しない場合は自動作成を試みます。

ディレクトリ構成（主要ファイル）
-----------------------------

src/kabusys/
- __init__.py
- config.py                — 環境変数/設定読み込みロジック（自動 .env ロード等）
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor 起動スクリプト
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート
- utils/
  - logging_setup.py        — ログ設定ユーティリティ
  - process_priority.py     — プロセス優先度 / CPU affinity 設定
- monitoring/
  - monitoring_db.py        — SQLite 永続化層（テーブル定義・CRUD）
  - system_monitor.py       — システム状態・データ鮮度監視
  - trade_monitor.py        — （存在する想定）取引監視ロジック
  - risk_monitor.py         — ドローダウン・ポジション上限監視
  - monitoring_engine.py    — 各 Monitor を束ねるループ
  - kill_switch.py          — kill.flag 管理
  - alert_manager.py        — （存在する想定）通知管理
- execution/
  - execution_engine.py     — ExecutionEngine 本体（起動・セッション管理）
  - order_manager.py
  - order_repository.py
  - broker_factory.py
  - risk_manager.py
  - reconciler.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- ai/
  - news_nlp.py             — ニュース NLP / OpenAI 連携
  - regime_detector.py      — レジーム判定
- data/ (実行時に作成される)
  - monitoring.db / paper_trading.db / kabusys.duckdb / *.pid / flags

注意点 / 運用上のヒント
---------------------
- .env を絶対にリポジトリにコミットしないこと（機密情報を含むため）
- 本番稼働前に validate_config を実行して重大な設定漏れを検出すること
- OpenAI を利用する機能は API 料金が発生するので利用状況に注意すること
- ペーパートレードモードを活用して本番口座へ誤発注しない運用フローを確立すること
- ログ・DB ファイルのバックアップ・ローテーションを運用で管理すること

開発 / テスト
--------------
- 各モジュールは比較的純粋関数化（research / portfolio 等）されており単体テストが書きやすい構成です。
- OpenAI 呼び出し部は _call_openai_api を patch してテスト可能です（news_nlp、regime_detector）。
- DuckDB / SQLite はテスト用に一時ファイルを使えば外部依存を避けられます。

ライセンス / 連絡
-----------------
- 本 README はコードベースに基づく要約ドキュメントです。実際の運用・導入にあたってはソースコード内コメントや実装を必ず併せて参照してください。

もし README に追加してほしい「起動例」「.env のサンプル」「依存パッケージの exact list」などがあれば教えてください。必要に応じてサンプル .env や systemd / cron での運用例も提供します。