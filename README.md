# KabuSys

日本株向け自動売買システムの軽量コアライブラリ兼実行スクリプト群です。本リポジトリはトレード実行エンジン、監視・アラート機構、ポートフォリオ構築ユーティリティ、リサーチ用ファクター計算、AI（ニュース NLP / レジーム判定）連携などを含みます。

※ この README はソース内の docstring と実装に基づいて作成しています。

## 概要

KabuSys は以下の要素で構成される自動売買プラットフォームのコアです。

- Execution Engine: ブローカーとのやり取り、注文状態管理、リコンシリエーション
- Monitoring: システム監視、注文滞留・約定異常検知、リスク監視（ドローダウン / ポジション上限）、kill flag 発行、LINE 通知
- Portfolio construction: 候補選定・重み計算・ポジションサイズ決定・セクター制限・レジーム調整
- Research: DuckDB 上で動くファクター計算（モメンタム、ボラティリティ、バリュー）と特徴量解析ユーティリティ
- AI 連携: OpenAI を用いたニュースセンチメントスコアリング / マクロセンチメントによる市場レジーム判定
- Tools: Paper Trading 検証レポート生成、Streamlit ダッシュボード等
- 設定管理: .env 自動ロード、Settings クラスによる環境変数ラップ

設計上の特徴:
- 本番 / paper_trading を環境変数で切替可能（DB を分離）
- lookahead バイアスを避ける実装（日時の扱いに配慮）
- フェイルセーフ：API 失敗時のフォールバックや部分的失敗を許容する設計
- DuckDB / SQLite をローカル DB として利用

## 主な機能一覧

- Execution
  - 注文作成 → 送信 → 状態同期（OrderManager）
  - 起動時の Reconciler による自動復旧（OrderSent の同期、ポジション差分検出）
  - Paper trading モード（MockBrokerClient を使用し、paper DB に分離）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、プロセス生存確認、データ鮮度チェック
  - TradeMonitor: 滞留注文検出、約定価格の異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボードの更新
  - KillSwitch: kill.flag により ExecutionEngine 停止トリガー
  - AlertManager: LINE Push による通知（クールダウン管理あり）
  - Streamlit ダッシュボード（監視用 UI）
- Portfolio
  - 候補選定（スコア順、上限指定）
  - 等重・スコア加重配分
  - リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（リスクベース / 等分配 / スコアベース、単元株丸め/aggregate cap）
- Research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン・IC（情報係数）・統計サマリ
- AI
  - news_nlp.score_news: ニュース記事を OpenAI でセンチメント評価して ai_scores に保存
  - regime_detector.score_regime: ma200 + マクロセンチメントで日次レジーム判定
- Tools
  - paper_verification_report: Paper Trading DB を集計して PASS/FAIL 判定レポート出力

## 前提 / 必要パッケージ

Python 3.9+ を想定。利用する主要ライブラリ（抜粋）:

- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボードを使う場合)
- sqlite3（標準ライブラリ）

インストール例（pip）:
pip install duckdb psutil requests openai streamlit

※ 実行環境や配布方法により requirements.txt / poetry 等で管理してください。

## 環境変数・設定（主なもの）

Settings クラスにより環境変数を参照します。以下は主なキーとデフォルト値 / 備考です。

必須（未設定だと例外）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意 / デフォルトあり:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: INFO（デフォルト）
- KABU_API_BASE_URL: http://localhost:18080/kabusapi
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db (paper_trading の場合に使用)
- PAPER_FILL_MODE: instant | partial | never | reject（paper trading の約定挙動）
- PID_FILE_PATH: data/execution.pid
- KILL_FLAG_PATH: data/kill.flag
- KILL_FLAG_CLEAR_ON_START: "1" で起動時に kill.flag を削除
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

.env の自動ロード:
- プロジェクトルート（.git または pyproject.toml を探索）にある `.env` / `.env.local` を自動読み込み（OS 環境変数優先）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能

簡単な .env 例:
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
OPENAI_API_KEY=...
KABUSYS_ENV=paper_trading
PAPER_FILL_MODE=instant
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...

## セットアップ手順

1. リポジトリをクローン / チェックアウト
2. Python 仮想環境を作成してアクティベート
   python -m venv .venv
   source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール
   pip install -r requirements.txt
   もしくは個別インストール（上記参照）
4. .env をプロジェクトルートに作成（.env.example を参照）
5. デフォルト DB ディレクトリを作成
   mkdir -p data

注: monitoring 用の SQLite DB (data/monitoring.db) は実行時に init_monitoring_db() が自動作成・マイグレーションを行います。

## 使い方（Quick start / コマンド）

パッケージをパスに通す / インストール後、以下のエントリポイントを利用できます（モジュール形式で実行可能）:

- 監視ループ（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）
  - 監視は常に production 用の sqlite_path（Settings.sqlite_path）を使用します（環境にかかわらず）
  - 起動時にプロセス優先度を "high" に設定しようとします

