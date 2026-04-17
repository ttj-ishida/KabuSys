# KabuSys

日本株自動売買システムの一部（ライブラリ & 実行スクリプト群）のリポジトリ。  
この README はコードベース（src/kabusys 以下）の主要コンポーネント、セットアップ、実行方法をまとめたものです。

注意: 実際の運用では .env に秘密情報（API キー・パスワード等）を保存しない、または厳重に管理してください。.env は絶対に Git にコミットしないでください。

---

## プロジェクト概要

KabuSys は以下の機能を持つモジュール群から構成されています（コードは src/kabusys 配下）：

- 環境設定・読み込み（.env 自動ロード、Settings クラス）
- 実行エンジン起動スクリプト（ExecutionEngine 起動）
- 監視用ポーリング（System / Trade / Risk Monitor）
- 監視 DB（SQLite）への永続化レイヤ
- ポートフォリオ構築（候補選定・重み付け・ポジショニング）
- 研究用ファクター計算（DuckDB を用いたファクター算出）
- AI（OpenAI）を使ったニュースセンチメント / レジーム判定
- ユーティリティ・ツール（.env ウィザード、設定検証、paper trading レポート等）

主要な設計方針：
- 実行ロジックと DB/外部 API 呼び出しを分離
- DuckDB を分析処理向けに使用、SQLite を稼働ログ/監視用に使用
- Paper Trading（ペーパートレード）向けに本番 DB と分離可能

---

## 主な機能一覧

- 設定管理
  - Settings クラスで環境変数を統合的に管理
  - .env/.env.local 自動ロード（プロジェクトルートが特定できる場合）
  - 対話式ウィザード: kabusys.config_setup.run_wizard（python -m kabusys.config_setup）
  - 設定検証 CLI: kabusys.validate_config（--strict オプションあり）

- 実行・監視
  - 実行エンジン起動: run_execution.py（KABUSYS_ENV に応じてモック or 実ブローカー）
  - 監視ループ起動: run_monitoring.py（SystemMonitor を定期実行）
  - 監視 DB（SQLite）へのログ永続化と簡易マイグレーションをサポート
  - Kill Switch（data/kill.flag）により ExecutionEngine を安全に停止可能
  - LINE 通知サポート（AlertManager） — トークン未設定時はログに出力のみ

- 戦略・ポートフォリオ
  - 銘柄選定（スコア順ソート）
  - 等配分 / スコア加重配分
  - セクター上限適用、レジームに応じた投資乗数
  - ポジションサイズ計算（ロット丸め・上限・資金スケーリング）

- リサーチ / AI
  - DuckDB を用いたファクター計算（モメンタム・ボラティリティ・バリュー）
  - 将来リターン計算・IC 計測・ファクター統計
  - OpenAI を用いたニュースセンチメント（ai.news_nlp.score_news）
  - レジーム判定（ai.regime_detector.score_regime）

- ツール
  - Paper Trading の検証レポート生成（kabusys.tools.paper_verification_report）
  - .env ウィザード（kabusys.config_setup）
  - 設定検証（kabusys.validate_config）

---

## 必要環境・依存ライブラリ（主なもの）

- Python 3.9+（型注釈で Optional 型などを使用）
- duckdb
- psutil
- openai
- requests
- PyYAML（設定検証で YAML パースを行う場合に必要。インストールされていない場合は YAML 検証をスキップ）

インストール例（仮）:
pip install duckdb psutil openai requests PyYAML

（実プロジェクトでは requirements.txt / poetry / pipfile を使って管理してください）

---

## セットアップ手順

1. リポジトリをチェックアウトしてプロジェクトルートへ移動
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存ライブラリをインストール
   - pip install duckdb psutil openai requests PyYAML
4. .env の作成（推奨: 対話式ウィザード）
   - python -m kabusys.config_setup
   - ウィザード完了後、.env に設定が保存されます
5. 設定検証（任意）
   - python -m kabusys.validate_config
   - すべて OK を期待。--strict を付けると警告もエラー扱いで失敗する
