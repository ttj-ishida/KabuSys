# KabuSys — 日本株自動売買システム

このリポジトリは日本株自動売買システム「KabuSys」のコアライブラリです。戦略の研究・ファクター計算、ポートフォリオ構築、発注エンジン、監視・アラート、Paper Trading 検証ツール、LLM を使ったニュース NLP 等を含みます。

---

## プロジェクト概要
- 目的: 日本株の自動売買に必要なコア機能群（リサーチ → シグナル → 発注 → 監視）を提供する。
- 設計方針:
  - DuckDB / SQLite を使ったローカルデータ処理（外部 API によるデータ取得は分離）
  - AI（OpenAI）呼び出しは明示的に API キーを渡すか環境変数を設定して使用
  - テストしやすい純粋関数（ファクター計算やポートフォリオ構築）と、永続化層（SQLite）を分離
  - Paper Trading を本番 DB と分離して安全に検証可能

---

## 主な機能一覧
- execution（発注関連）
  - OrderManager / ExecutionEngine / Reconciler：発注状態管理・再同期ロジック
  - Broker クライアントを抽象化し、paper_trading モード時は MockBroker を使用
- monitoring（監視）
  - SystemMonitor, TradeMonitor, RiskMonitor：CPU・メモリ・ディスク、データ鮮度、滞留注文、約定異常、ドローダウンなどを監視
  - MonitoringDB：監視ログを SQLite に永続化
  - AlertManager：LINE API へ通知（クールダウン管理）
  - KillSwitch：条件成立時にフラグファイルを生成して ExecutionEngine を停止
  - Streamlit ダッシュボード（リアルタイム参照用）
- research（リサーチ）
  - ファクター計算（Momentum / Volatility / Value）や将来リターン計算、IC 計算、統計サマリー
- portfolio（ポートフォリオ構築）
  - 候補選定、等配分／スコア加重、リスク調整（セクター上限、レジーム乗数）、株数（単元）計算
- ai（LLM を使った機能）
  - news_nlp.score_news(): ニュース記事を集約して OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを算出し ai_scores に保存
  - regime_detector.score_regime(): ETF の MA 乖離とマクロニュースを統合して市場レジーム（bull/neutral/bear）を判定
- tools
  - paper_verification_report: Paper Trading の検証レポートを生成（稼働率・注文成功率・レイテンシ等）

---

## セットアップ手順（ローカル実行用）
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo>

2. Python 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必要なパッケージ（例）:
     - duckdb, psutil, openai, requests, streamlit
   - インストール例:
     - pip install duckdb psutil openai requests streamlit
   - （プロジェクトに requirements.txt がある場合はそれを利用してください）

4. データディレクトリ作成
   - デフォルトの SQLite / DuckDB ファイルは `data/` に配置されます（自動作成はされますが、権限等に注意してください）。
   - 例:
     - mkdir -p data

5. 環境変数の設定（最低限）
   - KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
   - OPENAI_API_KEY: AI 機能を使う場合は必須
   - その他（Settings クラス参照、主なものを下記にまとめます）
   - 自動で `.env` / `.env.local` をロードします（プロジェクトルートに .env があれば自動読み込み）。
     - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

6. 主要な環境変数（抜粋）
   - JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須となる機能あり）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須となる機能あり）
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - OPENAI_API_KEY: OpenAI API キー（ai モジュールで必須）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE通知）を使う場合
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
   - KILL_FLAG_PATH: kill flag（デフォルト: data/kill.flag）
   - PAPER_FILL_MODE: Paper Trading の約定モード（instant|partial|never|reject、デフォルト: instant）
   - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）

---

## 使い方（主なコマンド）
- ExecutionEngine（発注エンジン）起動
  - 開発 / 本番モードは KABUSYS_ENV によって切り替わります。
  - 実行:
    - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用して PAPER_TRADING_SQLITE_PATH に書き込みます（本番 DB と分離）。

- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - 監視は常に本番用の sqlite_path を使用します（Settings に従う）。

- Streamlit ダッシュボード（監視確認）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - オプションで --db を指定して読み込む DB を切替可能（read-only モード推奨）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で別の DB パスを指定可能（デフォルトは env または data/paper_trading.db）

- AI 関連（プログラムから呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None) — OpenAI キーを渡すか環境変数 OPENAI_API_KEY を設定
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## 動作上の注意・トラブルシューティング
- 権限
  - set_process_priority() は OS と権限に依存します。権限不足時は警告ログが出ますが処理は継続します。
- DB マイグレーション
  - init_monitoring_db(conn) は冪等でテーブルといくつかのカラム追加（マイグレーション）を行います。起動時に自動で実行されます。
- Paper Trading と本番 DB の分離
  - KABUSYS_ENV=paper_trading の場合、専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用します。実運用時は誤って paper_trading モードにしないよう注意してください。
- OpenAI 関連
  - OPENAI_API_KEY が未設定だと AI 機能は例外を投げます（score_news / score_regime など）。テスト用に外部呼び出しをモックする設計になっています。
- LINE 通知
  - トークンや user_id が未設定の場合、AlertManager は送信をスキップしてログに残します。
- 環境変数の自動ロード
  - プロジェクトルートに .env / .env.local があれば自動で読み込まれます（OS 環境変数優先）。自動読み込みを禁止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイルの概観）
- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数／設定管理（.env 読み込みロジック、Settings クラス）
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - ai/
    - news_nlp.py — ニュース記事を OpenAI でスコアリングして ai_scores に書き込む
    - regime_detector.py — 市場レジーム判定（ETF MA + マクロニュース）
  - monitoring/
    - monitoring_db.py — SQLite 永続化層（テーブル作成／CRUD）
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py — 注文滞留／約定価格異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — フラグファイルによる停止シグナル生成
    - alert_manager.py — LINE 通知ラッパー
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
  - research/
    - factor_research.py — Momentum / Volatility / Value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリー等
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数計算（単元丸め、リスクベース、aggregate cap）
    - risk_adjustment.py — セクター上限、レジーム乗数
  - execution/
    - order_manager.py — OrderStateMachine の外向き API
    - reconciler.py — 起動時の注文／ポジションの再同期ロジック
    - (その他 broker_factory, order_repository 等が存在)
  - utils/
    - process_priority.py — プロセス優先度・CPU affinity ユーティリティ

（上記は主要モジュールの抜粋です。実際のファイルは更に細分化されています）

---

## 開発メモ / ドキュメント参照
- StrategyModel.md / PortfolioConstruction.md 等、設計ドキュメントに準拠した実装が散見されます（リポジトリ内に存在する場合は参照してください）。
- テスト: 各モジュールは可能な限り純粋関数で実装され、外部依存は注入可能です（例: DB 接続や OpenAI 呼び出しをモックしてテスト可能）。

---

必要であれば、README に含めるコマンド例（systemd ユニット、Dockerfile、requirements.txt の推奨内容）、あるいは各モジュールの API リファレンス（関数引数・戻り値の詳細）を追記します。どの情報を優先して追加しますか？