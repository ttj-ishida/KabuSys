# KabuSys

日本株自動売買システム（簡易版）  
このリポジトリは、シグナル生成・ポートフォリオ構築・注文実行（本番/ペーパー）・監視・研究用ユーティリティを含むパッケージ構成の例です。README は開発者・運用者向けに主要コンポーネント、セットアップ、起動手順、ディレクトリ構成をまとめています。

---

## プロジェクト概要

KabuSys は以下の機能を持つモジュール群で構成された自動売買フレームワークのサンプル実装です。

- データ解析・ファクター計算（DuckDB を前提）
- ポートフォリオ構築（候補選定、重み付け、株数決定、セクター制約）
- 発注実行エンジン（本番 / ペーパー分離）
- 監視（システム監視・注文監視・リスク監視）と Kill Switch
- AI（OpenAI を用いたニュースセンチメント / レジーム判定）
- 開発支援ツール（.env ウィザード、設定検証、ペーパートレード検証レポート）

設計上の特徴：
- 環境変数（.env）で設定を管理（自動ロード機能あり）
- ペーパートレードは本番 DB と分離（専用 SQLite）
- 監視は本番監視 DB に対して常に記録（KABUSYS_ENV に依存しない）
- OpenAI を用いる機能は API キーが必要。失敗時はフォールバックする実装多数。

---

## 主な機能一覧

- config
  - .env 自動読み込み / Settings ラッパー（kabusys.config）
  - 対話式 .env 作成ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
- execution
  - ExecutionEngine 起動スクリプト（kabusys.run_execution）
  - ブローカークライアント抽象化（本番 / Mock を切替）
  - リスク管理・注文管理・帳票保持
- monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine
  - 監視ログ永続化（SQLite via monitoring_db）
  - KillSwitch（条件に応じて data/kill.flag を作成）
  - run_monitoring 起動スクリプト
- portfolio
  - 銘柄選定・重み計算・単元丸め（等金額・スコア加重・リスクベース等）
  - セクター制約、レジーム乗数
- research
  - ファクター計算（momentum, volatility, value）
  - 将来リターン・IC 計算、特徴量要約
- ai
  - ニュース NLP によるセンチメント評価（OpenAI）
  - レジーム判定（MA200 と LLM による組合せ）
- tools
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

---

## セットアップ手順（開発・実行の流れ）

1. リポジトリをクローンし、仮想環境を作成
   - 例:
     ```
     git clone <repo-url>
     python -m venv .venv
     source .venv/bin/activate  # Windows: .venv\Scripts\activate
     ```

2. 依存パッケージをインストール
   - requirements.txt がある想定で:
     ```
     pip install -r requirements.txt
     ```
   - 必須ライブラリ（コード参照）：
     - duckdb
     - psutil
     - openai（ai 機能を使用する場合）
     - PyYAML（設定検証で YAML 検証を行う場合）
     - など

3. .env の作成（推奨: ウィザード）
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
   - 手動で `.env` を作る場合は `.env.example` を参考に必要な環境変数を設定してください。

4. 設定検証（起動前チェック）
   ```
   python -m kabusys.validate_config
   # 厳密モード（警告も失敗扱い）
   python -m kabusys.validate_config --strict
   ```

5. （Optional）ログディレクトリの作成
   - デフォルト: `logs/`。`LOG_DIR` 環境変数で変更可。

---

## 主要環境変数（代表）

必須
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

よく使う任意／上書き可能なキー
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 時に使用）
- OPENAI_API_KEY: OpenAI API キー（ai 機能で必要）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
- LOG_DIR: ログ保存先ディレクトリ
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 本番で Kill Flag を自動クリアするか（0/1）

注記:
- 自動 .env 読み込みはデフォルトで有効。無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。
- run_monitoring は Monitoring を行う際、KABUSYS_ENV に依存せず常に `sqlite_path`（本番監視 DB）を使用します。
- run_execution は `KABUSYS_ENV=paper_trading` の場合、`PAPER_TRADING_SQLITE_PATH` の DB を使用して本番 DB と完全分離します。

---

## 実行方法（コマンド例）

