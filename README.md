# KabuSys

KabuSys は日本株の自動売買システムのコードベースです。戦略・ポートフォリオ構築、発注（本番／ペーパートレード切替）、監視・アラート、調査・リサーチ、LLM を使ったニュース NLP などを含むモジュール群で構成されています。

この README はプロジェクト概要、機能一覧、セットアップ手順、基本的な使い方、主要ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

- 目的: 日本株自動売買（Execution / Monitoring / Research / Portfolio）を統合して運用するためのライブラリ／スクリプト群。
- データベース:
  - DuckDB: 分析・リサーチ用（デフォルト `data/kabusys.duckdb`）。
  - SQLite: 監視・ログ用（デフォルト `data/monitoring.db`）、ペーパートレード時は専用 `data/paper_trading.db` を使用可能。
- 環境設定: `.env` ファイルまたは環境変数で設定を行います。自動ロード機能あり（プロジェクトルートに `.env` / `.env.local` があれば読み込み）。
- CLI/スクリプト:
  - 環境ウィザード: `kabusys.config_setup`
  - 設定検証: `kabusys.validate_config`
  - 実行エンジン起動: `kabusys.run_execution`
  - 監視ループ起動: `kabusys.run_monitoring`
  - ペーパートレード検証レポート: `kabusys.tools.paper_verification_report`
- LLM 統合: OpenAI を使ったニュースセンチメント（`kabusys.ai.news_nlp`）、マクロニュースと MA によるレジーム判定（`kabusys.ai.regime_detector`）。

---

## 主な機能一覧

- Execution（発注）:
  - 実口座 / ペーパートレード切替（`KABUSYS_ENV=paper_trading` で MockBrokerClient を使用）。
  - リスク管理（rate limit, max position, circuit breaker 等）。
  - OrderManager / Reconciler / ExecutionEngine によるセッション実行。
- Monitoring（監視）:
  - SystemMonitor: CPU、メモリ、ディスク、プロセス稼働、データ鮮度の監視。
  - TradeMonitor: 注文滞留・約定異常などの検知（trade_logs テーブル参照）。
  - RiskMonitor: ドローダウン、ポジション数等の監視とリスクログ記録。
  - KillSwitch による停止フラグ生成（`data/kill.flag`）と Execution 停止トリガ。
  - MonitoringEngine によるポーリングとアラート通知の統合。
- Portfolio（ポートフォリオ構築）:
  - 候補選定（score / rank）、等分／スコア加重の重み計算。
  - セクター上限適用、レジーム乗数（bull/neutral/bear）適用。
  - ポジションサイジング（risk_based / equal / score）、単元株（lot）丸め、aggregate cap のスケールダウン。
- Research（リサーチ）:
  - ファクター計算（momentum / volatility / value）。
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー。
  - DuckDB を使った SQL + Python 実装。
- AI（LLM）:
  - ニュース記事を集約し OpenAI（gpt-4o-mini）でセンチメントを計算、`ai_scores` テーブルへ保存。
  - マクロニュース + ETF(1321) MA200 による市場レジーム判定と永続化。
  - API 呼び出しはリトライ、エラー時はフォールバックするフェイルセーフ設計。
- ユーティリティ:
  - ログ設定ユーティリティ（コンソール + 日次ローテートファイル出力）。
  - プロセス優先度 / CPU affinity 設定ユーティリティ。
  - ペーパートレード検証レポート生成ツール。

---

## 事前準備・依存関係

動作確認済みの Python バージョンは 3.10 以上を推奨（`|` 型注釈などを利用しているため）。

必須パッケージ（最低限）:
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（`validate_config` の YAML 検証を行う場合、任意）

インストール例:
```
python -m pip install duckdb psutil openai PyYAML
```

その他:
- SQLite は標準ライブラリで利用可能です。
- 必要に応じてログディレクトリ（デフォルト `logs/`）とデータディレクトリ（`data/`）を作成してください。スクリプトは自動作成を試みますが、権限が必要な場合があります。

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要な任意/設定可能項目（代表）:
- KABUSYS_ENV: execution 環境。`development` / `paper_trading` / `live`（デフォルト `development`）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH: 監視用 SQLite（デフォルト `data/monitoring.db`）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト `data/paper_trading.db`）
- LOG_LEVEL: `DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`
- OPENAI_API_KEY: OpenAI を利用する場合に設定
- PAPER_FILL_MODE: ペーパートレード時の約定挙動（`instant` / `partial` / `never` / `reject`）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、`run_monitoring` で利用。デフォルト 60 秒）
- KILL_FLAG_CLEAR_ON_START: 起動時に `data/kill.flag` を自動でクリアするか（テスト用。`1` でクリア）

.env ファイルはプロジェクトルートに配置できます。`kabusys.config_setup` が対話式ウィザードを提供します。

---

## セットアップ手順（基本）

1. リポジトリをクローン／展開する。
2. Python 仮想環境を作成して有効化:
   ```
   python -m venv .venv
   source .venv/bin/activate   # Linux/macOS
   .venv\Scripts\activate      # Windows
   ```
