# KabuSys

日本株向け自動売買システム（ライブラリ + 起動スクリプト群）

このリポジトリは、戦略リサーチ、ポートフォリオ構築、発注実行（本番 / ペーパートレード）、および稼働監視を一貫して実行するためのモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は次の主要機能を持つ自動売買フレームワークです。

- ファクター計算（モメンタム・バリュー・ボラティリティなど）と特徴量探索（Research）
- ポートフォリオ構築（候補選定、重み計算、リスク調整、ポジションサイズ計算）
- ExecutionEngine による発注実行（本番 / ペーパー）
- Monitoring（システム状態、注文ログ、リスク監視、Kill Switch）
- AI 補助機能（ニュースの NLP スコアリング、レジーム判定） — OpenAI を使用
- ツール類（ペーパートレード検証レポート生成、環境設定ウィザード、設定検証 CLI）
- ロギング・プロセス優先度のユーティリティ

設計方針の一部：
- データベースは DuckDB（分析用） と SQLite（監視・発注ログ）を併用
- 設定は .env ファイル / 環境変数で管理
- 本番（live）とペーパー（paper_trading）環境を明確に分離

---

## 機能一覧

- config
  - .env 自動ロード（プロジェクトルート検出）
  - interactive ウィザードで .env 作成（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
- execution
  - ExecutionEngine（発注エンジン）、OrderManager、RiskManager、Reconciler など
  - Broker クライアントファクトリ（本番／モック切替）
  - ペーパートレード時は MockBrokerClient を使用し専用 DB に記録
- monitoring
  - SystemMonitor（CPU/Mem/Disk、データ鮮度、プロセス死活）
  - TradeMonitor（注文滞留・約定異常検知）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（条件に応じて data/kill.flag を書き込み ExecutionEngine を停止）
  - Monitoring DB（SQLite）操作ラッパー
  - MonitoringEngine（各モニタをまとめて定期実行）
- portfolio
  - 候補選定、等金額／スコア加重、リスク調整、ポジションサイズ計算
- research
  - DuckDB に対するファクター計算（momentum/value/volatility）
  - 将来リターン計算、IC 計算、統計サマリーなど
- ai
  - news_nlp: OpenAI を用いたニュースセンチメントの銘柄別スコア化
  - regime_detector: ETF とマクロニュースを使った市場レジーム判定
- tools
  - paper_verification_report: ペーパートレードの検証レポート生成

---

## 必要な依存関係

主要な Python パッケージ（抜粋）:

- Python 3.8+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（設定 YAML の検証を行う場合、任意）
- その他標準ライブラリ（sqlite3 等）

インストール例（pip）:

```bash
pip install duckdb psutil openai pyyaml
```

（プロジェクトでは仮想環境の利用を推奨します）

---

## セットアップ手順

1. リポジトリをクローンしてルートに移動

2. 必要パッケージをインストール

3. .env を作成
   - 対話式ウィザードを使う：
     ```bash
     python -m kabusys.config_setup
     ```
   - もしくは `.env.example` を参考に手動作成（リポジトリに example がある場合）

   重要な環境変数（最低限）:
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
   - OPENAI_API_KEY（AI 機能を使用する場合）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（ペーパートレード専用 DB、デフォルト: data/paper_trading.db）
   - LOG_LEVEL（例: INFO）

4. 設定検証（起動前チェック）
   ```bash
   python -m kabusys.validate_config
   # 警告をエラーとして扱う場合
   python -m kabusys.validate_config --strict
   ```

5. ログディレクトリとデータディレクトリを作成（多くは自動で作られますが確認）
   - デフォルトのログディレクトリは `logs/`
   - SQLite / DuckDB のデフォルトパスは `data/` 配下

---

## 使い方（起動例）

- ExecutionEngine を起動（通常はサーバー上でデーモン的に実行）:
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し `data/paper_trading.db` に記録されます。
  - 実行中に停止させるには `data/stop_requested.flag` を配置するか、Kill Switch により `data/kill.flag` が作成されると停止します。
  - ExecutionEngine は起動時に `data/execution.pid` を書きます（PIDファイル）。

- Monitoring を起動（ポーリングループ）:
  ```bash
  python -m kabusys.run_monitoring
  ```
  - デフォルトのポーリング間隔は 60 秒（環境変数で上書き可能）:
    ```bash
    export MONITOR_POLL_INTERVAL=30
    ```
  - 監視は常に本番用の sqlite_path を使用します（設定の env にかかわらず）。

- Kill Switch（手動で停止フラグをセット）
  - Execution を安全に止めたい場合は `data/kill.flag` を作成します。KillSwitch クラス経由でも自動で作成されます。

- AI 機能（ニューススコアリング）を Python から呼ぶ例:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY を環境変数か引数で渡す
  score_news(conn, target_date=date(2026, 4, 1), api_key=None)
  ```

- ペーパートレード検証レポート:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を指定する場合
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

---

## 環境変数 / 設定（主なもの）

- KABUSYS_ENV: execution モード（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI を使う場合
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL / LOG_DIR
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant / partial / never / reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（開発用。0/1）

---

## ディレクトリ構成（主要ファイル）

ルート: src/kabusys 以下

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数・設定管理
  - config_setup.py           — 対話式 .env ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (※実装に依存するファイル)
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/                      — 実行時に生成される（logs、db、flag など）

（上記は主要ファイルの抜粋です。詳しくは src/kabusys 以下を参照してください。）

---

## 運用上の注意点

- 本番環境（KABUSYS_ENV=live）の設定は慎重に行ってください。validate_config によるチェックで注意喚起が出ます。
- .env は秘密情報を含むため絶対に Git 等へコミットしないでください。
- Monitoring は本番 sqlite_path を常に参照します（run_monitoring 内の設計）。監視 DB は本番と同じ設定のまま扱われます。
- ペーパートレード時は PAPER_TRADING_SQLITE_PATH により本番 DB と分離されます。
- AI 機能を使う場合は OPENAI_API_KEY が必要です。API エラーはフェイルセーフ（スコア 0.0 等）で処理される実装になっていますが、API 使用量・コストには注意してください。
- プロセス優先度・CPU affinity を設定するユーティリティが含まれています（psutil が必要）。権限不足やプラットフォーム差異により設定に失敗する場合は警告を出してスキップします。
- 監視ループやエンジンの停止は flag ファイル（data/stop_requested.flag, data/kill.flag）で行う設計になっています。手動操作や自動化スクリプトからこれらのファイルを管理することで安全停止できます。

---

## 開発・テスト

- 単体関数は副作用を持たない純粋関数として設計されているものが多く、ユニットテストが容易です（portfolio、research 等）。
- 外部 API 呼び出し部分（OpenAI、ブローカークライアントなど）はモック可能に実装されています（テスト時は patch してください）。
- config の自動ロードはプロジェクトルート検出に依存します。テストでは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。

---

必要に応じて README に追記します。特定の起動例やデプロイ手順（systemd / cron / Docker 化）を追加したい場合は用途を教えてください。