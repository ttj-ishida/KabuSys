# KabuSys — 日本株自動売買システム

簡単なREADME（日本語）。このリポジトリは日本株の自動売買基盤を想定したモジュール群を提供します。
実運用向けの ExecutionEngine / Monitoring / Portfolio construction / Research / AI (ニュースNLP・レジーム判定) 等を含みます。

## プロジェクト概要
KabuSys は以下の責務を持つコンポーネント群で構成された自動売買システムの基礎実装です。

- ExecutionEngine: 注文発行・リスク管理・約定の整合など発注処理を担う。
- Monitoring: システム状態、注文活動、リスク（ドローダウン・ポジション数）を監視し、必要に応じて Kill Switch を発動する。
- Portfolio construction: 候補選定、重み計算、株数決定（position sizing）等の純関数群。
- Research: DuckDB 上の市場データからファクター（モメンタム、バリュー、ボラティリティ等）を計算・分析するユーティリティ。
- AI: ニュース記事を LLM（OpenAI）でスコアリングする news_nlp と、市場レジーム判定（regime_detector）。
- Tools: Paper Trading の検証レポート生成等の補助スクリプト。
- 設定ユーティリティ: .env 生成ウィザード、設定検証 CLI。
- ユーティリティ: ロギング設定、プロセス優先度設定など運用に便利な関数群。

バージョンはパッケージルートで __version__ = "0.1.0" に定義されています。

## 主な機能一覧
- 実行エンジン起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading 用 DB（data/paper_trading.db）で分離実行。
  - プロセス優先度の調整、PID ファイル管理、停止フラグ監視（data/stop_requested.flag）に対応。
- 監視ループ起動スクリプト（run_monitoring.py）
  - システム状態・データ鮮度・注文関連を定期ポーリングして monitoring DB に記録。
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で変更可能（デフォルト 60 秒）。
  - Monitoring は環境に関わらず本番 sqlite_path を使って監視データを記録します。
- MonitoringDB 層（SQLite）: system_status / trade_logs / positions / risk_logs / dashboard テーブル管理と API 提供。
- RiskMonitor / KillSwitch: ドローダウンやポジション上限を検知して kill.flag（data/kill.flag）を作成。
- AI モジュール:
  - news_nlp.score_news: raw_news を集約して OpenAI に送信、銘柄ごとにスコアを ai_scores テーブルへ保存（バッチ処理・リトライ・検証あり）。
  - regime_detector.score_regime: MA200 乖離とマクロニュースセンチメントを合成してレジームを判定し、market_regime テーブルへ保存。
- Portfolio: 候補選定、等重/スコア重み、セクターキャップ適用、position sizing（単元株丸め・利用可能現金に応じた集約上限処理）を提供。
- Research: DuckDB に対するファクター計算（momentum / volatility / value）と特徴量解析（forward returns / IC / summary）。
- Utilities:
  - setup_logging: stdout + 日次ローテートのファイル出力設定（logs/<app>.log）。
  - process_priority: Windows/Linux の違いを吸収して優先度や CPU affinity を設定。

## 要件（推奨）
- Python >= 3.10（型ヒントの `X | Y` 記法を使用）
- 必要な外部パッケージ（抜粋）
  - duckdb
  - psutil
  - openai
  - PyYAML（config の YAML 検証を行う場合）
- SQLite（標準ライブラリの sqlite3 を使用）
- ネットワークアクセス: kabuステーション API、J-Quants、OpenAI（必要に応じて）

インストール例（仮の requirements として）:
```bash
python -m pip install duckdb psutil openai PyYAML
```

（実際の requirements.txt はプロジェクトルートに用意してください）

