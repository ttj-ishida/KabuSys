# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買システムのコア部分を含むライブラリ／起動スクリプト群です。  
本 README はコードベースの主要な機能、セットアップ、利用方法、およびディレクトリ構成を簡潔にまとめたものです。

注意: 本 README はソースコードに基づいて作成しています。実行環境や外部依存はプロジェクトの進行に伴い変わる可能性があります。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を提供します：

- 株価データの研究（DuckDB を利用したファクター計算・調査）
- ポートフォリオ構築（候補選定・重み算出・ポジションサイズ算出）
- Execution（発注エンジン）の起動ロジック（本番 / ペーパートレード切替）
- 監視（System / Trade / Risk）と Kill Switch による安全停止
- AI（OpenAI）を使ったニュースセンチメント・レジーム判定
- 運用支援ツール（設定ウィザード、設定検証、ペーパートレード検証レポート 等）

主要な設計方針：
- DB は DuckDB（分析用） と SQLite（監視・履歴）を利用
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と分離
- OpenAI 呼び出しは失敗時にフェイルセーフで続行する設計

---

## 機能一覧

- 環境設定管理
  - .env 自動読み込み（プロジェクトルート検出）
  - 対話式設定ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
- 起動スクリプト
  - 実行エンジン起動: run_execution.py
    - ペーパートレード時は MockBroker を使用し専用 SQLite に記録
    - PID / stop フラグを用いた制御
  - 監視ループ起動: run_monitoring.py
    - MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（デフォルト 60 秒）
    - 監視用 DB（SQLite）へログ保存
- 監視（monitoring パッケージ）
  - SystemMonitor: CPU/Mem/Disk・データ鮮度・実行プロセス健全性チェック
  - TradeMonitor: 注文ログのチェック（滞留注文・異常約定等）
  - RiskMonitor: ドローダウン・ポジション上限監視、リスクイベント記録
  - KillSwitch: 条件により data/kill.flag を作成して Execution を停止
  - MonitoringEngine: 各監視をまとめてポーリング・アラート送出
- ポートフォリオ構築（portfolio）
  - 候補選定、等金額／スコア加重配分、リスク調整（セクター上限、レジーム乗数）
  - ポジションサイズ計算（リスクベース、等分配等）、単元株丸め、aggregate cap
- 研究（research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- AI（ai）
  - news_nlp: OpenAI を用いたニュースセンチメントの銘柄別スコア化（ai_scores へ書込）
  - regime_detector: ETF の MA とマクロニュースを組合せた市場レジーム判定
- ユーティリティ
  - logging_setup: 統一ログ設定（stdout + 日次ローテートファイル）
  - process_priority: プロセス優先度 / CPU affinity 設定
- 運用ツール
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成

---

## 要件（推奨）

- Python 3.10+
  - ソースコードで | 型ヒント（Union 短縮表記）を使用しているため Python 3.10 以上を推奨します。
- 必須パッケージ（例）
  - duckdb
  - psutil
  - openai
- 任意（機能により）
  - PyYAML（validate_config の YAML 検証を有効にする場合）
- DB
  - SQLite（標準モジュール）
  - DuckDB（分析用ファイル）

インストール例:
```
python -m pip install duckdb psutil openai
# PyYAML が必要なら:
python -m pip install pyyaml
```

（requirements.txt は本コードベースに含まれていないため、実プロジェクトでは requirements.txt を用意することを推奨します）

---

## セットアップ手順

1. リポジトリをクローン / 配布ファイルを配置
2. Python 仮想環境作成とパッケージインストール
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
   - pip install duckdb psutil openai
   - （必要に応じて pip install pyyaml）
3. 環境変数（.env）作成
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
     ウィザードは .env（デフォルト: プロジェクトルート/.env）を生成します。
   - 自動読み込みを無効化したい場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
4. 設定検証（起動前に推奨）
   ```
   python -m kabusys.validate_config
   # 警告もエラー扱いにする場合:
   python -m kabusys.validate_config --strict
   ```
5. データディレクトリとログディレクトリの権限確認
   - デフォルトの DB / PID / flag は data/ 配下に置かれます。必要に応じて .env 内のパスを変更してください。
