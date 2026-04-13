# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買プラットフォームの一部実装です。トレード実行、監視、リサーチ（ファクター計算）、ポートフォリオ構築、AI（ニュースセンチメント / レジーム判定）などのコンポーネントを含みます。

主な設計方針としては、
- 実行・監視ロジックと DB（SQLite / DuckDB）を分離
- Paper Trading（検証）環境は本番 DB と完全に分離
- ルックアヘッドバイアスを避ける設計（日時参照の扱いに注意）
- フェイルセーフ（API 失敗時は安全側にフォールバック）  
などを念頭に置いて実装されています。

---

目次
- 機能一覧
- 動作要件 / 依存関係
- セットアップ手順
- 使い方（主要コマンド / スクリプト）
- 環境変数（主要なもの）
- ディレクトリ構成（主要ファイルと説明）
- 補足 / 注意事項

---

## 機能一覧
- ExecutionEngine 起動（run_execution.py）
  - ブローカークライアント抽象化（実ブローカー / Mock）
  - リスク制御（ポジション上限・利用比率・ドローダウン等）
  - 注文状態遷移・2相永続化（クラッシュ耐性考慮）
  - 再起動時リコンシリエーション（Reconciler）
- Monitoring（run_monitoring.py / MonitoringEngine）
  - 系統的なポーリングでシステム状態・注文状態・リスクを監視
  - kill.flag による外部停止シグナル出力
  - LINE によるアラート通知（AlertManager）
  - Streamlit ダッシュボード（監視用 UI）
- DB 層
  - MonitoringDB: SQLite ベースの監視ログ（system_status, trade_logs, positions, risk_logs, dashboard）
  - DuckDB を用いた時系列データ / ファクター計算
- Research（research パッケージ）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC 計算、統計サマリ
- Portfolio（portfolio パッケージ）
  - 候補選定、等重／スコア重み、ポジションサイズ算出、セクター制限、レジーム倍率
- AI（ai パッケージ）
  - news_nlp: OpenAI を使ったニュースセンチメント集計と ai_scores への書き込み
  - regime_detector: ETF MA とマクロニュースを組合せた市場レジーム判定
- ツール
  - paper_verification_report: Paper Trading の検証レポート生成スクリプト

---

## 動作要件 / 依存関係
推奨: Python 3.10 以上（型注釈に PEP 604 等を使用）

主要 Python パッケージ（抜粋）
- duckdb
- openai
- psutil
- requests
- streamlit (ダッシュボード利用時)
- （標準ライブラリ）sqlite3, logging, datetime, argparse など

インストール例:
- 仮想環境を作成してから:
  - pip install duckdb openai psutil requests streamlit

（実際の requirements.txt や poetry 設定がある場合はそちらを使ってください）

---

## セットアップ手順（ローカル開発向け、簡易）
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb openai psutil requests streamlit
4. data ディレクトリ作成（必要に応じて）
   - mkdir -p data
5. 環境変数設定
   - プロジェクトルートに .env を置くか、OS 環境変数を設定します。
   - 自動読み込みは既定で有効（.env → .env.local を読み込み、OS 環境変数を保護）
   - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
6. モニタリング DB 初期化
   - run_monitoring や run_execution を起動すると init_monitoring_db が呼ばれてテーブルを自動作成します

---

## 使い方（主要スクリプト／コマンド）

- ExecutionEngine を起動（本番 / ペーパー切替は KABUSYS_ENV）
  - KABUSYS_ENV=paper_trading を使うと MockBrokerClient を利用し、Paper Trading 専用 DB（PAPER_TRADING_SQLITE_PATH）に書き込みます。
  - 実行:
    - python -m kabusys.run_execution
  - 備考:
    - 実行開始時にプロセス優先度を "high" に設定しようとします（psutil が必要、権限がなければ警告が出ます）。
    - 設定は kabusys.config.Settings から読み込まれます。

- Monitoring を起動（ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視ログを書きます。
  - PID ファイル管理 / kill.flag の操作などを含みます。

