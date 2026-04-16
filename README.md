# KabuSys

日本株向けの自動売買・調査・監視フレームワークの一部です。本リポジトリは、注文実行エンジン、監視（モニタリング）、ポートフォリオ構築、リサーチ（ファクター計算）、AI を用いたニュース解析などのコンポーネントを含みます。

以下はこのコードベースに対する簡易 README（日本語）です。

---

## プロジェクト概要

KabuSys は次を目的としたモジュール群です。

- 注文実行（ExecutionEngine）とブローカー連携
- 実行・注文のリコンシリエーション（再同期）
- 監視（System / Trade / Risk）とアラート送信（LINE）
- Paper Trading（本番 DB と分離して動作可能）
- ポートフォリオ構築（候補選定・重み付け・株数算出）
- DuckDB を使ったファクター計算・リサーチ
- OpenAI を利用したニュース NLP（センチメント）やレジーム判定
- Streamlit による監視ダッシュボード
- 検証レポート生成ツール（Paper Trading 用）

設計上、DB（SQLite / DuckDB）や環境変数で挙動を制御します。主要な SQL スキーマや DB 初期化処理は自動的に行われます（監視 DB は `init_monitoring_db` により冪等に作成／マイグレーションされます）。

---

## 主な機能一覧

- ExecutionEngine 起動スクリプト（run_execution.py）
  - `KABUSYS_ENV=paper_trading` で MockBroker を使用し、paper_trading 用 DB に記録
  - 実行中は pid ファイルを作成／監視
- Monitoring（run_monitoring.py）
  - システムリソース、データ鮮度、注文滞留、ドローダウン等の定期チェック
  - kill.flag による ExecutionEngine 停止フラグ発行ロジック（KillSwitch）
  - LINE による通知（AlertManager）
- Monitoring DB（SQLite）
  - system_status, trade_logs, positions, risk_logs, dashboard テーブルを管理
  - スキーマの簡易マイグレーションを実装
- Streamlit ダッシュボード（monitoring/streamlit_dashboard.py）
  - 監視データを可視化（Portfolio, Positions, Orders, System）
- Paper Trading 検証レポート（tools/paper_verification_report.py）
  - 稼働率、注文成功率、レイテンシ等を集計してレポート出力