- 実行エンジン（Execution）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い paper_trading 用の SQLite(DB) に記録します（Settings.paper_sqlite_path。既定: data/paper_trading.db）
  - 起動時にプロセス優先度を "high" に設定しようとします

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB ファイル指定:
    - --db / 環境変数 PAPER_TRADING_SQLITE_PATH で指定可能

- Streamlit ダッシュボード（監視 UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視用 SQLite DB（読み取り専用）を参照してダッシュボードを表示します

- AI 機能（コード API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB の接続（duckdb.connect(...)）を渡して使用します

起動例（paper trading）:
export KABUSYS_ENV=paper_trading
python -m kabusys.run_execution

監視起動例:
export KABUSYS_ENV=development
python -m kabusys.run_monitoring

注意:
- 実行エンジンは Settings に基づく DB パス・PID ファイル等を使用します。
- 実行中は PID ファイル（デフォルト data/execution.pid）を作成・チェックします。kill.flag（デフォルト data/kill.flag） により停止シグナルを送出できます。

## 主要ファイル / ディレクトリ構成

リポジトリ内の主要なモジュール構成（src/kabusys 配下）:

- run_monitoring.py
  - SystemMonitor のポーリングループを起動するエントリポイント
- run_execution.py
  - ExecutionEngine を組み立てて実行するエントリポイント（paper_trading モード対応）
- config.py
  - .env 自動ロード、Settings クラス（環境変数ラッパー）
- __init__.py
  - パッケージメタ情報

- ai/
  - news_nlp.py: ニュース記事の OpenAI によるセンチメントスコアリング
  - regime_detector.py: ma200 + マクロセンチメントでレジーム判定
  - __init__.py

- monitoring/
  - monitoring_db.py: SQLite テーブル定義・読み書きラッパー
  - system_monitor.py: CPU/メモリ/ディスク/プロセス/データ鮮度監視
  - trade_monitor.py: 注文滞留・約定異常の検出
  - risk_monitor.py: ドローダウン・ポジション上限監視
  - kill_switch.py: kill.flag の書き込み / 管理
  - alert_manager.py: LINE 通知用
  - monitoring_engine.py: 複数 Monitor を束ねる実行ループ
  - streamlit_dashboard.py: streamlit での監視ダッシュボード
  - __init__.py

- execution/
  - reconciler.py: 起動時の注文・ポジション照合（自動復旧）
  - order_manager.py: 注文の作成・送信・同期処理
  - （その他: broker_factory, execution_engine, order_repository 等 — 実装により別ファイルが存在）

- portfolio/
  - portfolio_builder.py: 候補選定・スコアソート
  - risk_adjustment.py: セクター上限・レジーム乗数
  - position_sizing.py: 株数算出・単元丸め・aggregate cap
  - __init__.py

- research/
  - factor_research.py: momentum / volatility / value の DuckDB ベース計算
  - feature_exploration.py: 将来リターン計算・IC・統計サマリ
  - __init__.py

- tools/
  - paper_verification_report.py: Paper Trading DB の検証レポート出力
  - __init__.py

- utils/
  - process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティ
  - __init__.py

- data/
  - （実行時に作成される DB ファイルや PID / flag などを置く既定ディレクトリ）
  - data/kabusys.duckdb  （デフォルト）
  - data/monitoring.db   （監視ログ用 SQLite）
  - data/paper_trading.db（paper_trading 用 SQLite）

## 開発上の注意点 / 運用メモ

- Paper Trading と Live は DB を分離しているため、paper_trading 実行は本番データを汚しません。
- AI（OpenAI）を利用する機能は API キーの設定が必要。API 呼び出しはリトライ・フォールバック設計になっていますが、コストやレート制限に注意してください。
- .env のパースはシェル風の表現（export 付き、クォート、コメント）にある程度対応しますが、複雑なケースは .env.example を参考にしてください。
- Monitoring のメトリクスやリスクイベントは monitoring_db に記録され、streamlit ダッシュボードから閲覧可能です。
- プロセス優先度設定は OS に依存します（psutil 経由）。権限不足などで設定が失敗することがありますがその場合は警告に留まります。
- kill.flag は冪等に書き込みを行うため既に存在する場合は上書きしません。ExecutionEngine 側で起動時にクリアする設定（KILL_FLAG_CLEAR_ON_START）があります。

## 参照 / 利用例

- 監視を手早く試す:
  - 環境変数をセットし（最低でも SQLITE_PATH 等） python -m kabusys.run_monitoring を実行
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

詳細な API 使用方法や ExecutionEngine 内部の振る舞い（ブローカー実装、order_repository のスキーマ、ExecutionEngine のセッション運用等）は各モジュールの docstring を参照してください。必要であればモジュール別の詳細ドキュメント（API リファレンス、設計ドキュメント）を追加作成できます。