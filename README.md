# KabuSys — README

このリポジトリは日本株自動売買システム「KabuSys」のコアライブラリ群です。  
README ではプロジェクト概要、主な機能、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語でまとめます。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買／バックテスト／モニタリング用ライブラリ群です。  
主に以下の責務を持つモジュールで構成されています。

- 実行エンジン（ExecutionEngine）と注文管理（broker 接続・OrderManager）
- 取引ログ・監視データの永続化（SQLite）および分析用の DuckDB
- 監視コンポーネント（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算・セクター制限）
- 研究用モジュール（ファクター計算・特徴量解析）
- AI モジュール（ニュースの NLP スコアリング、レジーム判定 via OpenAI）
- 運用ツール（Paper Trading 検証レポート生成、Streamlit ダッシュボード）

設計上の方針として「本番 DB と paper_trading を分離」「ルックアヘッドバイアス回避」「外部副作用を最小化」などに配慮されています。

---

## 機能一覧（抜粋）

- Execution
  - 注文作成 / 状態同期 / リコンシリエーション（Reconciler）
  - Paper Trading 切替（KABUSYS_ENV=paper_trading で broker をモックし専用 DB に記録）
- Monitoring
  - システムリソース監視（CPU/メモリ/ディスク）、プロセス生存チェック
  - 注文滞留・約定異常価格検出
  - ドローダウン・ポジション上限監視、Kill Switch（停止フラグの書き込み）
  - AlertManager（LINE Push による通知・クールダウン管理）
  - Streamlit ベースの監視ダッシュボード
- Portfolio construction
  - 候補選定（スコア順、信号ランク考慮）
  - 等重・スコア加重・リスクベースの重み・単元丸めを含む株数決定ロジック
  - セクター上限適用、レジーム乗数計算
- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を利用）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
- AI
  - news_nlp: OpenAI を用いたニュースの銘柄別センチメントスコア生成（ai_scores へ保存）
  - regime_detector: マクロ記事 + ETF MA200 を組み合わせた日次レジーム判定
- Tools
  - paper_verification_report: Paper Trading DB から検証レポート生成
  - Streamlit ダッシュボード起動スクリプト

---

## セットアップ手順（例）

※実行環境や具体的な requirements.txt はこの README に含まれていません。以下は一般的な手順例です。

1. リポジトリをクローン
   - git clone <リポジトリ URL>

2. Python 仮想環境作成（例）
   - python3 -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージのインストール（想定）
   - pip install duckdb psutil openai requests streamlit
   - （ローカルに requirements.txt があれば `pip install -r requirements.txt`）

4. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くことで自動読み込みされます（OS 環境変数が優先）。
   - 自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

5. 必須環境変数（代表）
   - JQUANTS_REFRESH_TOKEN — J-Quants API トークン
   - KABU_API_PASSWORD — kabuステーション API パスワード
   - OPENAI_API_KEY — OpenAI API キー（AI 機能利用時）
   - KABUSYS_ENV — environment: development | paper_trading | live
   - （任意）LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 通知用

6. データディレクトリ
   - デフォルトの DB 等のパスは data/ 以下（README の「設定」節参照）
   - 必要に応じて `DUCKDB_PATH`, `SQLITE_PATH`, `PAPER_TRADING_SQLITE_PATH` を環境変数で上書き

---

## 主要設定（Settings クラスについて）

設定は `kabusys.config.Settings` で環境変数から読み込まれます。主なプロパティとデフォルト：

- env: KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
- duckdb_path: DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- sqlite_path: SQLITE_PATH（デフォルト: data/monitoring.db）
- paper_sqlite_path: PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- pid_file_path: PID_FILE_PATH（デフォルト: data/execution.pid）
- kill_flag_path: KILL_FLAG_PATH（デフォルト: data/kill.flag）
- PAPER_FILL_MODE: Paper Trading の約定モード（instant | partial | never | reject、デフォルト: instant）
- CPU/MEM/DISK 閾値等も環境変数で制御可能
- 自動 .env ロード: プロジェクトルートに `.env` / `.env.local` がある場合自動で読み込まれます（OS 変数保護あり）。無効化は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。

未設定の必須環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）を参照すると例外になります。

---

## 使い方（代表コマンドと動作）

以下は主要な起動方法の例です。プロセスはプロジェクトルートから実行する想定です。

1. 監視プロセス（SystemMonitor 単体スクリプト）
   - 実行:
     - python -m kabusys.run_monitoring
   - 特記事項:
     - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で秒数を指定（デフォルト 60 秒）。
     - 監視は常に本番 `sqlite_path` を使用（KABUSYS_ENV に依らず）。
     - 停止はプロジェクトルートの `data/stop_requested.flag` を作成するとループが終了します。

