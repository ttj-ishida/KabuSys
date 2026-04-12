# KabuSys

日本株自動売買フレームワーク（ライブラリ寄り）。戦略の研究・ファクター計算、ポートフォリオ構築、発注（ExecutionEngine）と監視（Monitoring）を含むモジュール群を提供します。

### 目的
- DuckDB / SQLite をデータ層に使い、アルゴリズム取引の研究・検証・実運用を分離して行えること
- Paper trading モードで本番 DB と完全分離して安全に検証できること
- 監視用の永続化・アラート・Kill Switch 機構を備え、実稼働監視を支援すること
- ニュースの自然言語処理（OpenAI）を使ったセンチメント評価・レジーム判定機能を持つこと

---

## 主な機能一覧

- execution（発注周り）
  - OrderManager / ExecutionEngine / Reconciler：発注状態管理・起動時の同期処理
  - BrokerClientFactory：環境に応じたブローカークライアント（本番 / mock）
  - リスク管理（RiskManager）や order_repository（SQLite）連携

- monitoring（監視）
  - SystemMonitor：CPU/メモリ/ディスク、プロセス存在、データ鮮度監視
  - TradeMonitor：滞留注文・約定価格異常検出
  - RiskMonitor：ドローダウン・ポジション上限監視
  - KillSwitch：条件に応じて flag ファイルを書いて ExecutionEngine 停止指示
  - AlertManager：LINE Push による通知（クールダウン管理）
  - MonitoringDB：SQLite スキーマの初期化と読み書きユーティリティ
  - Streamlit ダッシュボード（読み取り専用で監視 DB を可視化）

- portfolio（ポートフォリオ構築）
  - 候補選定（select_candidates）、等ウェイト／スコア加重計算
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ決定（単元丸め・aggregate cap）

- research（研究支援）
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算、IC 計算、統計サマリー

- ai（LLM 連携）
  - news_nlp.score_news：OpenAI（gpt-4o-mini 等）でニュースを銘柄ごとにセンチメント採点し ai_scores に書き込む
  - regime_detector.score_regime：ETF MA とマクロニュースセンチメントを合成して market_regime に記録

- tools
  - paper_verification_report：Paper trading DB を集計して検証レポートを標準出力に出す

---

## 前提 / 必須環境

- Python 3.10+（typing の | 形式等を使用）
- システムライブラリ：
  - sqlite3（標準）
- Python パッケージ（代表例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (監視ダッシュボード利用時)
- （任意）LINE 通知を利用する場合はインターネット接続と LINE チャネル設定

---

## セットアップ手順

1. リポジトリをクローン／配置
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - （テストや開発用に追加パッケージがあれば個別にインストールしてください）
4. 環境変数の準備
   - プロジェクトルートに .env / .env.local を置く（自動読み込みあり）
   - 自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

推奨する最低限の .env（例）:
JQUANTS_REFRESH_TOKEN=
KABU_API_PASSWORD=
OPENAI_API_KEY=
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
PID_FILE_PATH=data/execution.pid
KILL_FLAG_PATH=data/kill.flag
LOG_LEVEL=INFO

注意: 必須のキー（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は Settings クラスで require されるため、実行するコンポーネントによっては未設定だと例外になります。

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: development | paper_trading | live
  - paper_trading の場合、MockBrokerClient を使い PAPER_TRADING_SQLITE_PATH に記録（本番 DB と分離）
- OPENAI_API_KEY: OpenAI API キー（ai モジュール使用時必須）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン
- KABU_API_PASSWORD / KABU_API_BASE_URL: kabuステーション API 設定
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper trading 用 SQLite（デフォルト data/paper_trading.db）
- PID_FILE_PATH / KILL_FLAG_PATH: 実行プロセス PID / Kill flag ファイルパス
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading のフィルモード（instant|partial|never|reject）
- LOG_LEVEL: ログレベル（DEBUG, INFO, ...）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE通知）用

---

## 使い方（主要スクリプト）

- ExecutionEngine 起動（本番 or paper_trading を Settings.env で切替）
  - python -m kabusys.run_execution
  - 注意: 起動前に env を正しく設定（KABUSYS_ENV, DB パス, ブローカ設定 等）

