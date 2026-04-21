# KabuSys — README (日本語)

簡単な日本語ドキュメントです。本リポジトリは日本株向けの自動売買 / 研究 / 監視ユーティリティ群を含むパッケージです。ここではプロジェクトの概要、主要機能、セットアップ手順、使い方、ディレクトリ構成をまとめます。

なお本 README はソースコード（src/kabusys 以下）を参照して作成しています。

---

## プロジェクト概要

KabuSys は日本株自動売買システムのコアライブラリ群です。主な目的は以下です。

- シグナル生成・ポートフォリオ構築（ポートフォリオ構成ロジック）
- 発注実行エンジン（ExecutionEngine）および発注周りの管理
- 監視（System / Trade / Risk）と自動停止（Kill Switch）
- 研究用ファクター計算・特徴量探索（DuckDB 経由）
- Paper Trading の検証・レポート生成
- ニュースの NLP によるセンチメント評価（OpenAI を利用するモジュール）
- 起動時の設定ウィザード・検証ツール等の CLI

設計方針の一例：
- DuckDB / SQLite を使ったデータ管理（分析と監視で分離）
- 本番（live）・開発（development）・ペーパートレード（paper_trading）を環境変数で切替
- OpenAI API を利用した NLP 機能を備える（APIキーは環境変数で指定）

---

## 機能一覧（主なモジュール）

- 起動スクリプト
  - run_execution.py : ExecutionEngine を起動（KABUSYS_ENV による paper_trading 切替）
  - run_monitoring.py : SystemMonitor のポーリングループを起動（監視用）
