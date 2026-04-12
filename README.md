# KabuSys — README

本ドキュメントはソースツリー（src/kabusys 以下）に基づく簡易 README です。日本株自動売買システムの一部機能（実行エンジン、監視、研究・ポートフォリオ構築、AI ニューススコアリング等）が含まれます。

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（起動コマンド・主要スクリプト）
- 環境変数（主要な設定項目）
- ディレクトリ構成（主要ファイルと役割）

---

## プロジェクト概要

KabuSys は日本株の自動売買に関するモジュール群です。本リポジトリに含まれるコードは主に以下の責務を持ちます。

- ExecutionEngine（発注・状態管理・リスク管理・リコンシリエーション）
- Monitoring（システム状態・注文状態・リスクの定期監視、アラート送信）
- Research（ファクター計算、特徴量解析、IC 計算等）
- Portfolio（候補選定・重み計算・ポジションサイズ決定・セクター制限）
- AI（ニュースセンチメント評価、マーケットレジーム判定）
- ツール群（Paper Trading の検証レポート生成、Streamlit ダッシュボード等）
- 設定管理（.env 自動読み込み、Settings クラス）

設計方針として、DB は DuckDB（時系列・ファクターデータ用）と SQLite（監視ログ / 注文履歴）を使い分け、Paper Trading 環境は本番 DB と分離するようになっています。

---

## 主な機能一覧

- 実行エンジン（ExecutionEngine）
  - ブローカークライアント抽象化（mock / 実ブローカー切替）
  - OrderManager：発注ワークフロー（作成→送信→同期→拒否処理）
  - Reconciler：再起動時の注文/ポジション照合による自動復旧
  - RiskManager：ポジション・利用率等のリスク制御

- 監視
  - SystemMonitor：CPU/メモリ/ディスク、プロセス生存チェック、データ鮮度チェック
  - TradeMonitor：滞留注文・約定価格異常検出
  - RiskMonitor：ドローダウン・ポジション数監視、kill.flag 書き込み
  - AlertManager：LINE へプッシュ通知（cooldown 管理）
  - MonitoringEngine：上記モニタを束ねたポーリング実行
  - Streamlit ダッシュボード（監視データの可視化）

- 研究（Research）
  - calc_momentum / calc_volatility / calc_value：ファクター計算（DuckDB ベース）
  - calc_forward_returns, calc_ic, factor_summary：特徴量解析・IC 計算

- ポートフォリオ構築（Portfolio）
  - 候補選定（select_candidates）
  - 重み計算（等金額 / スコア重み）
  - セクター制限（apply_sector_cap）
  - ポジションサイズ計算（calc_position_sizes）（lot 単位丸め、集約キャップ）

- AI
  - news_nlp.score_news：OpenAI（gpt-4o-mini）を用いたニュースセンチメントの集計・書き込み
  - regime_detector.score_regime：ETF MA とマクロニュースセンチメントを合成してレジーム判定

- ツール
  - tools.paper_verification_report：Paper Trading の検証レポート出力
  - monitoring/streamlit_dashboard.py：Streamlit でダッシュボード表示

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈の union 型（|）等を使用しているため）
- SQLite は標準ライブラリで利用
- DuckDB, psutil, openai, requests, streamlit 等の外部ライブラリが必要

推奨インストール例（仮想環境を推奨）:

1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb psutil openai requests streamlit

   （requirements.txt がない場合は上記を個別にインストールしてください）

3. プロジェクトルートに .env を配置（任意）
   - リポジトリの config モジュールはプロジェクトルート（.git または pyproject.toml の存在するディレクトリ）を検出し、.env/.env.local を自動ロードします。
   - 開発時に自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. データディレクトリ作成
   - mkdir -p data

5. （Paper Trading を使う場合）
   - KABUSYS_ENV=paper_trading を設定すると mock ブローカークライアントが使用され、デフォルトで data/paper_trading.db を利用します。

---

## 使い方（起動コマンド・主要スクリプト）

- 実行エンジン（本番/テスト実行）
  - python -m kabusys.run_execution
    - 注意: 起動時に Settings を参照し、KABUSYS_ENV に応じて paper_trading 用 DB を使います。
    - 実行前に必要な環境変数（ブローカー認証等）を設定してください。

- 監視（SystemMonitor のポーリングループ）
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
    - 監視は常に本番用 sqlite_path（Settings.sqlite_path）を使用します（Paper 環境でも本番 DB を参照する仕様）。

- Streamlit ダッシュボード（監視データ可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    - 引数 --db で監視用 SQLite DB パスを指定可能（既定: data/monitoring.db）。
    - 読み取り専用で開くため、MonitoringEngine を先に起動してデータを確保することを推奨。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
    - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）

