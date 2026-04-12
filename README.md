# KabuSys

日本株向け自動売買システムのコードベース（抜粋）。本リポジトリはトレード実行、監視、ポートフォリオ構築、リサーチ、AI を用いたニュース評価などのコンポーネントを含みます。

なお本 README は提供されたソース群（src/kabusys 以下）をもとに作成しています。

---

## プロジェクト概要

KabuSys は日本株の自動売買を目的としたモジュール群です。特徴は以下の通りです。

- ExecutionEngine：ブローカーと連携して注文を発行・管理するランタイム
- Monitoring：システム稼働状態や注文の異常を監視しログ／アラートを生成
- Portfolio Construction：銘柄選定、重み付け、株数決定、リスク調整
- Research：ファクター計算・特徴量解析（DuckDB を用いて履歴データを解析）
- AI（ニュース NLP / レジーム判定）：OpenAI を用いたニュースのセンチメント評価・市場レジーム判定
- Tools：Paper Trading の検証レポート生成や Streamlit ダッシュボード等

設計上の留意点：
- 環境変数・.env による設定管理（自動ロード機構あり）
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と分離される（data/paper_trading.db を使用）
- DuckDB はリサーチ用の履歴 DB、SQLite は監視／注文ログ等に使用

---

## 主な機能一覧

- 実行関連
  - 起動スクリプト: run_execution.py（ExecutionEngine 起動）
  - 再起動後のリコンシリエーション（Reconciler）
  - OrderManager / OrderRepository による注文のライフサイクル管理
- 監視関連
  - SystemMonitor：CPU/メモリ/ディスク、プロセス生存、データ鮮度監視
  - TradeMonitor：滞留注文・約定異常価格検出
  - RiskMonitor：ドローダウン・ポジション上限監視とリスクログ記録
  - KillSwitch：条件に応じて kill.flag を書いて ExecutionEngine 停止を指示
  - AlertManager：LINE Push を使った通知（アクセストークンが必要）
  - Streamlit ダッシュボード（監視データ可視化）
- ポートフォリオ構築
  - 候補選定 / 等配分・スコア配分 / リスク調整（セクターキャップ、レジーム係数）
  - 株数決定（単元丸め、利用可能現金に対するスケーリング）
- リサーチ
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 接続を受け取る純粋関数）
  - 将来リターン計算、IC（スピアマン）計算、ファクター統計サマリ
- AI（OpenAI）
  - news_nlp.score_news: ニュースを LLM でスコア化し ai_scores テーブルへ書き込み
  - regime_detector.score_regime: ETF MA 乖離 + マクロニュースセンチメントで日次レジーム判定
- ツール
  - paper_verification_report: Paper Trading DB を解析して検証レポートを出力
  - streamlit_dashboard: 監視 DB を可視化する Streamlit アプリ

---

## 要件（推奨）

- Python 3.10+
- 必要な主なパッケージ（例）:
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit
- SQLite（組み込み）
- ネットワークアクセス（LINE / OpenAI を利用する場合）

（実際の requirements.txt はプロジェクトに合わせて用意してください）

---

## セットアップ手順（ローカル）

1. リポジトリをクローンし、作業ディレクトリに移動
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb psutil openai requests streamlit
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）
4. 環境変数設定
   - プロジェクトルートに .env を置くと自動で読み込まれる（.env.local は優先）
   - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定する
5. 初期 DB（モニタリング用など）は各スクリプト起動時に自動作成・マイグレーションされます（init_monitoring_db を呼ぶ）

---

## 環境変数（主なもの）

以下はソースから抽出した主な環境変数と説明 / デフォルト値。

- 一般
  - KABUSYS_ENV: 起動環境（development / paper_trading / live）。デフォルト: development
  - LOG_LEVEL: ログレベル（DEBUG/INFO/...）。デフォルト: INFO

- API / トークン
  - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
  - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
  - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
  - OPENAI_API_KEY: OpenAI API キー（AI 関連機能で使用）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（未設定時は送信しない）

- データパス
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）

- Paper Trading 制御
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）

- 監視系
  - PID_FILE_PATH: ExecutionEngine 用 PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を削除する場合 1 を設定
  - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: アラート閾値（%）

