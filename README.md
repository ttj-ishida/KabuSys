KabuSys — 日本株自動売買システム（簡易 README）
======================================

この README はリポジトリ内の主要スクリプト／モジュール群（監視、実行エンジン、ポートフォリオ構築、リサーチ、AI ヘルパー等）の概要、セットアップ、使い方、ディレクトリ構成をまとめたものです。コードを読みやすくするために主要な挙動や環境変数の説明も含めています。

プロジェクト概要
----------------
KabuSys は日本株向けの自動売買・監視・検証を行うためのライブラリ／アプリケーション群です。主な目的は以下です。

- 注文の作成・送信・状態同期（ExecutionEngine / OrderManager / Reconciler）
- 監視とアラート（MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor / AlertManager）
- ポートフォリオ構築（候補選定、重み計算、リスク調整、枚数算出）
- 研究用ファクター計算・特徴量解析（research パッケージ）
- ニュース NLP によるセンチメント評価（OpenAI を利用する ai.news_nlp）
- Paper Trading 用の検証・レポート出力ツール
- Streamlit ダッシュボードによる監視画面表示

主な機能一覧
--------------
- 実行 (Execution)
  - ブローカークライアント抽象化（本番／モックを切替）
  - OrderManager による注文状態遷移と二相永続化（クラッシュ安全）
  - 再起動時の自動リコンシリエーション（Reconciler）
  - リスク管理（RiskManager: ポジション上限、drawdown 等）
- 監視 (Monitoring)
  - システム状態（CPU/メモリ/ディスク）の定期記録
  - データ鮮度チェック（DuckDB の price テーブル参照）
  - 注文滞留 / 約定異常の検知とログ記録
  - Kill Switch（ファイルを書いて ExecutionEngine を停止する仕組み）
  - LINE Push による通知（AlertManager）
  - Streamlit ベースのダッシュボード表示
- ポートフォリオ構築
  - 候補選定（スコア／ランク）
  - 等ウエイト／スコア加重の重み計算
  - セクターキャップ適用、レジーム乗数
  - 単元株丸めを考慮した株数算出（リスクベース、等分配など）
- 研究・解析
  - Momentum / Volatility / Value ファクター計算（DuckDB を使用）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー
- AI 機能（OpenAI）
  - ニュース記事を銘柄ごとに集約して LLM でセンチメント評価（ai.news_nlp）
  - マクロ記事＋ETF MA 乖離で市場レジーム判定（ai.regime_detector）
  - API 呼び出しはリトライ・バックオフ・レスポンス検証を備える

セットアップ手順
----------------
1. Python 環境（推奨: 3.10 以上）を準備します。
2. 依存パッケージをインストールします（例）:
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit
   - その他プロジェクトで必要なパッケージ
   例:
   pip install duckdb psutil requests openai streamlit

   （プロジェクトに requirements.txt があればそれを使用してください。）
3. プロジェクトルートに .env を配置して環境変数を設定します（自動読み込み機能あり）。
   例 (.env):
   JQUANTS_REFRESH_TOKEN=your_jquants_token
   KABU_API_PASSWORD=your_kabu_password
   OPENAI_API_KEY=sk-...
   KABUSYS_ENV=development             # development | paper_trading | live
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   PID_FILE_PATH=data/execution.pid
   KILL_FLAG_PATH=data/kill.flag
   LOG_LEVEL=INFO
   PAPER_FILL_MODE=instant            # instant | partial | never | reject

   注意: .env の自動読み込みはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に行われます。テスト等で自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

4. データディレクトリ（data/ 等）を作成して適切な権限を与えます。

使い方（代表的なコマンド）
--------------------------
- 監視エンジンを起動（ポーリング）
  環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書きできます（デフォルト 60秒）。
  例:
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring

  備考:
  - このスクリプトはプロセス優先度を "high" に設定しようとします（psutil が必要、権限により失敗する場合あり）。
  - Monitoring は KABUSYS_ENV の値に関わらず本番 sqlite_path を使用します。

- 実行エンジンを起動（セッション実行）
  例（本番）:
  KABUSYS_ENV=live python -m kabusys.run_execution

  例（Paper Trading。ブローカーは MockBrokerClient、DB は data/paper_trading.db を使用）:
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution

  備考:
  - paper_trading 時は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に完全分離したデータを使います。
  - PID ファイルや kill.flag の扱いについては Settings の pid/kill 関連設定を参照してください。

- Streamlit ダッシュボード
  例:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

  引数 --db で監視用 SQLite DB を指定できます（デフォルト data/monitoring.db）。ダッシュボードは DB を読み取り専用で開きます。

- Paper Trading 検証レポート生成
  例:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  オプション --db で DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH でも可）。