- ポートフォリオ関連（portfolio/*.py）
  - 候補選定、重み付け（等重・スコア重み）、ポジションサイジング、セクター上限処理、レジーム乗数
- リサーチ（research/*.py）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC 計算、統計サマリー
- AI（ai/*.py）
  - news_nlp: OpenAI でニュースをセンチメント評価し ai_scores に書き込み
  - regime_detector: ETF MA とマクロニュースで市場レジームを判定

---

## セットアップ手順（ローカル開発向け）

前提：
- Python 3.10+（型注釈に union 型などを利用）
- Git / 任意のターミナル

1. リポジトリをクローンし、作業ディレクトリへ移動
   - 例: git clone ... && cd <repo>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - Unix/macOS: source .venv/bin/activate

3. 必要パッケージをインストール
   - 以下は代表的な依存（requirements.txt が無い場合は適宜調整してください）:
     - pip install duckdb psutil requests streamlit openai
   - 本番環境では追加のブローカークライアント等が必要になる可能性があります。

4. data ディレクトリを作成（DB やフラグファイル用）
   - mkdir -p data

5. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（OS 環境変数を保護）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 主要な環境変数（下に一覧）を .env に記載してください。

6. （任意）OpenAI を使う機能を利用する場合
   - 環境変数 `OPENAI_API_KEY` を設定するか、呼び出し時にキーを渡してください。

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: 起動環境
  - 有効値: development / paper_trading / live
  - default: development

- OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / regime_detector で必要）

- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須と想定される箇所あり）

- KABU_API_PASSWORD: kabuステーション API パスワード（必須と想定）

- DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）

- SQLITE_PATH: 監視用 SQLite（monitoring）パス（default: data/monitoring.db）

- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（default: data/paper_trading.db）

- PAPER_FILL_MODE: Paper Trading の約定挙動（instant | partial | never | reject。default: instant）

- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、default: 60）。run_monitoring で参照。

- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START など（Settings で定義）

---

## 使い方（主要スクリプト）

すべてパッケージとして実行可能です（パッケージパスは実行環境に応じて調整）。

- 監視ループを起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で変更可能（例: MONITOR_POLL_INTERVAL=30）

- 実行エンジンを起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - Paper Trading モードで起動する例:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - このモードでは専用の paper_trading DB を使用し、本番 DB と完全に分離されます。

- 強制停止 / 停止フラグ
  - 監視スクリプトや実行スクリプトはプロジェクト内の `data/stop_requested.flag` を検知して安全に停止します。
  - KillSwitch は `data/kill.flag` を書き込むことで ExecutionEngine に停止シグナルを送ります（KillSwitch のロジックにより発行されます）。`KillSwitch.clear()` を使って削除可能。

- Streamlit ダッシュボード（監視データ確認）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 先に監視エンジンを起動して `data/monitoring.db` が生成・更新されている必要があります。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数より優先）

- AI 機能（ニューススコアリング / レジーム判定）
  - kabusys.ai.score_news（内部 API）を通して呼び出します。OpenAI API キーが必要です。
  - 実行時に api_key 引数を渡すか、環境変数 OPENAI_API_KEY を設定してください。
  - エラー時のフォールバックとリトライロジックあり（429/5xx 等は指数バックオフでリトライ）。

---

## ディレクトリ構成（主要ファイルのみ）

src/kabusys/
- __init__.py — パッケージ定義
- config.py — 環境変数 / 設定読み込みロジック（.env 自動ロード、Settings クラス）
- run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト（paper_trading モード対応）

subpackages:
- ai/
  - news_nlp.py — ニュースの LLM センチメント化・ai_scores への書き込み
  - regime_detector.py — マクロ＋ETF MA を用いた市場レジーム判定
- monitoring/
  - monitoring_db.py — SQLite スキーマ管理・永続化 API（MonitoringDB）
  - system_monitor.py — システム / データ鮮度監視
  - trade_monitor.py — 注文滞留・約定異常監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag 書込みユーティリティ
  - alert_manager.py — LINE Push 通知
  - monitoring_engine.py — 複数モニタを束ねるエンジン
  - streamlit_dashboard.py — streamlit ベースの監視ダッシュボード
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数算出・スケーリング・単元丸め
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — モメンタム・ボラティリティ・バリュー算出
  - feature_exploration.py — 将来リターン・IC・統計サマリー
- execution/
  - order_manager.py — 発注 API の上位ラッパー（OrderManager）
  - reconciler.py — 起動時リコンシリエーション
  - （その他ブローカー関連・OrderRepository などが存在）
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート出力ツール
- utils/
  - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ

data/
- data/monitoring.db — 監視ログ SQLite（デフォルト）
- data/paper_trading.db — Paper Trading 用 SQLite（paper_trading 時）
- data/kabusys.duckdb — DuckDB（prices_daily 等のリサーチデータ）
- data/execution.pid — 実行エンジンの PID ファイル（起動時に作成）
- data/kill.flag, stop_requested.flag — フラグファイル

（上記はプロジェクトルートに相対する想定。Settings クラスでオーバーライド可能。）

---

## 注意事項・運用上のポイント

- Settings による `.env` 自動ロード
  - プロジェクトルート（.git または pyproject.toml の存在）を基準に `.env` / `.env.local` を読み込みます。
  - OS の環境変数は上書きされません。`.env.local` は `.env` の上書きに使えます。
  - 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

- Paper Trading
  - `KABUSYS_ENV=paper_trading` のとき、MockBrokerClient を使用し `PAPER_TRADING_SQLITE_PATH`（default: data/paper_trading.db）へ記録します。本番 DB と分離されます。
  - `PAPER_FILL_MODE` で約定挙動を制御できます（instant|partial|never|reject）。

- DB マイグレーション
  - monitoring_db.init_monitoring_db は簡易マイグレーション（カラム追加）を行います。複雑なスキーマ変更は別途対応してください。

- 権限・プラットフォーム差異
  - process_priority（psutil）で優先度変更を行いますが、権限不足や未対応 OS の場合は警告ログを出してスキップします。
  - CPU affinity 設定は OS により差異があります。エラーはログに記録されます。

- OpenAI / API 使用
  - API 呼び出しはリトライ・バックオフの実装がありますが、料金・レート制限に注意してください。
  - API レスポンスのパースやフォーマットは厳密にチェックしており、失敗時は安全にフォールバックします（例: macro_sentiment=0.0）。

- 停止制御
  - `data/stop_requested.flag` を作成すると、run_monitoring/run_execution のループは安全に終了します。
  - kill.flag は KillSwitch によって書き込まれることがあります。起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時にクリアする動作を有効化できます（Settings の設定に従う）。

---

## 例：よく使うコマンド集

- 仮想環境作成・依存インストール
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install duckdb psutil requests streamlit openai

- 監視開始
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring

- 実行エンジン開始（Paper Trading）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper 検証レポート（期間指定）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

以上がこのコードベースの概要と基本的な使い方になります。必要なら、README を補強して環境変数の完全な一覧、デプロイ手順（systemd / docker など）、CI テスト方法、より詳しい設計ドキュメントへのリンク（PortfolioConstruction.md / StrategyModel.md 等）を追記できます。どの項目を優先して追加しますか？