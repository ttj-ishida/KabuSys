# KabuSys

日本株向け自動売買システムのコンポーネント群（ライブラリ＋起動スクリプト）。  
このリポジトリはトレーディング実行・監視・リサーチ・ポートフォリオ構築・AI（ニュース NLP / レジーム判定）などの機能を含むモジュール化された実装です。

以下はコードベースから生成した README ドキュメントです。

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（起動例）
- 環境変数（主なもの）
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株の自動売買に必要な実行（Execution Engine）、監視（Monitoring）、リスク管理、ポートフォリオ構築、ファクター計算、ニュース NLP（OpenAI を利用）などを含むモジュール群です。
- 実行環境は本番（live）、ペーパートレーディング（paper_trading）、開発（development）を切替可能。ペーパー取引時はブローカークライアントはモックを使い、DB も本番と分離されます。
- 主要な永続化は SQLite（監視・発注ログ等）および DuckDB（時系列価格やリサーチ向けテーブル）を使用します。

主な機能
- Execution（発注）
  - ExecutionEngine、OrderManager、OrderRepository、Reconciler による発注・状態管理と再同期機能。
  - ペーパートレードモードでは MockBrokerClient を使用し DB を分離。
- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/ディスク・プロセス死活・データ鮮度監視。
  - TradeMonitor: 滞留注文（stale orders）・約定異常価格監視。
  - RiskMonitor: ドローダウン・ポジション上限監視、kill switch（停止フラグ生成）。
  - AlertManager: LINE Push による通知（クールダウン付き）。
  - streamlit ベースの監視ダッシュボード（read-only）。
- Portfolio（銘柄選定・配分・株数決定）
  - 候補選定、等配分／スコア加重配分、ポジションサイズ計算、セクター上限適用、レジーム乗数等。
- Research（ファクター・解析）
  - momentum / volatility / value 等のファクター計算、将来リターン、IC 計算、統計サマリ。
  - DuckDB を用いた SQL + Python 実装（prices_daily, raw_financials 等参照）。
- AI（ニュース NLP / レジーム判定）
  - OpenAI（gpt-4o-mini など）によりニュースセンチメントをスコア化し ai_scores に格納。
  - マクロニュース + ETF（1321）MA200 を組合せた市場レジーム判定。
  - API エラーや失敗時はフォールバック／リトライロジックあり。
- ツール
  - Paper Trading 検証レポート生成スクリプト（期間指定可）。
  - streamlit ダッシュボード（監視 DB の read-only 表示）。

セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   - git clone ... && cd <repo>

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 本リポジトリでは requirements.txt を明示していませんが、次のパッケージが想定されます：
     - duckdb, psutil, requests, openai, streamlit
   - 例:
     - pip install duckdb psutil requests openai streamlit

   （テストや開発で追加のパッケージが必要な場合があります）

4. 環境変数を設定
   - プロジェクトルートに .env/.env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN（J-Quants API 用）
     - KABU_API_PASSWORD（kabuステーション API 用）
   - OpenAI を使う機能を使う場合:
     - OPENAI_API_KEY を設定

   （後述の「環境変数（主なもの）」節を参照してください）

5. データディレクトリ
   - デフォルトでは data/ 配下にファイルを作成します（例: data/monitoring.db, data/kabusys.duckdb, data/execution.pid, data/stop_requested.flag など）。
   - 必要に応じて書き込み権限を確認してください。

初期 DB 作成
- 多くの起動スクリプトは起動時に monitoring DB スキーマを作成します（init_monitoring_db を実行）。明示的なマイグレーションは不要です。

使い方（起動例・コマンド）
- 実行（Production / Paper / Development 切替）
  - ExecutionEngine を起動する（通常はサービスとして実行）:
    - KABUSYS_ENV=live python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - Monitoring を起動する（ポーリング）:
    - python -m kabusys.run_monitoring
    - ポーリング間隔を上書き: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 停止制御
  - run_execution/run_monitoring は data/stop_requested.flag の存在を監視して自動停止します。手で停止させたい場合はそのファイルを作成してください（停止後は必要に応じて削除）。
  - Kill switch（自動停止）:
    - RiskMonitor 等が条件を満たすと data/kill.flag を生成して ExecutionEngine に停止シグナルを送ります（実行中の Engine は kill.flag を検知して停止します）。
    - kill.flag は KillSwitch.clear() で削除できます（ExecutionEngine 起動時にクリア設定がある場合あり）。

- Streamlit ダッシュボード
  - 監視 DB を読み込む read-only ダッシュボード:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  - レポートは標準出力に表示され、稼働率・注文成功率・レイテンシ等を集計・判定します。

環境変数（主なもの）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を利用する場合）
- PAPER_FILL_MODE: Paper Trading の約定挙動（instant|partial|never|reject。デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH: Execution PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: Engine 起動時に kill.flag を自動クリアする場合は "1"
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視しきい値（デフォルト値は Settings 内に定義）

注意点（運用上）
- Paper Trading モードは本番 DB と完全分離されるよう設計されています（settings.is_paper により sqlite_path を切り替え）。
- OpenAI を使う機能は API エラー・レート制限を考慮したリトライ実装を持ちますが、API キーの管理と利用料金に注意してください。
- プロセス優先度は起動時に高 ("high") にセットされます（set_process_priority）。環境によって権限が必要になる場合があります。
- データ鮮度チェック、PID ファイル管理、停止フラグの扱いなどは SystemMonitor/MonitoringEngine で定義されています。運用前に data/ 配下のファイル運用ルールを確認してください。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定の読み込み/検証
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - data/                    — 実行時生成ファイル置き場（./data/monitoring.db 等）
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）によるスコアリング
    - regime_detector.py     — レジーム判定（マクロ + MA200）
  - execution/
    - order_manager.py
    - reconciler.py
    - order_repository.py
    - execution_engine.py
    - broker_factory.py
    - ...                    — 発注/ブローカ関連
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
    - streamlit_dashboard.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - tools/
    - paper_verification_report.py
  - utils/
    - process_priority.py

- data/ (実行時生成想定)
  - monitoring.db           — SQLite（監視ログ）
  - kabusys.duckdb          — DuckDB（価格・財務データ等）
  - execution.pid
  - stop_requested.flag
  - kill.flag
  - paper_trading.db        — （ペーパートレード用、KABUSYS_ENV=paper_trading 時）

開発のヒント / テスト
- モジュールは pure function を多く含む（portfolio, research 等）。ユニットテストが作りやすい構造です。
- OpenAI 呼び出し部分は内部で一箇所に抽象化されており、テストでは _call_openai_api のパッチによるモック化が可能です。
- MonitoringEngine.run_once() を使えばポーリングループを回さず単発実行で監視の挙動を確認できます。

ライセンス / 貢献
- （この README はコードベースから自動生成された説明です。実際のライセンス・貢献ルールはリポジトリルートにある LICENSE や CONTRIBUTING を参照してください。）

---

必要であれば .env のサンプルや想定される requirements.txt（pip パッケージ一覧）を作成します。どの部分をより詳細に記載したいか教えてください。