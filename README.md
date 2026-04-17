# KabuSys

日本株自動売買システムのリポジトリ（ミニマルなコア実装）。  
この README はコードベースから抽出した仕様・使い方を日本語でまとめたものです。

注意: ソースは src/kabusys 配下にあり、実行時はプロジェクトルートから PYTHONPATH=src を指定して実行するか、パッケージとしてモジュール実行してください。

## プロジェクト概要
KabuSys は以下の主要コンポーネントで構成された自動売買フレームワークです。

- ExecutionEngine（発注・注文管理・リスク管理・リコンシリエーション）
- Monitoring（プロセス状態・データ鮮度・注文滞留・リスクの監視、アラート送信）
- Portfolio（候補選定、重み計算、ポジションサイズ計算、セクター制限）
- Research（ファクター計算・特徴量探索）
- AI モジュール（ニュースセンチメントスコアリング、レジーム判定） — OpenAI を利用
- 各種ユーティリティ（プロセス優先度、Streamlit ダッシュボード、検証レポート等）

設計方針の要点：
- DuckDB（時系列・研究データ）と SQLite（監視ログ / 発注ログ）を併用
- Paper Trading 環境と本番環境を明確に分離（データベースやブローカーが別）
- LLM（OpenAI）呼び出しは冪等性やリトライを考慮して実装

## 主な機能一覧
- SystemMonitor: CPU/メモリ/ディスク、Execution プロセスの生存、データ鮮度をチェック
- TradeMonitor: 滞留注文（stale）や約定価格の異常を検知
- RiskMonitor: ドローダウン・ポジション上限を監視・アラート／kill flag 発行
- KillSwitch / AlertManager: 条件に達したら kill flag を書き出し（Execution 停止）、LINE への通知機能
- MonitoringEngine: 上記モニタ群を定期実行するポーリングループ
- ExecutionEngine 起動スクリプト（paper/live 切替対応）と Reconciler（再起動後の自動同期）
- Portfolio モジュール: 候補選定（select_candidates）、重み（equal/score）、ポジションサイズ計算（risk_based 等）、セクターキャップ、レジーム乗数
- Research モジュール: momentum/volatility/value ファクター計算、将来リターン、IC の算出
- AI モジュール:
  - news_nlp.score_news: raw_news をまとめて OpenAI に送り銘柄ごとのセンチメントを ai_scores に保存
  - regime_detector.score_regime: ETF 指標 + マクロニュースを LLM で評価して market_regime に書き込む
- Streamlit ダッシュボード（監視データの可視化）
- tools.paper_verification_report: Paper Trading データの検証レポート生成

## セットアップ手順（開発環境）
最低限の前提：
- Python 3.10 以上（注: | タイプなどを利用しているため）
- プロジェクトルートに `src/` があり、パッケージは `src/kabusys` に配置されています。

1. リポジトリをクローンしプロジェクトルートへ移動
2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（代表的な依存）
   - pip install duckdb psutil requests streamlit openai
   - SQLite は標準ライブラリに含まれます
   - （プロジェクトに requirements.txt がある場合はそれを使ってください）

4. 環境変数の設定
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（OS 環境変数が優先）。
   - 自動読み込みを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

必須/推奨環境変数（抜粋）:
- JQUANTS_REFRESH_TOKEN — J-Quants 用トークン（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
- OPENAI_API_KEY — OpenAI を使う機能を使う場合に必須
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト development）
- PAPER_FILL_MODE — paper_trading の約定モード: instant | partial | never | reject（デフォルト instant）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- SQLITE_PATH — 監視ログ用 SQLite（デフォルト data/monitoring.db）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用（無ければ送信スキップ）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）

## 実行方法（代表例）

前提: プロジェクトルートから実行。ソースが src/ 下にあるので PYTHONPATH=src を指定する方法を例示します。

- Monitoring（監視ループ）を起動
  - MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可（秒）
  - コマンド:
    - PYTHONPATH=src python -m kabusys.run_monitoring
    - または: python src/kabusys/run_monitoring.py（実行環境に応じて）

  特記事項:
  - Monitoring は KABUSYS_ENV に依らず本番用 sqlite_path（settings.sqlite_path）を使います。
  - 停止は data/stop_requested.flag を作成するとループを終了します。

