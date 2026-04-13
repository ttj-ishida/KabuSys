# KabuSys

日本株自動売買システム KabuSys のコードベース README（日本語）

このリポジトリは、自動売買実行エンジン、監視（Monitoring）、ポートフォリオ構築やリサーチ、LLM を用いたニュースセンチメント評価などを含むモジュール群で構成されています。本 README ではプロジェクト概要、機能一覧、セットアップ手順、使い方、ディレクトリ構成をまとめます。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムです。主な責任は次のとおりです。

- 注文生成 → ブローカー送信 → 状態管理を行う ExecutionEngine
- 実行・監視（System / Trade / Risk）のための Monitoring サブシステム
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制限）
- リサーチ用のファクター計算（モメンタム / ボラティリティ / バリュー等）
- ニュースを LLM（OpenAI）でスコアリングして AI スコアを生成
- Paper Trading 向けのモードや検証用ツール（レポート生成）
- Streamlit による監視ダッシュボード

設計上の特徴：
- DuckDB（時系列・ファクターデータ）と SQLite（監視ログ・注文ログ）を併用
- 環境変数 / .env による設定（Settings クラス）
- Paper Trading（KABUSYS_ENV=paper_trading）では本番 DB と分離
- フェイルセーフ（API エラーや DB エラー時に必要以上に停止しない設計）

---

## 主な機能一覧

- Execution
  - 起動スクリプト: run_execution.py（ExecutionEngine を起動）
  - ブローカー抽象化（本番 / Mock を切替可能）
  - OrderManager / Reconciler（再起動時の同期・復旧処理）
  - RiskManager（発注前リスクチェック）

- Monitoring
  - run_monitoring.py：SystemMonitor のポーリングループを起動
  - SystemMonitor：プロセス状態・CPU/メモリ/ディスク・データ鮮度監視
  - TradeMonitor：滞留注文や約定価格異常の検出
  - RiskMonitor：ドローダウン・ポジション上限監視（kill.flag 発行）
  - AlertManager：LINE Push による通知（クールダウン有り）
  - Streamlit ダッシュボード（リアルタイム閲覧）

- Portfolio
  - 候補選定（select_candidates）
  - 等重・スコア重み付け（calc_equal_weights / calc_score_weights）
  - ポジションサイズ計算（calc_position_sizes）
  - セクターキャップ適用（apply_sector_cap）
  - レジーム乗数（calc_regime_multiplier）

- Research
  - ファクター計算（calc_momentum / calc_volatility / calc_value）
  - 将来リターン計算、IC 計算、特徴量サマリ（feature_exploration）

- AI
  - ニュース NLP（news_nlp.score_news）：OpenAI で銘柄別センチメントを算出し ai_scores に書込
  - レジーム検出（regime_detector.score_regime）：MA 乖離＋マクロニュースセンチメントで日次判定

- Tools
  - paper_verification_report：Paper Trading の検証レポート生成（稼働率・注文成功率・レイテンシ等）

---

## セットアップ手順

前提
- Python 3.10+（typing の Union short form や forward refs を使用）
- Git が使える環境

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # POSIX
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   - requirements.txt がある場合:
     ```
     pip install -r requirements.txt
     ```
   - ない場合は最低限必要なものを手動で:
     ```
     pip install duckdb psutil openai requests streamlit
     ```
   - 標準ライブラリ sqlite3 は Python に同梱されています。

4. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置けます。
   - 自動ロードはデフォルトで有効。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 主要な環境変数例（.env に設定）:
     ```
     KABUSYS_ENV=development        # development | paper_trading | live
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     OPENAI_API_KEY=...
     LINE_CHANNEL_ACCESS_TOKEN=...  # 通知用（任意）
     LINE_USER_ID=...               # 通知用（任意）
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     PAPER_FILL_MODE=instant        # instant|partial|never|reject
     PID_FILE_PATH=data/execution.pid
     KILL_FLAG_PATH=data/kill.flag
     MONITOR_POLL_INTERVAL=60       # run_monitoring のポーリング間隔（秒）
     ```

5. DB 初期化
   - run_monitoring / run_execution 実行時に監視用テーブル（MonitoringDB）を自動作成します（init_monitoring_db が冪等的に実行されます）。
   - DuckDB（prices_daily / raw_financials 等）は外部データロードが必要な場合があります（任意）。

---

## 使い方

以下は主要な実行方法の例です。

- ExecutionEngine を起動（本番 / paper_trading による切替）
  ```
  # production / development
  KABUSYS_ENV=live python -m kabusys.run_execution

  # paper trading（MockBrokerClient を使い、Paper DB に記録）
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```

  実行時に Process 優先度を High に設定します（内部で psutil を用いて設定）。Paper Trading の場合は `PAPER_TRADING_SQLITE_PATH` にログを保存します。

