README
=====

概要
----
KabuSys は日本株向けの自動売買・研究プラットフォーム向けの Python パッケージ群です。本リポジトリには以下を含みます:
- 実際の発注を行う ExecutionEngine（本番 / ペーパートレード対応）
- システム・注文・リスク監視用の Monitoring コンポーネント（Kill Switch を含む）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ計算）
- リサーチ用ファクター計算・特徴量探索モジュール（DuckDB を使用）
- ニュース NLP / レジーム判定（OpenAI を利用したセンチメント評価）
- 環境設定ウィザード・設定検証ツール・運用ユーティリティ

主要機能
--------
- Execution
  - 実口座（live）／ペーパートレード（paper_trading）を切替え可能
  - MockBroker を使ったペーパートレードは data/paper_trading.db に記録（本番 DB と分離）
  - RiskManager / OrderManager / Reconciler を組み合わせた発注管理
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス存在・株価データ鮮度を監視
  - TradeMonitor: 発注／約定ログの監視（滞留注文・異常約定など）
  - RiskMonitor: ドローダウン・ポジション上限などを監視し、必要なら Kill Switch を作動
  - MonitoringEngine によりポーリングループで定期チェック
- Portfolio construction
  - 候補選定（スコア順）・等重/スコア加重・リスクベースの株数算出
  - セクターキャップ適用、レジーム乗数（bull/neutral/bear）
- Research
  - DuckDB 接続を受けてモメンタム・ボラティリティ・バリュー等のファクターを計算
  - 将来リターン、IC（Information Coefficient）、統計サマリ機能
- AI（ニュース）
  - OpenAI（gpt-4o-mini）によるニュースの銘柄別センチメント評価（ai_scores テーブルへ書込）
  - マクロニュースを使った市場レジーム判定（market_regime テーブルへ書込）
  - API 呼び出しはリトライ・バックオフ・レスポンス検証あり
- 運用ユーティリティ
  - .env 対話式作成ウィザード（kabusys.config_setup）
  - 起動前の設定検証 CLI（kabusys.validate_config）
  - Paper Trading の検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
  - 統一ログ設定（logs/<app>.log、日次ローテート）

セットアップ手順
----------------
前提:
- Python 3.10+ を推奨（pyproject.toml 等が存在する前提）
- SQLite（標準ライブラリ）と DuckDB、psutil、OpenAI SDK 等が必要

推奨インストール（例）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - 任意で設定 YAML の検証に PyYAML を使う: pip install PyYAML

3. プロジェクトルートの初期設定
   - python -m kabusys.config_setup
     （対話式で .env を生成／更新します）
   - 生成後、設定を検証:
     - python -m kabusys.validate_config
     - 警告もエラー扱いにする場合: python -m kabusys.validate_config --strict

環境変数（主なもの）
- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API パスワード
- 主要（任意またはデフォルトあり）
  - KABUSYS_ENV: 実行環境 (development | paper_trading | live) — デフォルト: development
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト: INFO）
  - LOG_DIR: ログ出力ディレクトリ（デフォルト: logs）
  - OPENAI_API_KEY: OpenAI API キー（AI モジュールで利用）
  - PAPER_FILL_MODE: paper_trading 用の約定挙動 ("instant"|"partial"|"never"|"reject"), デフォルト "instant"
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
- その他は .env.example を参照してください

使い方（主なコマンド）
--------------------
- 環境設定ウィザード
  - python -m kabusys.config_setup
    - .env を対話的に作成・更新します

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（警告を FAIL とする）: python -m kabusys.validate_config --strict

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用、data/paper_trading.db に記録されます
    - 実行時、data/stop_requested.flag があると起動しません。また data/execution.pid に PID を書きます

- 監視プロセス起動
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
    - 監視は常に（KABUSYS_ENV にかかわらず）本番 sqlite_path を使用
    - 停止は data/stop_requested.flag を作成することで行います（監視ループが検知して終了）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB ファイルを指定できます（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI / リサーチのライブラリ的利用
  - news_nlp: from kabusys.ai import score_news; score_news(duckdb_conn, target_date, api_key=None)
  - regime_detector: from kabusys.ai.regime_detector import score_regime; score_regime(duckdb_conn, target_date, api_key=None)
  - research: from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary

運用上の注意
-------------
- ログ: setup_logging により logs/<app_name>.log に日次ローテーションで出力されます。LOG_DIR により出力先を変更可能。
- Kill Switch: KillSwitch は data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。KILL_FLAG_CLEAR_ON_START=1 を本番で使うと危険（自動クリアされるため）。
- DB 分離: ペーパートレードは paper_sqlite_path を使い、本番 monitoring.db と完全分離する設計になっています。
- OpenAI API: AI モジュールは OPENAI_API_KEY を必要とします。API 呼び出し時のエラー処理やリトライは組み込まれていますが、利用料やレート制限に注意してください。
- ユーティリティ:
  - config_setup は .env を作成します。.env は絶対に Git にコミットしないでください。
  - validate_config で設定不備を起動前に検出できます。PyYAML がインストールされていれば config/*.yaml の構文チェックも行います。

ディレクトリ構成（主要ファイル）
-------------------------------
- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings 管理
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - ai/
    - news_nlp.py                 — ニュースセンチメント（OpenAI）
    - regime_detector.py          — マクロ + MA に基づくレジーム判定
  - research/
    - factor_research.py          — ファクター計算（momentum, volatility, value）
    - feature_exploration.py      — 将来リターン / IC / summary
  - portfolio/
    - portfolio_builder.py        — 候補選定・重み計算
    - risk_adjustment.py          — セクターキャップ・レジーム乗数
    - position_sizing.py          — 株数決定・aggregate cap
  - monitoring/
    - monitoring_db.py            — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py           — CPU/メモリ/ディスク/データ鮮度監視
    - trade_monitor.py            — （滞留注文などの監視）※詳細実装あり
    - risk_monitor.py             — ドローダウン・ポジション上限監視
    - kill_switch.py              — kill.flag 管理
    - monitoring_engine.py        — 各 Monitor を束ねるループ
  - execution/
    - execution_engine.py         — 実行エンジン本体（EngineConfig 等）
    - broker_factory.py           — ブローカークライアント生成（Mock / 実口座）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py            — ログ初期化ユーティリティ
    - process_priority.py         — プロセス優先度 / CPU affinity
  - data/                         — 実行時に使用するファイル群（デフォルト）
    - monitoring.db (デフォルト)
    - kabusys.duckdb (デフォルト)
    - paper_trading.db (ペーパートレード)
    - kill.flag / stop_requested.flag / execution.pid など

補足（開発者向け）
------------------
- DuckDB 接続を受けて処理する設計のため、リサーチ機能は本番 DB にアクセスせず分析用途に使えます（安全な読み取り）。
- テスト時は一部の外部呼び出し（OpenAI など）を unittest.mock.patch で差し替えられるよう設計されています。
- ロギング・プロセス優先度設定等はプラットフォーム差分（Windows/Linux/Mac）を吸収する実装になっていますが、権限不足時は警告ログを出してスキップします。

ライセンス・貢献
----------------
- 本リポジトリのライセンスと貢献ポリシーは（プロジェクトルートの LICENSE / CONTRIBUTING を参照してください）。README に記載のない運用上の注意や制約がある場合は、コード中の docstring を参照してください。

以上。質問や追加で README に載せたい情報（例: サンプル .env、起動時の systemd / supervisor 設定例など）があれば教えてください。