- 監視ループを起動（ポーリング）
  ```
  python -m kabusys.run_monitoring
  # ポーリング間隔を変更したい場合
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- ExecutionEngine を起動（注文エンジン）
  ```
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` のときは MockBrokerClient が使われ、指定の paper DB に記録されます。
  - 起動時・停止は `data/stop_requested.flag` や `data/kill.flag` を用いるフラグファイルで制御する仕組みがあります。

- .env ウィザード（対話式）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート（SQLite DB を指定可能）
  ```
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 関連（ライブラリ関数呼び出し例、スクリプトは用意されていません）
  - ニューススコアリング:
    ```
    from kabusys.ai.news_nlp import score_news
    score_news(conn=duckdb_conn, target_date=date(2026,4,10), api_key="...")
    ```
  - レジーム判定:
    ```
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn=duckdb_conn, target_date=date(2026,4,10), api_key="...")
    ```

---

## 特記事項（運用に関する注意）

- Kill Switch / Stop フラグ
  - `kabusys.monitoring.kill_switch` はリスク条件に応じて `data/kill.flag` を書き込みます。ExecutionEngine は flag を検出すると停止する設計です。
  - `data/stop_requested.flag` は run_monitoring / run_execution スクリプトの手動停止制御に使用されます。

- ログ設定
  - 共通の `kabusys.utils.logging_setup.setup_logging()` を用いて、コンソールと日次ローテートファイルを設定します。
  - デフォルトログディレクトリは `logs/`、ファイル名はサービス名（例: `execution.log` / `monitoring.log`）です。

- DB 初期化
  - run 系スクリプトは起動時に monitoring のテーブル群を作る `init_monitoring_db()` を呼び出します（冪等）。既存 DB へマイグレーション（列追加）も含みます。

- OpenAI 利用
  - AI 機能は `OPENAI_API_KEY` を要求します。API 呼び出しはリトライ・フォールバックを組み込んでいますが、キーが未設定だと一部 API はエラーになります（関数は例外を投げる場合があります）。

---

## 使い方（簡単なワークフロー例）

1. .env を作成（ウィザード推奨）
2. 設定検証を実行
3. DuckDB / SQLite の初期データ準備（prices_daily / raw_news / raw_financials 等の取り込みは別途）
4. 監視を起動（常時稼働）
   - 監視が動いている間は system_status / risk_logs / trade_logs などが `SQLITE_PATH` の DB に記録されます。
5. ExecutionEngine を起動（本番 / ペーパー切替）
6. 必要に応じて AI レジーム判定やニューススコアを定期実行し、market_regime / ai_scores に書き込む
7. ペーパートレード解析・検証は tools のレポートを利用

---

## ディレクトリ構成（抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / Settings
    - config_setup.py          — .env ウィザード（対話式）
    - validate_config.py       — 設定検証 CLI
    - run_monitoring.py        — Monitoring ポーリングスクリプト
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - utils/
      - logging_setup.py       — 共通ログ設定
      - process_priority.py    — プロセス優先度設定
    - monitoring/
      - monitoring_db.py       — SQLite テーブル定義・永続化
      - system_monitor.py
      - trade_monitor.py       — （省略ファイルあり）
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py       — （省略）
    - execution/
      - execution_engine.py    — 実行エンジン（EntryPoint）
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
    - ai/
      - news_nlp.py
      - regime_detector.py
    - tools/
      - paper_verification_report.py

その他: `data/`（DB・pid・フラグファイル等）、`logs/`（ログ）を想定。

---

## 開発者向け補足

- モジュール設計は「ビジネスロジックと永続化の分離」「フェイルセーフな外部 API 呼び出し」「本番 / ペーパーの分離」を重視しています。
- テストでは env 自動ロードを無効化するため `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を利用してください。
- DuckDB / SQLite のスキーマ・データは別途データ投入スクリプト（pipeline 等）を用意して利用します。

---

以上。必要があれば以下を追加できます：
- .env.example のサンプル
- systemd / docker Compose 用の起動例
- 詳細な API リファレンス（各関数の入出力仕様）