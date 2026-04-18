# KabuSys

日本株向け自動売買システムのコアライブラリ／起動スクリプト群。

本リポジトリは取引実行エンジン、監視/アラート、ポートフォリオ構築、リサーチ（ファクター計算）、
および AI（ニュース NLP / レジーム判定）関連のユーティリティを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の関心事を分離したモジュール群で構成されています。

- ExecutionEngine：ブローカークライアントを使って注文を実行するエンジン（本番/ペーパートレード両対応）
- Monitoring：システム状態、注文状況、リスク（ドローダウン・ポジション数）を定期チェックして永続化／アラート発行
- Portfolio：銘柄選定・重み計算・ポジション切り上げ（単元）・リスク調整
- Research：DuckDB 上でファクター（モメンタム・ボラティリティ・バリュー）や IC 等を計算するための関数群
- AI：ニュースを LLM（OpenAI）でスコアリングし、銘柄・市場レジーム判定に利用
- Tools：Paper Trading 検証レポート生成などのユーティリティスクリプト
- Config：環境変数/.env の管理・ウィザード・検証

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py：ExecutionEngine を起動（KABUSYS_ENV に応じて本番 or ペーパートレード）
  - run_monitoring.py：SystemMonitor を定期ポーリングして監視ログを記録
- 設定ユーティリティ
  - config_setup.py：.env 対話式ウィザードで生成／更新
  - validate_config.py：起動前に環境変数や config/*.yaml を検証
- 監視
  - system_monitor, trade_monitor, risk_monitor：CPU/メモリ/ディスク、プロセス存在、滞留注文、ドローダウン、ポジション上限のチェック
  - monitoring_db：SQLite 上に監視テーブルを作成／マイグレーション
  - kill_switch：危険条件で data/kill.flag を書き込み Execution を停止させる仕組み
- ポートフォリオ構築
  - 候補選定、等金額/スコア重み、リスクベースの株数算出、セクターキャップ適用、レジーム乗数
- リサーチ
  - DuckDB を使ったファクター計算（モメンタム、ボラティリティ、バリュー）、将来リターン、IC、要約統計
- AI
  - ニュースの LLM によるセンチメントスコア化（gpt-4o-mini を想定）
  - 市場レジーム判定（ETF ma200 とマクロセンチメントの合成）
- ツール
  - paper_verification_report：ペーパートレード DB から検証レポートを生成

---

## 要件（推奨）

必須パッケージはプロジェクトの用途により変わりますが、主に次を想定しています。

- Python 3.9+
- duckdb
- psutil
- openai
- pyyaml（設定検証で YAML を検証する場合）
- （SQLite は標準ライブラリで利用可）

インストール例（プロジェクトに requirements.txt がある前提）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# または最低限:
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成して依存をインストールします（上記参照）。

2. .env を作成
   - 対話式ウィザードを使う:
     ```bash
     python -m kabusys.config_setup
     ```
   - または手動でプロジェクトルートに `.env` を作成。主な環境変数（例）:
     ```
     KABUSYS_ENV=development            # development | paper_trading | live
     JQUANTS_REFRESH_TOKEN=your_token
     KABU_API_PASSWORD=your_password
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO
     KILL_FLAG_CLEAR_ON_START=0
     # paper trading などを使う場合:
     PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     PAPER_FILL_MODE=instant           # instant | partial | never | reject
     ```

3. 設定検証（起動前チェック）:
   ```bash
   python -m kabusys.validate_config
   # 警告も FAIL としたい場合:
   python -m kabusys.validate_config --strict
   ```

4. データ・ログディレクトリの準備（多くの処理は自動作成しますが、手動で作成しておくと安心です）:
   ```bash
   mkdir -p data logs
   ```

---

## 実行方法（使い方）

- ExecutionEngine（取引実行）を起動:
  - 本番／開発／ペーパートレードは KABUSYS_ENV で切替。ペーパートレード時は専用 DB（data/paper_trading.db）を使用します。
  ```bash
  # 例: ペーパートレードで起動
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```
  - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
  - 実行中に同フラグが生成されるとエンジンが停止します（kill/stop 制御）。

- Monitoring（監視）を起動:
  ```bash
  # ポーリング間隔は MONITOR_POLL_INTERVAL で上書き（秒）
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  - Monitoring は Settings にかかわらず本番 sqlite_path を使用して監視ログを永続化します。
  - 停止フラグ: プロジェクトルート/data/stop_requested.flag

- Paper Trading 検証レポート生成:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を指定する場合:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI / レジーム判定 / ニューススコアリング（ライブラリ関数）
  - news NLP:
    ```py
    from kabusys.ai.news_nlp import score_news
    # duckdb_conn は duckdb.connect() の接続オブジェクト
    n_written = score_news(duckdb_conn, target_date, api_key="OPENAI_KEY")
    ```
  - regime 判定:
    ```py
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="OPENAI_KEY")
    ```

---

## 主な設定項目（Settings / 環境変数）

- 必須（起動検証でチェック）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 任意／デフォルト付き
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
  - LOG_LEVEL (default: INFO)
  - PAPER_FILL_MODE: instant | partial | never | reject (default: instant)
  - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START / 各種閾値（CPU/MEM/DISK）

詳細は `src/kabusys/config.py` の Settings クラスを参照してください。

---

## ログ・永続化

- ログ: デフォルト `logs/` 以下にアプリケーション名ごとのファイル（例: logs/execution.log, logs/monitoring.log）。`LOG_DIR` 環境変数で変更可。
- 監視 DB（SQLite）: `data/monitoring.db`（`SQLITE_PATH` で変更可）
- ペーパートレード DB（SQLite）: `data/paper_trading.db`（`PAPER_TRADING_SQLITE_PATH`）
- DuckDB（分析用）: `data/kabusys.duckdb`（`DUCKDB_PATH`）

---

## 安全に関する注意

- KABUSYS_ENV=live を設定すると本番動作になります。`validate_config.py` は live 時に複数の注意喚起を行います。LINE 通知の設定など本番用の設定漏れに注意してください。
- kill flag（data/kill.flag）を書き込むと ExecutionEngine を停止させられます。`KILL_FLAG_CLEAR_ON_START=1` を本番で設定するのは推奨されません（自動クリアは危険）。
- .env は機密情報を含むため Git にコミットしないでください（config_setup でも警告あり）。

---

## ディレクトリ構成（主要ファイルのみ）

プロジェクトルート（src/kabusys を想定）:

- src/kabusys/
  - __init__.py
  - config.py                      -- 環境変数 / Settings
  - config_setup.py                -- 対話式 .env ウィザード
  - validate_config.py             -- 起動前設定検証 CLI
  - run_execution.py               -- ExecutionEngine 起動スクリプト
  - run_monitoring.py              -- SystemMonitor ポーリングスクリプト
  - tools/
    - paper_verification_report.py -- ペーパートレード検証レポート
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
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (参照されるが今回抜粋外)
  - execution/                      (ExecutionEngine 関連、broker_factory 等)
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/ (ランタイムで使用 / 作成)
    - monitoring.db
    - paper_trading.db
    - kill.flag
    - stop_requested.flag
    - execution.pid
  - logs/ (ログファイル)

（上は抜粋で、実際はさらにモジュールが存在します）

---

## 開発・拡張メモ

- DuckDB を利用したファクター計算は SQL と Python を組み合わせて効率的に実装されています。prices_daily / raw_financials 等のテーブル設計に依存します。
- AI 関連は OpenAI API を利用。API 呼び出しのラップとリトライ、レスポンスバリデーションを実装しているため、テスト時には `_call_openai_api` 等をモック可能です。
- Monitoring の DB 初期化は `init_monitoring_db()` で冪等に実行され、古い DB に対する軽微なマイグレーション（カラム追加）処理を含みます。

---

## よく使うコマンドまとめ

- .env ウィザード:
  ```bash
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```bash
  python -m kabusys.validate_config
  ```
- 実行エンジン起動:
  ```bash
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```
- 監視起動:
  ```bash
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  ```
- ペーパートレード検証レポート:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要であれば、README に含めるサンプル .env テンプレート、より詳しいディレクトリ木、各モジュールの API 仕様（関数シグネチャ）なども追記できます。どの情報を優先して追加しますか？