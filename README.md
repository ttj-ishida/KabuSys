# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買・研究プラットフォームのコードベースです。監視・実行エンジン、ポートフォリオ構築、ファクター計算、ニュース NLP（LLM を使ったセンチメント評価）などを含むモジュール群で構成されています。

---

## 概要

- 自動売買実行エンジン（ExecutionEngine）
  - 本番 / ペーパートレードを切り替え可能（`KABUSYS_ENV`）
  - ブローカークライアントは環境に応じて実装を切替
- 監視（Monitoring）
  - システム稼働状況、データ鮮度、注文ログ、リスク監視（ドローダウン, ポジション上限）を定期チェック
  - Kill Switch（条件を満たすと `data/kill.flag` を書き、Execution を停止）
- ポートフォリオ建設（選定・重み付け・ポジションサイズ計算）
  - 等金額配分、スコア加重、リスクベース等
  - セクター集中制限や市場レジーム乗数を考慮
- リサーチ（ファクター計算・特徴量探索）
  - DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン・IC 計算など
- AI モジュール
  - ニュースの LLM ベースのセンチメントスコア化（OpenAI）
  - マクロ + ETF MA200 を使った市場レジーム判定
- ユーティリティ
  - ログ設定、プロセス優先度、設定ウィザード、設定検証、紙上検証レポート等

---

## 主な機能一覧

- run_monitoring: SystemMonitor ポーリングループを起動（`python -m kabusys.run_monitoring`）
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）
  - 監視用 SQLite は常に production の `SQLITE_PATH` を使用する設計
- run_execution: ExecutionEngine を起動（`python -m kabusys.run_execution`）
  - `KABUSYS_ENV=paper_trading` のときは MockBrokerClient を使い `data/paper_trading.db` に記録（本番 DB と分離）
