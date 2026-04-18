# KabuSys

日本株自動売買システムの Python パッケージ（ライブラリ兼起動スクリプト群）。

この README はリポジトリ内の主要モジュール（実行エンジン、監視、ポートフォリオ構築、リサーチ、AI ニューススコアリング等）についての概要、セットアップ手順、よく使うコマンド、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買／リサーチ基盤です。主要機能は以下の通りです。

- ExecutionEngine：発注・リスク管理・注文管理を行う実行エンジン（本番 / ペーパートレード対応）
- Monitoring：システム稼働・データ鮮度・注文状態・リスク（ドローダウン等）を定期監視し、Kill Switch（フラグファイル）でエンジン停止を行う
- Portfolio construction：候補選定、重み計算、ポジションサイズ計算、セクター上限・レジーム乗数
- Research：DuckDB を用いたファクター計算（モメンタム / ボラティリティ / バリュー）、将来リターン / IC 計算など
- AI モジュール：OpenAI を利用したニュースセンチメント（news_nlp）および市場レジーム判定（regime_detector）
- ユーティリティ：ログ設定、プロセス優先度設定、設定ウィザード、設定検証、監視 DB ラッパー等
- ツール：Paper Trading 用の検証レポート生成スクリプト 等

設計上の注意点：
- 環境変数 / .env を優先して設定を読み込む（自動ロードあり。無効化可）
- Paper Trading（KABUSYS_ENV=paper_trading）時は発注はモックとなり、監視用 DB と本番 DB を分離
- DuckDB は分析・リサーチ用に使用、SQLite は監視および（ペーパートレード時の）取引ログ保持に使用

---

## 主な機能一覧（抜粋）

- 起動スクリプト
  - run_execution.py — ExecutionEngine を起動（PID 管理 / stop フラグ対応）
  - run_monitoring.py — SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔制御）