6. OpenAI を使う機能を利用する場合は OPENAI_API_KEY を設定

重要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development / paper_trading / live）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/...）
- OPENAI_API_KEY（AI 機能使用時）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔秒数、デフォルト 60）

---

## 使い方（主要スクリプト）

- 設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- 監視ループ起動（SystemMonitor のポーリング）
  - 環境変数 MONITOR_POLL_INTERVAL で秒間隔を上書き可能（例: 30 秒）
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  - run_monitoring は監視用 SQLite を初期化して SystemMonitor をループで呼びます。
  - 停止は data/stop_requested.flag を作成するか Ctrl+C。

- 実行エンジン起動（発注エンジン）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 専用 SQLite に記録します（本番 DB と分離）。
  - 実行中に data/stop_requested.flag を作るとエンジンを停止します。
  - 実行中は data/execution.pid が作成されます。

- ペーパートレード検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを指定する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- プログラムからの利用例（AI / research 等）
  - OpenAI を使ったニューススコアリング（例）
    ```py
    import duckdb
    from datetime import date
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    # OPENAI_API_KEY は環境変数か引数で渡す
    written = score_news(conn, target_date=date(2026, 4, 11), api_key="sk-...")
    print("書き込み銘柄数:", written)
    ```
  - 研究関数の呼び出し（例）
    ```py
    from kabusys.research import calc_momentum
    import duckdb
    from datetime import date

    conn = duckdb.connect("data/kabusys.duckdb")
    records = calc_momentum(conn, target_date=date(2026,4,11))
    ```

---

## 運用上の注意点

- Kill Switch / stop フラグ
  - KillSwitch は RiskMonitor 等の判定で data/kill.flag を作成して Execution を停止させる仕組みです。
  - run_execution/run_monitoring は data/stop_requested.flag を監視して安全にループを抜けます。
  - 本番で KILL_FLAG_CLEAR_ON_START=1 を設定することは危険です（Kill Switch を自動クリアするため）。Settings により警告を出します。

- DB の分離
  - paper_trading 環境では paper_trading 用 SQLite（デフォルト data/paper_trading.db）が使用され、本番 sqlite_path とは完全に分離されます。
  - Monitoring は環境にかかわらず本番 sqlite_path を使用する挙動（run_monitoring の docstring を参照）に注意してください。

- ログ設定
  - 共通の logging_setup を用い、コンソール（stdout）と日次ローテートファイル（logs/<app>.log）に出力します。
  - LOG_DIR を指定してログ出力先を変更できます。

- OpenAI API
  - AI 機能（news_nlp, regime_detector）は OpenAI API を使用します。API エラーやレート制限はリトライやフォールバックで耐性を持たせていますが、API キーとレート管理は運用側で注意してください。

---

## ディレクトリ構成（主要ファイル）

以下はリポジトリ内の主要なモジュール・ファイルの構成（抜粋）です:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings 管理（.env 自動ロード）
  - config_setup.py              — 対話式 .env 作成ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py (存在：監視ロジック)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (存在：アラート送信用)
  - execution/                    (発注エンジン関連)
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - data/ (実行時生成想定)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper trading 用)
    - execution.pid
    - kill.flag / stop_requested.flag
  - logs/ (ログ出力先、実行時作成)

（上記はコードベースに含まれる主要モジュールの一覧です。実際のプロジェクトではさらに多くの補助モジュールが存在する可能性があります）

---

## 追加情報

- 自動 .env ロード
  - config.py はプロジェクトルート（.git または pyproject.toml がある場所）を基準に .env/.env.local を自動読み込みします。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- マイグレーション
  - monitoring_db.init_monitoring_db は既存 DB に必要カラムがない場合に ALTER TABLE による簡易マイグレーションを行います。
- テスト・デバッグ
  - 各モジュールは可能な限り純粋関数・外部副作用を限定する設計になっています（研究/ポートフォリオ関数など）。ユニットテストのしやすさを意図しています。

---

必要であれば README のサンプル .env、より詳細な運用手順、デバッグ方法、各モジュールの API ドキュメントを追記します。どの情報を優先して追加しましょうか？