- Streamlit 監視ダッシュボード
  - 起動:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - DB は read-only モードで開きます（URI に ?mode=ro を付与）。MonitoringEngine 起動後に利用してください。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数またはデフォルト data/paper_trading.db）
  - 出力: 稼働率、注文成功率、送信率、レイテンシなどのサマリと PASS/FAIL 判定

- AI 関連（プログラムから呼ぶ）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - raw_news / news_symbols を読み、OpenAI API に問い合わせて ai_scores を更新します
    - api_key を渡すか OPENAI_API_KEY 環境変数を設定してください
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF（1321）の MA200 等を使って market_regime テーブルへ書き込みます

---

## 主要な環境変数（一覧）
- KABUSYS_ENV: 起動環境（development / paper_trading / live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- PAPER_FILL_MODE: paper_trading 時の約定モード（instant / partial / never / reject）デフォルト: instant
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（"1" で有効）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE通知）で使用

設定は .env / .env.local または OS 環境変数で与えることができます。Settings クラスが読み込みと検証を行います。

---

## ディレクトリ構成（主要ファイルと説明）
（ルート: src/kabusys 以下を示す）

- __init__.py
  - パッケージエクスポート、バージョン情報
- config.py
  - 環境変数読み込みロジックと Settings クラス
  - .env 自動ロードの実装や値検証を含む
- run_execution.py
  - ExecutionEngine 起動スクリプト（プロセス優先度設定、DB 接続、コンポーネント組立）
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
- tools/
  - paper_verification_report.py: Paper Trading の検証レポートを生成する CLI
- monitoring/
  - monitoring_db.py: SQLite スキーマ作成 / MonitoringDB ラッパー（読み書き）
  - system_monitor.py: システム状態・データ鮮度チェック
  - trade_monitor.py: 注文滞留・約定異常チェック
  - risk_monitor.py: ドローダウン・ポジション上限監視
  - kill_switch.py: kill.flag の操作
  - alert_manager.py: LINE によるプッシュ通知
  - monitoring_engine.py: 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py: Streamlit ベースの監視ダッシュボード
- execution/
  - reconciler.py: 起動時の自動復旧ロジック（注文・ポジション照合）
  - order_manager.py, order_repository.py, order_record.py, risk_manager.py, etc.（注文管理・リスク管理）
- portfolio/
  - portfolio_builder.py: 候補選定・重み計算
  - position_sizing.py: 株数算出・単元丸め・資金割当
  - risk_adjustment.py: セクター上限・レジーム乗数
- research/
  - factor_research.py: ファクター計算（momentum / volatility / value）
  - feature_exploration.py: 将来リターン / IC / 統計サマリ
- ai/
  - news_nlp.py: ニュースのセンチメントスコアリング（OpenAI 使用）
  - regime_detector.py: レジーム判定（ETF MA + マクロニュース）
- utils/
  - process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティ

（上記は主要なモジュールの要約です。詳細な内部実装はソースをご覧ください。）

---

## 補足 / 注意事項
- Paper Trading は本番 DB と完全分離されています（PAPER_TRADING_SQLITE_PATH を使用）。
- run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視ログを書きます。
- OpenAI 呼び出しには API キーが必要です。失敗時はフォールバック（0.0 等）する設計ですが、API キー未設定の場合は一部機能で例外を投げます。
- process priority / CPU affinity の設定は psutil を用いています。権限が不足すると警告が出ますが、処理自体は継続します。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を基準）を探索して行います。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- monitoring DB のスキーマは init_monitoring_db() により冪等に作成されます。既存 DB に対する簡易マイグレーション（カラム追加）も実装されています。

---

README は以上です。各モジュールの詳細な使用方法・引数・戻り値は該当ソースの docstring を参照してください。必要であれば、README に含める具体的な例（.env.example、systemd サービス定義、docker-compose 例など）を追加できます。どの情報を追加したいか教えてください。