# KabuSys

日本株向け自動売買システム（ライブラリ / 実行スクリプト群）

このリポジトリは、シグナル生成・ポートフォリオ構築・発注エンジン・監視・AI ベースのニュースセンチメント集計などを備えた自動売買システムのコードベースです。モジュール設計により、ローカル開発（development）、ペーパートレード（paper_trading）、本番（live）を切り替えて運用できます。

---

## 概要

主なコンポーネント

- ExecutionEngine（発注エンジン）: 注文管理・リスク管理・ブローカークライアントを組み合わせて発注を行う。
- Monitoring（監視）: システム状態、注文ログ、リスク（ドローダウン・ポジション上限）を定期的にチェックし、kill flag やアラートを発動する。
- Portfolio モジュール: 銘柄選定・重み付け・株数決定（単元丸め）・セクター制約・レジーム乗数などの純粋関数群。
- Research／Feature モジュール: DuckDB の時系列データからファクター（モメンタム・ボラティリティ・バリュー）や将来リターン・IC を計算。
- AI モジュール: OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価（news_nlp）および市場レジーム判定（regime_detector）。
- Utilities: ロギング設定、プロセス優先度設定、設定読み込みウィザードと検証 CLI。
- Tools: ペーパートレード検証レポート生成スクリプトなど。

デフォルトの永続化先
- DuckDB: data/kabusys.duckdb
- SQLite（監視 DB）: data/monitoring.db
- Paper trading SQLite（KABUSYS_ENV=paper_trading）: data/paper_trading.db

---

## 機能一覧

