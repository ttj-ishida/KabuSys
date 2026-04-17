# KabuSys

KabuSys は日本株の自動売買・リサーチ・監視を目的とした小規模なシステム群です。本リポジトリには実行エンジン、監視・アラート、ポートフォリオ構築ユーティリティ、リサーチ用ファクター計算、AI を用いたニュースセンチメント評価などのコンポーネントが含まれます。

以下はコードベース（src/kabusys）に基づく README です。

## プロジェクト概要
- 日本株の自動売買を行うための実行エンジン（ExecutionEngine）と、それを監視・保護する監視系コンポーネント群を提供します。
- DuckDB / SQLite ベースで時系列データ・監視ログを保持します。
- Paper Trading（検証用）と Live（実運用）を環境変数で切り替え可能。
- OpenAI を利用したニュースセンチメント評価や市場レジーム判定機能を備えます（API キーは環境変数で指定）。

## 主な機能一覧
- Execution
  - ExecutionEngine を使った注文発行／管理、リスク管理、リコンシリエーション（再同期）。
  - Paper Trading モードでは MockBrokerClient を使い本番 DB と分離。
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor による定期チェック（CPU・メモリ・ディスク、データ鮮度、滞留注文、約定異常、ドローダウンなど）。
  - MonitoringDB（SQLite）へのログ永続化。
  - KillSwitch（条件に応じて data/kill.flag を作成して ExecutionEngine を停止）。
  - AlertManager による LINE プッシュ通知（設定があれば）。
  - Streamlit ベースの監視ダッシュボード（読み取り専用で表示）。
- Portfolio
  - 候補選定、等金額／スコア加重配分、リスク調整（セクター上限、レジーム乗数）、株数算出（単元丸め、利用可能現金に基づくスケーリング）。
- Research
  - DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー）・将来リターン・IC 計算・統計サマリー。
- AI
  - OpenAI（gpt-4o-mini）を用いたニュースのセンチメント集計（ai_scores への書き込み）。
  - マクロニュースと ETF MA200 を合成した市場レジーム判定（market_regime 書き込み）。
- Tools
  - Paper Trading 用の検証レポート生成スクリプト（期間指定可）。

## 必要条件（概略）
- Python 3.10+（型注釈・typing / duckdb / psutil 等を使用）
- 主要ライブラリ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード利用時）
- 実行前に依存関係をインストールしてください（例）:
  - pip install duckdb psutil requests openai streamlit

※ 実際のプロジェクトでは requirements.txt / poetry 等で依存管理してください。

## セットアップ手順
1. リポジトリをクローンし、Python 仮想環境を作成する:
   - git clone <repo>
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール:
   - pip install duckdb psutil requests openai streamlit

3. データディレクトリを作成:
   - mkdir -p data

4. 環境変数の設定:
   - ルートに `.env` / `.env.local` を置くと自動ロードされます（OS 環境変数が優先）。
   - 自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

5. 必須環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン（必須）
   - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
   - OPENAI_API_KEY — OpenAI を使う機能を利用する場合（news/regime）
   - KABUSYS_ENV — 実行環境: `development` | `paper_trading` | `live`（デフォルト: development）
   - その他（任意・デフォルトあり）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB, デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 時の専用 SQLite、デフォルト: data/paper_trading.db）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（監視アラート送信）
     - PAPER_FILL_MODE（paper_trading の約定動作: instant|partial|never|reject、デフォルト: instant）
     - MONITOR_POLL_INTERVAL（監視ループの秒間隔、デフォルト: 60）

## 主要ファイルと起動方法（使い方）
- 実行エンジン（ExecutionEngine）を起動:
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、専用の paper DB（PAPER_TRADING_SQLITE_PATH）を使用し、MockBrokerClient が使われます。本番 DB と分離されます。
    - 起動時に data/stop_requested.flag が存在する場合は起動を中止します。
    - 実行中は data/execution.pid に PID を書き込み、停止時に削除します。
    - 停止は data/stop_requested.flag を作成することで行えます（監視スクリプト・外部ツールから停止可能）。

- 監視ループを起動:
  - python -m kabusys.run_monitoring
  - オプション:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
    - 監視は MonitoringDB（settings.sqlite_path）に永続化されます。Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視は常に一意の DB にログを残す設計）。
    - 停止は data/stop_requested.flag の作成で行います。

