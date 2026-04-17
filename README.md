KabuSys — README
=================

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした Python ベースの小規模システムです。本リポジトリには以下の主要コンポーネントが含まれます。

- 実行エンジン（ExecutionEngine）: 発注・リスク管理・復旧（reconciliation）等を行う実稼働コンポーネント
- 監視（Monitoring）: システム状態、注文の滞留・約定異常、ドローダウン等を定期監視してログ化・アラート送信
- ポートフォリオ構築ユーティリティ: 候補選定・重み計算・ポジションサイズ算出・セクター制限などの純粋関数群
- リサーチ（Research）: ファクター計算、将来リターン、IC 計算、統計サマリー
- AI 支援モジュール: ニュースのNL Pによるセンチメント評価、レジーム判定（OpenAI API を利用）
- 運用支援ツール: Paper Trading 検証レポート生成、Streamlit ベースの監視ダッシュボード など

主な機能
--------
- Execution
  - Broker クライアント抽象化と発注フロー（OrderManager, OrderRepository）
  - 再起動時の自動リコンシリエーション（Reconciler）
  - リスク管理（RiskManager）と注文管理
  - Paper Trading と Live 環境の分離（専用 SQLite を使用）

- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス存否 / データ鮮度監視
  - TradeMonitor: 注文滞留・約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション数制限監視、ダッシュボード更新
  - KillSwitch / AlertManager: 異常時に停止フラグを書き込み・LINE へ通知（オプション）
  - Streamlit ダッシュボード（読み取り専用で監視状況を可視化）

- Portfolio
  - 候補選定（スコア順）、等金額/スコア加重配分
  - セクター集中制限適用、レジームに基づく乗数計算
  - ポジションサイズ計算（単元丸め、集計キャップ処理、リスクベース配分）

- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB を利用）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー

- AI
  - ニュース記事を OpenAI API でスコアリングして ai_scores テーブルへ保存
  - ETF とマクロニュースを組み合わせた市場レジーム判定（gpt-4o-mini を想定）

セットアップ（開発・実行環境）
------------------------------
前提
- Python 3.9+（typing | の使用および最新ライブラリ互換を考慮）
- DuckDB、psutil、requests、openai、streamlit 等のライブラリ

推奨インストール（例）
- 仮想環境作成
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

- 必要パッケージ（例）
  - pip install duckdb psutil requests openai streamlit

（プロジェクトに requirements.txt がある場合はそれを利用してください）

環境変数 / .env
- 自動でプロジェクトルートの .env / .env.local を読み込みます（OS 環境変数が優先）。
- 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- 主要な環境変数（例）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - OPENAI_API_KEY（AI 機能を使う場合）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（AlertManager）
  - SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト data/paper_trading.db）
  - DUCKDB_PATH（DuckDB ファイル、デフォルト data/kabusys.duckdb）
  - MONITOR_POLL_INTERVAL（監視ループ間隔 秒、デフォルト 60）
  - PAPER_FILL_MODE（paper_trading での約定モード: instant|partial|never|reject）

初回準備
- data ディレクトリを作成（必要に応じて）
  - mkdir -p data
- .env.example を参照して .env を作成（存在すれば自動で読み込まれます）
- DuckDB / SQLite の初期スキーマは実行スクリプトが起動時に init_monitoring_db を呼ぶため自動作成されます。

使い方（典型的な実行例）
-----------------------

1) 監視プロセスを起動
- 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（秒）
- 例:
  - KABUSYS_ENV=development MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

動作:
- process 優先度を高く設定し（可能な場合）、監視ループを実行
- MonitoringDB（SQLite）へ system_status / risk_logs / trade_logs 等を書き込む
- 停止は Ctrl+C またはプロジェクトルート/data/stop_requested.flag を作成すると検知して終了

2) 実行（ExecutionEngine）を起動
- Paper Trading と Live を環境変数 KABUSYS_ENV で切り替え
- Paper Trading の場合は専用 DB（data/paper_trading.db）を使用して本番 DB と分離
- 例（Paper Trading）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Engine は別スレッドで実行され、data/execution.pid に PID を書きます。停止は stop flag（data/stop_requested.flag）で行います。