3. 必要パッケージをインストール:
   ```
   python -m pip install --upgrade pip
   python -m pip install duckdb psutil openai PyYAML
   ```
4. 初期設定（対話式ウィザード）:
   ```
   python -m kabusys.config_setup
   ```
   対話に従って `.env` を生成してください。
5. 設定検証:
   ```
   python -m kabusys.validate_config
   ```
   `--strict` を付けると警告も失敗扱いになります。
6. `data/` と `logs/` の書き込み権限を確認・必要なら作成:
   ```
   mkdir -p data logs
   ```

---

## 使い方（主要スクリプト）

以下は主要な起動方法の例です。すべてプロジェクトルート（`pyproject.toml` や `.git` がある場所）から実行してください。

- 実行エンジン（ExecutionEngine）を起動:
  ```
  # 通常: python -m kabusys.run_execution
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` を設定するとペーパートレード用クライアントを使用し、`PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）に記録します。
  - 実行中に停止したい場合はプロセスに対して `data/stop_requested.flag` を作成するとエンジンは安全に停止します（同リポジトリ内スクリプトがチェックします）。

- 監視ループを起動:
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書きできます（デフォルト 60 秒）。
  - 監視は本番の sqlite_path を常に参照します（環境に関係なく本番 DB を使用する設計）。
  - 停止は `data/stop_requested.flag` を作成するか、Ctrl+C（KeyboardInterrupt）で終了します。

- 設定ウィザード:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ペーパートレード検証レポート:
  ```
  # デフォルト DB を使う
  python -m kabusys.tools.paper_verification_report

  # 期間指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

  # DB パス明示
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

---

## 停止・Kill Switch の扱い

- Kill Switch:
  - RiskMonitor が重大な条件（ドローダウン超過やポジション上限超過）を検知すると `KillSwitch` が `data/kill.flag` に理由を書き込んで Execution を停止するトリガを作ります。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill flag を自動クリアします（本番では危険な設定のためデフォルトは `0`）。
  - `KillSwitch.clear()` により明示的に `data/kill.flag` を消すことができます（通常は手動操作や管理用スクリプトで処理）。

- 手動停止:
  - 実行中の Engine / Monitoring は `data/stop_requested.flag` の存在を見て終了します。管理者がこのファイルを作成すると安全に停止します。

---

## ディレクトリ構成（主要ファイル）

以下は主要なファイル／モジュールの簡易ツリー（`src/kabusys` を基点）です。

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数・設定読み込み
  - config_setup.py                — .env 対話式ウィザード
  - validate_config.py             — 起動前設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - utils/
    - logging_setup.py             — ログ設定ユーティリティ
    - process_priority.py          — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py             — SQLite ベースの監視永続化層
    - system_monitor.py            — システム状態・データ鮮度監視
    - trade_monitor.py             — 注文滞留・約定異常の監視（存在）
    - risk_monitor.py              — ドローダウン等の監視
    - kill_switch.py               — Kill Switch 制御
    - monitoring_engine.py         — 監視ポーリングの統合
    - alert_manager.py             — アラート送信管理（存在）
  - execution/
    - execution_engine.py          — 実行エンジン（EngineConfig / run_session 等）
    - order_manager.py
    - order_repository.py
    - broker_factory.py            — BrokerClientFactory（実口座と Mock を切替）
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py                   — ニュース NLP（OpenAI）で ai_scores を書き込み
    - regime_detector.py            — マクロ + MA による市場レジーム判定
  - monitoring/monitoring_db.py     — 監視 DB スキーマ定義と永続化 API

（注）上の tree は主要ファイルを抜粋したもので、実際のコードベースにはさらに補助モジュール・テスト・データ等が含まれます。

---

## 運用上の注意

- 本番運用（KABUSYS_ENV=live）では API キーやパスワード等の管理に注意してください。`.env` を Git 管理しないでください。
- `KILL_FLAG_CLEAR_ON_START=1` は本番では危険です（kill flag が誤ってクリアされる恐れがあります）。デフォルトは `0`。
- ログファイルの保存先・パーミッション、DB ファイルのバックアップ・ローテーションを運用設計に組み込んでください。
- OpenAI 等外部 API 呼び出しはレート制限や課金が発生します。テスト時はモックを使用してください（コード内で呼出し箇所を差し替え可能です）。
- `run_monitoring` は監視の DB に対して本番 sqlite_path を常に使用します。監視が本番 DB に影響を与えないよう権限・パスに注意してください。

---

この README はコードの概要と起動方法の入門としてまとめたものです。詳細な設計やアルゴリズム（ポートフォリオ設計、戦略の仕様、DB スキーマなど）はコード内のドキュメント文字列（docstring）や別添の設計ドキュメント（例: PortfolioConstruction.md、StrategyModel.md）を参照してください。何か特定の部分（設定項目の説明、実行フロー、テスト方法など）を詳しく知りたい場合は教えてください。