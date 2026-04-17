# KabuSys

KabuSys は日本株向けの自動売買システムのコアライブラリ群です。戦略の因子計算・ポートフォリオ構築・発注エンジン・監視・AI を組み合わせて、実運用（live）とペーパートレーディング（paper_trading）両方をサポートします。本リポジトリはライブラリ／実行スクリプト群を提供し、外部ブローカーは抽象化されています。

以下はコードベースから生成した README（日本語）です。

注意: これは既存のソースコードをもとにしたドキュメントです。実行環境や追加の運用スクリプト・パッケージ管理（requirements.txt など）は別途用意してください。

---

目次
- プロジェクト概要
- 主な機能
- 要件（依存ライブラリ）
- 環境変数 / 設定
- セットアップ手順
- 実行方法（使い方）
- ファイル・ディレクトリ構成（概要）

---

プロジェクト概要
- 名前: KabuSys
- 目的: 日本株自動売買システムのコアコンポーネント（発注管理、リコンシリエーション、監視、ポートフォリオ構築、因子計算、ニュース NLP 等）を提供。
- 設計方針:
  - DuckDB / SQLite をデータ永続化に使用（分析は DuckDB、監視ログは SQLite）。
  - 本番とペーパートレードを明確に分離（paper_trading 環境は専用 SQLite を使用）。
  - 外部 API（ブローカー / OpenAI 等）は抽象化し、エラー耐性（リトライ・フェイルセーフ）を組み込む。
  - ルックアヘッドバイアスを避ける設計（計算関数は date を外部から渡す等）。

主な機能一覧
- Execution（発注エンジン）
  - ExecutionEngine, OrderManager, Reconciler による発注・状態管理・再同期
  - BrokerClientFactory による環境に応じたブローカークライアント生成（paper_trading 時は Mock）
- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/Disk・実行プロセス・データ鮮度監視
  - TradeMonitor: 滞留注文チェック・約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視とリスクログ
  - KillSwitch: 条件に応じた停止フラグ書き込み（data/kill.flag）
  - AlertManager: LINE Push による通知（オプション）
  - Streamlit ダッシュボード（読み取り専用で監視情報表示）
- Portfolio（ポートフォリオ構築）
  - 候補選定、重み計算（等分・スコア加重）、セクター制約適用、ポジションサイズ計算（単元丸め・リスクベース配分等）
- Research（リサーチ / 因子計算）
  - momentum, volatility, value 等のファクター計算（DuckDB 上の prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- AI 関連
  - news_nlp: ニュース記事を OpenAI に投げて銘柄ごとのセンチメント（ai_scores）を作成
  - regime_detector: ma200 とマクロニュースの LLM スコアを合成して市場レジーム判定（market_regime テーブルへ保存）
- ツール
  - paper_verification_report: Paper Trading DB を解析して稼働率・注文成功率・レイテンシ等の検証レポートを生成

要件（依存ライブラリ）
- Python 3.9+（ソースは型注釈に 3.10 相当を想定）
- 必須ライブラリ（一例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード利用時）
- 標準ライブラリ: sqlite3, threading, datetime, logging など

（実際の環境では requirements.txt を用意して pip install -r でインストールしてください）

環境変数 / 設定
- 自動ロード: Settings モジュールはプロジェクトルートの .env / .env.local を自動で読み込みます（OS 環境変数が優先）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- 主要な環境変数:
  - JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
  - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
  - OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
  - KABUSYS_ENV — 実行モード: development | paper_trading | live（デフォルト: development）
  - PAPER_FILL_MODE — paper_trading の約定モード: instant | partial | never | reject（デフォルト: instant）
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - PID_FILE_PATH — ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — KillSwitch の flag ファイルパス（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動削除する場合は 1 を設定
  - LOG_LEVEL — ログレベル（DEBUG/INFO/...）
  - MONITOR_POLL_INTERVAL — run_monitoring が使用するポーリング間隔（秒、デフォルト 60）
  - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視の閾値（%）

サンプル minimal .env（必須項目のみ例）
- .env.example を参照して作成してください。最低限 KABU_API_PASSWORD と JQUANTS_REFRESH_TOKEN は必要です。
例:
  JQUANTS_REFRESH_TOKEN=xxxxx
  KABU_API_PASSWORD=xxxxx
  OPENAI_API_KEY=xxxxx
  KABUSYS_ENV=paper_trading

セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   git clone <repo_url>
   cd <repo_root>

2. Python 仮想環境を作成・有効化
   python -m venv .venv
   source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   pip install -r requirements.txt
   （requirements.txt が無ければ手動で: pip install duckdb psutil requests openai streamlit）

4. .env を作成（.env.example を参照）
   - 必要な環境変数を設定すること
   - paper_trading を試す場合は KABUSYS_ENV=paper_trading を設定し PAPER_TRADING_SQLITE_PATH を確認

5. data ディレクトリの作成（必要に応じて）
   mkdir -p data