- 設定関連
  - config_setup.py — 対話式 .env 作成ウィザード
  - validate_config.py — .env と config/*.yaml の事前検証 CLI
  - config.Settings — 環境変数ラッパ（必須変数チェック・デフォルト値）
- 監視
  - monitoring.MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor
  - KillSwitch（data/kill.flag 書き込みで ExecutionEngine 停止）
  - monitoring.monitoring_db — SQLite テーブル初期化／読み書きユーティリティ
- 発注／実行
  - execution.ExecutionEngine, OrderManager, OrderRepository, RiskManager, Reconciler, BrokerClientFactory
  - paper_trading 用の専用 SQLite（PAPER_TRADING_SQLITE_PATH）
- ポートフォリオ構築
  - portfolio: 候補選定・重み計算・ポジションサイズ・リスク調整
- リサーチ
  - research.factor_research（ファクター計算）
  - research.feature_exploration（将来リターン / IC / サマリー）
- AI（OpenAI）
  - ai.news_nlp.score_news — ニュース記事を LLM でスコアリングして ai_scores に書き込み
  - ai.regime_detector.score_regime — ETF の MA とマクロニュースを組み合わせてレジーム判定
- ツール
  - tools.paper_verification_report — Paper Trading の実績を集計してレポート出力

---

## 必要条件 / 推奨環境

- Python 3.10+（型ヒントに `|` を使用しているため）
- 必要パッケージ（最低限）
  - duckdb
  - psutil
  - openai
- 任意（機能に応じて）
  - PyYAML（config/*.yaml の検証に使用）
- 標準で使用する DB:
  - SQLite（monitoring にデフォルト `data/monitoring.db`）
  - DuckDB（分析にデフォルト `data/kabusys.duckdb`）

例（仮の requirements）:
pip install duckdb psutil openai PyYAML

※ 実際の requirements.txt はプロジェクトに合わせて用意してください。

---

## セットアップ手順

1. リポジトリをクローン／配置
2. Python 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML
4. 初期設定（対話式ウィザードで .env を作成）
   - python -m kabusys.config_setup
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - KABUSYS_ENV=development|paper_trading|live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db (paper_trading 用)
     - OPENAI_API_KEY=... (AI モジュール使用時)
5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いで exit(1)
6. データディレクトリ等の準備（自動作成されることが多いが確認）
   - data/ ディレクトリに書き込み権限が必要
   - logs/ ディレクトリもログ出力用に作成される（setup_logging が自動作成）

---

## 環境変数の主要項目（抜粋）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境: development / paper_trading / live
- OPENAI_API_KEY — OpenAI を使う機能で必要
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 DB（paper_trading 時）
- LOG_LEVEL — ログレベル（DEBUG/INFO/…）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリア（0/1）

注意: .env 自動読み込みはデフォルトで有効。テストなどで無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

## 使い方（よく使うコマンド例）

- 設定ウィザード（.env を作る）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- ExecutionEngine 起動（本番/ペーパーともに）
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録され、本番 DB と分離されます。
  - 実行中に停止させたい場合は data/stop_requested.flag を作成（run_execution はこのフラグを検知して停止します）。

- Monitoring 起動（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する: MONITOR_POLL_INTERVAL 環境変数（秒）で上書き（デフォルト 60 秒）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - run_monitoring も data/stop_requested.flag を見てループを終了します。
  - 監視は常に本番 sqlite_path を参照（環境にかかわらず monitoring は本番の sqlite_path を使う設計になっています）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH （デフォルトは PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db）

- AI モジュール（ライブラリ呼び出し例）
  - ニューススコアリング（Python API）
    from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date, api_key="...")

  - レジーム判定
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key="...")

  これらは DuckDB 接続（duckdb.connect(...)）を渡して使います。OpenAI API キーが必要です。

---

## フラグ／PID の挙動

- 停止要求（外部→プロセス）
  - data/stop_requested.flag
    - run_execution.py / run_monitoring.py はこのファイルの存在を検知して終了します。
- Kill Switch（監視→ExecutionEngine 停止）
  - data/kill.flag
    - KillSwitch が条件を満たすとこのファイルを書き込み、ExecutionEngine は起動時や稼働中にこれを検知して安全停止します。
  - KILL_FLAG_CLEAR_ON_START=1 により起動時に自動クリアする設定があります（本番では 0 を推奨）。
- PID ファイル
  - data/execution.pid 等に PID を書くことでプロセスマネジメントを補助します。

---

## ディレクトリ構成（主要ファイル）

リポジトリの実際の構成に合わせて一部抜粋しています（src/kabusys 配下がメイン）:

- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数 / Settings
    - config_setup.py           — .env 対話式ウィザード
    - validate_config.py        — 設定検証 CLI
    - run_execution.py          — ExecutionEngine 起動スクリプト
    - run_monitoring.py         — SystemMonitor ポーリング起動
    - execution/                — 発注関連コンポーネント（Engine, Broker, OrderManager 等）
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - risk_monitor.py
      - trade_monitor.py
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
      - __init__.py
    - tools/
      - paper_verification_report.py
    - utils/
      - logging_setup.py
      - process_priority.py

- data/ (実行時に生成・使用)
  - monitoring.db (デフォルト)
  - paper_trading.db (ペーパートレード用)
  - stop_requested.flag
  - kill.flag
  - execution.pid

- logs/ (ログファイル出力先、デフォルト)
  - execution.log, monitoring.log, ...（日次ローテーション）

---

## 運用上の注意 / ベストプラクティス

- KABUSYS_ENV を正しく設定すること（development / paper_trading / live）。live は本番なので特に注意。
- .env は絶対にリポジトリにコミットしないこと（秘密情報を含む）。
- 本番では KILL_FLAG_CLEAR_ON_START は 0（自動クリアしない）を推奨。
- OpenAI 関連は API コストに注意してバッチ化・リトライ設計がされているが、呼び出し頻度とトークン量は監視すること。
- DuckDB / SQLite のパスはバックアップ対象に含めるか、定期的にエクスポートを行うこと。
- ログは logs/ に日次ローテーションで溜まるため、ディスク容量に注意してください。

---

## 参考 / トラブルシュート

- 設定が正しく読み込まれない場合:
  - .env の存在と値を確認
  - 自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- PyYAML がインストールされていない場合 validate_config は YAML のパース検証をスキップします（警告表示）
- run_monitoring のポーリング間隔設定:
  - MONITOR_POLL_INTERVAL を秒で指定（1秒以上）。不正値は 60 秒にフォールバック。

---

必要であれば README にサンプル .env.example、requirements.txt、または起動/デプロイ手順（systemd / Docker / コンテナ化の例）を追記できます。追加で欲しい情報があれば教えてください。