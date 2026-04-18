# KabuSys

日本株向けの自動売買システム（プロジェクト骨格）。  
Execution エンジン・監視（Monitoring）・ポートフォリオ構築・リサーチ・AI（ニュース NLP / レジーム判定）などを含むモジュール群を提供します。

## プロジェクト概要
- Python ベースの自動売買システムのコアライブラリ群。
- 本番（live）／ペーパートレード（paper_trading）／開発（development）を環境で切替可能。
- DuckDB（分析用）と SQLite（監視・発注ログ）を組み合わせてデータ管理。
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価・市場レジーム判定機能を備える（任意）。
- 監視コンポーネントにより稼働監視・データ鮮度チェック・リスク監視（ドローダウン、ポジション上限）を行い、条件によって kill flag を書き込んで ExecutionEngine を停止可能。

## 主な機能一覧
- Execution
  - 発注エンジン（ExecutionEngine）／OrderManager／RiskManager／Reconciler（モジュール化）
  - Paper trading（KABUSYS_ENV=paper_trading）では MockBrokerClient を使用し、本番 DB と分離された `data/paper_trading.db` に記録
- Monitoring
  - SystemMonitor（CPU/メモリ/ディスク・データ鮮度・プロセス監視）
  - TradeMonitor（注文滞留・約定異常チェック）
  - RiskMonitor（ドローダウン・ポジション上限）
  - KillSwitch（監視から kill.flag を書き込む）
  - MonitoringEngine（各モニタの巡回とアラート送出）
- Portfolio
  - 候補選定（select_candidates）
  - 重み計算（等金額 / スコア加重）
  - ポジションサイズ計算（単元丸め・上限・集約キャップ）
  - セクター制限・レジーム乗数
- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン・IC 計算・要約統計
- AI（任意）
  - ニュース NLP による銘柄センチメント（ai_scores への書き込み）
  - 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの LLM センチメントを合成）
- ツール
  - 環境設定ウィザード（.env 作成）: config_setup
  - 設定検証 CLI: validate_config
  - Paper Trading 検証レポート生成: tools.paper_verification_report
- ユーティリティ
  - ロギング統一設定（TimedRotatingFileHandler + stdout）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

## セットアップ（ローカル開発向け）
1. リポジトリをクローンして作業ディレクトリをルートにする。
2. Python 環境を用意（推奨: 3.10+）。
3. 依存パッケージをインストール（最低限）:
   - duckdb
   - psutil
   - openai（AI 機能を使う場合）
   - PyYAML（config の検証を行う場合に推奨）
   例:
   ```
   pip install duckdb psutil openai pyyaml
   ```
   ※ sqlite3 は標準ライブラリに含まれます。
4. 初期設定ファイル（.env）を作成:
   - 対話式ウィザードを使う:
     ```
     python -m kabusys.config_setup
     ```
   - 手動で `.env` をルートに作成する場合は `.env.example` を参照してください（プロジェクトに例ファイルがある想定）。
5. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
   - OPENAI_API_KEY（AI 機能を使う場合）
   - 省略時のデフォルト DB パス:
     - DuckDB: data/kabusys.duckdb
     - SQLite(監視): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db

6. 自動 .env 読み込みについて:
   - デフォルトでプロジェクトルート（.git か pyproject.toml を基準）にある `.env` / `.env.local` をロードします。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

## 使い方（実行例）
- 設定検証:
  ```
  python -m kabusys.validate_config
  # 警告も FAIL としたい場合:
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン起動（ExecutionEngine）:
  - 通常（environment に応じて本番 / paper_trading が切替）:
    ```
    python -m kabusys.run_execution
    ```
  - 起動前に `KABUSYS_ENV=paper_trading` を設定すると MockBroker を使用し `data/paper_trading.db` に記録され、本番 DB と分離されます。

- 監視ループ起動（Monitoring）:
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）。
  - 監視は常に本番用の sqlite_path を使用します（環境にかかわらず監視 DB は production path を想定）。

- Paper Trading 検証レポート生成:
  ```
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- .env の作成・更新（ウィザード）:
  ```
  python -m kabusys.config_setup
  ```

