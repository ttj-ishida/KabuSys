# KabuSys

日本株向け自動売買システムのコアライブラリ（リサーチ、ポートフォリオ構築、実行、監視、AI 補助機能を含む）。  
このリポジトリは、発注エンジン（ExecutionEngine）、監視（MonitoringEngine）、ポートフォリオ構築ユーティリティ、ファクター計算、ニュース NLP / レジーム判定などのモジュール群で構成されています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買ワークフローを支援するモジュール群です。主な用途は以下のとおりです。

- 戦略リサーチ（DuckDB 上の時系列データを使ったファクター計算）
- ポートフォリオ構築（候補選定、重み付け、株数算出、セクター制限など）
- 実行エンジン（ブローカークライアントを通じた発注管理、ペーパートレードの分離）
- 監視（システム稼働・注文・リスクの定期チェック、Kill Switch）
- AI 補助（ニュースのセンチメントスコアリング、マクロ系レジーム判定）
- 運用ツール（設定ウィザード、設定検証、ペーパートレード検証レポート）

設計方針として、DB（DuckDB/SQLite）を用いたデータ永続化、フェイルセーフ（API失敗時のフォールバック）、およびルックアヘッドバイアス回避が組み込まれています。

---

## 主な機能一覧

- 実行関連
  - ExecutionEngine（発注の管理・実行）
  - BrokerClientFactory（環境に応じて実ブローカー / MockBroker を切替）
  - Paper trading は本番 DB と分離（`data/paper_trading.db` がデフォルト）

- 監視 / アラート
  - SystemMonitor：CPU / メモリ / ディスク / プロセス生存チェック、データ鮮度チェック
  - TradeMonitor：注文滞留・約定異常の検出（trade_logs）
  - RiskMonitor：ドローダウン・ポジション上限監視、kill flag（停止信号）発行
  - MonitoringEngine：複数モニタを束ねポーリング処理を実行

- ポートフォリオ構築
  - 候補選定（スコア降順）
  - 等配分・スコア加重配分
  - リスクベース配分（position sizing）、単元株丸め、aggregate cap のスケーリング
  - セクター上限適用、レジームによる投下資金乗数

- リサーチ
  - ファクター計算（Momentum, Volatility, Value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー

- AI（OpenAI 依存）
  - news_nlp: ニュース記事を LLM で評価して ai_scores に書き込み
  - regime_detector: ETF（1321）MA 乖離 + マクロニュースセンチメントでレジーム判定

- ユーティリティ
  - 環境設定ウィザード（.env 生成）: `config_setup.py`
  - 設定検証 CLI: `validate_config.py`
  - Paper trading 検証レポート生成ツール: `tools/paper_verification_report.py`
  - ロギングセットアップ（コンソール + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 必要条件 / 依存パッケージ

推奨 Python バージョン: 3.10+

主な依存（環境によって必要なパッケージ）:
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config YAML のパース検証を行う場合）