6. DB 初期化
   - 監視 DB（monitoring.db）は run_monitoring/run_execution 起動時に init_monitoring_db() によって自動作成・マイグレーションされます。
   - DuckDB（data/kabusys.duckdb）はデータ投入 / マイグレーション手順に従って別途準備してください。

使い方（実行例）
- ExecutionEngine 起動（発注エンジン）
  - 本番モード:
    KABUSYS_ENV=live python -m kabusys.run_execution
  - ペーパートレード（Mock ブローカーを使用、専用 DB に保存）:
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 実行中、data/execution.pid に PID が書き込まれます。停止のために data/stop_requested.flag を作成すると安全停止します（同様に data/kill.flag は KillSwitch 用停止シグナル）。

- Monitoring 起動（ポーリング監視）
  - デフォルトポーリング 60 秒:
    python -m kabusys.run_monitoring
  - ポーリング間隔を変更:
    MONITOR_POLL_INTERVAL=10 python -m kabusys.run_monitoring

- Streamlit ダッシュボード（監視 UI、読み取り専用）
  - 例:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート（ツール）
  - 例:
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db でデータベースを明示的に指定可能。

- AI / Research 機能（ライブラリ API として利用）
  - ニューススコアリング:
    from kabusys.ai import score_news
    score_news(conn, target_date, api_key=...)
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key=...)
  - ファクター計算等:
    from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

停止・制御方法
- 停止フラグ:
  - data/stop_requested.flag — run_monitoring / run_execution が監視している停止フラグ（存在を検知すると安全に停止）。
  - data/kill.flag — KillSwitch が書き込むことで ExecutionEngine に停止シグナルを送る（外部からの停止ではなく、監視条件による自動停止用）。
- PID ファイル:
  - ExecutionEngine は PID を pid_file に書き込み、SystemMonitor は PID の存在確認を行う。stale PID は検出されると削除され、リスクログへ記録される。

ディレクトリ構成（主要ファイルの概要）
- src/kabusys/
  - __init__.py — パッケージ定義（__version__ など）
  - config.py — 環境変数・設定読み込みロジック（.env 自動ロード、Settings クラス）
  - run_execution.py — ExecutionEngine 起動スクリプト（KABUSYS_ENV による挙動切替）
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成 CLI
  - execution/
    - execution_engine.py — 実行エンジン本体（EngineConfig 等）
    - order_manager.py — OrderManager（発注 API の外向きインターフェース）
    - order_repository.py — OrderRepository（SQLite 永続化）
    - reconciler.py — Reconciler（再起動時の照合・復旧）
    - broker_factory.py / broker_api.py — ブローカークライアント抽象化
    - order_record.py — 注文レコード・状態遷移ロジック
  - monitoring/
    - monitoring_db.py — SQLite テーブル定義・読み書き層（init_monitoring_db, MonitoringDB）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン / 上限監視
    - kill_switch.py — 停止フラグ制御
    - alert_manager.py — LINE 通知ユーティリティ
    - monitoring_engine.py — 各モニタを束ねるランナー
    - streamlit_dashboard.py — 監視ダッシュボード（Streamlit）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・単元丸め・配分スケーリング
    - risk_adjustment.py — セクター制約・レジーム乗数
  - research/
    - factor_research.py — momentum/volatility/value ファクター計算
    - feature_exploration.py — 将来リターン・IC・統計サマリ等
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI 呼び出し・バッチ処理・検証）
    - regime_detector.py — ma200 + マクロニュースで市場レジーム判定
  - data/ （推奨ローカル格納場所 / デフォルト）
    - monitoring.db — 監視用 SQLite（デフォルト）
    - kabusys.duckdb — DuckDB（デフォルト）
    - paper_trading.db — paper_trading 用 SQLite（デフォルト）
    - execution.pid / stop_requested.flag / kill.flag — 制御用フラグや PID

補足 / 運用上の注意
- paper_trading 環境は本番 DB と完全に分離されるよう設計されています。実運用時は KABUSYS_ENV を確実に設定してから起動してください。
- OpenAI やブローカー API 呼び出しは料金・レート制限の対象です。API キーの管理と使用量に注意してください。
- PID / flag ファイルの扱いは OS によるファイルパーミッションの影響を受けます。権限に注意して実行してください。
- Monitoring は常に本番の sqlite_path を参照する実装部分があるため、監視用 DB の配置場所・アクセス権を確認してください（run_monitoring は Settings.env にかかわらず本番 sqlite_path を使用する実装がある点に注意）。

貢献・拡張
- 要望: 銘柄ごとの lot_size をマスタで持つ、より細かい手数料モデルの導入、バックテストモジュール追加などが想定されています。
- テスト: 各モジュールは副作用を分離する設計になっているため、ユニットテストやモックによる検証がしやすいです（例: OpenAI 呼び出し箇所は差し替え可能）。

---

この README はソースコードから要点を抽出して作成しています。実際の運用ガイド、CI/CD、デプロイ手順、requirements.txt、環境ごとの詳細な設定は別途整備してください。必要であれば README に含める具体的な .env.example や systemd / Supervisor 用のサービス定義のテンプレートも作成できます。必要でしたら教えてください。