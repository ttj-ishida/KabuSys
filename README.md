# KabuSys

日本株向け自動売買システムのコアライブラリおよび起動スクリプト群です。  
このリポジトリは、注文実行（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI（ニュースセンチメント）などの機能を持つモジュール群で構成されています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群です。

- データ駆動の銘柄選定・配分（portfolio）
- 注文管理・発注エンジン（execution）
- システム稼働・注文状態の監視（monitoring）
- ファクター計算・リサーチ（research）
- ニュースを用いた LLM ベースのセンチメント評価（ai）
- 運用に便利な CLI ツール（config_setup、validate_config、paper_verification_report）

設計上のポイント:

- 設定は環境変数（または `.env`）で管理。`.env` 作成支援ウィザードあり。
- 実行環境は `KABUSYS_ENV`（development / paper_trading / live）。
- 監視・ログは SQLite（monitoring.db）と DuckDB（分析用）を使用。
- Paper Trading（疑似発注）モードでは本番 DB と分離された専用 SQLite を使います。

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py — ExecutionEngine を起動（本番 / ペーパートレード対応）
  - run_monitoring.py — SystemMonitor のポーリングループ起動（デフォルト 60s）
- 設定管理
  - config_setup.py — 対話式に `.env` を作成・更新
  - validate_config.py — 環境変数 / config/*.yaml の事前検証（`--strict` あり）
- 監視
  - MonitoringDB：監視用 SQLite スキーマの初期化と読み書き
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / MonitoringEngine
  - kill.flag による ExecutionEngine 停止（Kill Switch）
- ポートフォリオ構築
  - 候補選定、等配分/スコア加重、ポジションサイジング、セクター制限、レジーム乗数
- リサーチ
  - ファクター（momentum / volatility / value）計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
- AI（LLM 統合）
  - news_nlp: raw_news を LLM（OpenAI）へ送り銘柄別センチメントを算出・保存
  - regime_detector: ETF の MA とマクロニュースを合わせて市場レジーム判定
- ツール
  - paper_verification_report — ペーパートレード履歴から検証レポートを出力

---

## 前提（依存パッケージ）

代表的な依存（requirements.txt を用意している想定）:

- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config ファイル検証を行う場合に必要）
- その他：標準ライブラリ

インストール例（最低限）:

```bash
pip install duckdb psutil openai pyyaml
```

※ 実際は requirements.txt がある場合は `pip install -r requirements.txt` を推奨します。

---

## セットアップ手順

1. レポジトリをクローンする
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境の作成（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージのインストール
   ```bash
   pip install -r requirements.txt
   # または最低限:
   pip install duckdb psutil openai pyyaml
   ```

4. .env を作成（対話式ウィザード）
   ```bash
   python -m kabusys.config_setup
   ```
   - 必須: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`
   - 重要: `KABUSYS_ENV`（development / paper_trading / live）
   - OpenAI を使う場合: `OPENAI_API_KEY` を設定

5. 設定の検証
   ```bash
   python -m kabusys.validate_config
   # 警告も厳格に扱う場合
   python -m kabusys.validate_config --strict
   ```

6. ディレクトリ作成（必要に応じて）
   - デフォルトの DB / ログ / data パスは次の通り:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper Trade DB: data/paper_trading.db
     - ログ: logs/
   - これらは環境変数で上書き可能（下記参照）。起動時にディレクトリが自動作成される場合がありますが、明示的に作ると安心です。

---

## 主要環境変数（代表）

- JQUANTS_REFRESH_TOKEN — 必須（J-Quants API）
- KABU_API_PASSWORD — 必須（kabuステーション API パスワード）
- KABUSYS_ENV — 実行環境。development / paper_trading / live（デフォルト: development）
- OPENAI_API_KEY — LLM 呼び出しに必要（news_nlp / regime_detector）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite (monitoring)（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード DB（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — paper_trading の約定モード（instant / partial / never / reject）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- LOG_DIR — ログ出力ディレクトリ（デフォルト: logs/）
- PID_FILE_PATH — ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — Kill Switch の flag パス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）

---

## 使い方（起動 / CLI）

- ExecutionEngine を起動（本番 / paper_trading は KABUSYS_ENV に依存）
  ```bash
  python -m kabusys.run_execution
  ```
  - paper_trading モードでは MockBrokerClient を使用し `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）に記録します。
  - 起動時に `data/stop_requested.flag` が存在すると起動を中止します。
  - 停止は `data/stop_requested.flag` の検出または `data/kill.flag` により行われます（Monitoring が kill.flag を書くことがある）。

- Monitoring を起動（SystemMonitor のポーリング）
  ```bash
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（秒、デフォルト 60）。
  - Monitoring は常に本番用の sqlite_path を使用して監視情報を記録します（KABUSYS_ENV にかかわらず）。
  - 停止は `data/stop_requested.flag` ファイルの作成で行えます。

- 環境設定ウィザード（.env 作成）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ペーパートレード検証レポート（ツール）
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- ライブラリとしての利用（一例）
  ```python
  from kabusys.portfolio import select_candidates, calc_equal_weights
  # リサーチ
  from kabusys.research import calc_momentum
  # AI
  from kabusys.ai import score_news
  # market regime
  from kabusys.ai.regime_detector import score_regime
  ```

---

## Kill Switch / 停止フロー

- KillSwitch: `data/kill.flag` を作成することで ExecutionEngine に停止シグナルを送ります。Monitoring の条件（ドローダウン超過等）がトリガーになり得ます。
- run_* スクリプトは `data/stop_requested.flag` の存在を監視して安全に終了します（外部から停止要求を出したい場合に便利）。

---

## ロギング

- 共通ロギング設定ユーティリティ: `kabusys.utils.logging_setup.setup_logging`
  - コンソール（stdout）と日次ローテートファイル（logs/<app_name>.log）を設定
  - デフォルト保持は 30 日
  - ログレベルは引数 / 環境変数 `LOG_LEVEL` で制御

---

## ディレクトリ構成（主要ファイル）

リポジトリのルートから見た想定構成（重要ファイルのみ抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込みロジック
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py       # (参照されるが実装ファイルはここでは省略されている可能性あり)
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       # （実装がある場合）
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - execution/               — ExecutionEngine 関連コンポーネント（order_manager, broker_factory 等）
  - data/                    — データパイプライン、DB 用スクリプト（prices_daily 等の参照先）
  - research/                — リサーチ用ユーティリティ（DuckDB クエリ）

- data/                      — データ・フラグ・DB の既定格納先
  - monitoring.db             — 監視ログ SQLite（デフォルト）
  - paper_trading.db          — paper_trading 用 SQLite（デフォルト）
  - kabusys.duckdb           — DuckDB（デフォルト）
  - execution.pid, kill.flag, stop_requested.flag など

- logs/                      — ログ出力先（デフォルト）

---

## 注意点 / 運用上のヒント

- 本番（KABUSYS_ENV=live）では `KILL_FLAG_CLEAR_ON_START` を `0`（無効）にすることを推奨します。自動クリアが有効だと Kill Switch が無効化される恐れがあります。
- OpenAI API（news_nlp, regime_detector）を使用する場合、API コストとレートリミットに注意してください。モジュールはリトライとバックオフ処理を行いますが、運用ポリシーに沿って設定してください。
- Paper Trading は本番 DB と分離されています。`KABUSYS_ENV=paper_trading` 時は `PAPER_TRADING_SQLITE_PATH` が使用されます。
- ログと DB のバックアップ・ローテーション方針を別途運用ドキュメントで整備してください。

---

## 開発者向けメモ

- テストや CI では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定することで `.env` の自動読み込みを無効にできます（config.py の挙動）。
- `monitoring_db.init_monitoring_db` は冪等でカラム追加マイグレーションも含みます（既存 DB の後方互換性を考慮）。
- `utils.process_priority.set_process_priority` は OS に依存した実装があり、権限不足時は警告を出してスキップします。

---

この README はコードベースから主要な機能と運用手順を抜粋してまとめたものです。細かい実装や拡張ポイントは各モジュール内の docstring / コメントを参照してください。README の内容に加筆や補足が必要であれば、利用シナリオ（開発/本番/検証）に合わせて追記可能です。