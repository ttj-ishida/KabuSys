# KabuSys

日本株自動売買システムのサンプル実装。ポートフォリオ構築、発注（ExecutionEngine）、監視（MonitoringEngine）、リサーチ / ファクター計算、AI を用いたニュースセンチメント評価などの主要コンポーネントを含みます。

以下はこのリポジトリの README（日本語）です。

- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（実行コマンド / 環境変数）
- ディレクトリ構成と主要ファイルの説明

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システム基盤です。主な関心は以下です。

- 戦略に基づく銘柄選定とポジションサイズ計算（等重/スコア/リスクベース）
- 発注エンジン（ExecutionEngine）とブローカークライアント抽象化
- 監視機能（System / Trade / Risk）とアラート（LINE へのプッシュ）
- モニタリング DB（SQLite）によるログの永続化と Streamlit ダッシュボード
- リサーチ用ファクター計算（DuckDB を用いた prices_daily / raw_financials 参照）
- AI（OpenAI）を使ったニュース NLP（銘柄別センチメント）と市場レジーム判定
- Paper Trading モード（本番 DB と分離）と検証レポート出力ツール

設計上の特徴:
- 設定は環境変数 / .env ファイルで管理（自動ロード機能あり）
- Paper Trading は本番 DB と完全分離（別 SQLite ファイル）
- 重要処理はフェイルセーフ: API エラーや DB 例外で致命的停止しない設計

---

## 機能一覧

- Portfolio
  - 銘柄候補選定（select_candidates）
  - 等金額・スコア加重のウェイト計算（calc_equal_weights, calc_score_weights）
  - ポジションサイズ計算（calc_position_sizes）
  - セクター集中制限・レジーム乗数（apply_sector_cap, calc_regime_multiplier）

- Execution
  - 発注管理（OrderManager）
  - リコンシリエーション（Reconciler）
  - RiskManager 等のリスク制御（設定可能）

- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス・データ鮮度監視
  - TradeMonitor: 滞留注文・約定価格異常の検出
  - RiskMonitor: ドローダウン・ポジション上限監視
  - KillSwitch: 条件に達すると data/kill.flag を生成して Execution を停止
  - AlertManager: LINE へ通知（クールダウン実装）
  - Streamlit ダッシュボード（監視情報の可視化）
  - monitoring DB（SQLite）: system_status, trade_logs, positions, risk_logs, dashboard

- Research
  - ファクター計算（momentum, volatility, value）
  - 将来リターン・IC・統計サマリ（feature_exploration）

- AI
  - ニュースセンチメント（news_nlp.score_news） — OpenAI（gpt-4o-mini）利用
  - レジーム判定（regime_detector.score_regime） — ETF MA とマクロ NLP を合成

- ツール
  - paper_verification_report: Paper Trading の検証レポート生成（稼働率・成功率・レイテンシ等）

---

## 前提（依存関係）

このリポジトリは次の Python ライブラリを利用します（最小限）:

- python >= 3.10（PEP 563 型注釈利用）
- duckdb
- psutil
- requests
- openai（OpenAI 新 SDK を想定）
- streamlit（ダッシュボード利用時）
- その他（標準ライブラリ: sqlite3, logging, threading, datetime 等）

インストール例:
- (推奨) 仮想環境を作成してから:
  - pip install duckdb psutil requests openai streamlit

プロジェクトに requirements.txt が無い場合は上記を個別にインストールしてください。

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置

2. データディレクトリを作成
   - data フォルダをプロジェクトルートに作成します（起動時に自動作成する処理もありますが、念のため）。
   - 例: mkdir -p data