インストール例（仮想環境推奨）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```
※ 実際の requirements.txt がある場合はそれに従ってください。

SQLite は Python 標準ライブラリに含まれます。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存パッケージをインストール
   ```
   pip install duckdb psutil openai pyyaml
   ```

4. .env の初期作成（対話式ウィザード）
   ```
   python -m kabusys.config_setup
   ```
   ウィザードで必須の環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）を入力してください。`.env` は Git にコミットしないでください。

5. 設定検証
   ```
   python -m kabusys.validate_config
   ```
   問題がなければ OK メッセージが出ます。`--strict` を付けると警告も失敗扱いになります。

6. データディレクトリの確認（`data/`、`logs/` はスクリプトが自動生成することが多いですが、必要に応じて権限等を確認してください）。

---

## 環境変数（主要なもの）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY（AI 機能を使う場合）
- KABUSYS_ENV（development | paper_trading | live、デフォルト: development）
  - paper_trading: MockBroker を使い、発注ログは paper_trading 用 DB に記録
  - live: 実運用モード（慎重に設定してください）
- PAPER_FILL_MODE（paper_trading 時の約定モード: instant | partial | never | reject、デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 SQLite パス、デフォルト: data/paper_trading.db）
- DUCKDB_PATH（DuckDB ファイル、デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視用 SQLite、デフォルト: data/monitoring.db）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- LOG_DIR（ログ保存先ディレクトリ、デフォルト: logs）
- PID_FILE_PATH（ExecutionEngine の PID ファイル、デフォルト: data/execution.pid）
- KILL_FLAG_PATH（Kill Switch の flag ファイル、デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか: 0/1、デフォルト: 0）
- MONITOR_POLL_INTERVAL（監視のポーリング間隔秒数、デフォルト: 60）

注意:
- Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視ログは一元化）。
- run_execution は `KABUSYS_ENV=paper_trading` の場合、`PAPER_TRADING_SQLITE_PATH` を使用し本番 DB と分離します。

---

## 使い方（主要コマンド）

エントリポイントはモジュール実行（-m）スタイルで提供されています。

- 環境設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン起動（ExecutionEngine）
  ```
  python -m kabusys.run_execution
  ```
  - 起動時に `data/stop_requested.flag` があると起動を停止します。
  - ExecutionEngine は `PID_FILE_PATH` に PID を書きます（設定による）。
  - `KABUSYS_ENV=paper_trading` の場合は MockBroker を使い `PAPER_TRADING_SQLITE_PATH` に記録します。

- 監視ループ起動（Monitoring）
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  - `MONITOR_POLL_INTERVAL`（秒）でポーリング間隔を上書き可能（デフォルト 60）。
  - 監視中に `data/stop_requested.flag` が作成されるとループを終了します。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - `--db` で SQLite DB を指定するか、環境変数 `PAPER_TRADING_SQLITE_PATH` を使用。

- AI 機能（プログラム側 API）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
  いずれも OpenAI API キーは引数または環境変数 `OPENAI_API_KEY` を参照します。

停止・Kill flag 操作:
- ExecutionEngine を即時停止させたい場合は `data/kill.flag` を作成する（KillSwitch が検知すると停止）。
- 監視ループ / 実行ループを完全停止させるために `data/stop_requested.flag` を作成することでも停止できます（スクリプトは存在チェックを行っています）。

---

## ログ

- ロギングはコンソール（stdout）出力と日次ローテートファイル（logs/<app_name>.log）を標準で設定します。
- ログレベルは `LOG_LEVEL` 環境変数または `setup_logging(..., level=...)` により指定可能。
- ログディレクトリは `LOG_DIR` 環境変数で変更可能（デフォルト: logs/）。
- 日次ローテートは 30 日分保持されます。

---

## ディレクトリ構成（概要）

以下は主要なファイル・モジュールの構成（src/kabusys 以下）です。実際のリポジトリには追加のサブモジュールが含まれる場合があります。

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / Settings クラス、.env 自動読み込み
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py      — 統一ログ設定ユーティリティ
    - process_priority.py   — プロセス優先度 / CPU affinity ユーティリティ
  - execution/               — ExecutionEngine、OrderManager、RiskManager 等（発注側）
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - monitoring/
    - monitoring_db.py      — SQLite 用永続層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py

（注）実際のサブモジュールの細部はコードを参照してください。上は主要な機能ごとの分類を示しています。

---

## 注意事項 / 運用上のヒント

- 本番運用（KABUSYS_ENV=live）では、LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID）など監視・通知系を必ず整備してください。
- `.env` は絶対にリポジトリにコミットしないでください（機密情報を含みます）。
- OpenAI 等の外部 API を使用する機能は、API コストやレート制限に注意して運用してください。AI 呼び出しはリトライ・バックオフ戦略を踏んでいますが、失敗時はフェイルセーフにより処理継続します。
- Paper trading（`KABUSYS_ENV=paper_trading`）は本番データベースと分離されます。ローカル検証やアルゴリズム評価に活用してください。
- 監視は `MONITOR_POLL_INTERVAL` で間隔を制御できます（デフォルト 60 秒）。短くしすぎると監視プロセス負荷が高まります。

---

## 開発 / テスト

- モジュールはなるべく副作用を持たない純粋関数群として設計されています（リサーチ / ポートフォリオ計算）。
- DB 接続や外部 API 呼び出しは引数で注入可能な設計で、ユニットテストが容易です（例: OpenAI 呼び出し関数はモック可能）。
- `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると config.py による `.env` の自動ロードを抑制できます（テスト用）。

---

README は以上です。さらに詳しい実装や設計方針（PortfolioConstruction.md 等のドキュメント）や実行エンジンの設定詳細が必要であれば、どの領域を深掘りするか教えてください。