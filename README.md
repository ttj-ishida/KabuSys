# KabuSys

日本株自動売買システム（ライブラリ＋起動スクリプト群）のリポジトリ向け README（日本語）。

この README はソースツリー（src/kabusys）に含まれる主なモジュール・CLI・設定手順をまとめたものです。開発者や運用担当者がローカルで起動・テスト・監視を行うための参照として作成しています。

注意: 各 CLI はパッケージモジュールとして実行できます（例: `python -m kabusys.run_execution`）。実行前に .env を準備し、必要な依存パッケージをインストールしてください。

概要
-----
KabuSys は日本株の自動売買を想定したシステム群です。主な責務は次の通りです。

- シグナル・ポートフォリオ構築（portfolio パッケージ）
- ポジションサイズ計算と発注ロジック（execution パッケージ）
- モニタリング（system/trade/risk）および Kill Switch（monitoring パッケージ）
- DuckDB / SQLite を使ったデータ取得・分析（research パッケージ）
- ニュースの NLP スコアリング・レジーム判定（ai パッケージ）
- 運用ユーティリティ（ログ設定、プロセス優先度、設定ウィザード、検証ツール、検証レポート）

特徴・機能一覧
----------------
- 環境分離
  - KABUSYS_ENV により `development` / `paper_trading` / `live` を切り替え。
  - paper_trading では MockBrokerClient を使用し、paper_trading 用の SQLite DB に記録（本番 DB と分離）。
- モニタリング
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねた MonitoringEngine。
  - SQLite に system_status, trade_logs, risk_logs, positions, dashboard などを永続化。
  - KillSwitch によりリスク条件（ドローダウン超過、ポジション上限など）で ExecutionEngine を停止可能（data/kill.flag を作成）。
- 実行エンジン（ExecutionEngine）
  - Broker クライアント抽象化（実ブローカー or Mock）。
  - リスク管理（最大ポジション比率、利用率、サーキットブレーカー等）。
- ポートフォリオ構築
  - 候補選定、等金額/スコア加重配分、リスクに基づく単元株数決定、セクター制約・レジーム補正。
- 研究・解析
  - DuckDB を使ったファクター計算（モメンタム、ボラティリティ、バリュー等）。
  - ファクターの IC・統計サマリ。
- AI（OpenAI）
  - ニュース記事を LLM で評価し銘柄別スコアを ai_scores に保存（OPENAI_API_KEY 必須）。
  - マクロ記事を基に市場レジーム（bull/neutral/bear）を判定して保存。
- 運用支援
  - .env 対話式ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート作成ツール（tools/paper_verification_report.py）
- ロギング・プロセス設定
  - 共通の logging 設定（logs 日次ローテート）
  - プロセス優先度・CPU affinity 設定ユーティリティ（psutil に依存）

セットアップ手順
----------------
1. Python 環境
   - Python 3.9+（ソース内型注釈等に合わせてください）。

2. 依存ライブラリ（最小）
   - pip でインストール例:
     - duckdb
     - psutil
     - openai （AI 機能を使う場合）
     - PyYAML（設定検証で YAML ファイルの中身もチェックしたい場合）
   - 例:
     pip install duckdb psutil openai PyYAML

   ※ requirements.txt がある場合はそれを使用してください（本リポジトリに同梱されている場合）。

3. ディレクトリ作成
   - デフォルトでは以下のファイルパスを使用します。事前に作成しておくと権限周りで安全です。
     - data/（SQLite、PID、flag 等）
     - logs/（ログファイル）
   - 例:
     mkdir -p data logs

4. .env の準備（対話式ウィザード推奨）
   - 対話式ウィザードを実行して .env を作成:
     python -m kabusys.config_setup
   - その後、設定検証:
     python -m kabusys.validate_config
   - 必須環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - AI 機能を使う場合:
     - OPENAI_API_KEY を環境変数に設定（.env に入れておくか実行時にエクスポート）

5. データベース初期化
   - 起動スクリプト（run_monitoring/run_execution）実行時に必要なテーブルが作成されます（init_monitoring_db を通じて冪等に作成）。