- Streamlit ダッシュボード（監視 UI）:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは監視 DB を読み取り専用で開きます（存在しない場合はエラー表示）。

- Paper Trading 検証レポート生成:
  - python -m kabusys.tools.paper_verification_report
  - 日付範囲を指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH が優先されます）

- AI モジュール（プログラムから呼び出す）
  - ニューススコア付け:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key=None)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=None)
  - OpenAI API キーは引数に渡すか環境変数 OPENAI_API_KEY を設定します。未設定時は ValueError が発生します。

- 停止・強制停止
  - ExecutionEngine 停止シグナル: Monitoring 側の KillSwitch が条件を満たすと data/kill.flag を作成します。KillSwitch は ExecutionEngine に停止要請を送るためのフラグです。
  - run_execution/run_monitoring の停止: data/stop_requested.flag の作成で優雅に停止します。

## 設定の自動読み込みについて
- ルート配下の `.env` と `.env.local` が自動的に読み込まれます（OS 環境変数が優先）。
- 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- .env のパーシングはシェル風の簡易対応（export プレフィックス、シングル/ダブルクォート、インラインコメント等）を行います。

## 監視 DB（MonitoringDB）
- SQLite を用いて以下のテーブルを管理します（init_monitoring_db にて自動作成／マイグレーション）:
  - system_status, trade_logs, positions, risk_logs, dashboard
- MonitoringDB クラスは永続化用の CRUD を提供します（log_system_status / log_trade_event / upsert_dashboard 等）。

## 注意点・運用メモ
- Paper Trading の DB は本番 DB と分離されます（settings.is_paper による切替）。
- Monitoring は KABUSYS_ENV に依存せず常に本番の monitoring DB（settings.sqlite_path）を使用する設計です。
- OpenAI 呼び出しは外部 API 依存であるため、API 呼び出し失敗時にはフェイルセーフ（スコア=0 やスキップ）となるよう設計されていますが、API 使用量・レート制限には注意してください。
- AlertManager（LINE）はチャンネルアクセストークン／ユーザID が未設定の場合は送信をスキップします。クールダウン管理あり。
- プロセス優先度設定は os/psutil の権限に依存します。権限不足時は警告を出してスキップします。

## ディレクトリ構成（src/kabusys）
（代表的なファイル＆簡単な説明）

- kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数・Settings 管理、.env 自動読み込み
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - monitoring/
    - monitoring_db.py — SQLite モデル + MonitoringDB
    - system_monitor.py — CPU/メモリ/ディスク/プロセス/データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン／ポジション上限監視
    - kill_switch.py — kill.flag 制御
    - alert_manager.py — LINE 通知
    - monitoring_engine.py — 監視コンポーネント束ねるエンジン
    - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
  - execution/
    - order_manager.py — 発注ロジックの外向き API
    - order_repository.py — SQLite を使った注文永続化（ファイル内に存在）
    - reconciler.py — 起動時の自動復旧（ブローカーとの再同期）
    - ...（ブローカー抽象化など）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・スケーリング
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — ファクター計算 (momentum/value/volatility)
    - feature_exploration.py — 将来リターン/IC/統計解析
  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI）処理
    - regime_detector.py — 市場レジーム判定（ma200 + マクロセンチメント）
  - data/ (ローカル実行時に使用される想定ディレクトリ)
    - monitoring.db (デフォルト)
    - kabusys.duckdb (デフォルト)
    - paper_trading.db (paper_trading 用デフォルト)
    - execution.pid / kill.flag / stop_requested.flag などのフラグ類

## よく使うコマンドまとめ（例）
- 実行エンジン起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - KABUSYS_ENV=live python -m kabusys.run_execution
- 監視起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- AI スコア付け（スクリプト呼び出し例）:
  - python -c "from kabusys.ai.news_nlp import score_news; import duckdb, datetime; conn=duckdb.connect('data/kabusys.duckdb'); print(score_news(conn, datetime.date(2026,4,1)))"

---

README はここまでです。さらに詳しい運用手順（デプロイ、systemd ユニット、監視ルールのチューニングなど）は運用環境に合わせて追加してください。必要であれば、README に含めるデプロイ例や systemd ユニットのテンプレートも作成します。