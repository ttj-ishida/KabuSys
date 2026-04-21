# KabuSys

日本株自動売買システム（ライブラリ / 実行スクリプト群）

このリポジトリは、銘柄選定 → ポジションサイズ計算 → 発注（ExecutionEngine） → 監視（Monitoring） → レポート / 解析 に至る一連の機能を備えた自動売買/解析基盤です。 Research（ファクター計算）、Portfolio（構成・リスク調整）、AI（ニュース NLP / レジーム判定）、Monitoring（稼働・注文・リスク監視）などモジュール化されています。

---

## 主な特徴

- Execution / Monitoring の分離（本番／ペーパーを設定で切り替え）
- DuckDB を用いたデータ解析（prices_daily / raw_financials 等）
- SQLite を用いた稼働・注文ログ（monitoring.db / paper_trading.db）
- OpenAI（gpt-4o-mini）を用いたニュースのセンチメント評価およびレジーム判定
- リスク監視（ドローダウン、ポジション上限）と Kill Switch（停止フラグ）
- ファクター計算・特徴量解析（モメンタム、ボラティリティ、バリュー等）
- ペーパートレード検証レポート生成ツール

---

## 必要環境 / 依存ライブラリ（例）

- Python 3.10+
- duckdb
- psutil
- openai
- PyYAML（config 検証時に任意）
- （その他、ExecutionEngine 周りで必要な broker ライブラリ等）

推奨インストール方法（プロジェクトに `requirements.txt` がある場合）:
```
python -m pip install -r requirements.txt
```
手動インストール例:
```
python -m pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン
   - 例: git clone <repo_url>

2. 仮想環境を作成して依存関係をインストール
   - python -m venv .venv
   - source .venv/bin/activate（Windows は .venv\Scripts\activate）
   - pip install -r requirements.txt（存在する場合）

3. 環境変数（.env）を作成
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
     ウィザードは .env を生成／更新します（.env は絶対に Git にコミットしないでください）。
   - 直接設定する場合は `.env` に以下の必須キーを設定:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - （必要に応じて OPENAI_API_KEY 等）
   - 自動読み込み: プロジェクトルートの `.env` / `.env.local` が自動で読み込まれます（テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

4. 設定検証
   ```
   python -m kabusys.validate_config
   ```
   `--strict` を付けると警告も失敗扱いになります。

5. ディレクトリ（data / logs 等）は起動時に自動作成されますが、権限等に注意してください。

---

## 環境変数（主なもの）

- KABUSYS_ENV: 実行環境。`development` | `paper_trading` | `live`（デフォルト: development）
  - paper_trading の場合、発注はモック（MockBrokerClient）になり、専用 DB を使用します。
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視DB）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（ai モジュールで使用）
- LOG_LEVEL: ログレベル（例: INFO）
- LOG_DIR: ログ保存ディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、run_monitoring で使用。デフォルト 60）
- PAPER_FILL_MODE: ペーパートレード時の約定モード（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアする（開発用）

---

## 使い方（起動方法 / CLI）

基本的にモジュールは `python -m kabusys.<module>` で実行できます。

- 設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 監視プロセス起動 (Monitoring)
  - スクリプト: `src/kabusys/run_monitoring.py`
  - 実行:
    ```
    python -m kabusys.run_monitoring
    ```
  - オプション: 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を秒単位で上書き（デフォルト 60 秒）。
  - 停止方法: プロジェクトルートの `data/stop_requested.flag` を作成するとループが検知して終了します（または Ctrl+C）。

- 実行エンジン起動 (ExecutionEngine)
  - スクリプト: `src/kabusys/run_execution.py`
  - 実行:
    ```
    python -m kabusys.run_execution
    ```
  - KABUSYS_ENV により動作が変化:
    - `paper_trading` の場合は MockBrokerClient を使い、データは `data/paper_trading.db` に保存（本番 DB と分離）。
  - 停止方法:
    - `data/stop_requested.flag` を作成すると起動中のループが停止処理を行う。
    - Kill Switch により `data/kill.flag` が作成されると ExecutionEngine に対して停止シグナルを送る（Monitoring の kill_switch が判定して書き込み）。

- Paper Trading 検証レポート生成
  - スクリプト: `src/kabusys/tools/paper_verification_report.py`
  - 実行例:
    ```
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - DB パスは `--db` オプションまたは環境変数 `PAPER_TRADING_SQLITE_PATH` で指定可能。

- AI 関連（ニュース NLP / レジーム判定）
  - ニューススコアリング（ai.news_nlp.score_news）や regime_detector.score_regime は DuckDB 接続と target_date, OpenAI API キーを渡して呼び出す形で利用します。
  - OpenAI API の呼び出しには `OPENAI_API_KEY` が必要です。