2. Execution エンジン（注文・実行）
   - 実行:
     - python -m kabusys.run_execution
   - 特記事項:
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、`data/paper_trading.db`（PAPER_TRADING_SQLITE_PATH）に記録し、本番 DB と分離されます。
     - 起動時に `data/stop_requested.flag` が既にある場合は起動せず終了します。
     - 実行中に `data/stop_requested.flag` を作成するとエンジンを停止します。
     - 実行中には PID が `data/execution.pid` に書かれます（設定で変更可能）。

3. Streamlit ダッシュボード（監視 UI）
   - 実行:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 説明:
     - read-only で SQLite を開いてダッシュボード表示を行います。MonitoringEngine を先に起動してデータを生成してください。

4. Paper Trading 検証レポート
   - 実行:
     - python -m kabusys.tools.paper_verification_report
     - もしくは期間指定例:
       - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - DB 指定:
       - --db PATH （指定がない場合は環境変数 PAPER_TRADING_SQLITE_PATH、なければ data/paper_trading.db を使用）
   - 出力:
     - 稼働率、注文成功率、送信率、レイテンシ指標（P95 など）を標準出力に出します。

5. AI 機能（プログラム API）
   - ニュースセンチメントを実行して DB に格納:
     - from kabusys.ai.news_nlp import score_news
     - score_news(conn, target_date, api_key="...")  — DuckDB 接続を渡して実行
   - レジーム判定:
     - from kabusys.ai.regime_detector import score_regime
     - score_regime(conn, target_date, api_key="...")

   - 注意:
     - `OPENAI_API_KEY` が必要（引数で渡すか環境変数で設定）。
     - API 呼び出しはリトライ・フェイルセーフの戦略が組み込まれています（エラー時はログ・ゼロフォールバック等）。

---

## 運用上のファイル / フラグ

- data/monitoring.db — 監視ログ SQLite（デフォルト SQLitE_PATH）
- data/paper_trading.db — Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）
- data/kabusys.duckdb（または data/kabusys.duckdb） — DuckDB（DUCKDB_PATH）
- data/execution.pid — ExecutionEngine の PID（PID_FILE_PATH）
- data/stop_requested.flag — 守護ループやエンジンを停止させるための外部フラグ
- data/kill.flag — KillSwitch が書き込む停止フラグ（ExecutionEngine を止める目的）

---

## ディレクトリ構成

主要ファイル・モジュールのツリー（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - run_monitoring.py
    - run_execution.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - __init__.py
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
      - streamlit_dashboard.py
    - execution/
      - order_manager.py
      - reconciler.py
      - (その他ブローカー・リポジトリ関連モジュール)
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - risk_adjustment.py
      - position_sizing.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - utils/
      - __init__.py
      - process_priority.py
    - data/  （実行時に使用するフラグ・DB を配置することが想定される）

上記の各モジュールはドキュメント文字列（docstring）や関数名・コメントで設計意図が明示されています。

---

## 注意点・運用上の留意事項

- Settings による環境変数管理:
  - `.env` / `.env.local` は自動で読み込まれる（プロジェクトルートが .git または pyproject.toml で判別される）。
  - OS の環境変数が優先されます。テスト等で自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Paper Trading の分離:
  - `KABUSYS_ENV=paper_trading` の場合、エンジンは paper_trading 用 DB を用い、実ブローカーと完全に分離して動作します。
- OpenAI API:
  - news_nlp / regime_detector は OpenAI を呼び出します。API キー管理、コスト、レート制限に注意してください。失敗時はフェイルセーフ（部分スキップ・ゼロフォールバック）がありますが、結果が欠落する可能性があります。
- プロセス優先度:
  - 起動スクリプトは可能な限りプロセス優先度を「high」に設定しようとします（権限不足時は警告でスキップ）。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db() は簡易的なマイグレーション（列追加）処理を含みます。既存 DB のバックアップを推奨します。
- ロギング:
  - 起動スクリプトは logging.basicConfig(level=logging.INFO) を使います。詳細ログは環境変数 LOG_LEVEL で指定可能（DEBUG/INFO/...）。

---

## よくあるコマンドまとめ

- 監視開始:
  - python -m kabusys.run_monitoring
- 実行エンジン開始:
  - python -m kabusys.run_execution
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

以上がこのコードベースの README 相当の説明です。追加で「環境変数のサンプル .env.example」や「requirements.txt の推奨一覧」「デプロイ手順（systemd / supervisor でのサービス定義例）」などが必要であれば、用途に合わせて追記します。