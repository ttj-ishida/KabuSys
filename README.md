# KabuSys

KabuSys は日本株向けの自動売買／リサーチ／監視フレームワークです。  
このリポジトリは取引エンジン（Execution）、監視（Monitoring）、ファクター計算・研究（Research）、ポートフォリオ構築（Portfolio）、LLM を使ったニュース NLP（AI）などのコンポーネントを含みます。

以下はコードベースから抽出した README です。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（コマンド例）
- ディレクトリ構成（主要ファイルの説明）
- 実行時の注意点 / 運用メモ

---

プロジェクト概要
- 日本株の自動売買システムの実行基盤・監視・研究用ユーティリティ群。
- SQLite（監視ログ等）・DuckDB（時系列 / ファクターデータ）をデータ層に使用。
- 本番/ペーパートレードを環境変数 KABUSYS_ENV により切り替え可能（development / paper_trading / live）。
- OpenAI（gpt-4o-mini）を用いたニュースのセンチメント評価やマクロ判定機能を搭載。
- 監視はローカルファイルによるフラグ（data/stop_requested.flag、data/kill.flag 等）を用いてプロセス間連携を行う設計。

機能一覧
- Execution（発注エンジン関連）
  - OrderManager: シグナルから注文を作成、ブローカ API 経由で発注
  - Reconciler: 再起動時の注文・ポジション突合（自動復旧）
  - BrokerFactory により実際のブローカーと MockBroker を切替（KABUSYS_ENV=paper_trading）
- Monitoring（監視）
  - SystemMonitor: CPU / メモリ / ディスク / プロセス生存 / データ鮮度監視
  - TradeMonitor: 注文滞留（stale）や約定価格異常の検出
  - RiskMonitor: ドローダウン監視、ポジション数上限監視（ハイウォーターマーク管理）
  - KillSwitch / AlertManager: 条件に応じた kill.flag 書き込みと LINE 通知（任意）
  - MonitoringEngine: 上記監視を定期実行するポーリングエンジン
  - Streamlit ダッシュボード（監視情報の可視化）
- Research（因子・統計）
  - factor_research: Momentum / Volatility / Value 等のファクター計算（DuckDB を使用）
  - feature_exploration: 将来リターン計算、IC（Information Coefficient）等の統計解析
- Portfolio（ポートフォリオ構築）
  - 候補選定、等重・スコア重み、ポジションサイズ計算、セクターキャップ、レジーム乗数
- AI（LLM 連携）
  - news_nlp.score_news: raw_news をまとめて LLM に送信し銘柄ごとの ai_score を生成
  - regime_detector.score_regime: ETF の MA 乖離 と マクロニュース LLM スコアを合成して市場レジーム判定
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成（稼働率・注文成功率・レイテンシ等）

---

セットアップ手順（ローカル開発 / 簡易）
1. リポジトリをクローンし、作業ディレクトリに移動
2. Python 環境（推奨: 3.10+）を用意し仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（コードベースから使用ライブラリの抜粋）
   - pip install duckdb psutil requests openai streamlit
   - （プロジェクトに requirements.txt があればそれを使用してください）
4. 環境変数設定
   - プロジェクトルートに .env / .env.local を置くと自動読み込みされます（OS 環境変数が優先）。
   - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 主要環境変数（抜粋）
     - KABUSYS_ENV: development | paper_trading | live  (default: development)
     - JQUANTS_REFRESH_TOKEN: （必須）J-Quants API 用トークン
     - KABU_API_PASSWORD: （必須）kabu API 用パスワード
     - OPENAI_API_KEY: OpenAI 呼び出しに必要（AI 機能を使う場合）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE）を使う場合
     - SQLITE_PATH: 監視用 SQLite（default: data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイル（default: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（default: data/paper_trading.db）
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、default: 60）
     - PID_FILE_PATH / KILL_FLAG_PATH など（必要に応じてカスタマイズ）
5. データディレクトリ作成
   - mkdir -p data
   - スキーマは起動スクリプトが必要に応じて初期化します（例: init_monitoring_db）

---

基本的な使い方（コマンド例）
- 監視ループ起動（Monitoring）
  - モジュール実行:
    - python -m kabusys.run_monitoring
  - もしくは直接実行（プロジェクトルートで）:
    - python src/kabusys/run_monitoring.py
  - 補足:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能
    - 監視は Settings の sqlite_path を常に「本番」用パスから参照（環境に依らず）
    - 停止: プロジェクトルート/data/stop_requested.flag を作成するとループが終了します

- 実行エンジン起動（Execution）
  - モジュール実行:
    - python -m kabusys.run_execution
  - もしくは直接実行:
    - python src/kabusys/run_execution.py
  - 補足:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 専用 DB（PAPER_TRADING_SQLITE_PATH）へ記録されます（本番 DB と分離）。
    - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
    - 実行中は data/execution.pid に PID を書きます。stop リクエストを出すには stop_requested.flag を作成します（監視側と同じ）。

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視データ（positions, trade_logs, system_status, risk_logs, dashboard）を可視化します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション: --db PATH で PAPER_TRADING_SQLITE_PATH を上書き可能