---

## 運用メモ / フラグファイル

- 停止要求（run_monitoring / run_execution と共通）
  - data/stop_requested.flag — スクリプトが定期チェックして存在すれば安全に停止します（スクリプト内で直接参照）。
- Kill Switch（自動停止判定）
  - data/kill.flag — Monitoring の KillSwitch が発動した理由をこのファイルに書き込み、ExecutionEngine を停止させる目的で使用します。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動でクリアします（本番では危険なのでデフォルト 0 推奨）。
- PID ファイル
  - data/execution.pid — ExecutionEngine が書き込む PID ファイル（既定値は Settings.pid_file_path）。
- ログ
  - デフォルトは `logs/<app_name>.log`（ログは日次ローテーション、30日分保存）。`LOG_DIR` で変更可。

---

## 主なモジュールと責務（簡易説明）

- kabusys.config
  - 環境変数/`.env` の読み込み・Settings クラス（アプリ設定取得）
- kabusys.config_setup
  - 対話式 `.env` 生成ウィザード
- kabusys.validate_config
  - 起動前チェック（環境変数・config/*.yaml の存在・基本的整合性）
- kabusys.utils.logging_setup
  - 共通のログ設定（StreamHandler + TimedRotatingFileHandler）
- kabusys.utils.process_priority
  - プロセス優先度 / CPU affinity 設定ユーティリティ
- kabusys.monitoring
  - monitoring_db: SQLite スキーマ初期化と簡易 CRUD
  - system_monitor: CPU/メモリ/ディスク・データ鮮度・プロセス生存のチェック
  - risk_monitor: ドローダウン / ポジション上限の監視（dashboard 更新・risk_logs）
  - kill_switch: Kill Switch の判定と `kill.flag` の書き込み処理
  - monitoring_engine: 監視ループのオーケストレーション
- kabusys.execution (参照のみ。実装ファイル群は別)
  - ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager, BrokerClientFactory
- kabusys.portfolio
  - portfolio_builder: 候補選定・重み計算
  - position_sizing: 株数算出（単元丸め・利用可能現金とのスケーリング）
  - risk_adjustment: セクター上限・レジーム乗数
- kabusys.research
  - factor_research: Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - feature_exploration: forward returns / IC / summary 等の統計解析
- kabusys.ai
  - news_nlp: ニュースを集約して OpenAI に送信、銘柄ごとのスコアを ai_scores に書き込む
  - regime_detector: ETF + マクロニュースを元に market_regime を算出して保存
- kabusys.tools
  - paper_verification_report: ペーパートレード検証用レポート生成

---

## ディレクトリ構成（抜粋）

プロジェクトルート（例）
- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_monitoring.py
    - run_execution.py
    - utils/
      - __init__.py
      - logging_setup.py
      - process_priority.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py (関連モジュール)
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py (通知管理)
    - execution/
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - broker_factory.py
      - reconciler.py
      - risk_manager.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - ai/
      - news_nlp.py
      - regime_detector.py
      - __init__.py
    - tools/
      - paper_verification_report.py
      - __init__.py
- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml
- data/
  - monitoring.db (デフォルト)
  - paper_trading.db
  - kill.flag
  - stop_requested.flag
  - execution.pid
- logs/
  - execution.log
  - monitoring.log
  - ...

> 注: 上記はリポジトリの現状ファイルに基づく抜粋です。実際のファイル構成はプロジェクトで差異がある場合があります。

---

## 開発・テストについて

- 単体関数の多くは純粋関数（副作用なし）で設計されており、ユニットテストを書きやすくなっています（portfolio / research 等）。
- 外部 API（OpenAI, broker 等）呼び出し部分はモック可能な設計（呼び出しラッパーを patch して差し替え）になっています。
- DB 操作は DuckDB / SQLite を使うため、テスト用に小型 DB ファイルを用意して実行できます。

---

## 補足事項

- 本番稼働時は `KABUSYS_ENV=live` 設定に注意してください。validate_config で本番向けのガード（LINE 通知など）をチェックします。
- `KILL_FLAG_CLEAR_ON_START` が `1` の場合、起動時に既存の kill.flag が自動でクリアされます（本番では推奨されません）。
- ログディレクトリや DB ファイルは起動ユーザーに書き込み権限が必要です。

---

必要であれば、README にサンプル `.env.example`、起動スクリプト systemd / Supervisor の設定例、Docker 化手順、依存関係の正確な list（requirements.txt）を追加できます。どの情報が必要か教えてください。