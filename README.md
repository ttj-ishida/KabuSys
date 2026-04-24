KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株向けの自動売買 / 調査 / 監視ライブラリ群です。  
このリポジトリには、発注エンジン、監視（Monitoring）、ペーパートレード検証、ファクター計算、ニュース NLP／レジーム判定などのモジュールが含まれます。  
設計方針としては「本番とペーパーを明確に分離」「DB はローカルファイル（SQLite / DuckDB）」「外部 API は明示的にキーを渡す」「ログやフラグファイルでプロセス制御」を採用しています。

主な機能
----------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV により本番 / paper_trading を切り替え
  - paper_trading 時は MockBrokerClient を使用し、専用 DB に記録
  - 運用中の停止はフラグファイル（data/stop_requested.flag / data/kill.flag）で制御
- Monitoring（run_monitoring.py / monitoring パッケージ）
  - システム状態（CPU/Memory/Disk）、データ鮮度、滞留注文、ドローダウンなどを定期監視
  - KillSwitch による自動停止（大きなドローダウン等で data/kill.flag を作成）
  - アラート発行（AlertManager 経由）
- 監視データの永続化（monitoring_db）
  - SQLite を用いたテーブル定義と読み書きユーティリティ
- ポートフォリオ構築（portfolio パッケージ）
  - 候補選定、等ウェイト／スコア加重、ポジションサイズ計算、セクター上限・レジーム補正
- 研究／調査（research パッケージ）
  - Momentum / Value / Volatility 等のファクター計算、将来リターン・IC 計算、統計サマリー
  - DuckDB 接続を受けて SQL と Python で処理
- AI モジュール（ai パッケージ）
  - news_nlp: OpenAI を使ったニュースセンチメントの取得（ai_scores への書き込み）
  - regime_detector: ma200 とマクロニュースを組み合わせた市場レジーム判定
- ユーティリティ
  - .env 対話ウィザード（config_setup.py）
  - 設定検証ツール（validate_config.py）
  - ペーパートレード検証レポート生成（tools/paper_verification_report.py）
  - ロギング設定・プロセス優先度設定ユーティリティ

セットアップ
-----------
1. リポジトリをクローン
   - git clone <リポジトリURL>
2. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - 本リポジトリに requirements.txt が無い場合は少なくとも以下をインストールしてください:
     - duckdb
     - psutil
     - openai
     - （validate_config の YAML 検証を有効にするなら）PyYAML
   - 例:
     - pip install duckdb psutil openai PyYAML
4. データ・ログディレクトリの作成（任意。スクリプトが自動作成します）
   - mkdir -p data logs
5. .env の作成
   - 対話ウィザードを利用:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に .env を作成（本リポジトリでは .env.example は付属しない想定）

主要な環境変数（概要）
---------------------
重要なキー（必須）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

運用／パス管理
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
  - paper_trading: 実発注を行わず、paper_trading DB に記録
  - live: 本番（注意して利用）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite （デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）

AI 関連
- OPENAI_API_KEY — OpenAI API キー（ai.news_nlp / regime_detector で使用）

その他
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE — ペーパートレードのマッチングモード ("instant" | "partial" | "never" | "reject")
- KILL_FLAG_CLEAR_ON_START — 本番起動時に kill.flag を自動クリアするか（0/1。0 推奨）

使い方（コマンド）
-----------------
- 環境ウィザード（.env の初期作成）
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - --strict を付けると警告でも exit 1 にする: python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path を使い発注はモック
    - 起動時に data/stop_requested.flag が存在する場合は起動を中止
    - 実行中に data/stop_requested.flag が作成されるとエンジンを停止
    - 実プロセスは data/execution.pid に PID を書き込む（設定参照）

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 挙動:
    - MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（秒）
    - 監視ログは settings.sqlite_path（監視 DB）へ記録。環境に依らず本番監視 DB を使う設計
    - data/stop_requested.flag を検出するとループを終了

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で別 DB を指定可能（優先度: --db > 環境変数）

