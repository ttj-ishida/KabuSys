# KabuSys — 日本株自動売買システム

このリポジトリは、バックテスト／運用のための各種コンポーネントを備えた日本株自動売買基盤「KabuSys」の実装です。  
主要機能は注文の実行・リコンシリエーション、ポートフォリオ構築、ファクター計算、監視（モニタリング）、およびニュースの NLP によるスコアリング（OpenAI）などです。

---

## プロジェクト概要

- Python ベースの自動売買／リサーチ基盤
- モジュール化された設計（execution, portfolio, research, ai, monitoring, tools, utils 等）
- 本番（live）／ペーパー取引（paper_trading）／開発（development）を環境変数で切替可能
- DuckDB を用いた時系列データ処理、SQLite による監視ログ保存
- OpenAI を利用したニュースセンチメント評価・市場レジーム判定（APIキーが必要）
- Streamlit による監視ダッシュボード（read-only 接続）

---

## 主な機能一覧

- Execution（注文実行）
  - ExecutionEngine（起動スクリプト: run_execution.py）
  - Broker クライアント抽象化（本番/Mock 切替）
  - OrderManager / OrderRepository / Reconciler（再起動時の自動復旧）
  - RiskManager（発注制限など）

- Monitoring（監視）
  - SystemMonitor：CPU/メモリ/Disk、プロセス存在チェック、データ鮮度チェック
  - TradeMonitor：滞留注文・約定異常チェック
  - RiskMonitor：ドローダウン・ポジション上限検出
  - KillSwitch：フラグファイルによる ExecutionEngine 停止指示
  - AlertManager：LINE へのプッシュ通知
  - MonitoringEngine：各モニタの統合ポーリング
  - Streamlit ダッシュボード（src/kabusys/monitoring/streamlit_dashboard.py）

- Portfolio（ポートフォリオ構築）
  - 銘柄選定、等金額・スコア加重の重み算出
  - リスク調整（セクター上限、レジーム乗数）
  - 株数決定（リスクベース、等配分など）と単元株丸め

- Research（調査・特徴量）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー

- AI（ニュース NLP / レジーム判定）
  - news_nlp.score_news: raw_news を集約して OpenAI へ投げ、銘柄ごとの ai_score を ai_scores テーブルへ書込
  - regime_detector.score_regime: ETF の MA とマクロ記事センチメントを合成して market_regime を書込

- Tools
  - paper_verification_report: Paper Trading DB を集計して検証レポートを生成

---

## セットアップ手順（概要）

※ 以下はリポジトリ内コードに基づく一般的なセットアップ手順です。環境・ポリシーに応じて調整してください。

1. Python（推奨: 3.10 以上）を用意する
2. 必要なパッケージをインストール
   - 主要依存例: duckdb, psutil, requests, openai, streamlit
   - 例:
     - pip install duckdb psutil requests openai streamlit
     - 実際は requirements.txt を用意している場合はそれを使用してください
3. データディレクトリを作成
   - data/ ディレクトリ等を作成し、書き込み権限を確認する
4. 環境変数配置 (.env)
   - プロジェクトルート（.git や pyproject.toml を検出できる位置）に `.env` または `.env.local` を置くと自動ロードされます（自動ロード無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）
   - 主な環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...（AI 機能を使う場合必須）
     - KABUSYS_ENV=development | paper_trading | live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - PAPER_FILL_MODE=instant | partial | never | reject
     - LOG_LEVEL=INFO
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - MONITOR_POLL_INTERVAL（監視ポーリング秒、デフォルト 60）
   - サンプル .env（例）
     ```
     KABUSYS_ENV=paper_trading
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     LINE_CHANNEL_ACCESS_TOKEN=
     LINE_USER_ID=
     ```
5. DB 初期化
   - Monitoring 用の SQLite テーブルは run_execution / run_monitoring 起動時に自動作成（init_monitoring_db）されます
   - DuckDB のスキーマ（prices_daily / raw_financials 等）は別途 ETL / データ投入処理が必要です（本リポジトリ外のデータパイプライン）

注意: psutil によるプロセス優先度設定や CPU affinity 設定は OS と権限に依存します。権限不足時は警告が出てスキップされます。

---

## 使い方（実行例）

各スクリプトはパッケージモジュールとして実行できます。リポジトリルートで以下を実行してください。