- 環境設定ウィザード（.env の対話式生成）: python -m kabusys.config_setup
- 設定検証 CLI（.env と config/*.yaml の簡易チェック）: python -m kabusys.validate_config
- 実行エンジン起動スクリプト: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して paper_trading DB に記録（本番 DB と分離）
  - 停止用フラグファイル（data/stop_requested.flag / data/kill.flag）に対応
- 監視ループ起動スクリプト: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング周期を上書き可能（デフォルト 60 秒）
  - SystemMonitor は常に本番 sqlite_path を使用して監視情報を書き込む
- MonitoringEngine: SystemMonitor / TradeMonitor / RiskMonitor を束ねてアラート・Kill Switch を評価
- AI ベースのニューススコアリング（OpenAI API 必須）: kabusys.ai.score_news（DuckDB の raw_news を参照）
- 市場レジーム判定（ETF MA + マクロニュースの LLM スコア合成）: kabusys.ai.regime_detector.score_regime
- ペーパートレード検証レポート生成: python -m kabusys.tools.paper_verification_report
- ポートフォリオ構築: 候補選定 / 等配分・スコア配分 / ポジションサイズ計算 / セクターキャップ / レジーム乗数
- ロギング: 統一的設定（stdout と日次ローテーションファイル出力）
- プロセス優先度・CPU affinity 設定ユーティリティ（psutil 使用）

---

## 依存関係（主なもの）

最低限インストール推奨パッケージ（別途 requirements.txt を用意してください）:

- Python 3.8+
- duckdb
- psutil
- openai
- PyYAML（任意。validate_config が YAML 検証を行う場合に必要）

標準ライブラリ: sqlite3, logging, threading, datetime, pathlib など。

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動

   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境の作成（推奨）

   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows (PowerShell 等)
   ```

3. 必要パッケージのインストール

   例（最低限）:

   ```
   pip install duckdb psutil openai
   # YAML 検証を行う場合:
   pip install pyyaml
   ```

   ※ 実運用では requirements.txt を用意して `pip install -r requirements.txt` を推奨します。

4. 環境変数の設定
   - 対話式ウィザードを使う（推奨）:

     ```
     python -m kabusys.config_setup
     ```

     これによりプロジェクトルートに `.env`（上書き/生成）を作成できます。

   - もしくは手動で `.env` を作成し、必須キーを設定してください（下記参照）。

5. 設定検証（起動前チェック）

   ```
   python -m kabusys.validate_config
   # 警告を厳密に扱う場合:
   python -m kabusys.validate_config --strict
   ```

6. データディレクトリとログディレクトリは自動作成されますが、必要に応じて事前に作成・権限を確認してください。

---

## 必須 / 主要な環境変数

必須（最低限設定が必要）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

その他の主要設定（デフォルト値あり）
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL （デフォルト: INFO）
- LOG_DIR: ログ出力ディレクトリ（デフォルト: logs）
- OPENAI_API_KEY: OpenAI を使う機能を有効にする場合に必須
- PAPER_FILL_MODE: instant | partial | never | reject （paper_trading の fill 挙動）

監視・停止に関連
- PID_FILE_PATH: data/execution.pid（デフォルト）
- KILL_FLAG_PATH: data/kill.flag（デフォルト）
- KILL_FLAG_CLEAR_ON_START: 0 | 1（本番では 0 推奨）

実行時の短期オプション
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒）。run_monitoring で使用（デフォルト 60）

簡単な .env の最小例:

```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
OPENAI_API_KEY=sk-...
```

---

## 使い方（主要コマンド）

- 環境設定ウィザード（.env 生成）

  ```
  python -m kabusys.config_setup
  ```

- 設定検証

  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン起動

  - 通常起動（デフォルトで KABUSYS_ENV を参照）:

    ```
    python -m kabusys.run_execution
    ```

  - KABUSYS_ENV=paper_trading を指定して起動（環境変数で切り替え）:

    ```
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```

  - 注意点:
    - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
    - 実行中は data/execution.pid が作成されます。
    - Kill Switch（data/kill.flag）は ExecutionEngine を停止させるために監視から書き込まれます。

- 監視ループ起動

  ```
  python -m kabusys.run_monitoring
  ```

  - ポーリング間隔を上書きする場合:

    ```
    export MONITOR_POLL_INTERVAL=120  # 120 秒
    python -m kabusys.run_monitoring
    ```

  - 監視は監視 DB（SQLite）へ定期的に system_status / trade_logs / risk_logs / dashboard 等を書き込みます。

- Paper Trading 検証レポート

  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを明示する場合:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI 関連（プログラムから呼び出す）
  - ニューススコアリング: kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

  どちらも OpenAI API キー（OPENAI_API_KEY または api_key 引数）が必要です。プログラム内で DuckDB 接続を生成して渡します。

---

## 運用上の注意

- KABUSYS_ENV が `live` の場合は本番モードです。LINE 通知設定や kill flag の設定などを慎重に行ってください（validate_config が追加警告を出します）。
- process priority（高優先度）設定を行うため、psutil の権限や OS による制約で警告が出ることがあります。権限がない場合はスキップされます。
- Monitoring の SystemMonitor は「データ鮮度」を DuckDB の prices_daily 等から判定します。DuckDB のデータが最新でないとアラートが発生します。
- OpenAI を利用する機能は API 利用コストとレート制限に注意してください。エラーはリトライ・フェイルセーフ挙動を持ちますが、設定や API の状態に依存します。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要ファイルとディレクトリ構成の抜粋です（ファイル数が多いため主要モジュールのみ示します）。

- src/
  - kabusys/
    - __init__.py
    - config.py                     — 環境変数読み込み / Settings
    - config_setup.py               — .env 対話式ウィザード
    - validate_config.py            — 設定検証 CLI
    - run_execution.py              — ExecutionEngine 起動スクリプト
    - run_monitoring.py             — SystemMonitor ポーリング起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py
    - ai/
      - __init__.py
      - news_nlp.py                 — ニュース NLP（OpenAI）によるスコアリング
      - regime_detector.py          — 市場レジーム判定（MA + マクロ NLP）
    - portfolio/
      - __init__.py
      - portfolio_builder.py        — 候補選定 / 重み付け
      - position_sizing.py          — 株数決定・スケーリング
      - risk_adjustment.py          — セクター制約・レジーム乗数
    - research/
      - __init__.py
      - factor_research.py         — モメンタム/ボラ/バリュー等ファクター計算
      - feature_exploration.py     — 将来リターン / IC / 統計サマリ
    - monitoring/
      - monitoring_db.py           — SQLite 永続化レイヤ
      - monitoring_engine.py
      - system_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - (trade_monitor.py など：注文監視ロジック)
    - execution/
      - (execution_engine.py, order_manager.py, broker_factory 等：発注ロジック)
    - utils/
      - logging_setup.py           — ロギング設定ユーティリティ
      - process_priority.py        — 優先度/CPU affinity 設定ユーティリティ
      - __init__.py
    - data/                         — 実行時に使用する data ディレクトリ（ログ・DB・フラグファイル等）
    - config/                       — YAML 設定テンプレート（system_config.yaml 等）

---

## データファイル / フラグ（実行時）

- data/monitoring.db          — 監視用 SQLite（init_monitoring_db でテーブルとマイグレーションを実行）
- data/paper_trading.db      — ペーパートレード専用 SQLite（KABUSYS_ENV=paper_trading）
- data/kabusys.duckdb        — DuckDB（分析用）
- data/execution.pid         — ExecutionEngine の PID ファイル（生成）
- data/stop_requested.flag   — 起動中のスクリプトを停止するために存在検査されるフラグ
- data/kill.flag             — Kill Switch 発動により ExecutionEngine に停止シグナルを送るためのフラグ

---

## 開発者向けメモ

- 設定自動ロード:
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）から `.env` と `.env.local` を自動ロードします。
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化します（テスト時に便利）。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db() 実行時にテーブル作成および軽微なカラム追加（マイグレーション）を行います（冪等）。
- テスト:
  - OpenAI 呼び出しや外部 API 呼び出し部分は内部で分離されており、ユニットテスト時にモック可能です（例: patch で _call_openai_api を差し替え）。

---

必要に応じて README を拡張します。たとえば「各モジュールの API ドキュメント」「設定項目の詳細な説明」「運用 runbook（起動・停止・監視）」「requirements.txt」「例の .env.example」などを追加できます。どれを優先して追加しますか？