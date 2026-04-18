# KabuSys

日本株向けの自動売買システム（ライブラリ兼実行スクリプト群）。  
このリポジトリは、シグナル生成・ポートフォリオ構築・約定エンジン・監視・リサーチ・AI 補助（ニュース NLP / レジーム判定）など、プロダクション運用を想定したコンポーネント群を含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は次の主要サブシステムで構成されます。

- ExecutionEngine: ブローカーとのインタフェースを持ち実際の発注（またはペーパートレード）を行うエンジン
- Monitoring: システム健全性、注文の滞留、リスク（ドローダウン・ポジション数）を監視し、必要に応じて Kill Switch を発動
- Portfolio: 銘柄選定・重み付け・ポジションサイズ計算の純粋関数群
- Research: ファクター計算・特色探索（DuckDB を使った分析）
- AI: ニュース記事のセンチメント集計（OpenAI）と市場レジーム判定
- Tools: ペーパートレード検証レポート等の CLI ツール
- Config: .env の対話式ウィザード / 設定検証 CLI

設計上の特徴:
- 環境変数／.env による設定
- DuckDB（分析向け）と SQLite（監視／発注ログ）を併用
- paper_trading モードでは本番 DB と分離された paper_trading.db を使用
- OpenAI を利用したニューススコアリング（オプション）

---

## 主な機能一覧

- 環境設定ウィザード（python -m kabusys.config_setup）
- 起動前の設定検証（python -m kabusys.validate_config）
- ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading のときは MockBroker を使い data/paper_trading.db に記録
  - PID ファイル / 停止フラグにより安全停止制御
- Monitoring 起動スクリプト（python -m kabusys.run_monitoring）
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）
  - システム稼働状況・データ鮮度・滞留注文・リスクを監視しログとアラートを出す
- Kill Switch（data/kill.flag）: 条件を満たすと ExecutionEngine に停止シグナルを書き込む
- Paper Trading レポート生成ツール（python -m kabusys.tools.paper_verification_report）
- ポートフォリオ構築関数群（候補選定・重み付け・ポジションサイズ計算）
- Research（DuckDB ベースのファクター計算、IC 等の統計）
- AI ニュース NLP（OpenAI を使った銘柄ごとのセンチメントスコア）
- ロギングユーティリティ（コンソール + 日次ローテートファイル）

---

## セットアップ手順

1. リポジトリをクローン／配置
   - 本 README はパッケージルート（src 配下をパッケージとして想定）での利用を前提とします。

2. Python 環境準備
   - 推奨: Python 3.9+
   - 仮想環境を作成して有効化（venv / poetry / pipenv 等）

3. 必要パッケージをインストール
   - 必須（最低限）: duckdb, psutil
   - OpenAI 統合を使う場合: openai（openai Python SDK）
   - validate_config の YAML 検証を使う場合: PyYAML
   - 例（pip）:
     ```
     pip install duckdb psutil openai PyYAML
     ```
   - 注: requirements.txt は本コードベースに含まれていないため、用途に応じて必要パッケージを追加してください。

4. データ／ログ用ディレクトリを作成
   - デフォルト:
     - data/ (SQLite DB, kill/stop フラグ, pid ファイルなど)
     - logs/ (ログファイル)
   - 例えば:
     ```
     mkdir -p data logs
     ```

5. .env を作成
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
   - 必須環境変数（最低限設定するもの）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要な環境変数（一部抜粋、デフォルトあり）:
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - DUCKDB_PATH — default: data/kabusys.duckdb
     - SQLITE_PATH — default: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
     - LOG_LEVEL — default: INFO
     - OPENAI_API_KEY — OpenAI を使う場合に必要
     - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒）
   - .env は Git にコミットしないこと（秘密情報を含むため）

6. 設定検証（推奨）
   ```
   python -m kabusys.validate_config
   ```
   - 警告も失敗にする strict モード:
     ```
     python -m kabusys.validate_config --strict
     ```

---

## 使い方

以下は主な起動・利用手順例です。

- 監視サービスを起動（ポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を上書き:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 監視は SQLite（settings.sqlite_path）にログを永続化します。監視は KABUSYS_ENV に関係なく本番 sqlite_path を使います。

- ExecutionEngine を起動（発注エンジン）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます（本番 DB と分離）。
  - 実行は別スレッドで行われ、data/stop_requested.flag を配置すると安全に停止できます。
  - 起動時に PID ファイル（デフォルト data/execution.pid）を書きます。