## セットアップ手順（簡易）
1. リポジトリをクローン / プロジェクトルートへ移動
2. Python 仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```
3. 依存パッケージをインストール（上のコマンド参照）
4. .env を作成
   - 対話式ウィザードを使う:
     ```bash
     python -m kabusys.config_setup
     ```
   - もしくは .env.example を参考に手動作成
5. 設定検証（必須環境変数等をチェック）
   ```bash
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict  # 警告もエラー扱い
   ```
6. データディレクトリ作成（必要に応じて）
   ```bash
   mkdir -p data logs
   ```

## 環境変数（主な項目）
以下は主要な環境変数とデフォルト値／説明（詳細は config.py / config_setup.py を参照）。

必須（少なくとも設定が必要）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）

運用関連 / 任意
- KABUSYS_ENV (default: development)
  - 値: development | paper_trading | live
  - paper_trading: 発注をモックし、専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用
  - live: 本番（注意深く設定）
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db) — Monitoring DB（run_monitoring が使用）
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db) — paper_trading 用 DB
- PAPER_FILL_MODE (default: instant) — MockBrokerClient の約定モード（instant|partial|never|reject）
- LOG_LEVEL (default: INFO)
- LOG_DIR (default: logs/)
- OPENAI_API_KEY — AI 機能を使う場合に必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番アラート（LINE）を使う場合
- PID_FILE_PATH (default: data/execution.pid)
- KILL_FLAG_PATH (default: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (default: 0) — ExecutionEngine 起動時に kill.flag を自動クリアするか（本番は 0 推奨）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒。run_monitoring で参照）。デフォルト 60。

注:
- run_monitoring は「環境にかかわらず」本番 sqlite_path（SQLITE_PATH）を使って監視データを保存します。
- run_execution は KABUSYS_ENV=paper_trading の場合に PAPER_TRADING_SQLITE_PATH を使うので本番 DB と分離できます。

## 使い方（主要コマンド）
プロジェクトルートで Python モジュールとして実行します。

- 環境ウィザード（.env 作成）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン起動（バックテストではなく実行プロセス）
  ```bash
  python -m kabusys.run_execution
  ```
  - 起動時に data/stop_requested.flag があれば起動しない
  - 実行中に data/stop_requested.flag が作成されると Engine.stop() を呼んで終了
  - PID ファイルは data/execution.pid（Settings.pid_file_path）に書き込まれます

- 監視ループ起動
  ```bash
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数で間隔を秒単位で上書きできます（例: MONITOR_POLL_INTERVAL=30）
  - 監視は停止フラグファイル data/stop_requested.flag の存在でループを抜けます

- Paper Trading 検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを指定する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI / Research / Portfolio の関数はライブラリ API として import して利用可能
  - 例: kabusys.research.calc_momentum, kabusys.portfolio.calc_position_sizes, kabusys.ai.score_news など

## 運用上の注意点
- 本番環境 (KABUSYS_ENV=live) では kill.flag や KILL_FLAG_CLEAR_ON_START の扱いに注意してください。KILL_FLAG_CLEAR_ON_START=1 は本番では危険です（自動で Kill Switch をクリアしてしまう）。
- ログはデフォルトで logs/<app>.log に日次ローテーションで保存され、stdout にも出力されます。
- OpenAI など API 呼び出しはレート制限やネットワークエラーに対してリトライ実装がありますが、API キーや料金に注意してください。
- run_monitoring は監視専用 DB（SQLITE_PATH）へ書き込むため、監視データは本番 DB に集約されます。Paper Trading 実行のログは paper_trading DB に記録されるため本番 DB と分離されます。

## ディレクトリ構成（主要ファイル）
src 以下をパッケージルートとして示します（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数 / Settings（.env 自動ロードロジック含む）
  - config_setup.py             — .env 対話ウィザード
  - validate_config.py          — 設定検証 CLI
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading レポート生成
  - execution/                   — 実行（broker, engine, order_manager 等）関連（サブモジュール）
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
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
  - utils/
    - logging_setup.py
    - process_priority.py

（実際のリポジトリには execution/ 以下や data/ 等さらに多くのファイルがあります。ここでは代表的な主要ファイルを列挙しています）

## 開発者向けメモ
- DuckDB 接続を受け取る研究関数群は副作用がなく、テストしやすい純粋関数設計を意識してあります。
- MonitoringDB は CRUD 的なラッパーに留め、ビジネスロジックは MonitoringEngine / RiskMonitor 側に実装されています。
- AI モジュールの OpenAI 呼び出しはテスト時に差し替え可能なように関数分離・ラップされています（単体テストでモックしやすい設計）。

---

問題や追加で README に追記したい情報（要求される CI 設定、詳しい依存関係、実行例のログ抜粋など）があれば教えてください。必要に応じて README を拡張します。