- Monitoring（SystemMonitor のポーリング）を起動
  ```
  # ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒）
  MONITOR_POLL_INTERVAL=120 python -m kabusys.run_monitoring
  ```

  監視は SQLite（settings.sqlite_path）にログを書き込みます。monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用します。

- Streamlit 監視ダッシュボード
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  監視 DB を読み取り専用で開いて表示します。MonitoringEngine を先に起動してデータを生成してください。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または DB を指定
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI 関連（プログラム的利用）
  - ニューススコアリング:
    - モジュール: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
    - DuckDB 接続（raw_news / news_symbols / ai_scores テーブル）を渡して実行します。
  - レジームスコア:
    - モジュール: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

  どちらも引数で API キーを渡すか、環境変数 `OPENAI_API_KEY` を設定してください。API リトライとフォールバックが組み込まれています。

- Process / Kill Flag
  - KillSwitch はリスク条件（ドローダウン / ポジション上限など）を満たすと `KILL_FLAG_PATH`（デフォルト: data/kill.flag）を書き込みます。ExecutionEngine 側でこのフラグを検出して安全に停止する仕組みを想定しています。
  - 起動時にフラグをクリアしたい場合は `KILL_FLAG_CLEAR_ON_START` を `1` に設定できます（Settings.kill_flag_clear_on_start を参照）。

---

## 設定（主な環境変数）

- KABUSYS_ENV: development | paper_trading | live（動作モード）
  - paper_trading: MockBrokerClient / 専用 SQLite に分離
  - live: 本番設定
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須箇所で使用）
- KABU_API_PASSWORD: kabuステーション API パスワード
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで使用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（Paper Broker のフィルモード）
- PID_FILE_PATH: ExecutionEngine の PID 保存先（デフォルト data/execution.pid）
- KILL_FLAG_PATH: Kill switch flag ファイルパス（デフォルト data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）

Settings クラスは .env / .env.local を自動でプロジェクトルートから読み込みます（OS 環境変数が優先）。ファイルの自動読み込みを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成

以下は主要ファイルとパッケージ構成（抜粋）です。実際にはさらに多くのモジュールが含まれますが、本 README ではプロジェクト内で参照される主要ファイルを示します。

- src/kabusys/
  - __init__.py
  - config.py                          — 環境変数／Settings 管理
  - run_execution.py                    — ExecutionEngine 起動スクリプト
  - run_monitoring.py                   — SystemMonitor ポーリング起動スクリプト

  - execution/
    - order_manager.py
    - reconciler.py
    - order_repository.py (参照あり)
    - broker_factory.py (参照あり)
    - execution_engine.py (参照あり)
    - ...（ブローカーインターフェース等）

  - monitoring/
    - monitoring_db.py                   — SQLite 監視テーブル定義・永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
    - __init__.py

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

  - tools/
    - paper_verification_report.py
    - __init__.py

  - utils/
    - process_priority.py
    - __init__.py

- data/
  - (デフォルトで使用される DB ファイルや pid / flag を配置する場所)
    - kabusys.duckdb
    - monitoring.db
    - paper_trading.db
    - execution.pid
    - kill.flag

---

## 運用上の注意点 / ベストプラクティス

- 環境分離: paper_trading を使うときは必ず `KABUSYS_ENV=paper_trading` を設定し、Paper 用 DB（PAPER_TRADING_SQLITE_PATH）を確認してください。本番 DB を上書きしないよう注意してください。
- API キー管理: OpenAI キーや外部トークンは .env / 環境変数で管理し、リポジトリにコミットしないでください。
- モニタリング: run_monitoring は監視ログとリスク検出（kill.flag 発行）を行います。ExecutionEngine と連携して安全に稼働を停止させる運用を検討してください。
- DB バックアップ: DuckDB / SQLite のバックアップ・ローテーションを運用してください。特に paper_trading.db と monitoring.db の整合性に注意。
- 権限: `set_process_priority`、`set_cpu_affinity` は権限や OS によって動作が制限される場合があります。ログを確認してください。
- ロギング: 起動スクリプトは標準で INFO レベルの基本設定を行います。詳細なデバッグが必要な場合は LOG_LEVEL を設定してください。

---

## 追加情報 / 開発者向け

- テスト・モック: AI 呼び出しや外部 API はモック可能な設計（関数分離、_call_openai_api の差し替え）になっています。ユニットテスト時は patch して外部呼び出しを差し替えてください。
- DB マイグレーション: monitoring_db.init_monitoring_db は既存 DB に対して安全に列追加（例: peak_value / latency_ms）を行います。
- 冪等性: 多くの書き込み操作（dashboard upsert、ai_scores 書き換え等）は冪等性を考慮して実装されています。

---

この README はコードベース提供分の主要機能と運用手順をまとめたものです。より詳しい API 仕様、Strategy / PortfolioConstruction ドキュメントや具体的な ExecutionEngine の設定は別ドキュメント（設計書）を参照してください。必要であれば README に追加したい内容（例: 具体的な設定例、requirements.txt の生成、運用例）を教えてください。