# KabuSys

日本株向けの自動売買システム（ライブラリ/サービス群）です。  
このリポジトリは取引エンジン、監視、ポートフォリオ構築、リサーチ、AI（ニュースセンチメント／レジーム判定）などのコンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を提供します。

- 注文発行・注文管理を行う ExecutionEngine（本番 / ペーパートレード両対応）
- システム状態・注文状態・リスク指標の監視（Monitoring）
- ポートフォリオ構築・ポジションサイズ決定・セクター制限などのロジック（Portfolio）
- ファクター計算・将来リターン・IC 等のリサーチ機能（Research）
- OpenAI を用いたニュースセンチメント解析 / 市場レジーム判定（AI）
- 設定ウィザード・設定検証 CLI、ペーパートレード検証レポートなどのツール群

設計上の重要点：
- Paper trading（`KABUSYS_ENV=paper_trading`）は本番 DB から分離され、Mock ブローカーを使って `data/paper_trading.db` に記録します。
- .env ファイルの自動ロード機能あり（プロジェクトルートを自動検出）。テスト用に無効化可能。
- Kill Switch（フラグファイル）により運用中の ExecutionEngine を安全に停止可能。
- DuckDB を分析用 DB、SQLite を監視・注文ログ等の永続化に使用。

---

## 主な機能一覧

- 実行/監視
  - run_execution: ExecutionEngine 起動（スレッドで実行、pid ファイル管理、停止フラグ監視）
  - run_monitoring: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定可能）
- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/Disk、プロセス生存、データ鮮度チェック
  - TradeMonitor: 注文滞留（stale orders）・約定価格異常検出
  - RiskMonitor: ドローダウン / ポジション数上限の監視とダッシュボード更新
  - KillSwitch / AlertManager 経由で停止や通知を行う
  - monitoring_db: SQLite スキーマの初期化・永続化 API
- Execution（発注関連）
  - 注文リポジトリ、OrderManager、RiskManager、Reconciler、ExecutionEngine（EngineConfig）
  - Paper trading 用の MockBrokerClient をサポート（環境変数で切替）
- Portfolio（銘柄選定・重み・株数決定）
  - select_candidates, calc_equal_weights, calc_score_weights
  - apply_sector_cap（セクター集中制限）、calc_regime_multiplier（レジーム乗数）
  - calc_position_sizes（単元株丸め、最大ポジション制限、スケーリング）
- Research（DuckDB を用いたファクター計算等）
  - calc_momentum, calc_volatility, calc_value（prices_daily / raw_financials を参照）
  - calc_forward_returns, calc_ic, factor_summary, rank（ファクターの統計解析）
- AI（OpenAI を利用）
  - news_nlp: raw_news から銘柄別にニュースを集約し LLM に問い合わせて ai_scores を生成
  - regime_detector: ETF（1321）の MA とマクロニュースの LLM スコアを組み合わせて market_regime を判定
