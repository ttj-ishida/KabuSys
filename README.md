# KabuSys

日本株向け自動売買システムのコアライブラリ群（モニタリング / 実行エンジン / ポートフォリオ構築 / リサーチ / AI 支援モジュール等）。

このリポジトリはライブラリと CLI スクリプト群を含み、ローカル開発・ペーパートレード・本番の各実行モードを想定しています。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（主要コマンド）
- 環境変数（主要項目）
- 動作上の注意点
- ディレクトリ構成（主要ファイル）

---

プロジェクト概要
- KabuSys は日本株の自動売買アルゴリズムを支援するためのモジュール群です。
- データ収集・DuckDB を用いたファクター計算、ポートフォリオ構築、発注エンジン（ExecutionEngine）、システム監視（Monitoring）、AI を用いたニュースセンチメントやレジーム判定機能を含みます。
- 本リポジトリは発注部分と監視・報告機能の両方を持ち、ペーパートレードモードでは実際のブローカーを模した Mock クライアントで完全分離された DB に記録します。

主な機能一覧
- 実行エンジン起動スクリプト（run_execution）
  - 実際のブローカーまたは MockBroker を環境に応じて切替
  - 発注・オーダー管理、リスクチェック、Reconciler による状態整合
  - PID / stop フラグで制御
- 監視ループ（run_monitoring）
  - プロセス・リソース（CPU/メモリ/ディスク）やデータ鮮度、発注滞留や約定異常を定期チェック
  - SQLite に監視ログを永続化
  - MONITOR_POLL_INTERVAL でポーリング間隔を制御（デフォルト 60 秒）
- 設定ウィザード（config_setup）および設定検証 CLI（validate_config）
  - .env の対話的作成・更新
  - 起動前の設定検証（必須環境変数、ファイルパス、YAML 構成ファイルの存在など）
- Paper Trading 検証レポート（tools/paper_verification_report）
  - ペーパートレード用 SQLite から稼働率・注文成功率・レイテンシ等を集計してレポート出力
- ポートフォリオ構築（portfolio）
  - 候補選定、スコア重み付け、等分配、リスク調整（セクター上限、レジーム乗数）
  - ポジション・ロット丸め / 投資総額スケーリング
- リサーチ（research）
  - DuckDB 上でのファクター計算（Momentum / Value / Volatility 等）
  - 将来リターン計算、IC（Information Coefficient）計算、ファクター統計
- AI モジュール（ai）
  - ニュースセンチメント（news_nlp）: OpenAI を用いてニュースを銘柄ごとに評価して ai_scores に書き込み
  - 市場レジーム判定（regime_detector）: ETF の MA200 乖離とマクロニュースセンチメントを合成して日次レジームを判定
- ユーティリティ
  - プロセス優先度 / CPU affinity 設定ユーティリティ（psutil 利用）
  - MonitoringDB: SQLite スキーマ初期化と読み書き

セットアップ手順（開発 / ローカル実行向け）
1. Python 3.9+（推奨）を用意
2. 仮想環境を作成して有効化
   - unix/mac:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```
3. 必要パッケージをインストール
   - 推奨依存パッケージ（requirements.txt の例）:
     - duckdb
     - psutil
     - openai
     - requests
     - PyYAML (任意: config YAML の検証時に使用)
   - インストール例:
     ```
     pip install duckdb psutil openai requests PyYAML
     ```
   - テストや開発に合わせて追加パッケージが必要になる場合があります。
4. 初期 .env を作成
   - 対話式ウィザードを利用:
     ```
     python -m kabusys.config_setup
     ```
   - あるいは .env ファイルを手動で作成（下の「環境変数」を参照）。
5. 設定検証（起動前チェック）
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict   # 警告も失敗扱い
   ```
6. データディレクトリ（デフォルト: data/）を作る:
   ```
   mkdir -p data
   ```
   実行スクリプトが PID ファイルや flag ファイルを作成します。

使い方（主要コマンド）
- 実行エンジン起動
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV によって挙動が変わります:
    - paper_trading: MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録して本番 DB と分離
    - live / development: settings.sqlite_path（デフォルト data/monitoring.db）を使用
  - 実行中は data/execution.pid が作成され、data/stop_requested.flag の存在で停止します。

- 監視ループ起動
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で指定（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する点に注意（監視ログは常に同一 DB に記録される設計）。

