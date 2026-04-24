# KabuSys

日本株向け自動売買システムのリポジトリ（ライブラリ＋起動スクリプト群）。  
この README はコードベースの主要コンポーネント、セットアップ方法、使い方、ディレクトリ構成をまとめたものです。

注意: 実際に発注を行う本番環境（KABUSYS_ENV=live）で運用する場合は、設定値・権限・運用手順を厳密に確認してください。

---

## 概要

KabuSys は以下のような責務を持つ Python モジュール群で構成された自動売買システムのコアです。

- データ処理・研究（DuckDB を用いたファクター計算・特徴量探索）
- ポートフォリオ構築（候補選定・ウェイト計算・ポジションサイズ決定）
- 実行エンジン（注文発行、ブローカークライアント抽象化、リスク制御）※実装は execution パッケージを参照
- 監視（システム・注文・リスクの定期チェックとアラート / Kill Switch）
- AI 補助（ニュース NLP によるセンチメント、レジーム判定）
- 運用ツール（環境ウィザード、設定検証、ペーパートレード検証レポート）

主要な永続化は次のとおりです:
- DuckDB: 価格やファイナンスデータ、研究用テーブル（デフォルト `data/kabusys.duckdb`）
- SQLite: 監視ログ・トレードログ（デフォルト `data/monitoring.db`）、ペーパートレードは分離された `data/paper_trading.db`

---

## 主な機能一覧

- 環境設定ウィザード（.env の対話式生成）: kabusys.config_setup
- 設定検証 CLI（.env と config/*.yaml のチェック）: kabusys.validate_config
- 実行エンジン起動スクリプト: run_execution.py（KABUSYS_ENV によって paper_trading の分離動作）
- 監視ポーリング（SystemMonitor）起動スクリプト: run_monitoring.py
- 監視 DB レイヤー（SQLite）: monitoring.monitoring_db
- Risk Monitor / Trade Monitor / System Monitor を束ねる MonitoringEngine
- Portfolio Construction（候補選定・重み付け・ポジションサイズ計算）
- Research モジュール（momentum / volatility / value の計算、IC・統計サマリ等）
- AI モジュール（ニュースのセンチメント付与、レジーム判定）
- 運用ツール: paper_verification_report（ペーパートレード検証レポート生成）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンして作業ディレクトリへ移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境を作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール  
   （requirements.txt が無い場合は以下等を個別にインストール）
   ```
   pip install duckdb psutil openai
   # 解析時に PyYAML が必要なら:
   pip install pyyaml
   ```
   ※ openai SDK のバージョン差異に注意してください。

4. ディレクトリの準備
   ```
   mkdir -p data logs
   ```

5. 環境変数の設定（.env を作成）
   - 対話式ウィザードで .env を作成できます:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは `.env` を手動作成し、少なくとも以下は設定してください:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - KABUSYS_ENV（development / paper_trading / live）
     - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH（必要に応じて）
     - LOG_LEVEL（DEBUG/INFO/…）

6. 設定検証（任意だが推奨）
   ```
   python -m kabusys.validate_config
   # 警告も失敗にしたい場合:
   python -m kabusys.validate_config --strict
   ```

---

## 使い方（よく使うコマンド）

- 実行エンジンを起動（通常はサービスとして起動）:
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い `data/paper_trading.db` に書き込みます。
  - 起動時に `data/stop_requested.flag` が存在する場合は起動せず終了します。
  - 実行中は `data/execution.pid` に PID を書きます。

- 監視（Monitoring）を起動:
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可（デフォルト 60 秒）。
  - 監視モジュールは本番 sqlite_path を参照（監視用 DB は環境に依存せず基本的に本番パスを使用する設計）。

- 環境設定ウィザード:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート（任意期間）:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを明示する例:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI 機能（例: ニューススコア付与）をコード内から呼ぶ（DuckDB 接続を渡す）:
  ```py
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  cnt = score_news(conn, date(2026, 4, 1), api_key="sk-...")
  ```

- 停止フラグ / Kill Switch:
  - 監視 / 実行ループを外部から停止したい場合は `data/stop_requested.flag` を作成（存在するとループが検知して終了）。
  - 監視側の KillSwitch は `data/kill.flag` を書き込んで ExecutionEngine に停止シグナルを送る（一定条件時に作成される）。`KillSwitch.clear()` で削除可能。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に自動で kill.flag をクリアします（本番では 0 推奨）。

---

## 主要な環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

運用 / 動作制御:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
- OPENAI_API_KEY: AI 機能利用時に必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 本番アラート送信用（任意）

DB / パス:
- DUCKDB_PATH (例: data/kabusys.duckdb)
- SQLITE_PATH (例: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、例: data/paper_trading.db)
- PID_FILE_PATH (例: data/execution.pid)
- KILL_FLAG_PATH (例: data/kill.flag)

監視関連:
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定モデル（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動削除するか（"1"で有効）

---

## 運用上の注意点

- 本番（live）モードでは設定を慎重に行ってください。validate_config は live 時に注意を促すチェックを行います。
- ペーパートレードは実口座と完全に分離するよう設計されています（別 SQLite ファイル）。
- AI 呼び出しは外部 API（OpenAI）を使用します。API の失敗時にはフェイルセーフで継続する設計ですが、API キーの漏洩等に注意してください。
- ログはデフォルトで `logs/<app_name>.log` に日次ローテーションで保管されます。ログディレクトリが作れない場合はコンソール出力のみになります。
- run_* スクリプトはプロセス優先度を高（high）に設定する処理を含みます。実行権限や OS によっては設定できない場合があり、その場合は警告になります。

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内の主要ファイル（src/kabusys 以下）の抜粋です。

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込み
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py            — ニュース NLP / スコアリング
    - regime_detector.py     — レジーム判定
  - research/
    - factor_research.py     — momentum/value/volatility 計算
    - feature_exploration.py — forward returns / IC / 統計サマリ
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - monitoring/
    - monitoring_db.py       — SQLite スキーマ + DB ラッパ
    - system_monitor.py
    - trade_monitor.py       — （実装参照）
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py       — （実装参照）
  - execution/               — Execution エンジン関連（注文管理、broker factory 等）
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - data/                    — データパイプライン / DuckDB 連携（prices_daily など）
  - utils/
    - logging_setup.py
    - process_priority.py
  - research/                — 研究用ユーティリティ（zscore 等）

（実際のファイルはリポジトリ内の src/kabusys/ 以下を参照してください。上記はコード中に見える主要モジュールの一覧です。）

---

## 開発者向け補足

- DuckDB はリサーチ・AI モジュールの高速集計に使われます。DuckDB 接続オブジェクトを関数に渡す設計です。
- monitoring.monitoring_db.py は監視用の SQLite スキーマ作成（冪等）とマイグレーションを行います。DB 接続を渡して初期化してください。
- ai.news_nlp.py / ai.regime_detector.py は OpenAI API を呼び出します。API 呼び出し部分はテスト時に差し替えることを想定しています（関数ラッパー / patch によるモック）。
- set_process_priority / set_cpu_affinity は psutil に依存します。権限がないと警告を出してスキップします。

---

## お問い合わせ / 貢献

バグ修正・改善提案はプルリクエストまたは Issue にてお願いします。重大な本番運用に関する変更は、必ず事前にレビュー・検証を行ってください。

---

以上。README に載せてほしい追加情報（例: 実行例のログ、CI 設定、テストの実行方法など）があれば教えてください。