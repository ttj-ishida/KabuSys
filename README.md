# KabuSys

日本株自動売買システム (KabuSys) のリポジトリ用 README（日本語）。

この README ではプロジェクトの概要、主な機能、セットアップ手順、使い方、ディレクトリ構成を説明します。

注意: 実行に必要な外部依存 (duckdb / psutil / openai など) は環境に応じてインストールしてください。requirements.txt がある場合はそれを利用してください。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買／リサーチ基盤です。主な機能は以下の通りです。

- 戦略に基づいた銘柄選定・重み付け・株数計算（Portfolio construction）
- 実行層（Execution Engine）：ブローカークライアント経由の発注管理、リスク管理、再整合
- 監視層（Monitoring）：プロセス・システム状態、注文ログ、リスク監視、Kill Switch
- 研究／ファクター計算モジュール（DuckDB を用いたファクター算出）
- AI モジュール（ニュース NLP によるセンチメント評価、レジーム判定）
- ペーパートレード用分離 DB と検証ツール（paper_verification_report）

設計方針の一部:
- 本番 / ペーパートレードを環境変数 `KABUSYS_ENV` で切り替え（`development` / `paper_trading` / `live`）。
- 設定は .env ファイルまたは環境変数から読み込み。`config_setup` で対話式に .env を作れる。
- ログはコンソール + 日次ローテーションファイル出力（`kabusys.utils.logging_setup`）。
- OpenAI API はニュースセンチメント／レジーム判定で利用（API キーは `OPENAI_API_KEY`）。

---

## 機能一覧（ハイレベル）

- 実行:
  - `run_execution.py`：ExecutionEngine を起動。`KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、専用の paper_trading DB（デフォルト `data/paper_trading.db`）に記録する。
  - PID ファイル管理（`data/execution.pid` など）、停止フラグ検知（`data/stop_requested.flag`）。
  - プロセス優先度を "high" に設定。

- 監視:
  - `run_monitoring.py`：SystemMonitor のポーリングループ起動。監視ログは SQLite（デフォルト `data/monitoring.db`）へ永続化。
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）でオーバーライド可能（デフォルト 60 秒）。
  - Kill Switch：ドローダウンやポジション上限検出時に `data/kill.flag` を書き込み、ExecutionEngine に停止を通知。

- 設定管理:
  - `config_setup.py`：対話式ウィザードで `.env` を生成 / 更新。
  - `validate_config.py`：.env / config/*.yaml の検証 CLI（`--strict` オプションあり）。

- リサーチ / 研究:
  - `research.factor_research`：モメンタム、ボラティリティ、バリュー等のファクター計算（DuckDB）。
  - `research.feature_exploration`：将来リターン計算、IC（Information Coefficient）等の統計処理。

- ポートフォリオ構築:
  - `portfolio.portfolio_builder`：候補選定（スコア順）・等重/スコア加重の重み計算。
  - `portfolio.position_sizing`：株数決定、単元丸め、Aggregate cap のスケール調整。
  - `portfolio.risk_adjustment`：セクター上限・レジーム乗数。

- AI:
  - `ai.news_nlp`：OpenAI を使ったニュースセンチメント評価 → `ai_scores` へ保存。
  - `ai.regime_detector`：ETF MA とマクロニュースの LLM センチメントを合成して市場レジーム判定。

- ツール:
  - `tools.paper_verification_report`：ペーパートレード DB の指標（稼働率 / 注文成功率 / レイテンシ等）を集計してレポート出力。

---

## 必要環境（例）

（プロジェクトに同梱の requirements.txt があればそちらを利用してください。以下は主要パッケージの例）

- Python 3.9+
- duckdb
- psutil
- openai (OpenAI Python SDK)
- PyYAML（config YAML 検証を行う場合）
- そのほか実行環境に応じた追加パッケージ（ブローカークライアント等）

インストール例（仮）:
```bash
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順（基本）

1. リポジトリをクローン / 配布アーカイブを配置。
2. Python 環境を用意して依存パッケージをインストール。
3. .env を生成（対話式ウィザード推奨）:
   ```bash
   python -m kabusys.config_setup
   ```
   - 対話で J-Quants トークン、kabu API パスワード、DB パス、環境（KABUSYS_ENV）などを設定します。
   - 生成される `.env` は Git にコミットしないこと。

