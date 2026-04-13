KabuSys — README
===============

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした Python 製のソフトウェア群です。本リポジトリは以下の主要機能を提供します。

- 発注エンジン（ExecutionEngine）と起動 / 復旧ロジック
- 監視（MonitoringEngine）：システム状態、注文滞留、リスク（ドローダウン、ポジション上限）を監視
- ポートフォリオ構築（候補選定・重み付け・ポジションサイジング・セクター制約）
- リサーチ（ファクター計算・特徴量解析）
- AI 支援（ニュースのセンチメント評価、マーケットレジーム判定：OpenAI を利用）
- ダッシュボード（Streamlit）と検証レポート生成（Paper Trading 用）

主な設計ポリシー
- DuckDB と SQLite を使いデータ永続化と解析を分離
- 本番 DB と Paper Trading DB を明確に分離（KABUSYS_ENV に依存）
- ルックアヘッドバイアスを防ぐ実装（date.today()/datetime.today() の未使用）
- フェイルセーフ：外部 API 失敗時は安全側で続行（例：AI API が失敗しても例外で停止しない）

機能一覧
--------
- monitoring:
  - SystemMonitor：CPU/メモリ/ディスク、Execution プロセス存在確認、データ鮮度チェック
  - TradeMonitor：滞留注文検出、約定の価格異常検出
  - RiskMonitor：ドローダウン / ポジション上限監視、kill.flag 書込（Execution 停止シグナル）
  - AlertManager：LINE Push API を使った通知（トークン未設定時はログ出力のみ）
  - Streamlit ダッシュボード（監視データ表示）
- execution:
  - ExecutionEngine（起動 / セッション実行）
  - OrderManager / Reconciler：起動時の自動復旧・ブローカー突合
  - BrokerClientFactory：環境に応じて実ブローカー / MockBroker を選択（paper_trading 用）
- portfolio:
  - 候補選定、等重・スコア重み付け、リスク調整（セクターキャップ、レジーム乗数）、ポジションサイジング
- research:
  - ファクター計算（Momentum / Volatility / Value）
  - 特徴量探索（将来リターン計算、IC 計算、要約統計）
- ai:
  - news_nlp.score_news：ニュース記事を OpenAI に投げて銘柄ごとのスコアを ai_scores に保存
  - regime_detector.score_regime：ETF (1321) の MA200 とマクロニュースでレジーム判定（bull/neutral/bear）
- tools:
  - paper_verification_report：Paper Trading DB を分析して検証レポートを標準出力に出す

セットアップ
-----------
必須（代表的なパッケージ）
- Python 3.8+
- duckdb
- psutil
- requests
- openai (AI 機能を使う場合)
- streamlit (Streamlit ダッシュボードを使う場合)

例（pip）
- requirements.txt がある場合:
  pip install -r requirements.txt
- 個別:
  pip install duckdb psutil requests openai streamlit

環境変数 / .env
- 自動読み込み:
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に .env と .env.local を自動で読み込みます（OS 環境変数が優先）。
  - 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 主な環境変数:
  - KABUSYS_ENV: 起動環境（development / paper_trading / live）デフォルト: development
    - paper_trading の場合、MockBrokerClient を使い DB は data/paper_trading.db に記録されます（本番 DB と分離）
  - SQLITE_PATH: 監視 DB（monitoring）デフォルト: data/monitoring.db
  - DUCKDB_PATH: DuckDB データベースデフォルト: data/kabusys.duckdb
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 各 API の必須トークン
  - OPENAI_API_KEY: OpenAI を使う機能で必須
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager（LINE）用（未設定でも動作。ログ出力にフォールバック）
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒）。run_monitoring で上書き可能（デフォルト 60 秒）
  - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等：監視・制御関連設定
- PAPER_FILL_MODE（paper_trading 時のモック約定挙動）:
  - instant / partial / never / reject（デフォルト: instant）

ファイル権限
- PID / kill.flag を書き込む data ディレクトリに対して書き込み権限が必要です。

使い方（主要コマンド）
--------------------

1) 監視ループの起動
- 目的: SystemMonitor をポーリングして監視ログを書き込む
- 実行:
  python -m kabusys.run_monitoring
- 環境変数:
  - MONITOR_POLL_INTERVAL=XX でポーリング間隔（秒）を上書き可能（1 秒以上を指定）
- 備考:
  - 実行開始時にプロセス優先度を "high" に設定します（set_process_priority 呼出し）
  - monitoring は KABUSYS_ENV にかかわらず sqlite_path（本番用）を使用します

2) Execution エンジンの起動
- 目的: ExecutionEngine を起動して戦略実行セッションを動かす
- 実行:
  python -m kabusys.run_execution
- 環境:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に書き込みます
- 備考:
  - 起動時に process priority を "high" に設定します
  - init_monitoring_db を呼んで監視テーブルの存在を保証します（冪等）