- AI スコア付け / レジーム判定（ライブラリ利用）
  - score_news と score_regime はライブラリ関数として公開されています。コード内から呼び出してください。
    - 例（簡易）:
      from kabusys.ai.news_nlp import score_news
      from kabusys.ai.regime_detector import score_regime
      score_news(duckdb_conn, target_date, api_key="xxxx")
      score_regime(duckdb_conn, target_date, api_key="xxxx")
    - OpenAI API キーは引数か環境変数 OPENAI_API_KEY を利用します。

- 注意点
  - 実行スクリプトは起動直後に set_process_priority("high") を呼びます（プラットフォーム依存で失敗する場合は警告を出してスキップ）。
  - run_execution は起動時に Reconciler 等を実行して DB の状態を整えたうえでセッションを開始します。

---

## 環境変数（主要な設定項目）

以下は主要な環境変数と既定値の例です。プロジェクトでは .env / .env.local をサポートします。

- KABUSYS_ENV: 起動環境（development | paper_trading | live） — デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで使用）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE アラート送信に使用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時のモック約定モード（instant|partial|never|reject。デフォルト: instant）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト: 60）
- LOG_LEVEL: ログレベル（DEBUG|INFO|...。デフォルト: INFO）

.env 例（最小）
    KABUSYS_ENV=development
    JQUANTS_REFRESH_TOKEN=your_jquants_token
    KABU_API_PASSWORD=your_kabu_password
    OPENAI_API_KEY=sk-...
    LINE_CHANNEL_ACCESS_TOKEN=
    LINE_USER_ID=

---

## 主要な設計・運用メモ

- Paper Trading の分離
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、data/paper_trading.db（または PAPER_TRADING_SQLITE_PATH）へ書き込みます。本番の SQLite（monitoring.db）とは分離されます。

- DB マイグレーション
  - monitoring_db.init_monitoring_db() は冪等でテーブル作成と簡単なスキーマ追加（ALTER TABLE）を行います。run_* スクリプトは起動時にこれを呼びます。

- フェイルセーフ
  - AI 呼び出しや API エラーは基本的にスキップして継続する設計（リトライ・バックオフを実装）。重要な障害時はログと risk_logs に記録されます。

- Kill Switch
  - RiskMonitor が危険条件（ドローダウン等）を検出すると、KillSwitch が data/kill.flag を書き込み ExecutionEngine 停止の合図を出します。ExecutionEngine は起動時に KILL_FLAG_CLEAR_ON_START に応じてクリアできます。

---

## ディレクトリ構成（主要ファイルと役割）

（src/kabusys をルートとした主要ファイル・モジュール一覧）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings を提供
  - run_execution.py
    - ExecutionEngine 起動エントリポイント
  - run_monitoring.py
    - SystemMonitor 単体のポーリング起動スクリプト

  - execution/
    - order_manager.py
    - order_repository.py (存在は示唆されているが長いファイルは省略)
    - reconciler.py
    - execution_engine.py (Engine 実装)
    - broker_factory.py, broker_api.py（ブローカ抽象）
    - order_record.py
    - risk_manager.py
    - ...（発注・リスク関連実装）

  - monitoring/
    - monitoring_db.py
      - system_status / trade_logs / positions / risk_logs / dashboard テーブル管理
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py

  - research/
    - factor_research.py
      - calc_momentum, calc_volatility, calc_value (DuckDB ベース)
    - feature_exploration.py
      - forward returns, IC, factor_summary
    - __init__.py

  - portfolio/
    - portfolio_builder.py (候補選定・重み)
    - position_sizing.py (株数決定・aggregate cap)
    - risk_adjustment.py (セクター上限・レジーム乗数)
    - __init__.py

  - ai/
    - news_nlp.py (ニュースを OpenAI でスコアリングして ai_scores に書き込み)
    - regime_detector.py (MA とマクロニュースでレジーム判定)
    - __init__.py

  - data/
    - pipeline.py 等（データ取得・前処理。get_last_price_date など参照あり）

  - tools/
    - paper_verification_report.py（Paper Trading の検証レポート）
    - __init__.py

  - utils/
    - process_priority.py（プロセス優先度 / CPU affinity ユーティリティ）
    - __init__.py

---

## 開発・運用上の補足

- テスト・CI
  - config._find_project_root() は __file__ を基準にプロジェクトルートを探します。テスト時に環境変数自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- ロギング
  - run_* スクリプトは起動時に logging.basicConfig(level=logging.INFO) を設定しています。LOG_LEVEL 環境変数で制御する設計になっている箇所もあります（Settings.log_level）。

- 安全な DB 操作
  - ai.news_nlp や regime_detector の DB 書き込みはトランザクション（BEGIN/DELETE/INSERT/COMMIT）を使って冪等に処理するよう配慮されています。

---

この README はコードベースから抽出した情報をまとめたものです。実運用に当たってはブローカー API の仕様、各種権限・API キーの取り扱い、バックテスト・検証を十分に行ってください。必要であれば各モジュールの詳細ドキュメント（関数ごとの docstring）を追加していきます。