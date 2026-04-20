KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株の自動売買・研究・モニタリング用ライブラリ群と起動スクリプトを含む小規模なシステムです。  
README はソースコード（src/kabusys/*.py）を参照して作成しています。起動方法・設定・主要コンポーネントの概要をまとめています。

主な特徴
--------
- 注文実行エンジン（ExecutionEngine）: ブローカークライアントを介して発注を管理（本番 / ペーパートレード切替対応）。
- 監視サブシステム（MonitoringEngine）: システム状態・注文ログ・リスク（ドローダウン、ポジション上限）を定期チェックしアラート/Kill Switch を評価。
- ポートフォリオ構築ユーティリティ: 候補選定、重み計算、ポジションサイズ算出、セクター制約などの純粋関数群。
- 研究用モジュール: DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー）、特徴量解析（IC 等）。
- AI モジュール: OpenAI（gpt-4o-mini）を使ったニュース NLP によるセンチメントスコアリング、レジーム判定の統合ロジック。
- 運用ツール: .env 作成ウィザード、設定検証 CLI、Paper Trading 検証レポート生成スクリプト。
- ロギング / 日次ローテート、プロセス優先度設定、DB マイグレーション（監視 DB の初期化）を組み込み。

必要な環境変数（主要）
--------------------
必須:
- JQUANTS_REFRESH_TOKEN — J‑Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

任意（デフォルトあり）:
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
- PAPER_FILL_MODE — ペーパートレードの約定挙動（instant|partial|never|reject、デフォルト: instant）
- LOG_DIR — ログ保存ディレクトリ（デフォルト: logs/）

自動 .env ロード:
- プロジェクトルート（.git または pyproject.toml がある場所）から .env および .env.local を自動読み込みします。OS 環境変数を優先します。
- 自動ロード無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

重要ファイル / フラグ
--------------------
- data/execution.pid — ExecutionEngine 用 PID ファイル（run_execution が使用）
- data/stop_requested.flag — run_monitoring / run_execution が監視する停止フラグ（存在するとループを終了）
- data/kill.flag — KillSwitch が書き込む停止指示（ExecutionEngine 側で kill flag を監視している想定）
- logs/<app>.log — 日次ローテーションされるログファイル（app=execution, monitoring など）

セットアップ手順
---------------
1. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリをインストール
   - 必要な主要パッケージ（例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config yaml の検証を行う場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   ※ リポジトリに requirements.txt がない場合はプロジェクトに合わせて必要パッケージを追加してください。

3. .env の初期作成（対話ウィザード）
   - python -m kabusys.config_setup
   - ウィザードに従って必要な環境変数を入力してください（.env を生成します）。
   - 生成後、python -m kabusys.validate_config で検証できます。

使い方（主要コマンド）
-------------------

1. 設定ウィザード（.env 作成）
   - python -m kabusys.config_setup
   - 既存 .env を読み込んで更新できます。

2. 設定検証
   - python -m kabusys.validate_config
   - --strict を付与すると警告も失敗扱い（exit(1)）になります。

3. 実行エンジン起動（ExecutionEngine）
   - python -m kabusys.run_execution
   - 挙動:
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し、paper_sqlite_path（デフォルト data/paper_trading.db）へ記録して本番 DB と分離します。
     - 起動時にプロセス優先度を "high" に設定し、PID ファイルを書きます。
     - data/stop_requested.flag が存在すると起動を行わない / 実行中は停止します。

4. 監視ループ起動（Monitoring）
   - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
   - 監視は Settings.sqlite_path（本番 sqlite path）を使用して永続化します（環境にかかわらず同一 DB を利用する設計）。

5. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - --db で SQLite ファイルを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH が優先）。

6. AI / 研究機能（プログラム的に呼び出し）
   - AI ニューススコアリング:
     - from kabusys.ai.news_nlp import score_news
     - score_news(duckdb_conn, target_date, api_key="...")
     - OPENAI_API_KEY が環境変数に設定されていれば api_key は省略可能。
   - レジーム判定:
     - from kabusys.ai.regime_detector import score_regime
     - score_regime(duckdb_conn, target_date, api_key="...")
   - ファクター計算（例）:
     - from kabusys.research import calc_momentum
     - calc_momentum(duckdb_conn, date(2026, 4, 1))

停止・Kill 操作
----------------
- 即時停止（監視/実行ループを優しく止める）:
  - data/stop_requested.flag を作成（touch data/stop_requested.flag）すると run_monitoring/run_execution のループは検知して終了します。
- Kill Switch（リスク検出による停止）:
  - KillSwitch が条件を満たすと data/kill.flag を書き込みます。ExecutionEngine はこのフラグを参照して安全に停止する設計です。
- kill.flag を手動でクリア:
  - rm data/kill.flag
  - 注意: 本番環境では KILL_FLAG_CLEAR_ON_START を 0 にしておくことを推奨します（誤って自動クリアされないよう）。

ログ
----
- 共通ロガー設定は kabusys.utils.logging_setup.setup_logging により行われます。
- デフォルト: stdout（コンソール）出力 + logs/<app>.log（日次ローテーション、30日保持）
- ログレベルは LOG_LEVEL または引数で設定可能。

データベース（デフォルトパス）
---------------------------
- DuckDB: data/kabusys.duckdb
- 監視 SQLite: data/monitoring.db
- ペーパートレード SQLite: data/paper_trading.db

初期化・マイグレーション
----------------------
- run_monitoring / run_execution 起動時に監視用テーブルの存在確認とマイグレーション（init_monitoring_db）を行います。監視 DB に必要なテーブル／カラムを冪等に作成します。

ディレクトリ構成（主要ファイル）
------------------------------
- src/kabusys/
  - __init__.py
  - config.py              — 環境変数 / Settings 管理（.env 自動ロード含む）
  - config_setup.py        — .env 対話ウィザード
  - validate_config.py     — 起動前の設定検証 CLI
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - run_monitoring.py      — Monitoring ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレードの検証レポート生成
  - execution/              — 発注周りの実装（Broker クライアント、ExecutionEngine 等）
  - monitoring/
    - monitoring_db.py      — 監視用 SQLite の永続化層
    - system_monitor.py     — CPU / メモリ / データ鮮度監視
    - trade_monitor.py      — 注文ログの監視（滞留注文など）
    - risk_monitor.py       — ドローダウン / ポジション数監視
    - monitoring_engine.py  — 監視コンポーネントの統合
    - kill_switch.py        — Kill Switch 実装（フラグファイル書き込み）
    - alert_manager.py      — アラート送信ロジック（LINE 等の通知を想定）
  - portfolio/
    - portfolio_builder.py  — 候補選定・重み計算
    - position_sizing.py    — 株数決定・資金割当
    - risk_adjustment.py    — セクター上限・レジーム乗数
  - research/
    - factor_research.py    — ファクター計算（momentum, volatility, value）
    - feature_exploration.py— IC / forward returns / summary 等
  - ai/
    - news_nlp.py           — ニュースセンチメント取得（OpenAI 呼び出し・バッチ処理）
    - regime_detector.py    — マクロセンチメント + ETF MA でレジーム判定
  - utils/
    - logging_setup.py      — ログ設定（共通）
    - process_priority.py   — プロセス優先度 / CPU affinity ユーティリティ

設計上の注意・運用上の留意点
----------------------------
- 本リポジトリには外部ブローカークライアント・ExecutionEngine の実装を想定した抽象層があります。実際の発注を行う場合は kabuステーション等の設定・テストを十分に行ってください。
- 本番（KABUSYS_ENV=live）では kill/alert 設定を慎重に扱ってください（LINE 通知の設定など）。
- プロセス優先度設定はプラットフォーム依存で権限により失敗することがあります（警告が出ますが起動は継続します）。
- OpenAI を使う機能は API キーが必須です。利用にはコストとレート制限があります。score_news / score_regime はリトライ・失敗時のフェイルセーフを備えていますが、実運用での監視が必要です。
- .env は機密情報を含むため必ず .gitignore に入れ、リポジトリにコミットしないでください（config_setup.py のヘッダにも注意喚起あり）。

トラブルシューティング（よくある問題）
-------------------------------------
- ログディレクトリ作成失敗:
  - 権限問題などで作成できない場合、標準出力のみで動作します。LOG_DIR を作成可能なパスに設定してください。
- DB ファイルの親ディレクトリがない:
  - 起動時に自動作成される場合もありますが、存在しない場合は警告が出ます。data/ ディレクトリを作成してください。
- MONITOR_POLL_INTERVAL が不正な値:
  - run_monitoring は不正な値を検出するとデフォルト（60 秒）にフォールバックします。

貢献
----
バグ報告・改善提案は Issue を立ててください。大きな変更を行う場合はまず Issue で設計方針を相談してください。

ライセンス
---------
ソースにライセンス表記がなければリポジトリ所有者に確認してください。

以上が主要な使用方法と構成の概要です。必要であれば個々のモジュール（ExecutionEngine、BrokerClientFactory、AlertManager 等）の内部仕様や拡張方法について別ドキュメントを作成します。