3. 環境変数（.env）を用意
   - プロジェクトルートに `.env` または `.env.local` を置くと、自動でロードされます（.git または pyproject.toml がプロジェクトルートの目印になります）。
   - 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で便利）。

   代表的な設定項目（.env の例）:
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - OPENAI_API_KEY=...
   - KABUSYS_ENV=development|paper_trading|live
   - PAPER_FILL_MODE=instant|partial|never|reject
   - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   - SQLITE_PATH=data/monitoring.db
   - DUCKDB_PATH=data/kabusys.duckdb
   - LINE_CHANNEL_ACCESS_TOKEN=...
   - LINE_USER_ID=...
   - LOG_LEVEL=INFO
   - MONITOR_POLL_INTERVAL=60

   ※ Settings クラスで値の妥当性チェックを行います（PAPER_FILL_MODE や KABUSYS_ENV の有効値など）。

4. DB 初期化
   - Monitoring / Execution 起動時に `init_monitoring_db()` が呼ばれ、必要なテーブルを冪等に作成します。手動で初期化する必要は基本的にありません。

---

## 使い方

以下は主要コンポーネントの起動方法と注意点です。各スクリプトはパッケージ内モジュールとして実行できます。

- 実行（ExecutionEngine / 発注エンジン）の起動
  - python -m kabusys.run_execution
  - 動作:
    - プロセス優先度を "high" に設定し、Settings に基づいて SQLite / DuckDB に接続します。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用の専用 SQLite を使い、本番 DB と分離します。
    - data/stop_requested.flag ファイルが存在すると起動せず終了します。
    - 起動中に stop フラグを置くと安全に停止します（flag ファイルは data/stop_requested.flag）。

- 監視（MonitoringEngine）の起動
  - python -m kabusys.run_monitoring
  - 動作:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。不正な値は 60 秒にフォールバックします。
    - 監視は Settings の sqlite_path（本番 DB）を使用します（環境に関係なく同じ監視 DB を参照）。
    - stop フラグ（data/stop_requested.flag）が存在するとループを抜けて終了します。

- Streamlit ダッシュボード（監視 UI）
  - 起動コマンド（プロジェクトルートから）:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - read-only で SQLite DB を開き、ポジション・注文・システム状態・リスクログを表示します。

- Paper Trading 検証レポート
  - 実行:
    - python -m kabusys.tools.paper_verification_report
    - オプション:
      - --from YYYY-MM-DD
      - --to YYYY-MM-DD
      - --db PATH  （PAPER_TRADING_SQLITE_PATH が優先される）
  - 検証項目: 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシ、リスク却下数など。閾値に基づき PASS/FAIL を判定。

- AI 関連（ニューススコア / レジーム判定）
  - プログラムから呼び出す:
    - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key=None)
    - または regime_detector.score_regime(conn, target_date, api_key=None)
  - 注意:
    - OPENAI_API_KEY 環境変数、または api_key 引数で API キーを供給する必要があります。
    - API 呼び出しはリトライやフェイルセーフを備えますが、キー未設定時は ValueError が発生します。
    - news_nlp は銘柄ごとに記事を集約して LLM に送り、結果を ai_scores テーブルに書き込みます。

- 停止・強制停止
  - ExecutionEngine の停止は主に以下で行います:
    - KillSwitch（条件が満たされると data/kill.flag を作成）→ 実行側で確認して停止
    - data/stop_requested.flag を作成（run_* スクリプトがループ中に検知して終了）
  - kill.flag のクリア:
    - KillSwitch.clear() を呼ぶか、手動で data/kill.flag を削除してください。
  - Settings.kill_flag_clear_on_start が "1" の場合、起動時に kill.flag のクリーンアップを行う挙動を設定できます。

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: J-Quants トークン（必須）
- KABU_API_PASSWORD: kabu API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading の約定挙動）
- PID_FILE_PATH: Execution の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch フラグパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: 監視ループの秒間隔（整数、デフォルト 60）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

.env 自動ロード:
- プロジェクトルート（.git または pyproject.toml のあるディレクトリ）を基に `.env` と `.env.local` を読み込みます。
- 読み込み優先順位: OS 環境 > .env.local > .env
- 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## ディレクトリ構成（主要ファイルの説明）

