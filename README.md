# KabuSys

日本株自動売買システムのサンプル実装（ライブラリ／起動スクリプト群）。  
この README はリポジトリ内の主要スクリプト・モジュールに基づいて作成しています。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要スクリプト）
- 環境変数一覧（主要）
- ディレクトリ構成（抜粋）
- 開発・運用メモ

---

## プロジェクト概要

KabuSys は日本株向けの自動売買／リサーチ／モニタリング基盤の骨格を提供する Python パッケージです。主なコンポーネントは以下です。

- ExecutionEngine（発注エンジン）: ブローカークライアント経由で発注を行う（本番 / ペーパー切替対応）。
- Monitoring（監視）: システム稼働状況、注文ログ、リスク（ドローダウン／ポジション上限）を監視し、Kill Switch を発火可能。
- Portfolio（ポートフォリオ構築）: 候補選定、重み付け、株数算出（単元丸め・リスク制限など）。
- Research（リサーチ）: DuckDB 上の価格・財務データからファクター算出や特徴量探索を行う。
- AI（オプション）: OpenAI を用いたニュースセンチメントや市場レジーム判定（OpenAI API 必須）。
- Tools: ペーパートレード検証レポートなどの補助スクリプト。

設計方針として、ルックアヘッドの回避（date.today() を直接参照しない等）、フェイルセーフ（API失敗時のフォールバック）、DB の冪等初期化などに配慮されています。

---

## 機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine の起動（KABUSYS_ENV により paper_trading では MockBroker・専用 DB 使用）
  - run_monitoring.py: SystemMonitor のポーリングループ起動（監視ログの記録）
