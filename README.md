# KabuSys

日本株向け自動売買システムのコアライブラリ群。  
ポートフォリオ構築、発注エンジン、監視、研究用ファクター計算、ニュースNLP / レジーム判定などの機能を含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は次のような責務を持つモジュール群で構成された自動売買システムの基盤です。

- 市場データ（DuckDB）を使ったファクター計算・リサーチ
- ポートフォリオ構築（候補選定、重み計算、株数決定）
- ExecutionEngine（発注ロジック、リスク管理、OrderManager 等）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor）と Kill Switch
- ニュースを LLM（OpenAI）で評価するニュースNLP・レジーム判定
- 付属ツール（.env ウィザード、設定検証、Paper Trading 検証レポート）

設計方針の一部：本番 DB とペーパートレード DB を分離、ルックアヘッド（日時参照）を避ける等。

---

## 主な機能一覧

- 環境設定ウィザード（`.env` 作成／更新）: `kabusys.config_setup`
- 設定検証 CLI（.env と config/*.yaml の簡易チェック）: `kabusys.validate_config`
- Execution 起動スクリプト（本番 / paper_trading 切替、プロセス優先度設定）: `run_execution.py`
- Monitoring 起動スクリプト（ポーリング監視ループ）: `run_monitoring.py`
- 監視 DB（SQLite）永続化レイヤー: `monitoring.monitoring_db`
- Risk / System / Trade モニタと Kill Switch / Alert 管理
- ポートフォリオ構築ユーティリティ（候補選定、等重配分、スコア重み付け）
- ポジションサイジング（リスクベース / 等配分 / スコア配分）
- ファクター計算（momentum, volatility, value）: DuckDB を用いた純粋関数群
- 研究用ユーティリティ（forward returns, IC, summary）
- ニュースNLP（OpenAI を用いた銘柄別センチメントスコアリング）
- レジーム判定（ETF の MA とマクロセンチメントを合成）
- Paper Trading 用検証レポート生成ツール

---

## 前提 / 必要条件

- Python 3.10 以上（注: 型注釈で `X | Y` を使用しているため）
- SQLite（標準ライブラリに含まれます）
- 以下の追加 Python パッケージ（最低限）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（設定検証で YAML の検査を行う場合に任意）
- ネットワークアクセス（kabuステーション API / OpenAI API を使用する場合）

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```
（requirements.txt がある場合は `pip install -r requirements.txt` を推奨）

---

## セットアップ手順

1. リポジトリをクローン／展開。

2. 仮想環境の作成、依存パッケージのインストール（上記参照）。

3. 環境変数設定（.env の作成）
   - 対話式ウィザードを使う:
     ```bash
     python -m kabusys.config_setup
     ```
     デフォルトはプロジェクトルートの `.env` を作成します。既存値は読み込まれ、Enter で再利用できます。

   - 主要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - KABUSYS_ENV: 実行環境（development | paper_trading | live）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading 時）
     - OPENAI_API_KEY: OpenAI を利用する機能の API キー
     - LOG_LEVEL / LOG_DIR / KILL_FLAG_CLEAR_ON_START 等

4. 設定検証（任意だが推奨）:
   ```bash
   python -m kabusys.validate_config
   # 警告もエラー扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリ等は起動時に自動作成されますが、権限に注意してください（logs/, data/ など）。

---

## 使い方

- ExecutionEngine を起動（本番 / paper_trading は KABUSYS_ENV に依存）:
  ```bash
  python -m kabusys.run_execution
  ```
  観点:
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient が使われ、デフォルトで `data/paper_trading.db` に記録され、本番 DB とは分離されます。
  - 起動前に `data/stop_requested.flag` が存在すると起動を中止します。
  - 実行中は `data/execution.pid` が使用されます（pid ファイル）。

- Monitoring を起動:
  ```bash
  python -m kabusys.run_monitoring
  ```
  観点:
  - 環境変数 `MONITOR_POLL_INTERVAL`（秒）でポーリング間隔を変更可能（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV に関係なく本番の `SQLITE_PATH` を使用して監視ログを記録します。
  - 監視ループの停止方法:
    - `data/stop_requested.flag` を作成するとループが終了します（外部からの停止要求）。
    - Risk モジュール等が条件を満たすと `data/kill.flag` を書き、ExecutionEngine 停止をトリガーします。

- Paper Trading 検証レポートの生成:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # またはデフォルト DB を上書き:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI（ニュース NLF / レジーム判定）:
  - `OPENAI_API_KEY` を環境変数に設定してから、プログラム経由で `kabusys.ai.score_news` / `kabusys.ai.regime_detector.score_regime` を呼び出します。
  - API 呼び出しはエラーに対してフォールバック動作（スコア 0 等）を取るよう設計されていますが、API キーは必須です。

- Kill Switch（監視から Execution 停止）
  - RiskMonitor がドローダウンやポジション上限を検出した場合、`KillSwitch` が `data/kill.flag` を書き込みます。ExecutionEngine はこのフラグを見て停止する動作を行います。
  - `KILL_FLAG_CLEAR_ON_START` を `.env` で `1` にすると起動時に kill flag を自動クリアしますが、本番では `0`（クリアしない）を推奨します。

---

## 主要環境変数（抜粋）

- KABUSYS_ENV: execution モード（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API（必須）
- KABU_API_PASSWORD: kabuステーション API（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（ニュースNLP / レジーム判定で必須）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ保存ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレード時の約定挙動（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag をクリアするか（0/1）

---

## ディレクトリ構成（主要ファイル）

プロジェクトの `src/kabusys` 以下を抜粋しています。

- __init__.py
- config.py                — 環境変数 / Settings を提供
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — Monitoring 起動スクリプト

パッケージ群:
- ai/
  - news_nlp.py            — ニュースの LLM スコアリング
  - regime_detector.py     — レジーム判定
- portfolio/
  - portfolio_builder.py   — 候補選定・重み計算
  - position_sizing.py     — 株数決定・キャップ処理
  - risk_adjustment.py     — セクターキャップ・レジーム乗数
- research/
  - factor_research.py     — momentum/volatility/value の計算
  - feature_exploration.py — forward returns / IC / summary
- monitoring/
  - monitoring_db.py       — SQLite 永続化レイヤ
  - system_monitor.py
  - risk_monitor.py
  - trade_monitor.py       — （trade 関連監視）
  - monitoring_engine.py
  - kill_switch.py
  - alert_manager.py       — （通知管理）
- execution/
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - broker_factory.py
  - reconciler.py
  - risk_manager.py
- utils/
  - logging_setup.py       — 共通ログ設定（console + 日次ローテート）
  - process_priority.py    — psutil を使った優先度 / affinity 設定
- tools/
  - paper_verification_report.py

データ / ログ:
- data/                    — 各種 DB とフラグファイル（例: monitoring.db, paper_trading.db, stop_requested.flag, kill.flag, execution.pid）
- logs/                    — ログファイル（デフォルト）

---

## 運用上の注意 / ヒント

- 本番（KABUSYS_ENV=live）では設定値やトークンの管理に注意してください。`validate_config` は live に設定されていると警告を出します。
- `KILL_FLAG_CLEAR_ON_START=1` は開発時のみ推奨。誤って本番で設定すると Kill Switch が自動でクリアされるため危険です。
- プロセス優先度設定（`psutil` を使用）や CPU affinity は環境の権限に依存します。権限不足時は警告が出てスキップされます。
- DuckDB / SQLite のファイルは設定で任意のパスに変更可能です。バックアップ / 保護を適切に行ってください。
- OpenAI 呼び出しはレート制限やネットワーク障害に対するリトライロジックを含みますが、API キーの漏洩やコストに注意してください。

---

## よく使うコマンドまとめ

- 環境ウィザード:
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```bash
  python -m kabusys.validate_config
  ```

- Execution 起動:
  ```bash
  python -m kabusys.run_execution
  ```

- Monitoring 起動:
  ```bash
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- Paper Trading 検証レポート:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要であれば、README にさらに具体的な環境変数サンプル（.env.example）やデプロイ手順（systemd / cron 設定例）、テスト手順を追加できます。どの情報を追加したいか教えてください。