3) Paper Trading 検証レポート
- 目的: paper_trading DB を解析して稼働率・注文成功率・レイテンシ等を表示
- 実行例:
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
- デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH 環境変数で変更可）

4) Streamlit ダッシュボード
- 目的: 監視 DB の可視化（Overview / Positions / Orders / System）
- 実行:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 備考:
  - ダッシュボードは監視ループが DB に書き込んでいることを前提とします（読み取り専用で開く）

5) AI 機能（ニュース NLP / レジーム判定）
- 必須: OPENAI_API_KEY を環境変数か関数引数で指定
- news_nlp.score_news(conn, target_date, api_key=None) を利用して ai_scores テーブルへスコアを書き込む
- regime_detector.score_regime(conn, target_date, api_key=None) で market_regime テーブルへ書き込む
- 実運用では OpenAI のレート制限や料金に注意してください（リトライやフォールバック実装あり）

設定・挙動の注意点
----------------
- .env の自動読み込みはプロジェクトルートを探索して行われます。プロジェクト配布後も .env を使えるように工夫されています。
- MONITORING は常に sqlite_path（本番用）を参照するため、paper_trading 環境でも監視は本番 DB を用います（設計に応じた動作）。
- paper_trading 環境では execution の発注はモックに切り替わり、実口座への影響はありません。
- OpenAI 呼び出しは一部で冪等 / フェイルセーフ処理が入っていますが、API キーとネットワークの健全性を確認してください。
- Process priority / CPU affinity の設定は OS に依存し、権限不足や未対応 OS では警告を出してスキップします。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py                 — パッケージ定義（__version__ 等）
- config.py                   — 環境変数 / Settings 管理（.env 自動読込）
- run_monitoring.py           — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py            — ExecutionEngine 起動スクリプト

src/kabusys/monitoring/
- monitoring_db.py            — SQLite テーブル初期化と永続層 (MonitoringDB)
- system_monitor.py           — システム状態・データ鮮度監視
- trade_monitor.py            — 注文滞留・約定異常監視
- risk_monitor.py             — ドローダウン・ポジション上限監視
- kill_switch.py              — kill.flag の操作（Execution 停止シグナル）
- alert_manager.py            — LINE 通知
- monitoring_engine.py        — 各 Monitor を束ねるエンジン
- streamlit_dashboard.py      — Streamlit ダッシュボード

src/kabusys/execution/
- order_manager.py
- reconciler.py
- order_repository.py
- execution_engine.py
- broker_factory.py
- broker_api.py
(発注 / リコンシリエーション / ブローカー抽象化）

src/kabusys/portfolio/
- portfolio_builder.py        — 候補選定・重み付け
- position_sizing.py          — 株数計算・スケーリング
- risk_adjustment.py          — セクター上限・レジーム乗数

src/kabusys/research/
- factor_research.py          — Momentum / Volatility / Value 計算
- feature_exploration.py      — 将来リターン・IC・統計サマリー

src/kabusys/ai/
- news_nlp.py                 — ニュース集合を LLM に投げて ai_scores を更新
- regime_detector.py          — ETF MA + マクロニュースでレジーム判定

src/kabusys/tools/
- paper_verification_report.py — Paper Trading 検証レポート生成スクリプト

src/kabusys/utils/
- process_priority.py         — プロセス優先度 / CPU affinity 設定ユーティリティ

データファイル（デフォルト）
- data/monitoring.db          — 監視ログ SQLite（SQLITE_PATH）
- data/paper_trading.db       — Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）
- data/kabusys.duckdb         — DuckDB（DUCKDB_PATH）
- data/execution.pid          — ExecutionEngine PID file（PID_FILE_PATH）
- data/kill.flag              — Kill flag（KILL_FLAG_PATH）

開発・デバッグのヒント
--------------------
- ローカルで Paper Trading を使うときは KABUSYS_ENV=paper_trading を設定すると実 DB への影響を避けられます。
- DB スキーマは monitoring_db.init_monitoring_db() が冪等に作成・マイグレーションを行います。既存 DB に列が足りない場合は自動で追加されます（例: latency_ms, peak_value）。
- Streamlit で DB を読み取り専用（URI mode=ro）で開いているため、監視エンジンが DB を書いている状態で可視化できます。
- OpenAI を使う関数は内部で再試行を行いますが、API キーの漏洩／課金には注意してください。

ライセンス / バージョン
----------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（現在 0.1.0）。

最後に
------
この README はコードベースの主要部分に基づいて作成しました。動作環境や依存パッケージは環境や要件により変わる可能性があります。追加の実行例・CI 設定・依存関係はプロジェクトのルートにあるドキュメントや requirements.txt／pyproject.toml を参照してください。質問や特定機能の詳細ドキュメントが必要な場合は教えてください。