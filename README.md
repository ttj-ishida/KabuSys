# KabuSys

日本株向け自動売買 / 研究プラットフォームのサブセット実装です。  
このリポジトリは、監視（Monitoring）、実行エンジン（Execution）、ポートフォリオ構築、ファクター研究、AI ニュース評価などの主要コンポーネントを含みます。

## プロジェクト概要
- 自動売買エンジン（ExecutionEngine）とそれを監視する監視コンポーネント群を含む。
- DuckDB を用いた研究・解析（prices_daily / raw_financials 等）モジュール。
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価・レジーム判定機能（AI モジュール）。
- Paper Trading（ペーパートレード）モードをサポートし、本番 DB と分離して動作可能。
- ログはコンソールおよび日次ローテートのファイルに出力（logs/）。

## 主な機能一覧
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（本番 / paper_trading 切替）
  - run_monitoring.py: SystemMonitor のポーリングループ起動
- 設定関連
  - config_setup.py: .env 作成ウィザード（対話式）
  - validate_config.py: 環境設定（.env / config/*.yaml）の検証 CLI
- 監視（monitoring）
  - SystemMonitor, TradeMonitor, RiskMonitor, MonitoringEngine
  - kill_switch による停止フラグ（data/kill.flag）生成
  - MonitoringDB: SQLite に監視ログを永続化
- 実行（execution）
  - BrokerClientFactory によるブローカー切替（paper_trading 時は Mock）
  - OrderManager, OrderRepository, RiskManager, ExecutionEngine（起動・停止管理）
- 研究（research）
  - factor_research: モメンタム / バリュー / ボラティリティ等のファクター算出（DuckDB）
  - feature_exploration: 将来リターン、IC、統計サマリ等
- ポートフォリオ構築（portfolio）
  - 銘柄選定、重み付け、ポジションサイジング、セクター集中制限、レジーム乗数
- AI（ai）
  - news_nlp.score_news: ニュースをまとめて LLM で銘柄別センチメントスコア化 → ai_scores に保存
  - regime_detector.score_regime: ma200 とマクロニュース（LLM）を合成して市場レジーム判定

## セットアップ手順（ローカル開発向け）
前提: Python 3.10+ を推奨します。

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # POSIX
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   - 最低限必要な外部パッケージ（例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config の YAML 検証を行う場合）
   - インストール例:
     ```
     pip install duckdb psutil openai PyYAML
     ```
   - 実運用では追加パッケージ（ブローカー SDK 等）が必要になる場合があります。

4. 環境変数 / .env の用意
   - 対話式ウィザードで生成:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは `.env` を手動で作成。最低限の必須環境変数:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
   - オプションの重要な環境変数:
     - KABUSYS_ENV : development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - LOG_LEVEL（デフォルト: INFO）
     - OPENAI_API_KEY（AI 機能を使う場合必須）
   - 自動ロード:
     - プロジェクトルートに `.env` / `.env.local` がある場合、起動時に自動で読み込まれます。
     - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

5. 設定検証（推奨）
   ```
   python -m kabusys.validate_config
   # 警告を FAIL 扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

## 使い方（起動 / 実行例）
- ExecutionEngine（本番 or paper_trading）
  - 本番モード（.env で KABUSYS_ENV=live を設定）
    ```
    python -m kabusys.run_execution
    ```
  - ペーパートレード（.env で KABUSYS_ENV=paper_trading）
    - PaperTrading では MockBrokerClient を使用し、データは `data/paper_trading.db` に記録されます。

- Monitoring（SystemMonitor ポーリング）
  - デフォルトは 60 秒間隔。環境変数で上書き可能:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 停止方法: プロジェクトルートの `data/stop_requested.flag` を作成するとループが停止します（`run_execution` も同様にチェック）。

- .env の作成（ウィザード）
  ```
  python -m kabusys.config_setup
  ```

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # デフォルト DB は data/paper_trading.db。別DB指定:
  python -m kabusys.tools.paper_verification_report --db /path/to/db.sqlite
  ```

- AI 機能例（プログラム内部呼び出し）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - どちらも api_key が渡されない場合は環境変数 OPENAI_API_KEY を参照します。

## 主要環境変数と挙動（抜粋）
- KABUSYS_ENV: development | paper_trading | live
  - paper_trading 時は発注は Mock、DB は PAPER_TRADING_SQLITE_PATH を使用。
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading 時の MockBroker の約定振る舞い（instant | partial | never | reject）
- DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH: 各 DB ファイルパス（デフォルトは data/ 以下）
- LOG_DIR: ログディレクトリの上書き（デフォルト logs/）
- OPENAI_API_KEY: OpenAI を利用する AI 機能で使用

注意:
- validate_config.py は config/*.yaml の存在と YAML パース（PyYAML がインストールされている場合）を検証します。
- KABUSYS_ENV=live の場合、LINE の通知設定や Kill Switch の設定など追加の注意喚起がされます（validate_config の警告）。

## ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings 管理（.env 自動ロード含む）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）による銘柄別スコア付与
    - regime_detector.py — ma200 + LLM によるレジーム判定
  - monitoring/
    - monitoring_db.py — SQLite 監視 DB 永続化層
    - system_monitor.py — システム状態・データ鮮度チェック
    - trade_monitor.py — （トレード監視；コードベースに複数モジュールあり）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書き込みロジック
    - monitoring_engine.py — 各モニタの統合
  - execution/ (発注関連、Engine 実装)
    - execution_engine.py, order_manager.py, order_repository.py, risk_manager.py, reconciler.py など
  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み付け
    - position_sizing.py — 株数決定・資金配分
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — モメンタム / バリュー / ボラティリティ計算（DuckDB ベース）
    - feature_exploration.py — 将来リターン、IC、統計
  - utils/
    - logging_setup.py — ログ初期化ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

（上記は主要ファイルの抜粋です。細かい実装はソースを参照してください）

## 運用・運転上の注意
- 本番（KABUSYS_ENV=live）での起動前に必ず `python -m kabusys.validate_config` を実行して設定を確認してください。
- kill.flag / stop_requested.flag によりプロセスの停止・起動制御が行われます。特に本番で `KILL_FLAG_CLEAR_ON_START=1` を設定すると危険です（validate_config も警告します）。
- ログディレクトリ・データディレクトリ（data/）は適切なパーミッションで管理してください。
- OpenAI API を使う機能（news_nlp, regime_detector）は API コストとレイテンシ・エラーに注意して運用してください。リトライ等の実装はありますが、API キーの漏洩や大量リクエストには注意が必要です。

---

問題や不明点があれば、どの部分について深掘りしたいか教えてください（起動手順の詳細、環境変数テンプレート、特定モジュールの説明など）。