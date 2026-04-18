# KabuSys

日本株自動売買システム (KabuSys) — 株価データ処理、ファクター計算、ポートフォリオ組成、実行エンジン、監視・アラート、AI を用いたニュース NLP などを含むモジュール群。

バージョン: 0.1.0

---

概要、機能、セットアップ、使い方、ディレクトリ構成を以下にまとめます。

※ 本 README はソースコード（src/kabusys 以下）から抽出した情報に基づくドキュメントです。

## プロジェクト概要
- モジュール構成により、データ処理（DuckDB）、リサーチ（ファクター・探索）、ポートフォリオ構築、発注（ExecutionEngine）、監視（Monitoring）、AI（ニュースセンチメント／レジーム判定）を分離して実装しています。
- 実行環境は `KABUSYS_ENV` で切り替え可能（development / paper_trading / live）。Paper Trading 時は発注をモック化して専用の SQLite DB に記録します。
- ログはコンソールと日次ローテートファイル（logs/*.log）に出力されます。
- 簡易な CLI ツール群（設定ウィザード、設定検証、ペーパートレード検証レポート等）を提供します。

## 主な機能一覧
- 設定管理
  - .env の自動読み込み（プロジェクトルートを自動検出）
  - 設定ウィザード（`kabusys.config_setup`）
  - 設定検証ツール（`kabusys.validate_config`）
- 実行（Execution）
  - ExecutionEngine（実取引またはモックによる Paper Trading）
  - ブローカークライアント抽象化（BrokerClientFactory）
  - リスク管理・注文管理・照合処理
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - 監視ログの永続化（SQLite: monitoring.db）
  - Kill Switch（条件成立時に kill.flag を書き込み、ExecutionEngine を停止）
- リサーチ / ポートフォリオ
  - ファクター計算（モメンタム / ボラティリティ / バリュー 等）
  - 特徴量探索、IC 計算、統計サマリ
  - 銘柄選定・重み計算・ポジションサイジング・セクター制限
- AI（OpenAI）
  - ニュース記事のセンチメントスコアリング（news_nlp）
  - マクロ記事とETFのMA乖離を用いたレジーム判定（regime_detector）
  - OpenAI API 呼び出しは冪等性・リトライ・バリデーションに配慮
- ツール
  - Paper Trading の検証レポート生成スクリプト（`kabusys.tools.paper_verification_report`）

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローンし、仮想環境を作成・有効化します（例: venv, poetry 等）。
2. 必要なパッケージをインストールします（プロジェクトには以下のような依存が見られます）:
   - duckdb
   - psutil
   - openai
   - PyYAML（設定ファイル検証を行う場合）
   - （その他、実装に応じた依存）
   例:
   ```
   pip install duckdb psutil openai PyYAML
   ```
3. .env の作成
   - 対話式ウィザードで初期 .env を生成できます:
     ```
     python -m kabusys.config_setup
     ```
   - もしくはプロジェクトルートに `.env` を作成して必要な環境変数を設定してください。
   - 自動ロードはデフォルトで有効（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化）。
4. 設定検証（推奨）
   ```
   python -m kabusys.validate_config
   ```
   - `--strict` を付けると警告も fail 扱いになります。
5. データディレクトリ（デフォルト）
   - DuckDB: `data/kabusys.duckdb`
   - SQLite 監視 DB: `data/monitoring.db`
   - Paper Trading（env=paper_trading の場合）: `data/paper_trading.db`
   - ログディレクトリ: `logs/`（デフォルト）
   - これらは `.env` の `DUCKDB_PATH` / `SQLITE_PATH` / `PAPER_TRADING_SQLITE_PATH` / `LOG_DIR` で上書き可能です。

## 主要な環境変数（抜粋）
- 必須（少なくとも設定ウィザードで設定する想定）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行制御・パス
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - DUCKDB_PATH: デフォルト `data/kabusys.duckdb`
  - SQLITE_PATH: 監視 DB デフォルト `data/monitoring.db`
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB（デフォルト `data/paper_trading.db`）
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）
  - OPENAI_API_KEY: OpenAI を使う処理で必要
- モニタリング固有
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- Paper Trading 固有
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト "instant"）
- Kill Switch
  - KILL_FLAG_PATH: デフォルト `data/kill.flag`
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"1" でクリア）

## 使い方（起動 / CLI）
- 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```
- 設定検証
  ```
  python -m kabusys.validate_config
  # --strict を付けると警告もエラー扱い
  python -m kabusys.validate_config --strict
  ```
- 実行エンジン起動（Execution）
  ```
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使い、`data/paper_trading.db` を使用して本番 DB と分離します。
  - 起動時に `data/stop_requested.flag` が存在すると起動を中止します（安全停止）。
  - 実行中は `data/execution.pid` を作成します。停止は stop フラグや Kill Switch により行われます。
- 監視（Monitoring）起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可（秒、デフォルト 60）。
  - 監視は常に本番用の sqlite_path を使用します（環境にかかわらず監視 DB は本番パスを使用する設計）。
  - 監視ループを止めるにはプロジェクトルート配下の `data/stop_requested.flag` を作成してください（run_monitoring はこのファイルを監視してループ終了します）。
- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - `--db` で DB パスを指定するか、環境変数 `PAPER_TRADING_SQLITE_PATH` を利用可能。
- AI / レジーム判定・ニューススコア
  - OpenAI API キーは `OPENAI_API_KEY` を設定するか、関数引数で渡します。
  - news_nlp と regime_detector は API 呼び出しのリトライやパースの堅牢性を備えています。

## 停止・Kill 操作
- Graceful stop:
  - `data/stop_requested.flag` を作成すると、`run_execution` / `run_monitoring` のループは検知して終了します（run_execution はこのファイルを見て実行中のエンジンを停止します）。
- Kill Switch:
  - 監視ロジック（RiskMonitor 等）から条件が満たされると `data/kill.flag` が書き込まれます。ExecutionEngine は `KILL_FLAG_PATH` を参照して適切に停止するロジックを持ちます（設定により起動時に自動クリアするか制御可能）。

## ログ
- ログは標準出力（stdout）と日次ローテーションファイルに出力されます。
- デフォルトログディレクトリ: `logs/`
- 例: `logs/execution.log`, `logs/monitoring.log`
- ログレベルは `LOG_LEVEL` で指定（デフォルト INFO）。

## データベース
- DuckDB（分析向け）: `data/kabusys.duckdb`（デフォルト）  
  - リサーチ / ファクター計算 / AI の集計は DuckDB を利用します。
- SQLite（監視・発注ログ）: `data/monitoring.db`（監視用）  
- Paper Trading は専用 SQLite（`data/paper_trading.db`）に記録し、本番 DB と分離します。

## 主要コマンドまとめ
- 設定ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行エンジン起動: python -m kabusys.run_execution
- 監視起動: python -m kabusys.run_monitoring
- Paper Trading レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

## ディレクトリ構成（主要ファイル）
（src/kabusys 以下の主要モジュールを抜粋）

- kabusys/
  - __init__.py
  - config.py                         # 環境変数・.env 自動ロード
  - config_setup.py                   # .env 対話式ウィザード
  - validate_config.py                # 設定検証 CLI
  - run_execution.py                  # ExecutionEngine 起動スクリプト
  - run_monitoring.py                 # SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py    # Paper Trading 検証レポート
  - ai/
    - __init__.py
    - news_nlp.py                     # ニュース NLP スコアリング
    - regime_detector.py              # 市場レジーム判定
  - monitoring/
    - monitoring_db.py                # SQLite 永続化層（監視ログ）
    - system_monitor.py
    - trade_monitor.py (実装省略ファイルあり)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (別ファイルがある想定)
  - execution/
    - execution_engine.py (主要な実行ロジック)
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/ (ランタイムに生成される / デフォルト)
    - monitoring.db
    - paper_trading.db
    - kabusys.duckdb
    - kill.flag
    - stop_requested.flag
    - execution.pid
  - logs/ (ランタイムに生成)

（上記は実装ファイルの抜粋・要約です。詳細はソースツリーを参照してください）

## 注意事項・運用メモ
- 本番環境（KABUSYS_ENV=live）では設定ミスが重大な結果を招く可能性があるため、`validate_config` や環境変数の確認を必ず行ってください。`--strict` モードで警告も厳格に扱うことを推奨します。
- .env は絶対にリポジトリへコミットしないでください（config_setup の出力ヘッダにも注記あり）。
- OpenAI 等外部 API を使う処理は API キー・利用制限に注意してください（レート制限・コスト）。
- Monitoring は `monitoring.db` を利用してプロセス状態を永続化します。監視は本番 DB パスを使用する設計なので、テスト時は環境変数で DB パスを切り替えるか、Paper Trading モードで分離された DB を使用してください。
- プロセス優先度や CPU affinity の設定はプラットフォーム依存で失敗することがあります（警告を出してスキップします）。

---

この README はソースコードから自動的に要点を抜粋してまとめたものです。詳細な挙動・API 仕様・各モジュールの内部アルゴリズムについては該当ソース（src/kabusys/...）を参照してください。必要であれば、各モジュールごとのより詳細なドキュメント（使用例・設計文書）も作成できます。