- config_setup: 対話式 .env 作成ウィザード（`python -m kabusys.config_setup`）
- validate_config: .env や config/*.yaml の事前検証 CLI（`python -m kabusys.validate_config`）
- tools.paper_verification_report: ペーパートレード検証レポート生成（`python -m kabusys.tools.paper_verification_report`）
- portfolio モジュール: 候補選定、重み計算、ポジションサイズ計算（純粋関数群）
- research モジュール: ファクター計算、将来リターン、IC、統計サマリなど
- ai モジュール: ニュース NLP（`score_news`）、レジーム判定（`score_regime`）

---

## 動作要件（推奨）

- Python 3.9+（型ヒントに準拠）
- 必須ライブラリ（代表）
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
- 推奨（オプション）
  - PyYAML（`validate_config` が YAML 検証を行う場合）
- SQLite は標準ライブラリで対応
- DuckDB ファイルはデフォルトで `data/kabusys.duckdb`

インストール例（仮想環境使用推奨）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

※ 実際の requirements ファイルがある場合はそちらを利用してください。

---

## セットアップ手順（クイックスタート）

1. リポジトリをクローンしてソースを配置（本リポジトリは src パッケージ構成を前提）
2. 仮想環境を作成・有効化して依存をインストール（上記参照）
3. 対話式ウィザードで .env を作成
   ```
   python -m kabusys.config_setup
   ```
   主に設定が必要な環境変数（最低限）:
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB; デフォルト: data/paper_trading.db）
   - OPENAI_API_KEY（AI 機能を使う場合）
   - LOG_LEVEL（デフォルト: INFO）
   - その他: LINE のトークン等（任意）
4. 設定を検証
   ```
   python -m kabusys.validate_config
   ```
   `--strict` を付与すると警告も失敗扱いになります。

5. 必要に応じてデータディレクトリを作成
   ```
   mkdir -p data logs
   ```

---

## 使い方（実行例）

- 監視ループを起動：
  ```
  python -m kabusys.run_monitoring
  ```
  - `MONITOR_POLL_INTERVAL` を環境変数で上書きできます（例: `MONITOR_POLL_INTERVAL=30`）

- エンジン（Execution）を起動：
  ```
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading python -m kabusys.run_execution` でペーパートレードモード
  - 実行停止はプロジェクトの data ディレクトリに `stop_requested.flag` を作成する（起動中のプロセスが検知して終了）

- 設定検証：
  ```
  python -m kabusys.validate_config
  ```

- .env を対話で編集・作成：
  ```
  python -m kabusys.config_setup
  ```

- ペーパートレード検証レポート（SQLite DB 指定可）：
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または DB パスを直接:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- ライブラリ的な利用例（Python 内から）：
  ```py
  import duckdb
  from kabusys.research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  result = calc_momentum(conn, target_date=date(2026, 4, 10))
  ```

- AI 機能を使う場合は `OPENAI_API_KEY` を環境変数に設定するか、関数呼び出し時にキーを渡してください。

---

## 環境変数の自動ロード

- プロジェクトルートに `.env` または `.env.local` があれば、自動的にロードされます（OS 環境変数が優先）。
- 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 監視・停止に関するファイル

- stop flag（プロセス停止要求）
  - ファイル: data/stop_requested.flag
  - run_monitoring / run_execution はこのファイルを検知すると安全に終了します

- kill switch（ExecutionEngine 停止トリガー）
  - ファイル: data/kill.flag
  - KillSwitch（監視）によって書き込まれる。Execution 起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定すると自動クリア（注意: 本番では推奨されない）

- PID ファイル
  - data/execution.pid（ExecutionEngine が書く想定）

---

## データベース・テーブル（監視用 SQLite schema 要約）

init_monitoring_db により作成されるテーブル（冪等）:

- system_status
  - recorded_at, cpu_percent, memory_percent, disk_percent, process_ok
- trade_logs
  - logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms
- positions
  - code (PK), qty, avg_price, current_price, updated_at
- risk_logs
  - logged_at, event_type, metric_name, metric_value, threshold, detail
- dashboard
  - id=1 固定, updated_at, portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value

DuckDB は分析用に使われる（`data/kabusys.duckdb` に格納がデフォルト）。

---

## 主要パッケージ構成（ソースツリーの概観）

(src/ 以下を基準に)

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込みロジック
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - ai/
    - news_nlp.py            — ニュース NLU & OpenAI 呼び出しロジック
    - regime_detector.py     — 市場レジーム判定
  - monitoring/
    - monitoring_db.py       — 監視用 SQLite 永続層
    - system_monitor.py
    - trade_monitor.py       — （コード参照）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       — （アラート送信処理）
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py

---

## 開発者向けメモ

- ログはデフォルト `logs/` 配下に日次ローテーションで出力されます（`kabusys.utils.logging_setup`）。
- プロセス優先度は起動時に `high` を試みます（`kabusys.utils.process_priority`）。権限不足の場合は警告にとどまります。
- DuckDB を利用するリサーチ関数は接続オブジェクトを受け取り SQL を実行するため、外部ファイルを直接参照することはありません。
- OpenAI を利用する機能はリトライ・レスポンス検証を備えていますが、APIキーは必須です。ローカルでのテスト時はモック化が可能な設計になっています（内部の呼び出し関数をパッチ可能）。

---

## よくある質問

- Q: 本番 / ペーパートレードの DB は分離されていますか？  
  A: はい。Execution は `KABUSYS_ENV=paper_trading` の場合に `paper_sqlite_path`（デフォルト `data/paper_trading.db`）を使用し、監視 DB は本番の `SQLITE_PATH` を使います（監視は常に本番 monitoring DB を見ます）。

- Q: 監視の間隔は変更できますか？  
  A: `MONITOR_POLL_INTERVAL` 環境変数で秒数を指定してください（デフォルト 60）。

- Q: 停止方法は？  
  A: 実行中のプロセスが `data/stop_requested.flag` の存在をチェックしているため、そのファイルを作成すると安全に停止します。Kick-by-risk（Kill Switch）は `data/kill.flag` を作成します。

---

README はプロジェクトの主要操作をカバーしていますが、詳細な設計ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）や config/*.yaml の例がプロジェクト内にある場合はそちらも併せて参照してください。