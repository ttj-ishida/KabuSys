# KabuSys

日本株自動売買システムのコアライブラリ群（ライブラリ兼コマンド群）です。  
このリポジトリは、発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築・サイズ計算、リサーチ（DuckDBベースのファクター計算）、およびAIを用いたニュース解析機能を含みます。

バージョン: 0.1.0

---

## 概要

- 発注ロジック（ExecutionEngine）と監視コンポーネント（Monitoring）が中心。
- DuckDB を用いた分析・リサーチ（prices_daily / raw_financials 等のテーブル想定）。
- SQLite を用いた監視ログ・ペーパートレード記録（デフォルト: `data/monitoring.db` / `data/paper_trading.db`）。
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント解析・レジーム判定機能（オプション、APIキー必要）。
- CLI ツール:
  - 環境設定ウィザード（`.env` 生成）: `config_setup.py`
  - 設定検証: `validate_config.py`
  - Paper Trading 検証レポート: `tools/paper_verification_report.py`

---

## 主な機能一覧

- Execution
  - 発注エンジン起動用スクリプト: `run_execution.py`
  - Paper trading（`KABUSYS_ENV=paper_trading`）時はモックブローカークライアントを使用し、DBを分離
  - プロセス優先度設定、PIDファイル管理、停止フラグ（`data/stop_requested.flag` / `data/kill.flag`）対応

- Monitoring
  - 監視ループ起動スクリプト: `run_monitoring.py`
  - システム状態監視（CPU / メモリ / ディスク / プロセス死活）
  - 取引ログ・リスクログ・ダッシュボードの永続化（SQLite）
  - Kill Switch（ドローダウンやポジション上限での自動停止フラグ書き込み）
  - アラート通知のフック（LINE トークンを設定すれば通知可能）

- Portfolio（ポートフォリオ構築）
  - 候補選定、等金額/スコア加重、リスクベースのポジションサイズ計算
  - セクターキャップやレジーム乗数の適用

- Research
  - DuckDB を用いたファクター計算（モメンタム / ボラティリティ / バリュー 等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- AI（オプション）
  - ニュースを LLM でスコアリングして `ai_scores` に保存（`OPENAI_API_KEY` 必須）
  - マクロニュース + ETF MA200 を使った市場レジーム判定

- ユーティリティ
  - 統一ログ設定（stdout + 日次ローテーションファイル）
  - プロセス優先度 / CPU affinity 設定
  - `.env` の自動読み込み / ウィザード / 検証ツール

---

## セットアップ手順

前提:
- Python 3.9+（型注釈等を考慮）
- システムに sqlite3 が利用可能（標準ライブラリ）
- 必要な外部パッケージを pip でインストール

推奨インストール（必要に応じて仮想環境を作成してください）:

pip の例:
```
pip install duckdb psutil openai
# PyYAML は設定ファイル検証を行う場合に必要
pip install PyYAML
```

重要な環境変数（代表例とデフォルト）:
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: 分析DB（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI を使う場合は必須（AI 機能）
- LOG_LEVEL, LOG_DIR など

.env の作成方法（推奨）
1. 対話式ウィザードで `.env` を作成:
   ```
   python -m kabusys.config_setup
   ```
   - `--env-file` で別パス指定可能。

2. 作成後、設定を検証:
   ```
   python -m kabusys.validate_config
   # 警告も厳密に扱いたい場合:
   python -m kabusys.validate_config --strict
   ```

ディレクトリ作成:
- デフォルトで `data/` と `logs/` を使用します。`setup_logging` が起動時に自動作成を試みますが、必要に応じて手動で作成してください。

---

## 使い方

起動スクリプトはモジュールとして実行できます（カレントディレクトリはプロジェクトルートが推奨）。

