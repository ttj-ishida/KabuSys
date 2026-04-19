# KabuSys

日本株自動売買システムのライブラリ/実行スクリプト群です。  
このリポジトリは取引エンジン（ExecutionEngine）、監視（Monitoring）、ファクター計算・研究ツール、ニュースNLP / レジーム判定などを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムの基盤となるコード群です。主な目的は次のとおりです。

- シグナル → ポートフォリオ構築 → 発注までの Execution エンジン
- 実行状況・システム状態の監視（Monitoring）と Kill Switch（異常時に発注を止める）
- DuckDB を使ったファクター計算 / 研究（research）
- OpenAI を利用したニュースセンチメント（ai.news_nlp）や市場レジーム判定
- Paper Trading 用検証ツール（tools）

設計方針の一部:
- データベース（SQLite / DuckDB）を用いて状態と履歴を永続化
- 環境変数と `.env` による設定管理（`config_setup.py` で対話的に作成可能）
- 本番（live）とペーパートレーディング（paper_trading）を明確に分離

---

## 主な機能一覧

- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - Paper Trading モード時は MockBroker を使用し専用 DB に記録
- Monitoring
  - System / Trade / Risk の各モニタと集約エンジン（MonitoringEngine）
  - kill.flag による外部からの停止（KillSwitch）
  - run_monitoring.py によるポーリング実行
- Portfolio
  - 候補選定、重み計算、ポジションサイズ計算、セクター制限、レジーム乗数
- Research
  - DuckDB を用いたファクター計算（モメンタム / ボラティリティ / バリュー等）
  - 将来リターン・IC 計算、統計サマリ
- AI
  - OpenAI を使ったニュースセンチメント（ai.news_nlp）
  - 市場レジーム判定（ai.regime_detector）
- Tools
  - Paper Trading 検証レポート生成スクリプト（tools.paper_verification_report）
- 設定管理
  - 対話式 .env 作成ウィザード（config_setup.py）
  - 起動前設定検証 CLI（validate_config.py）
- ユーティリティ
  - ロギング設定ユーティリティ（utils.logging_setup）
  - プロセス優先度 / CPU affinity ユーティリティ（utils.process_priority）

---

## 動作要件（推奨）

- Python 3.10+
- 必須 Python パッケージ（少なくとも実行時に必要なもの）
  - duckdb
  - psutil
  - openai
