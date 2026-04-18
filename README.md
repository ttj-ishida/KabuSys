KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買プラットフォームの一部モジュール群を含みます。
主要なコンポーネントは「Execution（発注エンジン）」「Monitoring（監視）」「Portfolio/Research（銘柄選定・ファクター計算）」および「AI（ニュース NLP / レジーム判定）」です。ここではプロジェクトの概要、機能一覧、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめます。

プロジェクト概要
---------------
KabuSys は以下機能を備えた自動売買/分析基盤のコード群です（実際の運用では追加コンポーネントや外部インテグレーションが必要です）。
- 発注エンジン（ExecutionEngine）: ブローカークライアントを使った注文発行・管理（paper_trading モードは MockBroker を使用、paper DB に分離）
- 監視（Monitoring）: システム稼働状況、データ鮮度、滞留注文、ドローダウン等を監視・ログ保存し、必要に応じて Kill Switch を発動
- ポートフォリオ構築（Portfolio）: 候補選定、重み計算、ポジションサイズ計算、セクター制限、レジーム乗数
- リサーチ（Research）: ファクター計算（モメンタム・バリュー・ボラティリティ等）、将来リターン、IC 計算、統計サマリー
- AI（ニュース NLP / レジーム判定）: OpenAI を用いたニュースセンチメント評価と市場レジーム判定（gpt-4o-mini を想定）
- ユーティリティ: .env 対話ウィザード、設定検証 CLI、ログ設定、プロセス優先度設定、Paper Trading 検証レポート出力等

主な特徴（機能一覧）
------------------
- 設定管理
  - .env 自動ロード（プロジェクトルートの .env / .env.local、環境変数が優先）
  - 対話式ウィザード: python -m kabusys.config_setup による .env 生成/更新
  - 起動前チェック: python -m kabusys.validate_config で環境・設定ファイルを検証
- Execution（発注）
  - KABUSYS_ENV による切替: development / paper_trading / live
  - paper_trading 時は MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と分離）
  - リスク管理（RiskManager）、注文管理（OrderManager）等の組み合わせで Engine を実行
- Monitoring（監視）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - 監視結果は SQLite（data/monitoring.db）に永続化
  - Kill Switch: 条件を満たすと data/kill.flag を書き込んで Execution 停止を促す
  - run_monitoring.py によりポーリングループで常時モニタリング（MONITOR_POLL_INTERVAL で間隔指定可）
- Portfolio & Position sizing
  - 候補抽出、スコア加重 / 等金額重み、リスクベースの株数決定、単元株対応、集約キャップ調整
  - セクター上限適用、レジーム乗数（bull/neutral/bear）の計算
- Research
  - DuckDB を用いたファクター計算（prices_daily / raw_financials ベース）
  - forward return、IC（Spearman rank）、ファクター統計量
- AI
  - news_nlp.score_news: OpenAI を呼んで銘柄ごとのニュースセンチメントを ai_scores に書き込み
  - regime_detector.score_regime: ETF 的指標 + マクロニュースセンチメントを合成して market_regime を更新
  - API 呼び出しはリトライ・バックオフ・フェイルセーフ処理あり
- ツール
  - Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report

セットアップ手順
----------------
以下は開発・実行のための最低限のセットアップ例です。実際には requirements.txt 等で依存管理してください。

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要なパッケージをインストール（例）
   - pip install duckdb psutil openai
   - 任意: PyYAML は validate_config の YAML 検証に使用される → pip install pyyaml

   （注）実際の requirements は本リポジトリに含まれていないため、環境に応じて調整してください。

4. .env の作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - もしくは手動で .env を作成（例は下記）

必須環境変数（最小例）
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
（その他、運用に応じて OPENAI_API_KEY, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, LINE_* 等を設定）

.example .env（参考）
- JQUANTS_REFRESH_TOKEN=your_jquants_token
- KABU_API_PASSWORD=your_kabu_password
- KABU_API_BASE_URL=http://localhost:18080/kabusapi
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- KABUSYS_ENV=development
- LOG_LEVEL=INFO
- KILL_FLAG_CLEAR_ON_START=0

使い方（主要コマンド）
--------------------

設定検証・ウィザード
- .env ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit(1)）