基本的な使い方（CLI）
---------------------
- 実行エンジン（発注系）
  - 本番 / ペーパーの切り替え: KABUSYS_ENV を設定
    - 本番:
      KABUSYS_ENV=live python -m kabusys.run_execution
    - ペーパー（別 DB に記録）:
      KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 実行前に data/stop_requested.flag が存在すると起動を行いません（制御フラグ）。

- 監視（Monitoring）
  - 監視ループを起動:
    python -m kabusys.run_monitoring
  - ポーリング間隔の上書き:
    - 環境変数 MONITOR_POLL_INTERVAL に秒数を設定（デフォルト 60）
      例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使用する点に注意。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code 1）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB パス: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH または --db で変更可）

- AI 関連（プログラム的呼び出し）
  - ニューススコアリング:
    from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date, api_key="...")
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key="...")

運用上の注意
-------------
- Kill Switch / Stop フラグ
  - Kill Switch は Settings.kill_flag_path（デフォルト data/kill.flag）に文字列を書き込み ExecutionEngine を停止させます。
  - 実プロセスの強制停止やメンテナンス時は data/stop_requested.flag を作成することで run_* スクリプトのループが終了します。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると ExecutionEngine 起動時に既存の kill.flag を自動クリアします（本番では 0 を推奨）。

- ログ
  - デフォルトで logs/<app_name>.log に日次ローテーションで出力されます（30日分保持）。
  - コンソール出力は stdout を使用。

- プロセス優先度
  - 起動スクリプトは set_process_priority("high") を呼びますが、権限やプラットフォームにより設定に失敗する場合があります（警告ログで通知）。

- DB 分離
  - paper_trading 環境は paper_sqlite_path（デフォルト data/paper_trading.db）にデータを保存し、本番 sqlite_path と明確に分離します。実行前にパスを確認してください。

設定の主な環境変数（抜粋）
-------------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- KABUSYS_ENV (development | paper_trading | live)（デフォルト: development）
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- LOG_LEVEL (DEBUG/INFO/...)
- OPENAI_API_KEY（AI 機能を使う場合）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒数）
- KILL_FLAG_CLEAR_ON_START（0/1）

ディレクトリ構成（主要ファイル）
------------------------------
リポジトリの src/kabusys 下の主な構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境・設定管理（.env 自動ロード含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - monitoring/
    - monitoring_db.py       — SQLite テーブル作成・IO ラッパ
    - monitoring_engine.py   — 各 Monitor の統合ループ
    - system_monitor.py      — CPU/メモリ/ディスク/データ鮮度監視
    - trade_monitor.py       — （発注ログ監視など）※ (実装あり)
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag の操作
    - alert_manager.py       — （通知機能）※ (実装あり)
  - execution/
    - execution_engine.py    — 実行エンジン本体（EngineConfig など）
    - broker_factory.py      — ブローカークライアントの生成
    - order_manager.py       — 注文管理
    - order_repository.py    — 注文 DB ラッパ
    - reconciler.py          — ブローカーとの差分解消
    - risk_manager.py        — 発注時のリスク判定
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py     — Momentum/Value/Volatility 等の DuckDB ファクター計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — 市場レジーム判定（OpenAI + MA200）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - utils/
    - logging_setup.py       — 共通ログ設定
    - process_priority.py    — プロセス優先度・CPU affinity

補足事項・開発者向けメモ
------------------------
- DuckDB 接続を引数で受ける設計が多く、ローカルでの解析・単体テストがしやすい構造です。
- 多くの関数は「副作用を持たない純粋関数」を意図して設計されているため、ユニットテストが容易です（portfolio / research など）。
- OpenAI へアクセスするコードはリトライ・バリデーション処理を備えていますが、API 利用量・レートに注意してください。
- validate_config.py により起動前に環境変数や config/*.yaml の存在・パスをチェックできます。PyYAML がインストールされていない場合は YAML パースチェックがスキップされます。

問題・貢献
----------
バグ報告や機能追加提案は Issues を立ててください。プルリク歓迎です。コードスタイルやテスト、ドキュメントの改善にご協力ください。

ライセンス
----------
プロジェクトルートの LICENSE を参照してください（本リポジトリに付属している場合）。

以上。必要なら実行例（各 CLI の具体的なフラグ・例）や .env.example のサンプルを追記します。どの部分を詳しく書けばよいか教えてください。