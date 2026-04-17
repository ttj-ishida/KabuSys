README — KabuSys（日本株自動売買システム）
======================================

概要
----
KabuSys は日本株向けの自動売買システムとそれを支える監視・研究ツール群の軽量実装です。  
主な目的は以下です。
- 発注エンジン（ExecutionEngine）による自動発注（本番 / ペーパートレード対応）
- 実行・約定・リスクを監視する Monitoring サービス（Kill Switch を含む）
- ファクター計算・リサーチ用モジュール（DuckDB ベース）
- ニュース NLP やレジーム判定などの AI 補助機能（OpenAI API を利用）
- 環境設定ウィザード・設定検証ツール・レポート生成ツール等のユーティリティ

主な機能
--------
- Execution
  - ExecutionEngine を用いた注文発行・注文管理（BrokerClient 抽象）
  - paper_trading 環境では MockBrokerClient を使用し、ペーパートレード用 DB に記録（本番 DB と分離）
  - リスク管理（RiskManager）、Reconciler、OrderManager 等の周辺コンポーネントを備える
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク監視、プロセス存在チェック、データ鮮度チェック
  - TradeMonitor: 滞留注文・約定異常の検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch: しきい値超過時に data/kill.flag を書き込み ExecutionEngine を停止させる
  - MonitoringEngine: 各モニタをまとめて定期実行しアラートを通知（LINE 連携可）
- Research / Portfolio
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC 計算、統計サマリー
  - ポートフォリオ構築関数（候補選定、重み付け、ポジションサイズ決定、セクター制限、レジーム乗数）
- AI
  - news_nlp: raw_news を OpenAI（gpt-4o-mini 等）でスコアリングして ai_scores に書き込む
  - regime_detector: ETF 200日MA とマクロニュースセンチメントを使い日次レジーム判定
- ツール
  - 対話式 .env 生成ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成（tools.paper_verification_report）

セットアップ
-----------
前提
- Python 3.10 以上（typing の | 演算子を使用）
- SQLite（標準）、DuckDB、psutil、openai 等の Python パッケージ

推奨インストール手順（仮想環境を推奨）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install -r requirements.txt
   ※ requirements.txt がない場合は最低限以下を入れてください:
     - pip install psutil duckdb openai

   - 監視・設定検証用に PyYAML を利用する場合:
     - pip install pyyaml

3. .env の初期作成
   - python -m kabusys.config_setup
     対話式で J-Quants トークン、kabu API パスワード、DB パス等を設定できます。
   - 生成された .env は絶対に Git にコミットしないでください。

4. 設定検証
   - python -m kabusys.validate_config
   - 本番前は --strict オプションで警告も FAIL 扱いにできます:
     python -m kabusys.validate_config --strict

主要な環境変数（代表）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- DUCKDB_PATH (default data/kabusys.duckdb)
- SQLITE_PATH (default data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (ペーパートレード専用 DB, default data/paper_trading.db)
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 用挙動）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL
- MONITOR_POLL_INTERVAL: 監視ループの秒間隔（run_monitoring で上書き可）

使い方
------
エントリポイント（スクリプト）
- 実行エンジン（ExecutionEngine）を起動:
  - python -m kabusys.run_execution
  - 実行中は data/execution.pid に PID が書かれ、停止は data/stop_requested.flag や data/kill.flag で制御できます。
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い PAPER_TRADING_SQLITE_PATH に記録します。

- 監視ループを起動:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で設定可能（デフォルト 60 秒）
  - 監視は本番 sqlite_path（SQLITE_PATH）を常に使用します（環境に関わらず）

- 設定ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱いになります

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

AI / 研究モジュール（プログラム内 API）
- kabusys.ai.score_news(conn, target_date, api_key=None)
  - DuckDB 接続を渡してニュースのセンチメントを計算し ai_scores に書き込む
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - レジーム判定を行い market_regime テーブルに保存
- kabusys.research.calc_momentum / calc_volatility / calc_value などは DuckDB 接続と日付を渡して計算

停止・Kill スイッチ
- data/stop_requested.flag を作成すると run_execution / run_monitoring が検知して安全に停止します（run scripts で利用）。
- KillSwitch（監視）によって危険と判定された場合、data/kill.flag が書き込まれ、ExecutionEngine の起動や継続がブロックされます。
- Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動で kill.flag をクリアしますが、本番では 0 を推奨します。

ディレクトリ構成（主なファイルと説明）
-----------------------------------
- src/kabusys/
  - __init__.py — パッケージ情報
  - config.py — 環境変数・設定読み込み / Settings クラス
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

  - ai/
    - news_nlp.py — ニュースの LLM ベースセンチメントスコア化
    - regime_detector.py — 市場レジーム判定（MA + マクロニュース）
  - monitoring/
    - monitoring_db.py — SQLite を使った監視ログの永続化層（初期化・I/O）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の評価・書き込み
    - monitoring_engine.py — 各 Monitor をまとめる実行ループ
    - alert_manager.py — （アラート発行ロジック、LINE 等と接続）
  - execution/         — （発注エンジン関連: BrokerFactory, EngineConfig, OrderRepository 等）
  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み付け
    - position_sizing.py — 株数決定・リスク制限
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — モメンタム・ボラティリティ・バリュー計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - data/              — （データパイプライン / DuckDB スキーマ関連）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート出力ツール
  - utils/
    - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ

データ / DB（デフォルトパス）
- DuckDB: data/kabusys.duckdb
- Monitoring SQLite: data/monitoring.db
- Paper Trading SQLite: data/paper_trading.db
- PID / フラグ:
  - data/execution.pid
  - data/stop_requested.flag
  - data/kill.flag

運用上の注意
-----------
- .env（機密情報）をリポジトリに含めないこと。config_setup で生成した .env は必ず .gitignore に入れて管理してください。
- 本番（KABUSYS_ENV=live）では LINE の通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を確認してください。validate_config の live ガードも有用です。
- OpenAI API を利用する機能は API キーの使用料が発生します。呼び出し頻度・モデル選定に注意してください。
- run_monitoring は常に本番用の sqlite_path を参照します（監視ログは環境に依らず production DB を想定）。
- process priority / CPU affinity の設定は OS 権限に依存します。psutil による設定が失敗した場合はログに出力されスキップされます。

開発・拡張
----------
- DuckDB のスキーマやテーブル名に依存しているモジュールが多いため、データパイプライン（prices_daily / raw_financials / raw_news 等）の準備が必要です。
- AI 呼び出し関数（_call_openai_api）はテスト時に patch して外部呼び出しをモックできます。
- portfolio / research 関数群は純粋関数ベースでテストしやすい設計です。ユニットテストの追加を推奨します。

問い合わせ / 貢献
-----------------
- バグ報告や機能提案は Issue を立ててください。Pull Request は歓迎します。
- 重大な変更（DB スキーマ変更・外部 API 仕様変更）はドキュメントとマイグレーション手順を併記してください。

以上。必要であれば各モジュールのより詳細な使い方（関数シグネチャやサンプルコード）を追記します。どの部分を深掘りしますか？