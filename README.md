# KabuSys

KabuSys は日本株の自動売買システム（モジュール群）です。本リポジトリには注文発行・リコンシリエーション・リスク監視・モニタリング・ポートフォリオ構築・研究用ファクター計算・ニュース NLP（OpenAI を用いたセンチメント評価）などの主要コンポーネントが含まれています。

この README ではプロジェクトの概要、機能一覧、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめます。

---

## プロジェクト概要

KabuSys は次のような役割を持つモジュールで構成されています。

- Execution（発注系）
  - ブローカークライアント抽象化（実ブローカー / モック切替）
  - OrderManager / ExecutionEngine / Reconciler による発注、同期、再起動後の自動復旧
  - Paper trading モード（本番 DB と分離された `data/paper_trading.db` を使用）
- Monitoring（監視系）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - 監視ログを保持する SQLite ベースの MonitoringDB
  - LINE でのアラート通知、kill.flag による ExecutionEngine 停止シグナル
  - Streamlit ダッシュボード
- Portfolio（ポートフォリオ構築）
  - 候補選定、重み計算、ポジションサイズ計算、セクター制限、レジーム乗数
- Research（研究用）
  - DuckDB を用いたファクター計算、将来リターン、IC（情報係数）計算など
- AI（ニュース NLP / レジーム判定）
  - raw_news を LLM（OpenAI）でスコアリングして ai_scores に格納
  - マクロニュース + ETF MA200 を組み合わせた市場レジーム判定
- Tools
  - Paper Trading の検証レポート生成スクリプト 等

設計上のポイント:
- DuckDB と SQLite を併用（時系列/ファクターデータは DuckDB、監視やトレードログは SQLite）
- Paper trading は実口座とデータを分離（環境変数により切替）
- LLM 呼び出しは失敗してもフェイルセーフ（スコア 0 やスキップで継続）
- .env 自動読み込み機能あり（プロジェクトルートに `.env` / `.env.local` があれば読み込む）

---

## 主な機能一覧

- 監視（Monitoring）
  - CPU / メモリ / ディスク使用率の定期ログ
  - Execution の PID 存在チェック（stale PID 検出）
  - 株価データ鮮度チェック（DuckDB の prices_daily）
  - 注文滞留（stale orders）と約定価格の異常検出
  - ドローダウン / ポジション上限の監視とリスクログ記録
  - kill.flag による ExecutionEngine 停止トリガー
  - Streamlit ダッシュボード（read-only モード推奨）
- 実行（Execution）
  - OrderManager による作成→送信→状態遷移（クラッシュ耐性を考慮した永続化手順）
  - ブローカー層の抽象化（実運用と Mock を切替可能）
  - Reconciler による起動時の注文・ポジション照合
  - RiskManager による発注制限・サーキットブレーカー等
- ポートフォリオ構築
  - シグナルに基づく候補選定、等重 / スコア重み、リスクベースの株数決定
  - セクターキャップ適用、レジーム乗数（bull/neutral/bear）
- 研究（Research）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - 将来リターン、IC、統計サマリー
- AI（OpenAI 連携）
  - ニュース記事をまとめ銘柄ごとのセンチメントを LLM で算出・格納
  - マクロニュース + ETF MA200 を元に市場レジームを LLM で判定
- ツール
  - Paper Trading 検証レポート生成（期間指定可）

---

## セットアップ手順

前提
- Python 3.10 以上（型ヒントや union 型表記を利用）
- SQLite（Python 標準ライブラリに同梱）
- 実行環境により root 権限がないとプロセス優先度変更が失敗する場合あり（警告を出して継続）

1. リポジトリをクローン
   - git clone してプロジェクトルートへ移動

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   主要な依存:
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit
   例:
   - pip install duckdb psutil requests openai streamlit

   （プロジェクトに requirements.txt がない場合は上記を個別インストールしてください）

4. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を置く（.env.example を参照して作成）
   - 自動読み込みはデフォルトで有効。無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

5. 主要な環境変数（よく使うもの）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須となる箇所あり）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
   - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
   - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
   - PAPER_TRADING_SQLITE_PATH: Paper trading 用 SQLite（デフォルト: data/paper_trading.db）
   - PID_FILE_PATH: Execution の PID ファイル（デフォルト: data/execution.pid）
   - KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
   - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト: 60）
   - PAPER_FILL_MODE: paper_trading の約定挙動（"instant" | "partial" | "never" | "reject"、default "instant"）

---

## 使い方

以下は典型的な実行例です。プロジェクトルートで実行してください。

1. 監視（MonitoringEngine）を起動
   - 監視は常に production 相当の sqlite_path（SQLITE_PATH）を使用します。
   - MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（1 秒以上）。
   - 実行:
     - python -m kabusys.run_monitoring
   - 環境変数例:
     - export MONITOR_POLL_INTERVAL=30
     - export KABUSYS_ENV=development

2. ExecutionEngine を起動（発注処理）
   - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper 用 DB（PAPER_TRADING_SQLITE_PATH）に記録されます。
   - 実行:
     - python -m kabusys.run_execution
   - Paper 例:
     - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

3. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - デフォルト DB パスは data/paper_trading.db。別 DB を使う場合は --db オプションか環境変数 PAPER_TRADING_SQLITE_PATH を指定。

4. Streamlit ダッシュボード（監視データ閲覧）
   - 起動例:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 注意: ダッシュボードは監視 DB を read-only URI で開くため、MonitoringEngine を先に起動してデータを作成しておくこと。

5. AI 機能（ニューススコア／レジーム判定）の呼び出し
   - OpenAI API キーが必要（環境変数 OPENAI_API_KEY または関数引数で指定）。
   - プログラム内で直接呼び出す例:
     - from kabusys.ai.news_nlp import score_news
     - score_news(conn, target_date, api_key=None)
   - 失敗時はフェイルセーフでスコア算出をスキップまたはゼロフォールバックします（例外は抑制する場合あり）。

6. kill.flag の操作
   - KillSwitch はドローダウン / ポジション上限等の条件で kill.flag を書き込みます（ExecutionEngine はこれを検出して安全停止する設計）。
   - kill.flag の初期化（ExecutionEngine 起動時のクリーンアップ）を有効にするため、Settings.kill_flag_clear_on_start を確認してください。

---

## 主要な実装上の注意点 / トラブルシューティング

- process 優先度変更:
  - 起動スクリプトは起動直後に set_process_priority("high") を呼びます。権限不足で失敗した場合はログに警告が出ますが処理は継続します。
- .env 自動読み込み:
  - プロジェクトルートが .git または pyproject.toml を基準に特定される場合、.env / .env.local が自動ロードされます。挙動を抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- データ分離（Paper Trading）:
  - 実行エンジンは KABUSYS_ENV=paper_trading の場合ペーパー専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使いますが、run_monitoring は常に `SQLITE_PATH`（本番相当）を参照します（設計上の意図）。
- OpenAI API:
  - API 呼び出しは Rate Limit / ネットワーク断 / 5xx に対して指数バックオフでリトライし、最終的に失敗した場合はフェイルセーフ（スコア 0.0 またはスキップ）。
  - OpenAI SDK のエラー種別に応じた扱いを実装していますが、キー未設定時は ValueError を投げる箇所があります。
- DuckDB / SQLite 接続:
  - DuckDB は大容量の時系列・ファクターデータ向け、SQL を直接投げる実装になっています。テーブルスキーマ（prices_daily / raw_financials / raw_news 等）準備が前提です。

---

## ディレクトリ構成

主要ファイル / モジュールのツリー（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数 / .env 読み込み / Settings 定義
  - run_monitoring.py                — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py                 — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py   — Paper Trading 検証レポート生成スクリプト
  - monitoring/
    - __init__.py
    - monitoring_db.py               — Monitoring DB スキーマ + MonitoringDB クラス
    - monitoring_engine.py           — MonitoringEngine（複数モニタを束ねる）
    - system_monitor.py              — システム・データ鮮度監視
    - trade_monitor.py               — 注文滞留・約定価格異常監視
    - risk_monitor.py                — ドローダウン・ポジション上限監視
    - kill_switch.py                 — kill.flag 書き込みユーティリティ
    - alert_manager.py               — LINE push 通知ラッパ
    - streamlit_dashboard.py         — Streamlit ダッシュボード
  - execution/
    - order_manager.py               — OrderManager（注文状態機械の外向け API）
    - reconciler.py                  — 起動時リコンシリエーション
    - ... (ブローカー関連、order_repository 等が存在します)
  - portfolio/
    - __init__.py
    - portfolio_builder.py           — 候補選定・重み
    - position_sizing.py             — 株数決定・スケールダウンロジック
    - risk_adjustment.py             — セクターキャップ・レジーム乗数
  - research/
    - __init__.py
    - factor_research.py             — Momentum / Volatility / Value 等の計算
    - feature_exploration.py         — 将来リターン / IC / 統計サマリ
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュース集約 → OpenAI でセンチメント評価 → ai_scores 書込
    - regime_detector.py             — ETF MA200 + マクロ NLP によるレジーム判定
  - data/
    - (データパイプライン / stats など、DuckDB 用ユーティリティが別にある想定)
  - utils/
    - __init__.py
    - process_priority.py            — プラットフォーム差分を吸収するプロセス優先度 / CPU affinity

（※上記は主要ファイルの抜粋です。実際のリポジトリにはさらに execution/broker_*、order_repository、order_record 等の実装が含まれます）

---

必要に応じて README に追記します。特に以下を教えていただければさらに詳細な手順やサンプル設定ファイル（.env.example 風）を追加できます。

- 実際に使うブローカー（kabuステーション等）の設定例
- データ（DuckDB/SQLite）初期化手順やサンプルデータの用意方法
- systemd / Supervisor 等での運用方法（サービス化）

ご希望があれば .env.example のテンプレートや systemd ユニットファイル例も作成します。