# KabuSys

日本株向けの自動売買システムのコアライブラリ群。発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ（ファクター計算）および AI（ニュース NLP / レジーム判定）などの機能を含みます。

## 特徴（機能一覧）
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV により paper_trading（モックブローカー）/ live を切替
  - paper_trading 時は data/paper_trading.db に記録して本番 DB と分離
  - リスク管理（RiskManager）、注文管理、照合（Reconciler）などを組み立てて実行
- Monitoring（run_monitoring.py）
  - System / Trade / Risk モニタを定期ポーリングし、監視ログを SQLite に永続化
  - KillSwitch によるフラグファイル（data/kill.flag）で ExecutionEngine を停止可能
  - 停止要求ファイル（data/stop_requested.flag）でループ終了
- 監視永続化層（monitoring_db.py）
  - system_status, trade_logs, positions, risk_logs, dashboard テーブルを定義・マイグレーション
  - ログ / ダッシュボードの読み書きユーティリティ
- ポートフォリオ構築（portfolio）
  - 銘柄選定、重み計算（等配分／スコア加重）、単元丸め、リスク調整、ポジションサイズ計算
- リサーチ（research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリ
  - DuckDB を対象に SQL + Python で高性能に処理
- AI モジュール（ai）
  - news_nlp: OpenAI を使ったニュースのセンチメント（ai_scores への書き込み）
  - regime_detector: ETF（1321）MA200 とマクロニュースの LLM 評価を合成して市場レジーム判定
- ツール
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: .env / config/*.yaml の起動前検証
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成

## 動作要件
- Python 3.10+
- 主な依存パッケージ:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証を有効化する場合）
- 標準ライブラリ: sqlite3, logging など

例（pip）:
pip install duckdb psutil openai PyYAML

※プロジェクトに requirements.txt がある場合はそちらを使ってください。

## セットアップ手順

1. リポジトリをクローン／配置
2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML
4. .env の作成（対話式推奨）
   - python -m kabusys.config_setup
   - 作成後、設定を検証:
     - python -m kabusys.validate_config
     - 必要に応じて --strict を付けて警告をエラー扱いにできます
5. データディレクトリの準備（自動作成されることが多いですが、明示的に作る場合）:
   - mkdir -p data logs

## 主要な環境変数（抜粋）
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用
- KABU_API_PASSWORD — kabuステーション API パスワード

重要（デフォルトあり）:
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- OPENAI_API_KEY — OpenAI を使う機能で必要

paper_trading 関連:
- PAPER_FILL_MODE — instant / partial / never / reject（デフォルト: instant）

監視・kill:
- KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1。デフォルト: 0）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒。デフォルト: 60）

ログ出力:
- LOG_DIR — ログ保存先ディレクトリ（デフォルト: logs/）

## 使い方（起動・コマンド例）

- .env 作成（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine を起動（本番 / ペーパーどちらも Settings が切替）
  - python -m kabusys.run_execution
  - 動作中は data/execution.pid（デフォルト）に PID が書かれます
  - ペーパートレード時は KABUSYS_ENV=paper_trading を指定し、専用 DB に記録

- Monitoring を起動（ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL で秒間隔を上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - 停止: data/stop_requested.flag を作成するとループが停止します

- Kill Switch の発動（ExecutionEngine 停止）
  - KillSwitch は条件を満たすと data/kill.flag を書き込みます
  - ExecutionEngine 側で kill.flag を検出し停止する仕組みです

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 日付範囲指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI モジュール呼び出し（ライブラリ利用）
  - from kabusys.ai import score_news
  - score_news(duckdb_conn, target_date, api_key="...")

## 停止方法
- 実行スクリプトの標準的な停止
  - Ctrl+C（KeyboardInterrupt）
- 外部からの停止指示
  - data/stop_requested.flag を作成 → run_monitoring / run_execution の監視ループが検出して停止
  - KillSwitch による停止: monitoring が条件を満たすと data/kill.flag を書く → ExecutionEngine が検出して停止
- kill.flag を自動クリアしたい場合:
  - KILL_FLAG_CLEAR_ON_START=1 を .env に設定（注意: 本番では危険）

## ログ
- ロギングは kabusys.utils.logging_setup.setup_logging により統一設定されます
- コンソール（stdout）と日次ローテートファイル（logs/<app_name>.log）に出力
- ログディレクトリは LOG_DIR 環境変数またはデフォルト logs/ を使用

## データベース
- SQLite（監視用）: data/monitoring.db（デフォルト）
- SQLite（paper_trading）: data/paper_trading.db（paper_trading 用）
- DuckDB（分析用）: data/kabusys.duckdb（デフォルト）
- 初回起動時や接続時に init_monitoring_db() が呼ばれ、必要テーブル・簡易マイグレーションを実行します

## ディレクトリ構成（主要ファイル）
プロジェクトルート（例）:
- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / Settings
    - config_setup.py          — .env 対話式ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — Monitoring 起動スクリプト
    - execution/               — 発注エンジン関連（ブローカ、order_manager 等）
    - monitoring/
      - monitoring_db.py       — 監視 DB 層
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
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
    - tools/
      - paper_verification_report.py
- config/
  - system_config.yaml, data_config.yaml, ... （テンプレート / 生成スクリプトあり）
- data/
  - monitoring.db (デフォルト)
  - paper_trading.db (paper_trading 用)
  - kill.flag, stop_requested.flag, execution.pid など
- logs/
  - execution.log, monitoring.log, ...

（上記はコード・コメントを元に抜粋・要約しています）

## 注意事項 / 運用上のポイント
- KABUSYS_ENV は重要。`live` 設定は実際の発注を伴うため特に注意して設定・確認してください。
- .env は絶対に Git にコミットしないでください（APIキー等の機密情報を含む）。
- OpenAI を使う機能を有効にする場合は OPENAI_API_KEY を必ず設定してください。API 呼び出しは冪等やフェイルセーフを考慮して実装されていますが、コストやレート制限に注意してください。
- Paper Trading は本番 DB と分離されています。ペーパーモードでの運用は production に影響しません。
- run_monitoring のポーリング間隔は MONITOR_POLL_INTERVAL で制御可能（秒）。不正値が指定された場合はデフォルト 60 秒にフォールバックします。

---

必要であれば、README に記載するサンプル .env のテンプレート（.env.example 形式）や、よく使う運用コマンド集、デバッグ方法（ログの見方や duckdb の中身確認 SQL 例）を追加します。どの情報を追加しますか？