- 監視ループ間隔
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）。0 や負の値は無効としてデフォルトにフォールバック。

---

## 使い方（起動例）

- 実行エンジン（ExecutionEngine）を起動
  - KABUSYS_ENV を設定してから実行します（paper_trading の場合は MockBroker が使われ、paper DB を使用）
  - 例（本番想定）:
    - export KABUSYS_ENV=live
    - python -m kabusys.run_execution
  - 例（ペーパートレード）:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution

- 監視ループを起動
  - MONITOR_POLL_INTERVAL で間隔を指定可能（秒）
  - 例:
    - export MONITOR_POLL_INTERVAL=120
    - python -m kabusys.run_monitoring

- Streamlit ダッシュボード（監視データを可視化）
  - 起動コマンド:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 引数 --db で DB パスを指定できます（デフォルト data/monitoring.db）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間を指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI（ニューススコア / レジーム判定）
  - OpenAI API キーが必要（OPENAI_API_KEY または関数引数で指定）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは通常バッチ的に日次で呼び出します（外部スケジューラや実行フローから）

---

## Paper Trading の挙動

- KABUSYS_ENV=paper_trading の場合、ExecutionEngine は MockBrokerClient（実ブローカーを叩かない）を使用し、取引ログ等は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます。これにより実口座と完全分離して検証可能です。

---

## 注意点 / 運用メモ

- Settings モジュールはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して .env / .env.local を自動でロードします。自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_monitoring は KABUSYS_ENV に関係なく本番 sqlite_path（SQLITE_PATH）を使用して監視ログを記録します（監視は本番 DB を参照する前提）。
- PID ファイルや kill.flag による外部制御を実装しています。kill.flag は KillSwitch により作成され、ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START を使ってクリアするオプションがあります。
- OpenAI を利用するモジュールはネットワーク・API の失敗に対してバックオフ・フォールバックを行う設計ですが、API キーの設定漏れは例外になることがあります。必ず OPENAI_API_KEY を設定してください（該当関数は None を渡すと環境変数を参照します）。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py — パッケージ定義、バージョン
- config.py — 環境変数読み込み・Settings クラス（.env 自動ロード等）
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト

src/kabusys/monitoring/
- monitoring_db.py — SQLite を使った監視ログ永続化層（テーブル作成・読み書き）
- system_monitor.py — システム状態・データ鮮度監視
- trade_monitor.py — 注文滞留・約定異常監視
- risk_monitor.py — ドローダウン・ポジション上限監視
- kill_switch.py — kill.flag 管理
- alert_manager.py — LINE プッシュ通知ラッパ
- monitoring_engine.py — 各モニターを束ねるエンジン
- streamlit_dashboard.py — Streamlit ベースの簡易ダッシュボード

src/kabusys/execution/
- order_manager.py — 注文ステートマシンの外向き API
- reconciler.py — 再起動時のリコンシリエーション（注文・ポジション整合）
- （その他ブローカー関連、OrderRepository などが存在）

src/kabusys/portfolio/
- portfolio_builder.py — 候補選定・重み計算
- position_sizing.py — 株数計算・投資上限処理
- risk_adjustment.py — セクター上限・レジーム乗数

src/kabusys/research/
- factor_research.py — Momentum/Volatility/Value 等のファクター計算（DuckDB）
- feature_exploration.py — 将来リターン、IC、統計サマリ

src/kabusys/ai/
- news_nlp.py — ニュースを LLM に渡して銘柄別スコア生成
- regime_detector.py — ETF MA + マクロセンチメントによるレジーム判定

src/kabusys/tools/
- paper_verification_report.py — Paper Trading 検証レポート生成スクリプト

src/kabusys/utils/
- process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

（上記は提供ソース内の主要ファイルの抜粋です。実際のリポジトリではさらに多くのモジュールが存在する可能性があります）

---

## 参考コマンドまとめ

- 実行エンジン（デフォルト実行）
  - python -m kabusys.run_execution
- 監視ループ起動
  - python -m kabusys.run_monitoring
- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要であれば README に記載する具体的な .env.example（鍵名と例）や requirements.txt のテンプレート、運用手順（systemd ユニットや Supervisor の例）、FAQ（トラブルシューティング）なども追加できます。どの情報を優先して追記しますか？