- 実行エンジン（ExecutionEngine）起動（本番またはペーパー）
  - KABUSYS_ENV を設定して起動します（paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録されます）
  - 例（ペーパー取引）:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
  - 例（開発 / live）:
    - export KABUSYS_ENV=development
    - python -m kabusys.run_execution

- 監視ループ起動（Monitoring）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60）
  - python -m kabusys.run_monitoring
  - 例:
    - export MONITOR_POLL_INTERVAL=30
    - python -m kabusys.run_monitoring

- Streamlit ダッシュボード（ローカルで監視状況を可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数の代替）
  - 例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- AI / 研究系関数の実行（ライブラリ呼び出し）
  - news_nlp.score_news(conn, target_date, api_key=...) — DuckDB 接続を渡して呼ぶ
  - regime_detector.score_regime(conn, target_date, api_key=...)
  - research.calc_momentum(conn, target_date) など
  - これらはライブラリ関数（CLI は用意していません）。スクリプトやジョブからインポートして利用します。

---

## 設定の自動読み込みについて

- .env / .env.local をプロジェクトルートに置くと、起動時に自動で読み込まれます（既存 OS 環境変数は保護されます）
- 自動ロードを無効化するには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- Settings クラス（kabusys.config.Settings）で必要な環境変数の検証を行います。必須変数が未設定の場合は起動時に例外が発生します。

主要な Settings プロパティ（抜粋）:
- jquants_refresh_token (必須)
- kabu_api_password (必須)
- kabu_api_base_url (既定: http://localhost:18080/kabusapi)
- line_channel_access_token, line_user_id
- duckdb_path, sqlite_path, paper_sqlite_path
- paper_fill_mode (instant | partial | never | reject)
- pid_file_path, kill_flag_path, kill_flag_clear_on_start
- cpu_threshold_pct, memory_threshold_pct, disk_threshold_pct
- KABUSYS_ENV の有効値: development, paper_trading, live

---

## ディレクトリ構成（主なファイル）

以下は src/kabusys 以下の主要な構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / .env 読み込みと Settings
  - run_execution.py  — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - execution/
    - order_manager.py
    - reconciler.py
    - order_repository.py (※一部コードは省略)
    - execution_engine.py (※存在する想定)
    - broker_factory.py / broker_api.py（ブローカー抽象）
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
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - utils/
    - process_priority.py
    - __init__.py
  - data/ (想定: データファイル・DB を格納)
    - kabusys.duckdb
    - monitoring.db
    - paper_trading.db

---

## 実運用上の注意・トラブルシュート

- Paper Trading と本番 DB は分離されています（KABUSYS_ENV=paper_trading のとき PAPER_TRADING_SQLITE_PATH を使用）。
- run_execution / run_monitoring 起動時にプロセス優先度を試行的に "high" に設定します（OS 権限がない場合は警告が出てスキップ）。
- Monitoring は監視ログ（SQLite）を永続化します。初回起動時にテーブルを自動作成します。
- OpenAI を使う機能は API キーが必須です。キー未設定時は ValueError を返す設計の関数があります。
- psutil 等システムライブラリは OS に依存する挙動や権限エラーが発生することがあります（警告ログが出ます）。
- MONITOR_POLL_INTERVAL を 0 や負の数に設定すると無効扱いになり、デフォルト（60秒）にフォールバックします。
- kill.flag 機能で ExecutionEngine を停止する際は、該当ファイルが存在するか確認してください（kill.flag の既存時は再書き込みされません）。

---

## 開発・拡張ガイド（簡単な指針）

- DuckDB 側のテーブル（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, market_regime など）はデータパイプラインから供給すること。
- 新しい監視ルールやリスクポリシーは monitoring/ 以下に Monitor クラスを追加し、MonitoringEngine に組み込む。
- ブローカー実装は execution/broker_api.py のプロトコルに従って実装。テスト用に MockBroker を用意しておくと便利。
- AI 関連は外部 API 呼び出し部を小さなラッパー関数で囲っておくとユニットテストで差し替えやすい（既にその設計がなされています）。

---

もし README に追加したい内容（要求例: CI 設定、Dockerfile、より詳しいコマンド例、DB スキーマ定義、ユニットテストの実行方法など）があれば教えてください。必要な箇所を追記・詳細化します。