- ツール
  - config_setup: 対話式 .env 作成ウィザード
  - validate_config: .env / config/*.yaml の設定検証 CLI（--strict オプションあり）
  - tools.paper_verification_report: ペーパートレードの検証レポート生成（期間指定可）

---

## 前提・依存関係

- Python 3.10 以上（PEP 604 の型表記（A | B）を使用）
- 推奨パッケージ（最低限）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config の YAML 検証に使用。無くても実行は可能だが YAML 検証がスキップされます）
- 標準で使用する DB:
  - DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLite（監視用: data/monitoring.db、ペーパートレード: data/paper_trading.db）

インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

（requirements.txt がない場合は上記を参考にしてください）

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

重要（よく使う）:
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant|partial|never|reject、デフォルト instant）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（"1" で有効、デフォルト "0"）

.env はプロジェクトルートの `.env` / `.env.local` から自動ロードされます（自動ロードを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

---

## セットアップ手順

1. リポジトリをクローンしてワークスペースへ移動
   - （本説明はプロジェクトルート直下で実行することを前提とします）

2. Python 仮想環境の作成と依存パッケージのインストール
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb psutil openai PyYAML
   ```

3. 環境変数ファイルを作成（推奨: 対話式ウィザードを使用）
   ```
   python -m kabusys.config_setup
   ```
   - ウィザードは .env を作成します（.env は絶対に git にコミットしないでください）

4. 設定検証
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict   # 警告を FAIL 扱いにする
   ```

5. 必要なディレクトリ作成（data ディレクトリ等）
   - 例: `mkdir -p data`

6. OpenAI を使う機能を動かす場合は `OPENAI_API_KEY` を設定

---

## 使い方（主なコマンド）

- ExecutionEngine を起動（本番 / ペーパートレードは KABUSYS_ENV に依存）
  ```
  python -m kabusys.run_execution
  ```
  - 実行中に `data/stop_requested.flag` が作成されると安全に停止します。
  - ExecutionEngine は pid ファイル（デフォルト: data/execution.pid）を作成します。
  - Paper trading の場合、`KABUSYS_ENV=paper_trading` を設定すると専用 DB（PAPER_TRADING_SQLITE_PATH）を使用します。

- Monitoring を起動（SystemMonitor のポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）。
  - run_monitoring は常に本番の sqlite_path（監視 DB）を使用します（環境にかかわらず）。

- .env（環境変数）ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading レポート生成
  ```
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI 機能実行（例: ニューススコアリング / レジーム判定）
  - これらは Python API 経由で呼ぶ設計です（DuckDB 接続を渡して使用）。
  - 簡易的に呼ぶ場合は Python REPL / スクリプト内で:
    ```python
    from kabusys.ai.news_nlp import score_news
    # duckdb_conn: duckdb.connect(...)
    score_news(duckdb_conn, target_date, api_key="...")  # Returns number of written codes
    ```

注意:
- AI 機能は OPENAI_API_KEY が必要です。キーが未設定の場合、明示的に api_key 引数を渡す必要があります。
- `validate_config` は PyYAML がない場合、config/*.yaml の内容検証をスキップします（警告が出ます）。

---

## 運用上のポイント

- Kill Switch（data/kill.flag）:
  - RiskMonitor 等が条件を満たすと `kill.flag` を書き込み、ExecutionEngine に停止シグナルを送ります。
  - `KILL_FLAG_CLEAR_ON_START=1` にすると起動時に自動クリアされますが、本番では推奨されません（危険）。
- 停止フラグ:
  - `data/stop_requested.flag` を作成すると run_execution / run_monitoring のループが終了します（開発用）。
- ペーパートレード:
  - 本番 DB と完全分離されます。`KABUSYS_ENV=paper_trading` を設定すると MockBrokerClient を使用し、データは `PAPER_TRADING_SQLITE_PATH` に書き込まれます。
- プロセス優先度:
  - 起動時にプロセス優先度を "high" に設定するユーティリティを呼び出します（権限により無視される場合があります）。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor のポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - execution/               — Execution 関連（OrderManager, ExecutionEngine 等）※詳細は該当モジュール参照
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - process_priority.py

（上記は本 README に含まれる代表的なファイル。詳細はソースツリーを参照してください）

---

## 開発・テスト時のヒント

- 自動ロードを無効化する（ユニットテストなどで便利）:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- validate_config の `--strict` は警告を FAIL として返すため、本番デプロイ前チェックに有用
- DuckDB / SQLite の場所は Settings で参照されるため、テスト時は一時ディレクトリを指定して分離してください
- OpenAI 呼び出し箇所はテスト時にモック化（patch）する設計になっています（モジュール内で _call_openai_api を分離）

---

## ライセンス / 注意事項

- 本リポジトリの .env（API キー等の機密）は絶対にコミットしないでください。
- 本 README はコードベースから抽出した情報をまとめたもので、運用前に `python -m kabusys.validate_config` で設定検証を実施してください。

---

質問やドキュメントの補足が必要であれば、どのセクションを詳しく出力するか指定してください。