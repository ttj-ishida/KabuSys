# KabuSys

日本株向け自動売買システム（ライブラリ＋起動スクリプト群）

このリポジトリは、注文実行エンジン、監視（モニタリング）、ポートフォリオ構築、ファクター分析、ニュースNLP（OpenAI 連携）等を含む自動売買プラットフォームのコア実装です。

---

## プロジェクト概要

- 実行エンジン（ExecutionEngine）による発注管理とリスク制御
- 監視コンポーネント（System / Trade / Risk）による稼働・注文・リスク監視
- Kill Switch（flag ファイル）による外部停止制御
- ポートフォリオ構築（候補選定・重み付け・株数決定・セクター制限）
- 研究用モジュール（ファクター計算・IC 計算・将来リターン）
- ニュース NLP（OpenAI API を使ったセンチメントスコアリング）
- ペーパートレード用の分離 DB と検証レポート生成ツール

設計方針として「本番 DB とペーパートレード DB の分離」「ルックアヘッドバイアスの排除」「フェイルセーフ（API失敗時の挙動）」等に配慮しています。

---

## 主な機能一覧

- run_execution.py: ExecutionEngine を起動（本番 / ペーパートレード切替）
- run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔調整）
- monitoring_engine: 各 Monitor の集合体としてアラート送信や Kill Switch 評価を実施
- monitoring_db: 監視用 SQLite スキーマの自動初期化・永続化 API
- portfolio モジュール: 候補選定、重み付け、ポジションサイズ計算、セクター上限適用
- research モジュール: ファクター計算（momentum/value/volatility）、IC・統計サマリ
- ai.news_nlp / ai.regime_detector: OpenAI を利用したニュース評価・市場レジーム判定
- tools.paper_verification_report: ペーパートレード DB を集計して検証レポートを生成
- config_setup.py: 対話式 .env 作成ウィザード
- validate_config.py: 環境変数 / config/*.yaml の事前検証 CLI

---

## 動作環境・依存

- Python 3.10 以上（型ヒントで `|`、組込みジェネリクス等を使用）
- 必須ライブラリ（例）:
  - duckdb
  - psutil
  - openai (AI 機能を利用する場合)
- 任意（機能により必要）:
  - PyYAML（config/*.yaml のパース検証）
- 標準ライブラリ: sqlite3, logging, threading, datetime 等

requirements.txt がある場合はそれを利用してください（本コード提供時点ではサンプルのため明示的な requirements ファイルは含まれていない可能性があります）。

インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成・依存インストール（上記参照）

3. .env の作成
   - 対話式ウィザードを推奨:
     ```
     python -m kabusys.config_setup
     ```
     で `.env` を生成できます（.env は絶対に Git にコミットしないでください）。
   - もしくは手動で `.env` を用意（`.env.example` を参照する想定）。

4. 設定検証（任意）
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict   # 警告も FAIL 扱い
   ```

5. DB 初期化
   - 監視用 SQLite（デフォルト: data/monitoring.db）と DuckDB（デフォルト: data/kabusys.duckdb）は起動時に必要テーブルが自動作成されます。特別な初期化は不要です（run_* スクリプトが内部で init_monitoring_db を呼びます）。
   - ペーパートレード時は PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）を使用します。

6. OpenAI を使う機能を使う場合
   - 環境変数 `OPENAI_API_KEY` を設定するか、関数呼び出し時に api_key を渡してください。

---

## 使い方（主要コマンド）

- ExecutionEngine を起動（本番 / paper_trading は KABUSYS_ENV に依存）
  ```
  export KABUSYS_ENV=development            # development / paper_trading / live
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、ペーパートレード専用 DB に記録されます（本番 DB と完全に分離）。

- Monitoring を起動（監視ループ）
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は常に本番用 sqlite_path を使用します（環境に依らず）。

- 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config [--strict]
  ```

- ペーパートレード検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - `--db` で DB パスを指定可能。環境変数 `PAPER_TRADING_SQLITE_PATH` でも指定可。

- ライブラリとしての利用（例）
  - AI ニューススコアリング:
    ```py
    import duckdb
    from datetime import date
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    n_written = score_news(conn, target_date=date(2026, 4, 11), api_key="sk-...")
    ```
  - ファクター計算:
    ```py
    from kabusys.research import calc_momentum
    conn = duckdb.connect("data/kabusys.duckdb")
    recs = calc_momentum(conn, target_date=date(2026,4,11))
    ```

---

## 停止・Kill Switch について

- 停止フラグ:
  - data/stop_requested.flag
    - run_execution/run_monitoring はこのファイルの存在を監視し、検出すると安全にループを終了します（外部から停止を要求する簡易手段）。
  - data/kill.flag
    - KillSwitch（監視側）が条件を満たすとこのファイルを書き込み、ExecutionEngine に停止を促します。
- PID 管理:
  - data/execution.pid に ExecutionEngine の PID を書き込み（run_execution が使用）。SystemMonitor はこの PID ファイルをチェックしてプロセスの有無を確認します。
- 起動時の Kill Flag クリア:
  - 環境変数 `KILL_FLAG_CLEAR_ON_START=1` を設定すると ExecutionEngine 起動時に自動で kill.flag をクリアします（本番では 0 推奨）。

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: 実行環境（development / paper_trading / live。デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（monitoring.db）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時の約定挙動（instant | partial | never | reject）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU/MEM/DISK の閾値設定等は Settings クラスで参照

（詳細は `src/kabusys/config.py` の Settings を参照してください）

---

## ディレクトリ構成（抜粋）

リポジトリの主要ファイル・パッケージ構成の例:

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
  - execution/                 (実行エンジン関連: broker_factory, execution_engine, order_manager, etc.)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - process_priority.py
    - __init__.py
  - data/                      (ランタイム生成ファイル: *.db, *.pid, *.flag 等)

（上記はソースに含まれるファイルを抜粋したものです）

---

## 運用上の注意

- .env は絶対に VCS にコミットしないでください（API キーやパスワード等が含まれます）。
- 本番（KABUSYS_ENV=live）では LINE 通知や Kill Switch 設定を十分確認してください。
- OpenAI 連携はコストとレート制限に注意して運用してください（リトライやバッチ処理は実装済み）。
- Monitor や Execution のログは標準出力に流れます。運用では systemd / supervisor 等でプロセス管理・ログローテートしてください。
- ペーパートレードは本番 DB とは分離されていますが、設定ミスによる混同を避けるため .env の確認を徹底してください。

---

## 開発者向けメモ

- type 注釈や新しい構文を多用しているため Python 3.10 以上を推奨します。
- DuckDB を用いた分析・研究用機能は、prices_daily / raw_financials / raw_news 等のテーブルが存在することを前提としています。
- テストやモックの容易化を意図して OpenAI 呼び出し部分はラップしてあるため、ユニットテストでは該当関数を patch して検証できます（例: news_nlp._call_openai_api のモック）。

---

README の内容や使い方で補足が必要であれば、実行コマンドの具体例や .env のサンプル（敏感情報は除く）など追加で作成します。どの項目を詳しくしたいか教えてください。