- 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB を指定する場合:
    ```
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
    ```

主要な環境変数（簡易）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用トークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — アラート用 LINE 設定（任意）
- OPENAI_API_KEY — OpenAI を使う AI モジュールの API キー
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒, デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（"1" でクリア、デフォルト "0"）

停止制御とフラグファイル
- data/stop_requested.flag
  - run_execution / run_monitoring はこのファイルの存在を検知してループを終了または停止します（外部から安全に停止要求を出す際に利用）。
- data/execution.pid
  - 実行エンジンの PID を保存します。SystemMonitor は PID ファイルの存在やプロセスの存否をチェックして stale PID を検出します。
- data/kill.flag
  - KillSwitch（監視の一部）が深刻な事象（例: ドローダウン閾値超過）を検出したときにこのファイルを書き込み、ExecutionEngine に停止を促します。
  - KillSwitch の振る舞いは Settings.kill_flag_clear_on_start によって起動時に自動クリア可能ですが、本番では 0 を推奨します。

動作上の注意点
- Monitoring は KABUSYS_ENV に依存せず常に本番用 sqlite_path を参照します（監視ログは分離されません）。
- run_execution は paper_trading モードの際、paper_trading 用 DB を使い実際の発注を行わない設計です（本番 DB とは完全に分離されます）。
- process priority / CPU affinity の設定には psutil が必要で、環境によっては権限不足で設定に失敗することがあります（失敗時はログに WARN を出しスキップします）。
- AI モジュール（news_nlp / regime_detector）は OpenAI API（OPENAI_API_KEY）に依存します。API 呼び出し失敗時はフェイルセーフで継続する実装が多いですが、正確性は API の応答に依存します。
- DB スキーマのマイグレーション（monitoring_db.init_monitoring_db）は起動時に自動で行われます。既存 DB に新カラムがない場合は ALTER TABLE で追加します。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理、自動 .env 読込ロジック
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動ラッパ
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - utils/
    - __init__.py
    - process_priority.py     — psutil を使った優先度 / affinity ユーティリティ
  - execution/                — (発注関連実装群: Engine / OrderManager / BrokerFactory 等)
    - ...
  - monitoring/
    - monitoring_db.py        — SQLite スキーマ定義 & MonitoringDB ラッパ
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py             — ニュースを OpenAI でスコアリング
    - regime_detector.py      — 市場レジーム判定
    - __init__.py
  - tools/
    - paper_verification_report.py
    - __init__.py
  - data/                     — 実行時に使用する DB / PID / flag ファイルを置く想定（デフォルトパス）

（実際の実装ファイルは上記に加えて execution/* や data pipeline / order repository 等、多数の内部モジュールを含みます）

開発者向けメモ
- DuckDB を利用する関数は DuckDB 接続を受け取り SQL でデータを取得する設計です。prices_daily / raw_financials / raw_news 等のテーブルを前提としています。
- AI モジュールは外部 API 呼び出しを行う箇所があり、テスト時は API 呼び出し関数をモックする想定です（コード内にモック可能なラッパー関数が用意されています）。
- ロギングは標準 logging を使用。起動時に log レベルは Settings.log_level または環境変数 LOG_LEVEL で調整できます。

トラブルシューティング
- DB ファイルが見つからない/アクセス権がない:
  - .env の DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を確認
  - ディレクトリが存在しない場合は自動作成されないことがあるため手動で作成
- OpenAI 呼び出し失敗:
  - OPENAI_API_KEY を設定。レート制限やネットワーク問題はリトライ実装がありますが、キー未設定では動作しません。
- psutil による優先度設定で AccessDenied が出る:
  - 権限不足。無視しても処理は続行しますが優先度設定はされません。

ライセンス / バージョン
- パッケージバージョンは src/kabusys/__init__.py に定義されています（現状 0.1.0）。

---

この README はコードベース（src/kabusys/*）の主要機能と使い方の要点をまとめたものです。より詳しい実装仕様（ポートフォリオ構築ルール、StrategyModel/PortfolioConstruction のドキュメント参照箇所）はリポジトリ内の設計ドキュメント（例: PortfolioConstruction.md, StrategyModel.md 等）があれば併せて参照してください。必要であれば README にサンプル .env の雛形や requirements.txt の完全な例も追記します。