4. 設定を検証:
   ```bash
   python -m kabusys.validate_config
   # 警告を厳密に扱う場合:
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリ作成（必要に応じて）:
   - デフォルトの DB / PID / フラグファイル は `data/` 配下を使用します。書き込み権限が必要です。

6. （OpenAI を使う機能を利用する場合）`OPENAI_API_KEY` を .env または環境変数で設定。

---

## 使い方（主要コマンド）

- ExecutionEngine を起動（常用）:
  ```bash
  python -m kabusys.run_execution
  ```
  補足:
  - `KABUSYS_ENV=paper_trading` の場合、ペーパートレード専用 DB (`PAPER_TRADING_SQLITE_PATH` / default `data/paper_trading.db`) を使用し、MockBrokerClient が使われます。実世界への発注は行いません。
  - 実行前に `data/stop_requested.flag` が存在すると起動せず終了します（停止フラグ）。
  - 実行中に `data/stop_requested.flag` を作成するとエンジンが停止します。

- Monitoring を起動:
  ```bash
  python -m kabusys.run_monitoring
  ```
  補足:
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を変更可能。例: `MONITOR_POLL_INTERVAL=30`
  - 監視は `data/monitoring.db`（Settings が指す sqlite_path）へ記録します（環境に関わらず本番 sqlite_path を参照する設計）。

- .env の対話式作成:
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート出力:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を直接指定する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

---

## 主要環境変数（抜粋）

- KABUSYS_ENV: execution モード。`development` / `paper_trading` / `live`（デフォルト: development）
  - `paper_trading`：Mock broker を使用、paper_trading DB に記録
  - `live`：本番（実発注）
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（"1" で有効）。本番では 0 推奨。

---

## Kill Switch / 停止フラグについて

- Kill Switch は `kabusys.monitoring.kill_switch` により判定され、発動条件（例: ドローダウン超過、ポジション上限超過）が満たされた場合 `data/kill.flag` に理由を書き込みます。`Settings.kill_flag_path` でパスを変更可能。
- Execution 起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定すると自動で kill.flag をクリアしますが、本番では危険なため推奨されません。
- 監視 / 実行の停止フラグとして `data/stop_requested.flag` を使用しています（スクリプト内部で参照）。このファイルが存在すると run_execution/run_monitoring はループを終了します。

---

## ログ

- ログ設定ユーティリティ: `kabusys.utils.logging_setup.setup_logging(app_name=...)`
  - コンソール（stdout）と日次ローテーションファイル（`logs/<app_name>.log`）をルートロガーに設定。
  - デフォルトログディレクトリ: `logs/`（環境変数 `LOG_DIR` で変更可）
  - ログレベルは `LOG_LEVEL` 環境変数または引数で指定

---

## ディレクトリ構成（主要ファイル）

（プロジェクトルート直下 `src/kabusys` を想定）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/設定管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py          (参照されるが省略)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py          (参照されるが省略)
  - execution/
    - execution_engine.py      (参照されるが省略)
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py

（この README に載せたのは主な高レベル構成で、実際のファイルはリポジトリでご確認ください。）

---

## よくある操作例

- 開発で素早く環境セットアップ（対話式）と検証:
  ```bash
  python -m kabusys.config_setup
  python -m kabusys.validate_config
  ```

- ペーパートレードでエンジンを起動（本番 DB を汚さない）:
  ```bash
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```

- 監視を 30 秒間隔で回す:
  ```bash
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

- OpenAI を使ったニューススコアリングを単発で呼びたい（内部 API の利用想定）:
  - ai モジュールは DuckDB 接続と日付を受け取る関数を提供しています。テストや定期処理から呼び出してください。
  - 例（擬似）:
    ```py
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026,4,14), api_key="sk-...")
    ```

---

## 備考 / 運用上の注意

- 本番（KABUSYS_ENV=live）では設定と権限を厳重に管理してください。`validate_config` の `--strict` モードで事前チェックが可能です。
- .env に機密情報（API キー等）を平文で保存するため、絶対に Git 等へコミットしないでください。
- Execution / Monitoring はそれぞれ PID ファイルやフラグファイルを使います。自動運用（systemd / cron など）と組み合わせる場合はこれらのファイルの取り扱いに注意してください（`KILL_FLAG_CLEAR_ON_START` は本番では無効化推奨）。
- DuckDB / SQLite ファイルはバックアップやローテーション、アクセス制御を検討してください。

---

必要であれば、この README を元に「運用手順書」「systemd ユニット例」「docker-compose 設定」などの追加ドキュメントも作成できます。どのドキュメントが欲しいか教えてください。