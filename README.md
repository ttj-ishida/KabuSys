KabuSys — 日本株自動売買システム
================================

この README はリポジトリ内のコードベースに基づく概要・セットアップ・使い方・ディレクトリ構成の説明です。

プロジェクト概要
----------------
KabuSys は日本株向けの自動売買システム（バックエンドライブラリ）です。  
主な機能は以下のとおりです。

- 発注エンジン（ExecutionEngine）を起動して注文管理・約定処理を行う
- 監視プロセス（SystemMonitor / TradeMonitor / RiskMonitor）によるシステムの健全性監視とアラート発行
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ計算）
- リサーチ用ファクター計算（モメンタム／ボラティリティ／バリュー等）
- ニュース NLP による銘柄別センチメント算出（OpenAI API を利用）
- ペーパートレード用の検証レポート作成ツール

主な特徴
-------
- 環境変数・.env による柔軟な設定管理（config_setup によるウィザードあり）
- paper_trading と live を明確に分離（paper_trading は MockBroker と専用 DB）
- 監視系と実行系が分離され、kill flag / stop flag による安全停止機構
- DuckDB / SQLite を用いた分析・ログ保存
- OpenAI（gpt-4o-mini など）との統合（ニュース評価・レジーム検出）

前提 / 必要パッケージ
-------------------
推奨: Python 3.10+（コードは型ヒントに Union 表記などを使用）  
主な依存（最低限）:
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（validate_config の YAML 検証を有効にする場合）

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

環境変数（主なもの）
-------------------
主要な環境変数とデフォルト値の一覧（.env で管理）:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- KABUSYS_ENV (development | paper_trading | live) — default: development
  - paper_trading: MockBroker を使用し、Paper Trading 専用 DB に記録
  - live: 実際の発注を行う
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db) — 監視 DB（monitoring は環境にかかわらず本番 sqlite_path を使用）
- PAPER_TRADING_SQLITE_PATH (paper_trading 用、default: data/paper_trading.db)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL, default: INFO)
- OPENAI_API_KEY (AI 機能を使う場合に必要)
- MONITOR_POLL_INTERVAL (監視ループのポーリング間隔秒、default: 60)
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START など

セットアップ手順
----------------
1. リポジトリをクローンし、仮想環境を作成して依存をインストールする。
2. .env の作成:
   - 対話式ウィザードを使用:
     ```bash
     python -m kabusys.config_setup
     ```
   - 手動で .env を作成する場合は .env.example を参考に必要な環境変数を設定。
3. 設定検証（推奨）:
   ```bash
   python -m kabusys.validate_config
   # 警告も厳密に扱いたい場合:
   python -m kabusys.validate_config --strict
   ```
4. データディレクトリを準備（必要なら）:
   - デフォルトでは data/ 下に SQLite / PID / stop flag / kill flag などが格納されます。起動により自動作成されることが多いですが、権限や配置先を確認してください。

基本的な使い方
-------------

- ExecutionEngine（発注エンジン）を起動する:
  - 実行:
    ```bash
    python -m kabusys.run_execution
    ```
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録します（本番 DB と分離）。
    - 起動時に data/stop_requested.flag が存在すると起動を中止します。
    - 実行中は data/execution.pid に PID を書きます（設定に基づく）。

- Monitoring（監視プロセス）を起動する:
  - 実行:
    ```bash
    python -m kabusys.run_monitoring
    ```
  - 特記事項:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用してログ保存します。
    - 監視ループは data/stop_requested.flag の存在を検出すると終了します。

- 設定検証:
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成:
  ```bash
  python -m kabusys.tools.paper_verification_report
  # 期間指定例:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB 指定:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI / NLP 機能:
  - ニューススコアリング / レジーム判定などの機能を利用するには OPENAI_API_KEY を設定する必要があります。
  - 実装上、API 呼び出しにはリトライやスコア検証が組み込まれていますが、API レスポンスの安定性に注意してください。

停止・安全機構
----------------
- stop_requested.flag（data/stop_requested.flag）
  - 実行ループ（run_monitoring / run_execution の監視ループ）を外部から停止させるために存在をチェックします。フラグがあるとループは終了します。
- kill.flag（Settings.kill_flag_path, デフォルト data/kill.flag）
  - KillSwitch によって書き込まれ、ExecutionEngine に停止シグナルを送ります（リスク判定等に応じて生成）。
  - KILL_FLAG_CLEAR_ON_START=1 にすると起動時に自動でクリアします（本番では推奨しません）。

ログ
----
- 標準のロギング設定は kabusys.utils.logging_setup.setup_logging を通じて行われます。
- デフォルトログディレクトリ: logs/
- ログレベルは環境変数 LOG_LEVEL または setup_logging の引数で制御します。
- ログは stdout（コンソール）と日次ローテーションされるファイルに出力されます。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys/ 以下の主要なモジュールの概要です（重要ファイルのみ抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込みロジック
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパー検証レポート生成
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — （該当の実装ファイルあり）注文関連監視
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - monitoring_engine.py   — 各モニタを束ねるエンジン
    - kill_switch.py         — kill.flag 書き込み / 評価
    - alert_manager.py       — （アラート送信管理）
  - execution/
    - execution_engine.py    — ExecutionEngine（発注ワークフロー）
    - broker_factory.py      — ブローカクライアント生成（Mock を含む）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py   — 候補選定 / 重み計算
    - position_sizing.py     — 株数決定 / 投下金額制限
    - risk_adjustment.py     — セクター制限 / レジーム乗数
  - research/
    - factor_research.py     — モメンタム・ボラティリティ・バリュー計算
    - feature_exploration.py — IC 計算等のリサーチユーティリティ
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）でスコア算出
    - regime_detector.py     — レジーム判定（MA + マクロセンチメント）
  - data/                    — 実行時に生成されるデータ（SQLite / PID / flags 等）
  - logs/                    — デフォルトログ出力先

注意事項 / 運用上のヒント
------------------------
- 本番（KABUSYS_ENV=live）では kill flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は危険です。0 を推奨。
- paper_trading は本番 DB を汚さないよう専用の PAPER_TRADING_SQLITE_PATH を使います。
- monitoring は設計上「監視向け」の DB（SQLITE_PATH）に書き込みます。環境にかかわらず sqlite_path を参照するため、本番 DB の位置に注意してください。
- OpenAI API を使う機能はレート・コストやプライバシーに注意して運用してください。APIキーは外部に漏れないよう .env を安全に管理してください。
- ログディレクトリの作成に失敗するとファイル出力は無効になり stdout のみで出力されます。権限やディスク容量に注意してください。

トラブルシューティング
---------------------
- validate_config でエラーが出たら、.env に必要なキーが存在するか、パスが正しいか、KABUSYS_ENV の値が正しいかを確認してください。
- OpenAI 周りのエラーはネットワーク・レート制限・API キー設定を確認。ライブラリ（openai）バージョン互換性にも要注意。
- psutil による優先度設定が失敗した場合は権限不足（非 root）やプラットフォーム非対応の可能性があります。ログに警告が出ますが実行自体は継続されます。

ライセンス / バージョン
---------------------
- パッケージのバージョンは src/kabusys/__init__.py の __version__ を参照してください（現状 0.1.0）。

最後に
------
この README はソースコードの実装から自動的に要点を抜粋して作成しています。詳細な実装や追加の運用手順は各モジュールの docstring / コメントを参照してください。質問や追加で README に含めたい運用手順があれば教えてください。