- ライブラリとしての利用例（AI スコア付与）
  - duckdb 接続を作成して関数を呼ぶ:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key="...")

注意点・運用メモ
--------------
- ロギング
  - setup_logging を各起動スクリプトで呼んでおり、logs/<app_name>.log に日次ローテーションで出力します（デフォルト logs/ ディレクトリ）。
  - ログディレクトリ作成に失敗するとコンソール出力のみになります。

- プロセス優先度
  - set_process_priority("high") を呼んでいるため、権限不足や OS により設定できない場合は警告が出ますが動作は継続します。

- フラグファイル
  - 停止制御: data/stop_requested.flag（run_execution/run_monitoring が参照）
  - Kill Switch: data/kill.flag（KillSwitch が作成。ExecutionEngine は kill.flag を検出して停止）
  - 起動時に kill.flag を自動クリアする設定は KILL_FLAG_CLEAR_ON_START（ただし本番では 0 推奨）

- DB マイグレーション
  - init_monitoring_db は idempotent（存在チェック付き）で、既存 DB に列がない場合は ALTER TABLE で追加する簡単なマイグレーション処理を持ちます。

- OpenAI API
  - news_nlp / regime_detector は OpenAI を呼ぶため OPENAI_API_KEY が必要。API 呼び出しはリトライ・フォールバック戦略を備えていますが、キーの漏洩に注意してください。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py              — 環境変数読み込み / Settings クラス
- config_setup.py        — .env 対話式ウィザード
- validate_config.py     — 起動前設定検証 CLI
- run_execution.py       — ExecutionEngine 起動スクリプト
- run_monitoring.py      — Monitoring 起動スクリプト

src/kabusys/ai/
- news_nlp.py            — ニュースセンチメント（OpenAI）処理
- regime_detector.py     — 市場レジーム判定

src/kabusys/monitoring/
- monitoring_db.py       — SQLite テーブル定義 / MonitoringDB クラス
- system_monitor.py      — システム状態監視
- trade_monitor.py       — （注文滞留などの監視。ファイルにより詳細実装あり）
- risk_monitor.py        — ドローダウン / ポジション上限の監視
- kill_switch.py         — Kill Switch 実装（フラグファイル）
- alert_manager.py       — （アラート管理。メール/LINE 等の実装想定）
- monitoring_engine.py   — 各 Monitor を束ねるエンジン

src/kabusys/execution/
- execution_engine.py    — ExecutionEngine 本体（起動スクリプトから利用）
- broker_factory.py      — ブローカークライアント生成（実・モック切替）
- order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 発注関連

src/kabusys/portfolio/
- portfolio_builder.py
- position_sizing.py
- risk_adjustment.py

src/kabusys/research/
- factor_research.py
- feature_exploration.py

src/kabusys/tools/
- paper_verification_report.py

src/kabusys/utils/
- logging_setup.py
- process_priority.py

logs/                         — デフォルトログ出力先（起動時に作成される）
data/                         — データファイル・フラグ置き場（SQLite, DuckDB, pid, flag）

追加情報 / トラブルシューティング
---------------------------------
- validate_config の YAML 検証は PyYAML がインストールされている場合のみ実行されます。未インストール時は警告が出ますが検証は続行します。
- psutil を用いたプロセス優先度や CPU affinity の設定は権限によって失敗することがあります。失敗すると警告ログが出ますが致命的ではありません。
- DuckDB / SQLite のファイルはデフォルトで data/ 配下に作成されます。別パスを使う場合は .env で DUCKDB_PATH / SQLITE_PATH を調整してください。
- AI 周りは API の料金およびレート制限に注意してください。news_nlp はバッチ・トリム・リトライを実装していますが、運用時はレートとコストを考慮してください。

ライセンス・貢献
----------------
（この README には記載されていません。リポジトリの LICENSE を参照してください。）

以上が本コードベースの概要と使い方のまとめです。必要であれば、README に含めたい「実行例（環境変数込みの起動コマンド）」「.env のサンプル」「監視項目一覧（閾値）」などを追記します。どの情報を詳細化したいか教えてください。