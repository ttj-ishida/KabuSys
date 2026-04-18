# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買・リサーチ基盤の一部です。  
主要な機能群（監視、発注エンジン、ポートフォリオ構築、ファクター計算、AI ニュース解析 等）を含み、ローカル・ペーパートレード・本番（live）環境を想定した設計になっています。

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（主要スクリプトの実行例）
- 環境変数一覧（主要）
- ディレクトリ構成（抜粋）
- 補足（運用メモ）

---

## プロジェクト概要

KabuSys は取引エンジン（ExecutionEngine）／監視（Monitoring）／リサーチ（DuckDB を使ったファクター計算や特徴量探索）／AI（ニュース NLP によるセンチメント評価、レジーム判定）を備えた日本株自動売買支援ライブラリです。構成要素はモジュール化されており、テストやペーパートレードに配慮した設計がされています。

主な設計方針：
- 環境ごとに設定を切り替え（development / paper_trading / live）
- Paper Trading は本番 DB と完全分離（data/paper_trading.db）
- DuckDB を分析用に利用（prices_daily / raw_financials 等を想定）
- OpenAI を用いたニュース解析・レジーム判定をサポート（API キー必須）
- 監視・Kill Switch による発注エンジンの安全停止機構

---

## 主な機能一覧

- 監視（monitoring）
  - システムリソース監視（CPU / メモリ / ディスク）
  - データ鮮度チェック（prices_daily の最新日付確認）
  - 発注状況・リスク（ドローダウン / ポジション上限）監視
  - kill.flag による ExecutionEngine 停止シグナルの発行
  - ログ永続化（SQLite：monitoring DB）

- 発注エンジン（execution）
  - Broker クライアント抽象化（本番 / Mock）
  - Order 管理、リスク管理、Reconciler、ExecutionEngine
  - Paper Trading 時は MockBrokerClient を使用して data/paper_trading.db に記録

- ポートフォリオ構築（portfolio）
  - 候補選定、等重・スコア加重配分、リスク調整（セクターキャップ）
  - 株数算出（リスクベース / 等分配 / スコア加重）、単元株丸め、aggregate cap の適用

- リサーチ（research）
  - DuckDB を使ったファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー

- AI（ai）
  - ニュース記事を LLM（gpt-4o-mini を想定）でセンチメント化して ai_scores に格納
  - マクロニュース＋ETF MA200 を組み合わせた市場レジーム判定（bull/neutral/bear）

- ユーティリティ
  - .env 対話ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 用検証レポート生成ツール（tools/paper_verification_report）
  - ロギング・プロセス優先度設定ユーティリティ等

---

## セットアップ手順

1. Python と依存パッケージをインストール
   - 推奨 Python バージョン: 3.9 以上（型注釈に対応したバージョンを推奨）
   - 必須ライブラリ（例）:
     - duckdb
     - psutil
     - openai
     - （オプション）PyYAML（設定ファイル検証で使用）
   - 例:
     ```
     pip install duckdb psutil openai
     pip install PyYAML  # 任意（validate_config の YAML 検証用）
     ```

2. リポジトリルートで .env を作成
   - 対話式ウィザードを利用:
     ```
     python -m kabusys.config_setup
     ```
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 生成された .env は Git にコミットしてはいけません（README 内にも注意書きあり）。

3. 設定の検証
   ```
   python -m kabusys.validate_config
   # 警告も厳格に FAIL とする場合:
   python -m kabusys.validate_config --strict
   ```

4. 初回起動で必要なディレクトリを作成
   - data/（データベース・フラグファイル）
   - logs/（ログ出力）
   - 多くのスクリプトは実行時に必要なら自動作成しますが、ファイル権限等を確認してください。

---

## 使い方（主要スクリプト）

※パッケージをモジュールとして実行します（リポジトリルートで実行）。

- 監視ループを起動
  - デフォルト：ポーリング間隔 60 秒（環境変数 MONITOR_POLL_INTERVAL で秒数を指定可能）
  ```
  python -m kabusys.run_monitoring
  ```
  - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使用します。
  - 停止方法：
    - data/stop_requested.flag を作成すると監視ループが検出して終了します（run_monitoring が使用）。
    - Kill switch による data/kill.flag は ExecutionEngine 停止用です（run_execution 側で参照）。

- 発注エンジン（ExecutionEngine）を起動
  - Paper Trading（擬似発注）モード:
    ```
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
    Paper Trading の場合、MockBrokerClient を使用し、データは data/paper_trading.db に記録されます（Settings.paper_sqlite_path）。
  - 本番モード:
    ```
    export KABUSYS_ENV=live
    python -m kabusys.run_execution
    ```
  - run_execution はデーモン的にスレッドでエンジンを起動し、data/stop_requested.flag の検知で停止します。
  - 実行時は data/execution.pid（デフォルト）に PID を書きます。

- .env の作成・更新（対話式）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB を指定する場合:
  ```
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```
  - 環境変数 PAPER_TRADING_SQLITE_PATH でデフォルト DB を上書き可能。

- AI / リサーチ機能の呼び出し（ライブラリとして利用）
  - OpenAI を使う機能は OPENAI_API_KEY 環境変数を設定してください。
  - 例（Python から）:
    ```py
    from kabusys.ai.news_nlp import score_news
    import duckdb, datetime
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=datetime.date(2026,4,1), api_key="sk-...")
    ```

---

## 環境変数（主要）

- KABUSYS_ENV: 実行環境（development / paper_trading / live） — デフォルト development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（ai/news_nlp, ai/regime_detector で使用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（monitoring）パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: Paper Trading でのフィルモード（instant / partial / never / reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログファイル出力先ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring で使用）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START など監視・運用関連

設定は .env（または .env.local）で管理できます。config.py はリポジトリルートの .env を自動読み込みします。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主なファイル/フォルダ抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_monitoring.py
  - run_execution.py
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - data/
    - pipeline.py
    - stats.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring scripts and DB initialization lives under monitoring/

- データ/ログ（実行時作成想定）
  - data/
    - monitoring.db (SQLite)
    - paper_trading.db (SQLite, paper_trading 用)
    - kabusys.duckdb (DuckDB)
    - execution.pid
    - kill.flag
    - stop_requested.flag
  - logs/
    - execution.log
    - monitoring.log
    - ...（日次ローテーション）

---

## 補足 / 運用メモ

- 監視（run_monitoring）は MONITOR_POLL_INTERVAL 環境変数（秒）で間隔を上書きできます。無効値はデフォルト 60 秒にフォールバックします。
- run_execution は KABUSYS_ENV=paper_trading のときに paper_trading 用 DB を使用し、本番 DB とデータを分離します。
- Kill Switch（kill.flag）は RiskMonitor と KillSwitch によって書き込まれます。ExecutionEngine は起動時に KILL_FLAG_CLEAR_ON_START を見て kill.flag を自動クリアするか判断します（本番では自動クリアを無効化することを推奨）。
- .env は機密情報を含むため絶対にコミットしないこと。
- OpenAI API を利用する機能はネットワークエラーやレート制限に対してリトライ・フェイルセーフが組み込まれていますが、APIキーや利用制限には注意してください。
- validate_config は設定ファイル（config/*.yaml）の存在・基本検証を行います。PyYAML がない場合は YAML 内容の検証はスキップされ、警告が出ます。

---

必要であれば README に「インストール例（requirements.txt）」や「実運用での systemd / Supervisor 設定例」「DB スキーマ説明」などを追加できます。どの情報を優先して補完するか教えてください。