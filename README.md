# KabuSys

日本株自動売買システムのコードベース（ライブラリ＋起動スクリプト）の README。  
この README はリポジトリ内のスクリプト・モジュール群から自動でまとめたドキュメントです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムです。主な機能としては：

- 発注実行エンジン（ExecutionEngine） — 実際のブローカ API と連携して注文を管理。
- 監視（Monitoring） — システム稼働状況、注文状態、リスク（ドローダウン・ポジション上限）を定期チェックし、必要時に Kill Switch を作動。
- ペーパートレード分離 — `KABUSYS_ENV=paper_trading` 時はモックブローカーを使い、専用 DB に記録して本番口座と完全分離。
- 研究/リサーチモジュール — DuckDB を用いたファクター計算、将来リターン・IC 計算、特徴量要約など。
- AI モジュール — OpenAI を用いたニュースセンチメント（ai_scores）と市場レジーム判定。
- ユーティリティ群 — ロギング設定、プロセス優先度設定、.env ウィザード、設定検証ツールなど。

設計上のポイント：
- 環境ファイル（`.env`）を読み込み、環境変数ベースで設定を管理。
- Paper trading は物理的に DB を分けて安全に検証可能。
- DuckDB を分析用に利用、SQLite を監視・履歴記録に利用。
- ログは stdout と日次ローテーションファイルに出力。

---

## 機能一覧（主なモジュール）

- 起動スクリプト
  - run_execution.py — ExecutionEngine を起動（`python -m kabusys.run_execution`）
  - run_monitoring.py — SystemMonitor ポーリング（`python -m kabusys.run_monitoring`）

- 設定関連
  - config.py — Settings クラス（環境変数と自動 `.env` 読み込みロジック）
  - config_setup.py — 対話式 `.env` 作成ウィザード（`python -m kabusys.config_setup`）
  - validate_config.py — 設定検証ツール（`python -m kabusys.validate_config`）

- 監視
  - monitoring/monitoring_db.py — SQLite に対する永続化 API
  - monitoring/system_monitor.py — CPU/メモリ/ディスク・データ鮮度・プロセス存在監視
  - monitoring/trade_monitor.py — （注文に関する監視）
  - monitoring/risk_monitor.py — ドローダウン・ポジション上限の監視
  - monitoring/kill_switch.py — `data/kill.flag` による ExecutionEngine 停止トリガ
  - monitoring/monitoring_engine.py — 各 Monitor を束ねる