主要な環境変数（主なもの）
--------------------------------
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（ai モジュール使用時必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant|partial|never|reject）
- PID_FILE_PATH / KILL_FLAG_PATH: PID ファイル / kill flag のパス
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）

設計上の注意点・挙動
--------------------
- Monitoring は常に本番の sqlite_path を使って監視ログを書きます（開発・paper_trading でも同じ DB を使用する設計）。これにより監視は常に稼働状況を一箇所に集約します。
- 実行エンジン（ExecutionEngine）は KABUSYS_ENV=paper_trading のときに mock ブローカーと分離 DB を使います（data/paper_trading.db）。
- OpenAI を使う ai モジュール（news_nlp, regime_detector）は API 呼び出しに対してリトライ・バックオフやレスポンスバリデーション機構を実装しています。API キーがないとエラーになります（score_regime / score_news は API キーを必須とします）。
- Process priority / CPU affinity: 起動スクリプトは最初に set_process_priority("high") を呼びます。psutil による権限不足や未サポート OS の場合は警告を出してスキップします。
- KillSwitch はデータディレクトリ（デフォルト data/kill.flag）にフラグファイルを書き込み、ExecutionEngine 側の監視により停止シグナルとして機能します。KillSwitch は冪等です（既にファイルがあれば再書き込みしません）。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py                      — パッケージ宣言、__version__ 等
- config.py                        — 環境変数／Settings 管理（.env 自動ロードを含む）
- run_monitoring.py                — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py                 — ExecutionEngine 起動スクリプト

パッケージ（主要）
- ai/
  - news_nlp.py                     — ニュース記事の LLM スコアリング（ai_scores 書込）
  - regime_detector.py              — マクロ + ETF MA に基づくレジーム判定
- monitoring/
  - monitoring_db.py                — SQLite スキーマ作成・永続化 API（MonitoringDB）
  - system_monitor.py               — システム状態・データ鮮度チェック
  - trade_monitor.py                — 注文滞留・約定異常チェック
  - risk_monitor.py                 — ドローダウン・ポジション上限監視
  - kill_switch.py                  — kill.flag 書込・評価
  - alert_manager.py                — LINE へのプッシュ通知
  - monitoring_engine.py            — 各 Monitor を束ねる実行エンジン
  - streamlit_dashboard.py          — Streamlit ダッシュボード
- execution/
  - order_manager.py                — 注文の作成・送信・同期を司る
  - reconciler.py                   — 起動時の注文・ポジション整合性確認
  - ...（broker 関連、注文リポジトリ等） 
- portfolio/
  - portfolio_builder.py            — 候補選定・スコアソート等
  - position_sizing.py              — 株数算出・aggregate cap
  - risk_adjustment.py              — セクターキャップ・レジーム乗数
- research/
  - factor_research.py              — Momentum/Value/Volatility ファクター計算
  - feature_exploration.py          — 将来リターン計算・IC・統計サマリ
- monitoring/ (前述)                — 監視関連
- tools/
  - paper_verification_report.py    — Paper Trading 用検証レポート生成スクリプト
- utils/
  - process_priority.py             — プロセス優先度 / CPU affinity ユーティリティ
- data/                             — 既定の DB ファイル配置（ローカルで作成する）

追加のドキュメント参照
---------------------
- PortfolioConstruction.md / StrategyModel.md 等（リポジトリ内にあれば参照）に実装に対する設計メモや推奨値が含まれています。
- 各モジュールの docstring に設計の重要ポイント（例: ルックアヘッド防止、JSON バリデーション、DB の冪等マイグレーション等）が記載されています。実装や挙動を変更する際は docstring を参照してください。

トラブルシューティング / 注意
-----------------------------
- DuckDB / SQLite のファイルパスは Settings により expanduser() されます。ファイルのパーミッションに注意してください。
- psutil による優先度設定や cpu_affinity は OS と権限に依存します。権限不足時はログにワーニングが出ますが処理は継続します。
- OpenAI 呼び出しはコストとレート制限が発生します。運用時は API キー管理とコール頻度に注意してください。
- monitoring_db.init_monitoring_db は冪等に設計されており、既存 DB に対する簡易マイグレーション（カラム追加等）を行いますが、重要データがある場合はバックアップを取ってから実行してください。

ライセンス・貢献
----------------
（ここにライセンス情報や貢献方法を追記してください。）

最後に
------
この README はコードベースの主要機能と実行方法を素早く理解するための要約です。より詳細な API 仕様やアルゴリズムの背景（PortfolioConstruction.md / StrategyModel.md 等）が付随している場合はそちらを参照してください。質問や改善提案があればお知らせください。