3) Paper Trading 検証レポート（コマンドラインツール）
- SQLite DB（paper_trading）から簡易レポートを生成
- 例:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または DB を指定: python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

4) 監視ダッシュボード（Streamlit）
- 実行コマンド:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 読み取り専用で現在のダッシュボード、ポジション、最近の注文、システム状況、リスクイベントを表示します。

5) AI 系機能（ニューススコアリング / レジーム判定）
- OPENAI_API_KEY が必要。未設定だと関数は ValueError を投げます。
- ニューススコアリング例（プログラム的に呼ぶ）:
  - from kabusys.ai.news_nlp import score_news
  - score_news(duckdb_conn, target_date, api_key="sk-...")

運用に関する注意点
- Paper Trading は本番 DB と完全分離されます（settings.is_paper で sqlite_path を切り替え）。
- Kill Switch（data/kill.flag）を作成すると ExecutionEngine に停止シグナルを送ります。既存の場合は再書き込みしません。消去は rm data/kill.flag または KillSwitch.clear を利用してください。
- Settings は .env/.env.local を自動ロードしますが、テスト等で自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- MONITOR は常に本番 sqlite_path を参照する実装（一部スクリプトの挙動に注意）。
- OpenAI API 呼び出しはリトライ・フォールバック実装がありますが、APIキー未設定時は呼び出し側で対処が必要です。

ディレクトリ構成（抜粋）
----------------------
src/kabusys/
- __init__.py
- config.py                     — 環境変数 / 設定読み込みロジック
- run_monitoring.py             — SystemMonitor ポーリング起動スクリプト
- run_execution.py              — ExecutionEngine 起動スクリプト

- ai/
  - __init__.py
  - news_nlp.py                  — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py           — 市場レジーム判定（OpenAI）

- monitoring/
  - __init__.py
  - monitoring_db.py             — SQLite 永続化層（テーブル初期化・CRUD）
  - monitoring_engine.py         — 各 Monitor を束ねるエンジン
  - system_monitor.py            — システム状態・データ鮮度監視
  - trade_monitor.py             — 注文滞留・約定異常監視
  - risk_monitor.py              — ドローダウン・ポジション上限監視
  - kill_switch.py               — kill.flag 管理
  - alert_manager.py             — LINE Push 通知ラッパ
  - streamlit_dashboard.py       — Streamlit ダッシュボード

- execution/
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - ...（Broker 関連、ExecutionEngine 実装は同階層）

- portfolio/
  - portfolio_builder.py         — 候補選定・重み計算
  - position_sizing.py           — 株数決定・リスク・丸め処理
  - risk_adjustment.py           — セクターキャップ・レジーム乗数

- research/
  - factor_research.py           — Momentum/Volatility/Value 計算
  - feature_exploration.py       — 将来リターン・IC・統計サマリー

- tools/
  - __init__.py
  - paper_verification_report.py — Paper Trading 検証レポート出力

- utils/
  - process_priority.py          — プロセス優先度 / CPU affinity ユーティリティ

補足（開発者向け）
- DB スキーマのマイグレーションは monitoring_db.init_monitoring_db が簡易で行います（既存カラム確認 & ALTER を実行）。
- DuckDB を活用して時系列ファクター計算を高速に行う設計です。DuckDB の接続は各モジュールへ明示的に渡します。
- OpenAI 関連の API 呼び出し部分はテストしやすく設計されており、内部の _call_openai_api を patch してモック可能です。

トラブルシューティング
- DB が見つからない / 開けない:
  - run_monitoring/run_execution は必要に応じてファイルを作成しますが、streamlit は読み取り専用で開くため DB が存在しないとエラーになります。まず監視プロセスを起動してください。
- OpenAI キー未設定:
  - AI 機能呼び出しで ValueError が出ます。環境変数 OPENAI_API_KEY を設定してください。
- プロセス優先度の設定失敗:
  - psutil の権限不足等で警告ログが出ますが処理自体は継続します（フォールバック済み）。

ライセンス / 貢献
-----------------
（リポジトリの実際のライセンスやコントリビュート規約に従って追記してください）

お問い合わせ
------------
実行方法や設定に関する質問はリポジトリの Issue に投稿してください。