- 任意（機能により必要）
  - PyYAML（config/*.yaml の検証に使用）
- 標準ライブラリ: sqlite3, logging, threading, datetime, pathlib 等

インストール例:
```
python -m pip install duckdb psutil openai PyYAML
```
（プロジェクトに requirements.txt がある場合は `pip install -r requirements.txt` を推奨します）

---

## セットアップ手順

1. リポジトリをクローン／展開する
2. Python 環境を用意する（仮想環境推奨）
3. 依存パッケージをインストールする（上記参照）
4. 対話式ウィザードで `.env` を作成する:
   ```
   python -m kabusys.config_setup
   ```
   - .env は Git にコミットしてはいけません（秘密情報を含むため）。
5. 設定を検証:
   ```
   python -m kabusys.validate_config
   ```
   - 警告を厳密に扱いたい場合は `--strict` を付けて実行（警告があると exit(1)）。

注意:
- .env の自動ロードはデフォルトで有効です。テスト等で無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 主要スクリプトの使い方

- 監視ループ（Monitoring）
  - ポーリングループを起動します。デフォルトの間隔は 60 秒。
  - 環境変数 `MONITOR_POLL_INTERVAL` で秒数を上書き可能（例: 30）。
  - 実行例:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 実行中にプロジェクトルート `data/stop_requested.flag` が作成されるとループが終了します。

- 実行エンジン（Execution）
  - ExecutionEngine を起動します。Paper Trading モードでは MockBrokerClient を用いて `data/paper_trading.db`（デフォルト）に記録します。
  - 実行例（通常/デフォルト環境）:
    ```
    python -m kabusys.run_execution
    ```
  - Paper Trading 起動例:
    ```
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
  - 停止は `data/stop_requested.flag` を作成するか、Execution 側が Kill Switch (`data/kill.flag`) を検知して停止します。実行中に PID は `data/execution.pid` に書き込まれます。

- 設定検証（CLI）
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB パスは `data/paper_trading.db`。`--db` で指定可能。
  - 環境変数 `PAPER_TRADING_SQLITE_PATH` でも指定可能。

- AI / リサーチ用関数はライブラリとしてインポートして利用できます（例: kabusys.research.calc_momentum, kabusys.ai.score_news）。

---

## 主要な環境変数（主なもの）

- 認証関連
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - OPENAI_API_KEY (ai 機能を使う場合必須)
- 環境 / 動作制御
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
  - KILL_FLAG_CLEAR_ON_START: 0|1（本番では 0 推奨）
- データベース / ファイルパス
  - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db） — Monitoring は環境にかかわらず本番 sqlite_path を使用
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH: 実行エンジンの PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- Monitoring 固有
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

（上記以外にも細かな閾値設定や AI パラメータ等が .env / config に存在します。`.env.example` を参照してください）

---

## 注意事項（運用上のポイント）

- 監視（monitoring）は「環境にかかわらず」本番の sqlite_path（`SQLITE_PATH`）を参照します。ペーパートレードの監視を別 DB にしたい場合は適宜パスを変えてください。
- Execution は `KABUSYS_ENV=paper_trading` の場合に Paper 用 DB を使う設計です（本番 DB とファイルが分離されます）。
- Kill Switch:
  - `KillSwitch` はリスク基準（ドローダウン、ポジション上限等）により `data/kill.flag` を書き込むことで ExecutionEngine に停止を促します。
  - `KILL_FLAG_CLEAR_ON_START=1` に設定すると起動時に kill.flag を自動クリアします。 本番では 0 を推奨します。
- 停止フラグ:
  - `data/stop_requested.flag` を作成すると run_monitoring / run_execution の polling loop / session が安全に終了します。
- ログ:
  - デフォルトで `logs/` に日次ローテートでログを出力します。`LOG_DIR` 環境変数で変更可能。
- セキュリティ:
  - `.env` に機密情報を含めるため絶対に Git にコミットしないでください。

---

## ディレクトリ構成（抜粋）

以下はリポジトリ内の主要なファイル/ディレクトリ構成の抜粋です（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / 設定クラス
  - config_setup.py            — .env ウィザード（対話式）
  - validate_config.py         — 起動前設定検証 CLI
  - run_monitoring.py          — Monitoring ポーリング起動スクリプト
  - run_execution.py           — ExecutionEngine 起動スクリプト
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
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - execution/
    - (Execution エンジン、order_manager 等が格納される想定ファイル群)
  - data/                      — 実行時に作成される（logs, sqlite, pid, flags 等）

（実際のリポジトリのファイル数が本ドキュメントで示したものと若干異なる場合があります。上記は主要モジュールの一覧です）

---

## 開発・拡張メモ

- 新しい config/*.yaml を追加した場合は `validate_config.py` にファイル名を追記すると検証に組み込めます。
- DuckDB スキーマやテーブル名は ai / research モジュールに依存しています。テーブル定義を変更する場合は参照箇所を合わせて更新してください。
- OpenAI 呼び出し部分はリトライやレスポンス検証を備えていますが、API バージョン変更などに備えてテスト用に `_call_openai_api` を patch する設計になっています。

---

## よくあるコマンドまとめ

- .env 作成（対話式）:
  ```
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```
  python -m kabusys.validate_config
  ```
- 監視起動（60秒間隔）:
  ```
  python -m kabusys.run_monitoring
  ```
- 監視起動（30秒間隔）:
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
- Execution 起動（Paper Trading）:
  ```
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```
- Paper Trading 検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要に応じて、この README の改善や特定モジュールの詳細ドキュメント（API リファレンス、設定項目の一覧、運用手順書など）を作成できます。どの部分を優先して詳細化するか指示をください。