- AI / レジーム判定・ニューススコア
  - kabusys.ai.score_news および kabusys.ai.regime_detector.score_regime を呼び出して使用（プログラム内 API）。
  - 両機能は OpenAI API キー（OPENAI_API_KEY または引数）を必要とします。

---

環境ファイルの自動読み込み
- プロジェクトルートが .git または pyproject.toml により特定できれば、起動時に自動で .env（優先度低）と .env.local（優先度高）を読み込みます。
- OS 環境変数は .env の上書きを保護します（.env の値は OS の値がある場合は設定されません）。
- 自動読み込み停止: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

主要ディレクトリ構成（抜粋）と説明
- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — Settings クラス、環境変数の読み込み/検証ロジック
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト（paper_trading モード対応）
  - ai/
    - news_nlp.py — raw_news を LLM で評価し ai_scores に書き込む
    - regime_detector.py — 市場レジーム判定（MA + LLM）
  - monitoring/
    - monitoring_db.py — SQLite スキーマ作成と永続化 API（MonitoringDB）
    - system_monitor.py — システム / データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常検出
    - risk_monitor.py — ドローダウン・ポジション上限監視（ハイウォーターマーク管理）
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - kill_switch.py — kill.flag の書き込みロジック
    - alert_manager.py — LINE 通知ユーティリティ
    - streamlit_dashboard.py — Streamlit ベースの可視化ツール
  - execution/
    - order_manager.py — 注文フロー管理（OrderManager）
    - reconciler.py — 起動時リコンシリエーション
    - ...（ブローカーファクトリ、engine などが存在）
  - portfolio/
    - portfolio_builder.py — 候補選定、重み付け
    - position_sizing.py — 株数計算・投下額調整
    - risk_adjustment.py — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py — Momentum/Volatility/Value 等のファクター計算（DuckDB 使用）
    - feature_exploration.py — 将来リターン、IC、統計サマリ
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - data/（実行時に作成される想定）
    - monitoring.db（デフォルト SQLite）
    - paper_trading.db（ペーパートレード用）
    - kabusys.duckdb（DuckDB ファイル）
    - stop_requested.flag / kill.flag / execution.pid などのフラグ / PID ファイル

---

実行時の注意点 / 運用メモ
- DB の取り扱い
  - Monitoring は常に Settings.sqlite_path（デフォルト data/monitoring.db）を参照してログを永続化します。
  - ペーパートレードは settings.is_paper を用いて paper_sqlite_path（デフォルト data/paper_trading.db）に完全分離して記録されます。
  - DuckDB（data/kabusys.duckdb）はファクター計算・履歴データ用です。性能上の注意やバックアップを推奨します。
- プロセス制御
  - run_* スクリプトは起動直後に set_process_priority("high") を試みます。権限がない場合は警告を出して続行します。
  - 停止は data/stop_requested.flag の作成で実行中の run_monitoring/run_execution を穏やかに停止できます。外部から強制停止する場合は PID を使って kill してください。
  - KillSwitch はリスク条件（ドローダウンやポジション上限）を満たしたときに data/kill.flag を書き、ExecutionEngine に停止シグナルを送る仕組みです。
- AI 呼び出し
  - OpenAI API はネットワーク・課金・レート制限の影響を受けます。score_news / score_regime はリトライやフェイルセーフを備えていますが、API キーは必ず管理してください。
- テスト性
  - config._find_project_root() は __file__ を基準にプロジェクトルートを特定するため、CWD に依存せずに .env の自動読み込みを行います。
  - AI 呼び出し部分は _call_openai_api をモックできるよう設計されています（ユニットテスト容易化）。

---

サポート / 拡張のヒント
- 新しいブローカープラグインは execution/broker_factory 経由で実装し、BrokerAPIProtocol に従って実装すると既存の OrderManager / Reconciler と連携できます。
- DuckDB のテーブルスキーマ（prices_daily / raw_financials / raw_news 等）に合わせて research や ai モジュールを拡張できます。
- AlertManager は現在 LINE push をサポート。SMTP や別チャネルを追加する場合は同様のインターフェース（notify）を実装してください。
- デプロイ時は systemd や supervisord 等でプロセス管理を行い、stop/kill フラグや PID の扱いを調整してください。

---

ライセンス / 責任
- この README はコードから抽出した実装意図・使い方をまとめたドキュメントです。実際の運用前にコードの詳細を確認し、テストや安全弁（サンドボックス・資金管理）を必ず行ってください。

もし README に加えたい特定の情報（例: 依存関係の固定バージョン、チュートリアル、CI 設定、具体的な API キー取得方法など）があれば教えてください。必要に応じて追記します。