- ExecutionEngine 起動（本番 / paper_trading 判定は `KABUSYS_ENV` に依存）:
  ```
  python -m kabusys.run_execution
  ```
  - Paper trading の場合、`KABUSYS_ENV=paper_trading` を設定すると専用の mock ブローカー・DB（`PAPER_TRADING_SQLITE_PATH`）を使用します。
  - 停止フラグ: `data/stop_requested.flag` を作成すると起動を阻止・停止処理を行います。
  - PID ファイル: `data/execution.pid`（デフォルト）にプロセスIDを書きます。

- Monitoring 起動:
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔: 環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）。
  - 監視は環境に関わらず本番用の `SQLITE_PATH` を使用して記録します（monitoring は常に監視用 DB を参照）。
  - 停止フラグ: 実行ディレクトリの `data/stop_requested.flag` を確認し、存在するとループを終了します。

- Paper Trading 検証レポート（ツール）:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを指定する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```
  - デフォルト DB: `data/paper_trading.db`（`PAPER_TRADING_SQLITE_PATH` 環境変数で上書き可）。
  - 稼働率、注文成功率、レイテンシ等の指標を算出して PASS/FAIL を判定します。

- AI 機能（ニューススコアリング等）
  - `OPENAI_API_KEY` を設定してから使用してください。
  - 例: ニューススコアリング呼び出し（プログラムから）
    ```
    from kabusys.ai.news_nlp import score_news
    # conn は duckdb.connect(...) の接続オブジェクト、target_date は datetime.date
    score_news(conn, target_date, api_key="sk-...")
    ```
  - 市場レジーム判定:
    ```
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key="sk-...")
    ```

ログ
- ログは stdout とファイル（デフォルト `logs/<app_name>.log`）に出力されます。
- ログレベルは環境変数 `LOG_LEVEL` または `setup_logging(app_name, level=...)` で制御可能。

停止フラグ / Kill Switch
- `data/kill.flag` は Kill Switch によって書き込まれ、ExecutionEngine の停止トリガーになります（`Settings.kill_flag_path` でパスを変更可）。
- Kill Switch の評価条件はリスクモニターの結果（ドローダウンやポジション上限など）に依存します。

---

## 主要ファイルとディレクトリ構成

プロジェクトの主要なファイルと役割を抜粋します（簡易ツリー）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（自動 .env ロード含む）
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py       — 共通ログ設定
    - process_priority.py    — プロセス優先度 / CPU affinity
  - execution/               — 発注関連（BrokerFactory / Engine / OrderManager 等）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status / trade_logs / ...）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       — （通知ロジック）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py      — 市場レジーム判定（OpenAI + ETF）
  - tools/
    - paper_verification_report.py
  - data/ (runtime)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper trading 用)
    - execution.pid
    - stop_requested.flag
    - kill.flag
  - logs/ (runtime)
    - execution.log
    - monitoring.log
    - ...（日次ローテーション保持）

---

## 注意点 / 動作上の取り決め

- .env は絶対にリポジトリにコミットしないでください（`config_setup.py` の注釈にも記載）。
- Monitoring は監視データのため常に本番用 `SQLITE_PATH` を参照します（KABUSYS_ENV に依存しない）。
- ExecutionEngine は `KABUSYS_ENV=paper_trading` の場合のみ `PAPER_TRADING_SQLITE_PATH` を使用して本番 DB と完全分離します。
- AI 機能（news_nlp / regime_detector）は OpenAI API を呼び出します。APIキー未設定時は例外を投げる箇所があります。テスト時は API 呼び出し関数をモックしてください（コードにモック用のコメントあり）。
- 外部依存: duckdb, psutil, openai。YAML 検証は PyYAML が必要です（オプション）。

---

## よく使うコマンドまとめ

- .env 作成ウィザード:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Execution 起動:
  ```
  python -m kabusys.run_execution
  ```

- Monitoring 起動:
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- Paper Trading 検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要に応じて README に追記します（例: インストール要件の requirements.txt、デプロイ手順、systemd/cron のユニットファイル例、LINE 通知設定方法など）。どの情報を追加しますか？