- 設定管理
  - config_setup.py: .env を対話的に生成／更新するウィザード
  - validate_config.py: .env および config/*.yaml の事前検証 CLI
- 監視機能
  - system_monitor: CPU / メモリ / ディスク / データ鮮度 / 実行プロセス監視
  - trade_monitor: 注文の滞留・約定異常等の検出（ソース参照）
  - risk_monitor: ドローダウン・保有上限検出、ダッシュボード更新
  - kill_switch: 条件に応じて data/kill.flag を書き込み Execution を停止
  - monitoring_db: 監視用 SQLite スキーマと永続化操作
- ポートフォリオ構築
  - 候補選定（スコア順）、等金額／スコア加重配分、リスクベースのポジションサイズ算出
  - セクター上限の適用、レジーム乗数
- リサーチ
  - momentum / volatility / value 等のファクター計算（DuckDB を使用）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI（オプション）
  - news_nlp: ニュース記事から銘柄別センチメントを OpenAI に依頼して ai_scores に書き込み
  - regime_detector: ETF とマクロ記事を組み合わせて日次レジームを判定・保存
- ツール
  - paper_verification_report: ペーパートレード結果を集計して PASS/FAIL レポート生成

---

## セットアップ手順

1. Python 環境（推奨: 3.10+）を準備します。

2. 依存パッケージをインストールします（プロジェクトに requirements.txt があればそれを使ってください）。主要依存は以下です:

   pip install duckdb psutil openai PyYAML

   - duckdb: リサーチ・分析用
   - psutil: プロセス／リソース監視
   - openai: AI 機能（任意・有料 API）
   - PyYAML: validate_config の YAML 検証（任意）

3. プロジェクトルートに .env を配置するか、対話式ウィザードを使って生成します:

   python -m kabusys.config_setup

   生成後、設定を検証:

   python -m kabusys.validate_config
   # 警告も FAIL 扱いにしたい場合:
   python -m kabusys.validate_config --strict

4. データディレクトリ（デフォルトは data/）やログディレクトリ（logs/）を作成します（多くは自動作成されますが、権限等を事前確認してください）。

5. （ペーパートレードを使用する場合）PAPER_FILL_MODE などを .env で設定します（後述の環境変数参照）。

---

## 使い方（主要スクリプト）

プロジェクトはパッケージとして提供される前提で、モジュール実行を推奨します。

- ExecutionEngine を起動（本番／ペーパーは KABUSYS_ENV により切替）:

  KABUSYS_ENV=development python -m kabusys.run_execution
  # または
  python -m kabusys.run_execution  # .env の KABUSYS_ENV に従う

  ※ paper_trading モードでは MockBrokerClient が使用され、DB は data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可能）に分離されます。

- Monitoring を起動（SystemMonitor のループ）:

  python -m kabusys.run_monitoring

  環境変数でポーリング間隔を指定可能（デフォルト 60 秒）:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

  停止方法:
  - モニター側は data/stop_requested.flag の存在を検出してループを終了します（stop フラグは手動で作成できます）。
  - ExecutionEngine 側は data/kill.flag を監視して停止します（KillSwitch による自動書き込みもあり）。

- .env の作成／更新:

  python -m kabusys.config_setup

- 設定検証:

  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- ペーパートレード検証レポート:

  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを明示する場合:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI 機能（ニューススコア、レジーム判定）は OpenAI API キーが必要です。モジュールを直接呼ぶことを想定:

  from kabusys.ai.news_nlp import score_news
  from kabusys.ai.regime_detector import score_regime

  # 例: DuckDB 接続を渡してスコアを生成
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  score_news(conn, target_date=date.today(), api_key="sk-...")

---

## 主要な環境変数（抜粋）

- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API パスワード

- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

- データベース / ファイルパス
  - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
  - SQLITE_PATH: data/monitoring.db（監視 DB、デフォルト）
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（ペーパー専用 DB）
  - PID_FILE_PATH: data/execution.pid（ExecutionEngine の PID ファイル）
  - KILL_FLAG_PATH: data/kill.flag（Kill Switch ファイル）

- モニタリング関連
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
  - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: しきい値

- ペーパートレード
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）

- OpenAI
  - OPENAI_API_KEY: AI 機能を使う場合に必要

- その他
  - KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（"1" でクリア。production では通常 0）

注: .env 自動ロード機能が有効であれば、プロジェクトルートの .env と .env.local が起動時に読み込まれます。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                — 環境変数/設定管理（.env 自動ロード含む）
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py            — ニュースからセンチメントを算出して ai_scores に書き込む
  - regime_detector.py     — 市場レジーム判定
- monitoring/
  - monitoring_db.py       — SQLite スキーマと永続化 API
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py       —（実装参照）
- execution/
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - broker_factory.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- data/ (想定されるランタイムディレクトリ)
  - monitoring.db
  - paper_trading.db
  - kabusys.duckdb
  - kill.flag / stop_requested.flag / execution.pid
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py       — ログ設定ユーティリティ（stdout + 日次ローテーション）
  - process_priority.py    — プロセス優先度 / CPU affinity 設定（psutil）

（上記はソースの主要ファイルを抜粋した一覧です）

---

## 開発・運用メモ

- DB 初期化: monitoring_db.init_monitoring_db は冪等的にテーブルを作成し、必要に応じて簡単なマイグレーションを行います。起動スクリプト（monitoring / execution）内で呼び出されています。
- ロギング: kabusys.utils.logging_setup.setup_logging を起動時に呼んで統一的なログ出力（コンソール stdout + logs/<app>.log 日次ローテーション）を使用してください。
- 優先度設定: 起動スクリプトは set_process_priority("high") を最初に実行します。psutil による権限不足等で失敗した場合は警告になりますが処理は継続します。
- 停止制御:
  - run_monitoring / run_execution ともに data/stop_requested.flag を見て安全シャットダウンします。
  - KillSwitch は条件を満たすと data/kill.flag を書き込み、ExecutionEngine がこれを検出して停止します。
- 本番注意:
  - KABUSYS_ENV=live の場合、LINE 通知設定や kill フラグの取り扱いなどを十分に確認してください。
  - KILL_FLAG_CLEAR_ON_START=1 を本番で使うと危険です（自動的に Kill Switch をクリアしてしまうため）。
- AI 機能:
  - OpenAI API コールはコストとレイテンシを伴います。API キーの管理やリトライポリシー（実装済み）を理解した上で有効化してください。
  - news_nlp と regime_detector は応答の検証やフォールバック処理を備え、失敗時はフェイルセーフ（0 にフォールバック）します。
- テスト:
  - モジュール単位（system_monitor.check_once / MonitoringEngine.run_once など）はユニットテストしやすい設計になっています。外部依存（OpenAI, psutil, DuckDB）をモックしてテストしてください。

---

もし README に追記してほしい内容（例: 実際の設定例、systemd / supervisor 用のサービス unit、Dockerfile、CI 流れ、より詳細な API 使用例など）があれば教えてください。必要に応じて追加で例やテンプレートを用意します。