- 発注関連（execution/*） — BrokerClientFactory、ExecutionEngine、OrderManager、RiskManager、Reconciler 等

- ポートフォリオ構築（portfolio/*）
  - 銘柄選定、重み計算、リスク調整、株数決定（ロジックは純粋関数でテスト容易）

- 研究（research/*）
  - factor_research: Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - feature_exploration: 将来リターン / IC / 統計サマリ

- AI（ai/*）
  - news_nlp.py: OpenAI を用いたニュースセンチメントスコアリング（ai_scores テーブルへ書込）
  - regime_detector.py: MA200 とマクロニュースを組み合わせた市場レジーム判定

- ツール
  - tools/paper_verification_report.py — ペーパートレード検証レポート生成（期間指定可）

- ユーティリティ（utils/*）
  - logging_setup.py — 統一ロギング設定（stdout + 日次ファイル）
  - process_priority.py — プロセス優先度 / CPU affinity 設定

---

## セットアップ手順

1. リポジトリをクローンして Python 環境を用意します（仮想環境推奨）。

2. 必要な Python パッケージをインストールします（例）:
   - duckdb
   - psutil
   - openai
   - PyYAML（設定検証で YAML 検査を行う場合に必要）
   例:
   ```
   pip install duckdb psutil openai PyYAML
   ```

3. .env の準備（推奨: 対話式ウィザード）:
   ```
   python -m kabusys.config_setup
   ```
   ウィザードで入力した内容はプロジェクトルートの `.env` に保存されます。
   ※ 自動ロードが不要な場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してから import してください。

4. 設定検証:
   ```
   python -m kabusys.validate_config
   # 厳密モード（警告も失敗にする）
   python -m kabusys.validate_config --strict
   ```

5. DB 初期化
   - 起動スクリプトが必要に応じて DB テーブルを作成するため、手動での初期化は通常不要です。
   - DuckDB / SQLite のデフォルトパス:
     - DuckDB: data/kabusys.duckdb （環境変数 `DUCKDB_PATH` で変更可）
     - SQLite (monitoring): data/monitoring.db （`SQLITE_PATH` で変更可）
     - Paper trading の SQLite: data/paper_trading.db （`PAPER_TRADING_SQLITE_PATH` で変更可）

6. ログディレクトリ
   - デフォルトは `logs/`。環境変数 `LOG_DIR` で変更可。

---

## 使い方（起動・ツール）

基本的にはモジュールを直接実行します。プロジェクトルートで実行してください。

- 実行エンジン起動（本番または paper_trading によって振る舞いが変わる）:
  ```
  python -m kabusys.run_execution
  ```
  特記事項:
  - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient が使用されデータは `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）に記録され、本番 DB と完全分離されます。
  - エンジンは `data/execution.pid` を PID ファイルとして使用します。
  - 停止シグナルは `data/stop_requested.flag`（手動で作成）または `data/kill.flag`（Kill Switch により作成）で処理されます。

- 監視ループ起動:
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能。デフォルトは 60 秒。
  - 監視は常に本番の `SQLITE_PATH` を使用して監視データを記録します（環境にかかわらず）。

- 設定ウィザード:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  ```

- ペーパートレード検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを指定する場合
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 機能（ライブラリ呼び出し例）:
  - OpenAI API キーが必要（環境変数 `OPENAI_API_KEY` または引数で渡す）。
  - 例（Python REPL）:
    ```python
    import duckdb
    from datetime import date
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    n = score_news(conn, target_date=date(2026,4,10), api_key="sk-...")
    ```

---

## 主要な環境変数

必須（実稼働前に設定が必要）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

任意 / 設定例
- KABUSYS_ENV — 実行環境: "development" | "paper_trading" | "live"（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視）ファイルパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — paper_trading のフォールバック約定モード: "instant" | "partial" | "never" | "reject"（デフォルト: instant）
- LOG_LEVEL — ログレベル ("DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL")
- LOG_DIR — ログディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY — OpenAI を使う機能で必要
- MONITOR_POLL_INTERVAL — monitoring ポーリング間隔（秒、デフォルト 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動で `.env` を読み込まない（1を設定すると無効化）

その他、validate_config.py と config_setup.py で列挙されている設定はウィザード / 検証参照。

---

## 停止・Kill Switch

- 手動停止（run_execution / run_monitoring のループ停止）:
  - `data/stop_requested.flag` ファイルを作成すると、ループは検知して安全に終了します。
- Kill Switch（自動停止）:
  - 監視側で `RiskMonitor` が門限を超えた場合、`KillSwitch` が `data/kill.flag` を書き込みます。
  - ExecutionEngine 起動時に `KILL_FLAG_CLEAR_ON_START=1` が設定されていれば自動でクリアされますが、本番では `0` を推奨します。

---

## ディレクトリ構成（主なファイル）

プロジェクトの主要ファイル／ディレクトリは以下の通りです（src/kabusys/ 以下）:

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (アラート送信ロジック等)
  - execution/
    - execution_engine.py
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
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/ (上記)
  - tools/
    - paper_verification_report.py

（実際のリポジトリにはさらに細分化されたファイルが含まれます。上は主要コンポーネントの一覧です。）

---

## 追加情報 / 注意点

- .env の自動読み込み: config.py はプロジェクトルート（.git か pyproject.toml のあるディレクトリ）を探索して `.env` と `.env.local` を自動読み込みします。テストなどで自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- ロギング: `kabusys.utils.logging_setup.setup_logging(app_name=...)` を各起動スクリプトで呼んでおり、`logs/<app_name>.log` に日次ローテーションでログが出力されます。
- Paper trading: `KABUSYS_ENV=paper_trading` の際には本番 API ではなく Mock ブローカーが使われ、DB も `PAPER_TRADING_SQLITE_PATH` に分離されます。これにより本番口座に影響を与えず検証可能です。
- OpenAI 利用: `ai` モジュールは OpenAI API を利用します。API キー (`OPENAI_API_KEY`) は必ず設定してください。API エラー時はフェイルセーフで進行する設計になっていますが、機能が限定されます。
- テストと可搬性: 多くのユーティリティはプラットフォーム差分（Windows / POSIX）を吸収する実装になっています（例: process_priority.py）。ただしアクセス権限により優先度設定は失敗する可能性があり、その場合は警告でスキップされます。

---

必要であれば、この README を README.md としてリポジトリルートに保存するための提案テンプレート（英語版や導入手順の詳細化、docker-compose 例など）を作成します。どの部分を詳しく補足しましょうか？