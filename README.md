# KabuSys

日本株向け自動売買システムのモジュール群です。本リポジトリは戦略（リサーチ/ファクター計算）、ポートフォリオ構築、発注実行、監視・アラート、AI（ニュースセンチメント / レジーム判定）などを含んでいます。

---

## プロジェクト概要

KabuSys は日本株自動売買を支援するための内部ライブラリ兼実行環境です。主な目的は以下です。

- DuckDB / SQLite を利用したデータ処理・永続化
- ファクター計算・特徴量探索（research）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイジング）
- 発注実行（ExecutionEngine / Broker 抽象化）
- 監視（System / Trade / Risk）とアラート（LINE）
- AI を使ったニュースセンチメント評価・市場レジーム判定
- Paper Trading 用の分離された DB と検証用ツール

---

## 機能一覧

- research
  - モメンタム / ボラティリティ / バリュー等ファクター計算（DuckDB ベース）
  - 将来リターン、IC 計算、統計サマリ
- portfolio
  - 候補選定、等配分・スコア配分、リスク調整（セクターキャップ、レジーム乗数）
  - ポジション数計算（単元丸め、リスクベース、利用可能現金によるスケール）
- execution
  - 発注マネージャ、リコンシリエーション、リスク管理、ブローカーファクトリ
  - Paper Trading 時は Mock ブローカーと専用 SQLite（data/paper_trading.db）を使用
- monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor による定期監視
  - MonitoringDB（SQLite）へのログ永続化、アラート（LINE 送信）、Kill Switch（フラグファイル）
  - Streamlit ダッシュボードによる可視化
- ai
  - news_nlp: OpenAI を使ったニュースのセンチメント集約・書込み
  - regime_detector: ETF + マクロニュースを組み合わせた日次レジーム判定
- tools
  - paper_verification_report: Paper Trading の検証レポート生成スクリプト

---

## セットアップ手順（開発環境）

以下は最小限の手順です。プロジェクトでは Python 3.10+（PEP 604 の `X | Y` 記法が使われているため）を推奨します。

1. リポジトリをクローン / ワークディレクトリに移動

2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なパッケージをインストール
   - 必須（代表的なもの）:
     - duckdb
     - psutil
     - requests
     - streamlit
     - openai
   - 例:
     - pip install duckdb psutil requests streamlit openai

   （プロジェクトに requirements.txt がある場合はそれを使ってください）

4. data ディレクトリを作成（スクリプトが期待するファイルパス）
   - mkdir -p data

5. 環境変数の設定
   - 実行に必要な環境変数は `src/kabusys/config.py` の Settings クラスで管理されています。主なもの:
     - KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（監視アラート用）
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 時の fill 挙動）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - LOG_LEVEL（デフォルト: INFO）
     - MONITOR_POLL_INTERVAL（監視ポーリング秒、デフォルト 60）

   - .env / .env.local をプロジェクトルートに置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。読み込み順は OS 環境 > .env.local > .env。

---

## 使い方

※ 以下コマンドはプロジェクトルートから実行することを想定しています（src 配下を PYTHONPATH に含める必要は通常ありません）。モジュールは `python -m kabusys.<module>` で実行できます。

1. 監視ループ起動（SystemMonitor 単独・本番 DB を監視）
   - python -m kabusys.run_monitoring
   - 環境変数でポーリング間隔を変更:
     - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
   - 監視ループは data/stop_requested.flag（プロジェクトルートの data）を検知すると終了します。

2. 実行エンジン起動（ExecutionEngine）
   - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し、記録先は PAPER_TRADING_SQLITE_PATH（default: data/paper_trading.db）になります。
   - 実行中の停止は data/stop_requested.flag を作成することで行えます。ExecutionEngine は pid ファイル（data/execution.pid）を作成します。

3. Streamlit 監視ダッシュボード
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - オプション `--db` で読み込む SQLite ファイルを指定できます。

4. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB パス指定:
     - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

5. AI 関連（ニューススコア / レジーム判定）
   - news_nlp.score_news(conn, target_date, api_key=...) — DuckDB 接続を渡して呼び出す。内部で OPENAI_API_KEY を参照します。
   - regime_detector.score_regime(conn, target_date, api_key=...) — 同様に DuckDB 接続で実行。API キー未設定時は ValueError。

6. データベース初期化
   - monitoring 用 SQLite スキーマは init_monitoring_db(conn) で作成されます。run_monitoring/run_execution 内で自動的に呼ばれます。

7. 強制停止 / Kill Switch
   - risk 条件（ドローダウン／ポジション上限）等で自動的に `data/kill.flag` が書かれると、ExecutionEngine 側で起動時やランタイムに検出して停止シグナルとして扱います。KillSwitch は冪等に flag を書きます。
   - Kill flag の手動クリアはファイル削除（または KillSwitch.clear()）で行います。

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API 用（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading DB（デフォルト data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- MONITOR_POLL_INTERVAL: 監視ポーリング秒（デフォルト 60）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定動作）

設定は .env / .env.local に記述しておくと自動読み込みされます（ただし OS 環境変数が優先）。

---

## ディレクトリ構成（要約）

src/kabusys/
- __init__.py — パッケージ情報
- config.py — 環境変数 / Settings 管理（.env 自動読み込みロジック含む）
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
- monitoring/
  - monitoring_db.py — SQLite ベースの監視ログ永続化層（スキーマ定義）
  - system_monitor.py — CPU/Mem/Disk / データ鮮度 / プロセス PID チェック
  - trade_monitor.py — 滞留注文・約定異常検査
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — kill.flag 書込ロジック
  - alert_manager.py — LINE push 通知クライアント
  - monitoring_engine.py — 複数モニタの統合ポーリング実装
  - streamlit_dashboard.py — Streamlit ダッシュボード（UI）
- execution/
  - order_manager.py — 発注ワークフローの外向き API
  - reconciler.py — 起動時のリコンシリエーション（自動復旧）
  - （その他 Broker 抽象・エンジン等は同階層）
- portfolio/
  - portfolio_builder.py — 候補選定、等/スコア配分
  - position_sizing.py — 発注株数計算、スケールダウン / 単元丸め
  - risk_adjustment.py — セクターキャップ、レジーム乗数
- research/
  - factor_research.py — モメンタム/ボラティリティ/バリュー計算（DuckDB）
  - feature_exploration.py — 将来リターン・IC・統計サマリ
- ai/
  - news_nlp.py — OpenAI を用いたニュースセンチメント集約・ai_scores 書込
  - regime_detector.py — ETF MA + マクロニュースで市場レジーム判定
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート出力
- run_monitoring.py — SystemMonitor の polling loop 起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト

（上記は主要ファイルのみを抜粋した構成です）

---

## 開発上の注意 / 補足

- Settings はプロジェクトルート（.git または pyproject.toml を探索）を自動検出し `.env` / `.env.local` を読み込みます。テストなどで自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- run_monitoring は常に「本番 sqlite_path」を使用します（環境に依らず監視 DB は同一ファイルを参照する設計）。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_trading 用 DB を使用して発注の本番 DB と分離します。
- OpenAI API 呼び出しでは冪等性・リトライ・バリデーションに配慮した実装になっていますが、API キーの漏洩・料金に注意してください。
- process_priority.set_process_priority を呼んでプロセス優先度を上げます。権限不足で失敗することがありますが、その場合は警告ログを出して継続します。
- DB マイグレーション（monitoring_db.init_monitoring_db）は簡易的に既存スキーマの列追加を行います。

---

問題や追加してほしいドキュメント（詳しい API リファレンス、設定例、運用手順など）があれば教えてください。README を拡張します。