6. データディレクトリ作成（必要時）
   - デフォルト DB パスは data/*.db 等なので data ディレクトリを作成しておくとよい
   - mkdir -p data

主要な環境変数（必須・重要）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live。デフォルト: development)
- OPENAI_API_KEY (AI 機能を使う場合に必要)
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- SQLITE_PATH (監視 DB、デフォルト data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、デフォルト data/paper_trading.db)
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知用、任意）
- PAPER_FILL_MODE（paper_trading の約定挙動: instant | partial | never | reject。デフォルト: instant）
- KILL_FLAG_CLEAR_ON_START（Execution 起動時に kill.flag を自動クリアするか (0/1)、本番では 0 推奨）

---

## 使い方（実行例）

- 環境変数読み込み後、設定検証:
  - python -m kabusys.validate_config
  - あるいは対話式で .env を作る: python -m kabusys.config_setup

- 監視ループ起動（SystemMonitor のポーリング）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（秒、デフォルト 60）
  - python -m kabusys.run_monitoring
  - 監視は常に settings.sqlite_path（本番 DB パス）を使用して監視データを記録します（KABUSYS_ENV にかかわらず）。

  停止:
  - プロジェクトルート/data/stop_requested.flag を作成すると監視ループは停止します（run_monitoring, run_execution ともに同様のフラグを参照）。

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に発注ログを書きます（本番 DB と分離）
  - 実行中は data/execution.pid に PID が書かれます。PID ファイルが stale（存在するがプロセスが無い）なら監視が検出して削除します。

  停止:
  - data/stop_requested.flag の作成で実行中エンジンに停止指示を出せます。
  - kill.flag（Settings.kill_flag_path, デフォルト data/kill.flag）を監視/アラートから書き込むことで Execution を停止させる（KillSwitch が書き込み）。

- Paper Trading 検証レポート出力
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで SQLite パス指定可（環境変数 PAPER_TRADING_SQLITE_PATH 優先）

- AI / レジーム判定・ニューススコアリング（Python API）
  - DuckDB 接続を作って呼び出す:
    from kabusys.ai.news_nlp import score_news
    from kabusys.ai.regime_detector import score_regime
    score_news(conn, target_date, api_key="...")  # ai_scores を更新
    score_regime(conn, target_date, api_key="...")  # market_regime を更新

  - 注意: OPENAI_API_KEY が無いと例外になる。API 呼び出しはリトライ・フォールバック処理あり。

---

## 重要な動作・挙動メモ

- run_monitoring と run_execution は両方とも data ディレクトリ下の stop_requested.flag を監視します。これにより外部からプロセスを停止できます。
- Monitoring 側は SQLite（monitoring DB）にテーブルを冪等に作成する init_monitoring_db 関数を持っています。既存 DB に対して必要なマイグレーション（カラム追加）も行います。
- run_execution は KABUSYS_ENV=paper_trading のとき専用の paper_trading DB を使います（本番監視 DB とは分離）。
- Settings.kill_flag_clear_on_start が 1 の場合、Execution 起動時に kill.flag を自動クリアします。本番では 0 を推奨。
- MONITOR_POLL_INTERVAL は正の整数で指定してください。不正値や 0 以下はデフォルト 60 秒にフォールバックします。
- process priority（優先度）は起動時に set_process_priority("high") が呼ばれます（psutil を使って OS に依存した設定を行いますが、権限不足等で失敗することがあります）。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                      — 環境変数 / Settings
- config_setup.py                — .env 対話式ウィザード
- validate_config.py             — 設定検証 CLI
- run_execution.py               — ExecutionEngine 起動スクリプト
- run_monitoring.py              — SystemMonitor ポーリング起動スクリプト

- ai/
  - __init__.py
  - news_nlp.py                   — ニュースセンチメント（OpenAI 呼出）
  - regime_detector.py            — レジーム判定（MA + macro sentiment）

- monitoring/
  - monitoring_db.py              — SQLite 用永続化層
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - alert_manager.py
  - kill_switch.py

- execution/                      — ExecutionEngine 周辺（発注・オーダー管理等）
  - (order_manager, broker_factory, execution_engine など — 本 README の抜粋ではコード省略)

- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py

- research/
  - factor_research.py
  - feature_exploration.py

- tools/
  - paper_verification_report.py

- utils/
  - process_priority.py           — psutil による優先度 / affinity 設定

data/                              — 実行時に使用する（DB ファイル, flag, pid など）
- kill.flag
- stop_requested.flag
- execution.pid
- monitoring.db (default SQLITE_PATH)
- kabusys.duckdb (default DUCKDB_PATH)
- paper_trading.db (default PAPER_TRADING_SQLITE_PATH)

（上記はリポジトリの抜粋です。実際のファイル構成はリポジトリを参照してください）

---

## よくあるコマンドまとめ

- .env 作成（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視開始
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジン開始
  - python -m kabusys.run_execution

- Paper Trade レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

---

## トラブルシューティング（簡易）

- .env が読み込まれない・値が不正
  - プロジェクトルートが .git または pyproject.toml で特定されない場合、自動読み込みをスキップします。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます（テスト時に便利）。

- OpenAI 呼び出しで失敗する
  - OPENAI_API_KEY を設定しているか確認
  - API レート制限やネットワーク障害は内部でリトライが働きますが、最大リトライ回数超過で処理がスキップされることがあります

- データベースにテーブルがないエラー
  - init_monitoring_db は起動時に呼ばれるため通常は自動で作成されます。手動で確認する場合は sqlite3 でファイルを開いてテーブル一覧を確認してください。

---

この README はコードから抽出した情報を元に作成しています。実運用時は各モジュールのドキュメントやコード内コメント（docstring）を合わせて参照してください。質問や補足があればお知らせください。