- 設定
  - config_setup.py : 対話式 .env 作成ウィザード
  - validate_config.py : .env と config/*.yaml の起動前検証 CLI
  - config.py : 環境変数と Settings クラス（既定値と検証ロジック含む）
- 監視
  - monitoring/monitoring_db.py : 監視ログ用 SQLite テーブル（初期化・永続化）
  - monitoring/system_monitor.py : CPU/メモリ/ディスク・データ鮮度・プロセス監視
  - monitoring/trade_monitor.py, monitoring/risk_monitor.py, monitoring/kill_switch.py, monitoring/monitoring_engine.py 等（監視ロジック・Kill Switch）
  - monitoring/init スキーマは冪等で作成し既存 DB へマイグレーション処理あり
- 発注関連（Execution）
  - execution/* : BrokerClientFactory、ExecutionEngine、OrderManager、RiskManager、Reconciler 等（発注実行に係るコンポーネント）
  - ペーパートレード時は MockBrokerClient を利用し、paper_trading 用 DB に記録して本番 DB と分離
- ポートフォリオ（Portfolio）
  - portfolio/portfolio_builder.py : 候補選定・重み計算（等金額 / スコア加重）
  - portfolio/position_sizing.py : 株数決定・単元丸め・資金スケーリング（risk_based / equal / score）
  - portfolio/risk_adjustment.py : セクター上限適用・レジーム乗数
- 研究（Research）
  - research/factor_research.py : Momentum / Volatility / Value などファクター計算（DuckDB で SQL 実行）
  - research/feature_exploration.py : 将来リターン計算、IC（Information Coefficient）、統計サマリ等
- AI（OpenAI 連携）
  - ai/news_nlp.py : ニュース記事の銘柄別センチメント評価（OpenAI API）
  - ai/regime_detector.py : マクロ＋ETF MA の合成で市場レジーム判定（LLM を利用）
- ユーティリティ
  - utils/logging_setup.py : 統一的なログ設定（stdout + 日次ローテーションファイル）
  - utils/process_priority.py : プラットフォーム差分を吸収したプロセス優先度 / CPU affinity 設定
- ツール
  - tools/paper_verification_report.py : Paper Trading の検証レポート生成（SQLite DB を読みレポート出力）

---

## 事前要件（依存パッケージの例）

下記はソースで明示的に使われている主要ライブラリです。環境や用途に応じて追加してください。

- Python 3.9+（型ヒントにより 3.9+ を想定）
- duckdb
- psutil
- openai（AI モジュール利用時）
- PyYAML（config 検証で YAML を検査したい場合）
- sqlite3（標準ライブラリ）

インストール例（最低限）:
```
pip install duckdb psutil openai pyyaml
```
（プロジェクト内に requirements.txt があればそれを利用してください。）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンして作業ディレクトリに移動
2. 仮想環境を作成・有効化（任意）:
   - python -m venv .venv
   - source .venv/bin/activate（Windows は .venv\Scripts\activate）
3. 必要なパッケージをインストール:
   - pip install duckdb psutil openai pyyaml
4. .env を作成
   - 対話式ウィザードを使う（推奨）:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは手動で .env を作成（例は下記参照）
5. 設定検証:
   ```
   python -m kabusys.validate_config
   # --strict を付けると警告も失敗扱い（exit code 1）
   python -m kabusys.validate_config --strict
   ```
6. データディレクトリ（logs, data など）は自動作成される機能がありますが、必要に応じて手動で作成してください。

---

## 使い方（主要 CLI / 実行例）

- .env 作成（対話式）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証（起動前チェック）
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine を起動（本番 / ペーパーは KABUSYS_ENV に依存）
  ```
  python -m kabusys.run_execution
  ```
  挙動のポイント:
  - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite DB（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient での発注記録を行います。本番 DB と分離されます。
  - 起動時に data/execution.pid が作成される等、pid ファイルパスは Settings.pid_file_path（デフォルト data/execution.pid）。
  - 停止は実行中に data/stop_requested.flag を作成することで検出されエンジンが停止します（同様に run_monitoring でも stop フラグを参照）。

- Monitoring（監視）を起動
  ```
  python -m kabusys.run_monitoring
  ```
  主な挙動:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き（デフォルト 60 秒）
  - 監視は Settings.sqlite_path（デフォルト data/monitoring.db）に接続しログを保存します。監視モジュールは環境にかかわらず本番 sqlite_path を使用する設計です。
  - 停止: data/stop_requested.flag を作成すると監視ループが終了します。

- Paper Trading の検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB パス: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH または --db オプションで上書き可）

- AI / レジーム判定等（ライブラリ関数の呼び出し）
  - News NLP や regime_detector は OpenAI API キー（OPENAI_API_KEY 環境変数）を必要とします。
  - 例（簡易、DuckDB 接続を前提）:
    ```py
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, date(2026, 4, 1))  # OPENAI_API_KEY が環境変数に必要
    ```

---

## 主要な環境変数（主なもの）

（.env の項目は config_setup.py に定義があります。ここに代表的なキーとデフォルトを示します）

- 必須（起動に必須）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）

- データベース
  - DUCKDB_PATH: DuckDB ファイルのパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）

- ログ / 動作
  - LOG_LEVEL: DEBUG|INFO|...（デフォルト INFO）
  - LOG_DIR: ログファイル格納ディレクトリ（デフォルト logs）
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒） — run_monitoring が参照（デフォルト 60）

- OpenAI
  - OPENAI_API_KEY: OpenAI API を利用する機能で必須

- Kill Switch / フラグ
  - KILL_FLAG_PATH: kill.flag のパス（Settings.kill_flag_path, デフォルト data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアする（"1" で有効。production では推奨しない）

---

## ファイル・フラグの挙動（停止 / Kill Switch）

- 停止フラグ（run_execution / run_monitoring）
  - data/stop_requested.flag を作成すると両スクリプトは検出して終了処理を行います（デーモン化している場合は同様に停止シグナルとして機能）。
- Kill Switch
  - monitoring の KillSwitch（monitoring/kill_switch.py）はリスク条件（ドローダウン超過・ポジション上限超過等）で data/kill.flag を書き込み、ExecutionEngine 側で参照して停止させる運用を想定しています。
  - 設定で KILL_FLAG_CLEAR_ON_START=1 をセットすると起動時に kill.flag を自動クリアする挙動になりますが、本番では 0 を推奨します。

---

## ログ

- ログ設定は utils/logging_setup.py に集約されています。
- デフォルトで stdout に出力され、日次ローテーションでファイル出力（logs/<app_name>.log）されます。
- ログディレクトリは LOG_DIR 環境変数またはデフォルト "logs" を使用します。

---

## ディレクトリ構成（抜粋）

（パッケージルート: src/kabusys）

- __init__.py
- config.py
- config_setup.py
- validate_config.py
- run_execution.py
- run_monitoring.py

- ai/
  - news_nlp.py
  - regime_detector.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- monitoring/
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py (参照あり)
- execution/
  - execution_engine.py (参照あり)
  - broker_factory.py (参照あり)
  - order_manager.py (参照あり)
  - order_repository.py (参照あり)
  - reconciler.py (参照あり)
  - risk_manager.py (参照あり)
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py
  - process_priority.py

（概要のみ。各ファイルの詳細はソースコメントを参照してください。）

---

## サンプル .env（参考）

以下は .env の一例（機密情報は伏せてください）:

```
# 環境
KABUSYS_ENV=development
LOG_LEVEL=INFO

# J-Quants / kabuステーション
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here

# DB
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

# OpenAI
OPENAI_API_KEY=sk-...

# Kill Switch
KILL_FLAG_CLEAR_ON_START=0
```

対話式で安全に作成する場合は `python -m kabusys.config_setup` を使ってください。

---

## デバッグ / 開発時のヒント

- validate_config.py は起動前の必須環境変数やファイルパスをチェックします。CI やデプロイ前に実行してください。
- DuckDB は分析用途で使われ、research や ai モジュールで参照されます。prices_daily / raw_financials / raw_news などのテーブルが想定されています。
- AI 関連は API 呼び出し失敗時にフェイルセーフ（スコア 0.0 やスキップ）となる設計です。実行時のログを確認してください。
- process_priority.set_process_priority は起動直後に呼ばれます。必要に応じてコメントアウトしてテストしてください（権限によっては AccessDenied が発生しますが警告でスキップされます）。

---

## ライセンス・貢献

本 README にライセンス情報は含めていません。プロジェクトの LICENSE ファイルや CONTRIBUTING ポリシーがあればそちらに従ってください。

---

以上。さらに詳細な API ドキュメントや開発フローが必要であれば、対象モジュールを指定して欲しい箇所の README を追記します。