- ExecutionEngine（発注エンジン）を起動
  - KABUSYS_ENV=paper_trading とすると MockBrokerClient が使われ、DB は data/paper_trading.db に保存され本番 DB と分離されます。
  - コマンド:
    - PYTHONPATH=src python -m kabusys.run_execution
    - または: python src/kabusys/run_execution.py
  - 停止は data/stop_requested.flag を作成すると検出してエンジン停止処理を行います。
  - 起動時に data/kill.flag がある場合は起動を中止します（kill flag により停止が要求された状態）。

- Streamlit ダッシュボード（監視 UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ローカルにある monitoring.db を読み取り専用で接続して表示します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD  （開始日）
    - --to   YYYY-MM-DD  （終了日）
    - --db PATH          （SQLite DB パス。環境変数 PAPER_TRADING_SQLITE_PATH を優先）

- AI 関連（ニューススコア / レジーム判定）
  - news_nlp.score_news(conn, target_date, api_key=None) — OPENAI_API_KEY が必要
  - regime_detector.score_regime(conn, target_date, api_key=None) — OPENAI_API_KEY が必要
  - OpenAI API 呼び出しは gpt-4o-mini を利用する想定で実装されています。API Key を環境変数 OPENAI_API_KEY に設定してください。

## 主な挙動・注意点
- .env の自動ロード:
  - プロジェクトルート（.git または pyproject.toml を基準）を自動検出して .env/.env.local を読み込みます。
  - OS の環境変数は保護され、.env.local の override は可能ですが OS 環境変数は上書きされません。
- KABUSYS_ENV の値:
  - development / paper_trading / live のいずれか。無効な値は例外になります。
  - paper_trading では paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、Mock ブローカーで振る舞いを分離します。
- 停止方法:
  - data/stop_requested.flag を作成することで run_* スクリプトのポーリングループが終了します（監視・実行双方で利用）。
  - KillSwitch は条件に達した場合 data/kill.flag を書き込み、ExecutionEngine 停止を誘発します。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等でテーブル作成を行い、既存テーブルにカラムがない場合は ALTER で追加する簡易マイグレーションを持ちます。
- OpenAI 呼び出し:
  - 429・ネットワーク断・タイムアウト・5xx は指数バックオフでリトライする実装（上限あり）。
  - レスポンスのバリデーションやクリップ（スコア ±1.0）を行います。
- プロセス優先度:
  - 起動時に set_process_priority("high") が呼ばれます。psutil を利用して OS に合った優先度設定を行いますが、失敗した場合は警告を出してスキップします。

## ディレクトリ構成（抜粋）
以下はソース配下の主要ファイル・モジュール構成（src/kabusys 以下）。

- kabusys/
  - __init__.py
  - config.py                — 設定 / .env 読み込み / Settings
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント（OpenAI 連携）
    - regime_detector.py     — 市場レジーム判定（ETF + マクロ + LLM）
  - monitoring/
    - __init__.py
    - monitoring_db.py       — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
    - streamlit_dashboard.py
  - execution/
    - reconciler.py
    - order_manager.py
    - (その他：broker_factory, execution_engine, order_repository など)
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - tools/
    - __init__.py
    - paper_verification_report.py
  - utils/
    - __init__.py
    - process_priority.py

（実際のファイル一覧はリポジトリを参照してください）

## 開発時のヒント
- テストやデバッグで環境変数自動読み込みを抑えたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- パッケージ実行時の作業ディレクトリに依存しないように config._find_project_root() は __file__ を起点にプロジェクトルートを探索します。
- DuckDB を使う研究系関数は接続オブジェクトを受け取り SQL を用いて処理するため、単体テストがしやすい設計です（副作用を最小化）。

---

必要に応じて README に追記します（例: requirements.txt の正確な内容、起動スクリプトの追加オプション、CI/CD 手順など）。どの情報を詳細化したいか教えてください。