以下は src/kabusys 以下の主要モジュールと簡単な説明です。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス（各種設定プロパティ、.env ロードロジック）
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプト（paper_trading 時は専用 DB を使用）
  - tools/
    - paper_verification_report.py
      - Paper Trading の検証レポート生成 CLI
  - portfolio/
    - portfolio_builder.py
      - 候補選定・重み計算関数
    - risk_adjustment.py
      - セクター制限・レジーム乗数
    - position_sizing.py
      - 発注株数算出ロジック
  - utils/
    - process_priority.py
      - psutil を用いたプロセス優先度 / CPU affinity の設定ユーティリティ
  - research/
    - factor_research.py
      - momentum / volatility / value ファクター計算（DuckDB を使用）
    - feature_exploration.py
      - 将来リターン計算 / IC / 統計サマリ
  - ai/
    - news_nlp.py
      - raw_news を集約して OpenAI でセンチメントスコアを計算し ai_scores に書き込む
    - regime_detector.py
      - ETF MA とマクロニュースの LLM スコアを合成して市場レジームを判定し書き込む
  - monitoring/
    - monitoring_db.py
      - monitoring DB の初期化と読み書きラッパー（MonitoringDB）
    - system_monitor.py
      - CPU/メモリ/ディスク/プロセス/データ鮮度監視
    - trade_monitor.py
      - 注文滞留・約定異常チェック
    - risk_monitor.py
      - ドローダウン・ポジション上限チェック
    - alert_manager.py
      - LINE への通知（クールダウン管理）
    - kill_switch.py
      - data/kill.flag を書くユーティリティ（KillSwitch）
    - monitoring_engine.py
      - 各 Monitor を束ねてポーリング・アラート発行
    - streamlit_dashboard.py
      - Streamlit で表示する監視ダッシュボード
  - execution/
    - order_manager.py
      - 発注の外向き API / Order State Machine
    - reconciler.py
      - 起動時の自動復旧処理（OrderSent の同期、ポジション差分チェック）
    - （その他: broker_factory, order_repository, order_record, risk_manager 等 - 発注関連の実装が含まれる想定）
  - data/（実行時に利用されるディレクトリ）
    - monitoring.db（SQLITE_PATH）
    - kabusys.duckdb（DUCKDB_PATH）
    - paper_trading.db（PAPER_TRADING_SQLITE_PATH）
    - execution.pid / stop_requested.flag / kill.flag などの制御ファイル

---

## 運用メモ / 注意点

- Monitoring は Settings.sqlite_path（監視 DB）を使用します。監視は本番 DB を見て行う設計になっているため、Paper Trading でも監視 DB は同じ場所を参照します（run_monitoring は環境に関係なく sqlite_path を使用します）。
- Execution は KABUSYS_ENV=paper_trading のとき paper_sqlite_path を使用して DB を完全分離します。
- .env のパースはシェル風の quoted value / コメント処理に対応しています。ただし特殊なケースでは期待通りに動かない場合があるため注意してください。
- OpenAI API 呼び出しはレート制限・ネットワーク断に対してリトライ実装がありますが、API キーの残高やポリシーによっては失敗します。失敗時は安全側の既定値（macro_sentiment=0 等）で継続する実装です。
- Streamlit ダッシュボードは監視 DB を read-only で開くため、MonitoringEngine が稼働していないと情報が乏しい可能性があります。
- process priority / CPU affinity の設定は OS に依存し、権限のない環境では失敗（警告ログ）します。

---

## よく使うコマンド例

- 監視を起動（60秒間隔、MONITOR_POLL_INTERVAL を上書き可能）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Execution 起動（Paper Trading）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Streamlit ダッシュボード起動
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート（期間指定）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- AI スコア処理（Python スクリプト内から）
  - from kabusys.ai import score_news
  - score_news(duckdb_conn, target_date, api_key="...")

---

この README はコードベースの主要部分をカバーしています。開発者向けにより詳細な設計ドキュメント（例: PortfolioConstruction.md、StrategyModel.md 等）がリポジトリ内にある想定です。運用上の質問や追加説明が必要であれば、どの部分を深掘りしたいか教えてください。