- Monitoring（SystemMonitor のポーリングループ）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数で間隔を変更可能（0以下は無効でデフォルト 60 秒）
  - 監視は常に本番 sqlite_path を参照（Monitoring は KABUSYS_ENV に依存せず本番 DB を使用）

- Streamlit ダッシュボード（監視 DB の可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH より優先）

- AI 系関数（コードから呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続と target_date を渡して ai_scores に書き込む
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - market_regime テーブルへ書き込み

- モジュール的利用
  - portfolio.select_candidates / calc_equal_weights / calc_score_weights
  - portfolio.calc_position_sizes
  - research.calc_momentum / calc_volatility / calc_value
  - research.calc_forward_returns / calc_ic / factor_summary

---

## 実行時の注意点 / 運用メモ

- Paper trading モードは DB を data/paper_trading.db（デフォルト）に分離して記録するため、本番データを汚染しません。
- OpenAI を使う機能は API キーが無いと ValueError を投げます。運用では API のレート制限やエラーに備えリトライロジックが盛り込まれていますが、コストとレート制御は運用側で管理してください。
- set_process_priority を起動直後に呼びプロセス優先度を上げようとします。Linux や macOS では nice 値により制御、Windows ではプロセスクラスを設定します。権限不足で Warning が出る場合があります（問題ない）。
- MonitoringDB.init_monitoring_db は冪等でスキーマ作成・簡易マイグレーションを行います。
- KillSwitch は flag ファイルを作成して ExecutionEngine に停止を促します。ExecutionEngine 側はそのファイルの存在をチェックして安全停止する実装が期待されます。
- デフォルトでは .env と .env.local をプロジェクトルートから自動ロードします。プロジェクトルートは .git または pyproject.toml を基準に探索します。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py                 — パッケージ情報（バージョン等）
- config.py                   — 環境変数 / Settings 管理 (.env 自動ロードロジック含む)
- run_execution.py            — ExecutionEngine 起動スクリプト
- run_monitoring.py           — SystemMonitor ポーリングループ起動スクリプト

src/kabusys/execution/
- order_manager.py
- order_repository.py
- reconciler.py
- execution_engine.py
- broker_factory.py
- broker_api.py
- ...（発注/リスク関連実装）

src/kabusys/monitoring/
- monitoring_db.py            — SQLite スキーマ・読み書きラッパー
- system_monitor.py
- trade_monitor.py
- risk_monitor.py
- monitoring_engine.py
- kill_switch.py
- alert_manager.py
- streamlit_dashboard.py

src/kabusys/portfolio/
- portfolio_builder.py
- position_sizing.py
- risk_adjustment.py

src/kabusys/research/
- factor_research.py
- feature_exploration.py

src/kabusys/ai/
- news_nlp.py                 — ニュース -> OpenAI -> ai_scores
- regime_detector.py          — レジーム判定（ETF MA + マクロセンチメント）

src/kabusys/tools/
- paper_verification_report.py

src/kabusys/utils/
- process_priority.py         — プロセス優先度 / CPU affinity ユーティリティ

その他:
- data/                       — デフォルトの DB ファイルや PID/flag を置く想定（運用環境でマウント）
  - kabusys.duckdb
  - monitoring.db
  - paper_trading.db
  - execution.pid
  - kill.flag

---

## 開発・拡張のヒント

- DuckDB はデータ集計・研究向けに高速で便利です。research モジュールは DuckDB 接続を受け取り SQL と Python を組合せて計算します。
- AI 関連は OpenAI SDK（chat.completions）へ依存します。テスト時は _call_openai_api をモックして外部依存を切ってください（ニュース / レジームともに想定済み）。
- monitoring_db の操作は MonitoringDB クラスを通して行うと安全です。マイグレーションは簡易実装ですが、スキーマ変更時は init_monitoring_db を更新して互換性を保つ設計です。
- streamlit ダッシュボードは読み取り専用モードで SQLite を URI 指定で読み込みます（?mode=ro）。運用中にダッシュボードを開くときは読み取りロックやパーミッションに注意してください。

---

## ライセンス / 作者
（このテンプレート README には含まれていません。実際のプロジェクトに合わせて記載してください）

---

README に書かれていない細かな仕様や内部 API の使い方は、各モジュールの docstring を参照してください。必要であれば、各コンポーネントの利用例や設計ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）を追加で作成できます。