- ペーパートレード検証レポート（CLI）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB: data/paper_trading.db。別パス指定は --db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH。

- AI 関連（プログラム呼び出し）
  - ニュース NLP のスコア付与:
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    written = score_news(conn, target_date=date(2026,4,10), api_key="sk-...")
    ```
  - レジーム判定:
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026,4,10), api_key="sk-...")
    ```
  - これらは OpenAI API キー（OPENAI_API_KEY 環境変数または api_key 引数）が必要です。

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- .env 作成ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 停止 / Kill Switch 管理
  - ExecutionEngine を停止させたい場合は監視側の KillSwitch が data/kill.flag を書き込みます。手動で停止させるには該当フラグファイルを作成してください（推奨は監視経由）。
  - 監視自体を止めたい（外部から）場合はプロジェクトルートの data/stop_requested.flag を作成します（run_monitoring/run_execution はこれを監視して終了します）。
  - kill.flag を手動でクリアする場合:
    ```
    rm data/kill.flag
    ```
    - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していると自動で消去されますが、本番では 0 を推奨します。

---

## 重要な環境変数（抜粋）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 運用関連
  - KABUSYS_ENV: development | paper_trading | live
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - OPENAI_API_KEY: OpenAI を利用する場合必須
  - MONITOR_POLL_INTERVAL: 監視ポーリング秒数（デフォルト 60）
  - PID_FILE_PATH, KILL_FLAG_PATH（Settings で参照）

詳しくは `src/kabusys/config.py` を参照してください。

---

## ディレクトリ構成

主要ファイル・ディレクトリは以下の通りです（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring ポーリング起動スクリプト
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ（コンソール + 日次ローテート）
    - process_priority.py     — プロセス優先度 / CPU affinity 設定
  - execution/                — 実際の発注ロジック群（Engine, BrokerFactory, OrderManager 等）
    - (実装ファイル群)
  - monitoring/
    - monitoring_db.py        — SQLite 用永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py       — システム状態 / データ鮮度チェック
    - trade_monitor.py        — 注文滞留・約定異常の検出（ファイル内参照）
    - risk_monitor.py         — ドローダウン・ポジション上限チェック
    - kill_switch.py          — kill.flag 書き込みロジック
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - alert_manager.py        — （アラート送信ロジック）
  - portfolio/
    - portfolio_builder.py    — 候補選定・スコアソート
    - position_sizing.py      — 発注株数計算（単元丸め・agg cap）
    - risk_adjustment.py      — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py      — Momentum / Volatility / Value 等のファクター計算（DuckDB）
    - feature_exploration.py  — 将来リターン / IC / 統計サマリー
  - ai/
    - news_nlp.py             — ニュースを OpenAI でスコアリングして ai_scores に書き込む
    - regime_detector.py      — ETF MA + マクロニュースでレジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成 CLI

上記に加え、プロジェクトルートに以下が想定されます:
- .env (機密情報のため Git 管理外)
- data/ (データベースファイル、フラグ、pid)
  - monitoring.db (デフォルト)
  - paper_trading.db (paper_trading 用)
  - kabusys.duckdb (DuckDB、デフォルト path は DUCKDB_PATH)
  - kill.flag, stop_requested.flag, execution.pid など
- logs/ (ログファイル)

---

## 運用上の注意

- 本番モード（KABUSYS_ENV=live）では Kill Switch / LINE 通知設定等を事前に十分確認してください。
- .env に機密情報（API トークン等）を含めるため、絶対にリポジトリにコミットしないでください。
- OpenAI を利用する部分は API 呼び出しの失敗を想定してフェイルセーフ実装（フォールバック値）になっていますが、API 利用料金やレート制限には注意してください。
- データ鮮度チェックやポジション制限などは設定で閾値を変更できます（config.yaml や環境変数で上書き可能な設計を想定）。
- ログはデフォルトで logs/<app_name>.log に日次ローテーション保存されます。ログディレクトリの権限とディスク容量を監視してください。

---

README はこのプロジェクト全体の概要と代表的な操作方法をまとめたものです。詳細な実装／設定は各モジュール（特に config.py、monitoring/*.py、execution/*）のドキュメントとソースコメントを参照してください。必要であれば、特定コンポーネント（例: ExecutionEngine の起動手順、AI モジュールの詳細設定）の追加ドキュメントを作成します。