監視プロセス
- 監視ループの起動:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL=30 などでポーリング間隔を秒で上書き可（デフォルト 60秒）
  - 監視は常に本番 sqlite_path を使用（KABUSYS_ENV に依らず data/monitoring.db を参照）

Execution（発注エンジン）
- エンジン起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient が使われ、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH, default data/paper_trading.db）に記録されます
- 停止方法:
  - data/stop_requested.flag を作成すると run_execution/run_monitoring のループが停止します
  - Kill Switch は data/kill.flag を作成して Execution 停止を促します（KillSwitch は冪等で書き込み）

AI 関連
- ニュース NLP（プログラムから呼ぶ例）:
  - from kabusys.ai.news_nlp import score_news
  - score_news(duckdb_conn, target_date, api_key="...")  ※ api_key を渡さない場合は OPENAI_API_KEY を参照
- レジーム判定:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(duckdb_conn, target_date, api_key="...")

ツール
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で SQLite ファイル指定（環境変数 PAPER_TRADING_SQLITE_PATH でも可）

ログ
- setup_logging によりログは stdout と logs/<app_name>.log（日次ローテート）に出力されます
- デフォルトログディレクトリ: logs/

主要ファイル / ディレクトリ構成
-----------------------------
（リポジトリの src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/.env 自動ロードと Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI 呼び出し、ai_scores 書込）
    - regime_detector.py     — 市場レジーム判定
    - __init__.py
  - monitoring/
    - monitoring_db.py       — SQLite テーブル定義・永続化レイヤ
    - system_monitor.py      — CPU/メモリ/ディスク/データ鮮度監視
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - trade_monitor.py       — (参照されるがここにない場合は同様の監視モジュール)
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - kill_switch.py         — data/kill.flag の書込み
    - alert_manager.py       — (参照: アラート送信ロジック)
  - execution/
    - execution_engine.py    — ExecutionEngine 本体（参照）
    - order_manager.py       — 注文管理
    - order_repository.py    — 注文リポジトリ
    - reconciler.py          — 注文整合処理
    - risk_manager.py        — 発注リスク管理
    - broker_factory.py      — ブローカークライアント生成
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 株数計算・集約キャップ処理
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py     — モメンタム/バリュー/ボラティリティ計算
    - feature_exploration.py — 将来リターン・IC・統計
    - __init__.py
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
    - __init__.py
  - monitoring/monitoring_db.py (上記)

- data/                      — 実行時に使用する DB / フラグ / pid ファイルを格納する想定
  - monitoring.db            — SQLite 監視 DB（デフォルト）
  - paper_trading.db         — Paper Trading 用 DB（paper_trading モード）
  - kill.flag                — Kill Switch フラグ（作成で Execution 停止）
  - stop_requested.flag      — 外部からプロセス停止を依頼するためのフラグ
  - execution.pid            — Execution の PID ファイル（Engine によって使用）

注意事項 / 運用メモ
------------------
- KABUSYS_ENV の値: development / paper_trading / live（Settings で検証）
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 本番運用時は KABUSYS_ENV=live による設定を厳重に確認してください（validate_config に警告表示あり）。
- AI（OpenAI）を使う機能は OPENAI_API_KEY が必要です。API 呼び出しに伴うコストとレイテンシに注意してください。
- Paper Trading は本番 DB と分離するよう設計されていますが、実行前に .env のパス設定を必ず確認してください。
- ログディレクトリなどファイル作成に失敗した場合、ファイル出力が無効化され stdout のみになる点に注意してください。

貢献 / 開発
------------
- コードの追加・修正は PR を送ってください。ユニットテストや CI の設定により品質を保つことを推奨します。
- 実運用で使う場合、ブローカー/取引所 API の実装（broker client）、AlertManager（LINE 等通知）、運用用プロセスマネージャ（systemd / supervisor / container）および監視ダッシュボードの整備が必要です。

ライセンス
----------
（ここにライセンス情報を記載してください）

最後に
------
この README はソースコードの現状をもとに自動売買システムの使い方・構成をまとめたドキュメントです。詳細な設計や実装の使用法については各モジュールの docstring を参照してください。何か追加で README に入れたい項目があれば教えてください。