### 停止 / Kill スイッチ
- 実行・監視の即時停止（手動）:
  - 実行スレッドを停止させるためにモニタが書き込む `data/kill.flag` を自分で作成しても効果がある設計です（KillSwitch が存在すれば ExecutionEngine に停止指示が入る）。
- 監視 / 実行スクリプト自身を優雅に終了させるためのフラグ:
  - `data/stop_requested.flag` が存在すると `run_monitoring` と `run_execution` のループは終了します。
- PID ファイル:
  - Execution 用 PID ファイル: `data/execution.pid`（デフォルト）。起動時に PID を書き込みます。

## 設定の要点（環境変数）
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 推奨 / 任意
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視用、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
  - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - OPENAI_API_KEY（AI 機能を使う場合）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（本番でアラート通知を行う場合）
  - MONITOR_POLL_INTERVAL（監視ポーリング間隔、秒）
  - KILL_FLAG_CLEAR_ON_START（本番での自動クリアは危険: デフォルト 0 推奨）

## ロギング
- ログはデフォルトで stdout に出力され、ファイルは `logs/<app_name>.log` に日次ローテーションで保存されます（30日分保持）。
- ログ設定は `kabusys.utils.logging_setup.setup_logging(app_name="...")` で統一的に行われます。

## AI 機能について
- ニュース NLP（ai/news_nlp.py）
  - raw_news と news_symbols を集約して OpenAI に送信し、ai_scores テーブルへ書き込む。
  - OpenAI API（gpt-4o-mini）を用いるため `OPENAI_API_KEY` が必要。
  - 失敗時はフェイルセーフでスキップ（例外を上位に広げない設計）。
- レジーム判定（ai/regime_detector.py）
  - ETF 1321 の MA200 とマクロニュースの LLM センチメントを合成。
  - 同様に OpenAI API キーが必要。

## ディレクトリ構成（主要ファイル）
ルート: src/kabusys 以下の主な構成:

- run scripts
  - run_execution.py
  - run_monitoring.py
- 設定 / ユーティリティ
  - config.py
  - config_setup.py
  - validate_config.py
  - utils/
    - logging_setup.py
    - process_priority.py
- Execution（発注周り）
  - execution/（BrokerFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager 等）
- Monitoring（監視）
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
- Portfolio（ポートフォリオ構築）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
- Research（ファクター・探索）
  - research/
    - factor_research.py
    - feature_exploration.py
- AI
  - ai/
    - news_nlp.py
    - regime_detector.py
- Tools
  - tools/
    - paper_verification_report.py
- その他
  - data/（データ・DB・フラグファイル等、実行時に生成）
  - logs/（ログファイル、実行時に生成）

（実際のリポジトリにはさらに細かいファイル・モジュールが含まれます。上は主要な概観です。）

## 運用上の注意
- 本番運用時は `KABUSYS_ENV=live` に設定し、`.env` の中身（APIキー等）を厳重に管理してください。
- `KILL_FLAG_CLEAR_ON_START=1` は本番では危険です（kill.flag を自動クリアしてしまうため）。デフォルト 0 を推奨します。
- Paper trading を使うときは paper 用 DB が本番 DB と分離されていることを必ず確認してください。
- ログディレクトリの権限やディスク容量に注意してください（ログローテートでディスクを圧迫する可能性があります）。
- AI 機能は外部 API を利用するためコスト・レート制限に注意してください。リトライ・バックオフ設計はありますが、使用量は監視してください。

---

その他の詳細は各モジュールのドキュメント文字列（docstring）を参照してください。必要であれば各コンポーネント（ExecutionEngine、MonitoringEngine、AI モジュール等）の使い方や設定例を追記します。どの箇所を詳しく書くか教えてください。