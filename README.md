KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株の自動売買 / 研究 / 監視を目的とした Python コードベースです。  
本リポジトリは次のような責務を持つモジュール群を含みます。

- ExecutionEngine（発注ロジック、リスク管理、注文管理）
- Monitoring（システム稼働・注文・リスク監視、Kill Switch）
- Portfolio（銘柄選定・配分・ポジションサイズ計算）
- Research（ファクター計算・特徴量解析）
- AI（ニュース NLP によるセンチメント評価 / レジーム判定）
- ユーティリティ（設定ロード、ログ設定、プロセス優先度など）
- ツール（ペーパートレード検証レポート等）

主な特徴
---------
- ExecutionEngine と Monitoring を分離したプロセス構成（stop/kill フラグによる制御）
- Paper Trading 用の完全分離された SQLite（data/paper_trading.db）サポート
- DuckDB を利用した高速な時系列・財務データ集計（research モジュール）
- ニュースを LLM（OpenAI）で評価する AI パイプライン（batch / retry / validation 実装）
- 監視用 DB（SQLite）と永続化 API（MonitoringDB）によるログ管理
- 環境設定ウィザード（対話式 .env 作成）と設定検証 CLI

前提条件
---------
- Python 3.10 以上（型ヒントに PEP 604 の union 型 (X | Y) を使用）
- 必要な Python パッケージ（最低限）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML (config ファイル検証を行う場合)
- 任意: SQLite (標準ライブラリで提供)

インストール（例）
------------------
仮想環境を作成して必要ライブラリをインストールします。

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

設定（.env）
-----------
1. 対話式ウィザードで .env を生成する（推奨）:
   ```bash
   python -m kabusys.config_setup
   ```
   ウィザードは J-Quants / kabuAPI のトークン、DB パス、ログレベル等を対話形式で設定します。

2. 手動または CI で環境変数を設定する場合は以下を最低限用意してください:
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - OPENAI_API_KEY (AI 機能を使う場合)
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development

設定自動ロードについて:
- プロジェクトルートに .env/.env.local があれば自動で読み込みます（OS 環境変数が優先）。
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

設定検証
-------
起動前に設定をチェックできます。

```bash
python -m kabusys.validate_config
# 警告を FAIL 扱いにする場合:
python -m kabusys.validate_config --strict
```

主な実行方法
------------

- ExecutionEngine（取引エンジン）を起動:
  - 本番 / 開発 / ペーパートレードは KABUSYS_ENV に依存します。
  - ペーパートレード時は MockBrokerClient を使用し、データは data/paper_trading.db に保存されます。
  ```bash
  # 例: ペーパートレードで起動
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```

  実装のポイント:
  - 起動時にプロセス優先度を high に設定します。
  - 停止フラグ (data/stop_requested.flag) を監視して安全停止します。
  - PID ファイル (data/execution.pid) を利用します。

- Monitoring（監視）を起動:
  ```bash
  # 例: 監視プロセス起動
  python -m kabusys.run_monitoring
  ```
  設定:
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能。デフォルト 60 秒。
  - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用して監視ログを保存します。

- Paper Trading 検証レポート:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを指定する場合:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI 機能（プログラム API）:
  - ニュースセンチメント（銘柄別）:
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key=None)
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key=None)
  両関数とも OPENAI_API_KEY（または引数 api_key）を必要とします。

重要なファイル・フラグ
---------------------
- data/stop_requested.flag — run_execution/run_monitoring の停止検知フラグ
- data/execution.pid — 実行エンジンの PID ファイル
- data/kill.flag — KillSwitch が書き込む停止フラグ（ExecutionEngine に対する上位停止命令）
- data/monitoring.db — 監視用 SQLite（デフォルト）
- data/paper_trading.db — paper_trading 用 SQLite（KABUSYS_ENV=paper_trading）

ログ
----
- ログはデフォルトで logs/ 配下に出力されます（例: logs/execution.log, logs/monitoring.log）。
- ログ設定は kabusys.utils.logging_setup.setup_logging() で統一管理されており、日次ローテーション（30 日分）となっています。
- ログレベルは環境変数 LOG_LEVEL または .env で設定します（デフォルト: INFO）。

ディレクトリ構成（抜粋）
-----------------------
以下は主要なディレクトリ / ファイル構成と簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / 設定読み込みロジック（.env 自動読み込み機能含む）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py — ログ初期化ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - execution/  — 発注エンジン周り（BrokerFactory, ExecutionEngine, OrderManager 等）
  - monitoring/
    - monitoring_db.py — 監視用 DB 層（テーブル定義・永続化 API）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文/約定監視（滞留、異常検知）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — Kill Switch（flag ファイル制御）
    - monitoring_engine.py — 各 Monitor を束ねるループ
    - alert_manager.py — 通知管理（LINE 等）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 株数計算・投資上限・丸め処理
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — Momentum/Value/Volatility 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - ai/
    - news_nlp.py — ニュースセンチメントスコア（OpenAI）
    - regime_detector.py — マクロ + ETF MA を合成したレジーム判定（OpenAI）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - data/ （アプリ実行時に生成される想定）
    - monitoring.db, paper_trading.db, stop_requested.flag, execution.pid, kill.flag など

開発・運用時の注意点
--------------------
- KABUSYS_ENV=live のときは本番向けの厳重な確認を行ってください（validate_config に本番ガードがあります）。
- .env は絶対にバージョン管理にコミットしないでください（config_setup.py のメッセージ参照）。
- OpenAI 呼び出しは外部ネットワーク・コストが発生します。API キー・レート制限に注意してください。
- ペーパートレード用 DB は本番 DB と明確に分離されていますが、環境変数確認は怠らないでください。
- ローカルで自動テストを行う場合、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使うことで .env 自動読み込みを抑制できます。

サンプル実行フロー（簡易）
------------------------
1. 仮想環境作成・依存インストール
2. python -m kabusys.config_setup で .env を作成
3. python -m kabusys.validate_config で検証
4. 起動:
   - 監視: python -m kabusys.run_monitoring
   - 実行エンジン: KABUSYS_ENV=paper_trading python -m kabusys.run_execution
5. ペーパートレード結果・ログを確認し、必要に応じて paper_verification_report を実行

問い合わせ・拡張
----------------
- 研究用の DuckDB テーブル（prices_daily, raw_financials, raw_news 等）を整備することで research/ai 部分を活用できます。
- Execution や BrokerClient の実装はプラガブルになっている想定（BrokerClientFactory を参照）。
- 追加の通知チャネルや監視ルールは monitoring/*.py を拡張してください。

ライセンスや貢献方法についてはリポジトリのトップレベルドキュメントをご参照ください（この README はコードベースの概要説明と利用方法を中心に記載しています）。

---  
以上がプロジェクトの概要・セットアップ・基本的な使い方です。必要があれば、具体的な起動スクリプトの systemd サービス定義例や docker 化手順、よくあるトラブルシュート（ログの見方、DB マイグレーション等）を追加で作成します。どの部分を深掘りしますか？