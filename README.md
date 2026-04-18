README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤の一部を実装した Python コードベースです。
主な用途は次のとおりです:

- ExecutionEngine: 注文発行・リスク管理・約定管理を行う実行エンジン
- Monitoring: システム状態・注文状態・リスクを定期監視し、必要に応じて Kill Switch を発動
- Research / AI: DuckDB 上の時系列データからファクター計算・特徴量解析、ニュースの NLP スコアリング
- Portfolio: 候補選定・重み算出・ポジションサイズ計算などポートフォリオ構築ロジック
- CLI ユーティリティ: .env ウィザードや設定検証、Paper Trading 検証レポートなど

主な機能
--------
- 実行／監視用の起動スクリプト:
  - run_execution.py — ExecutionEngine を起動（KABUSYS_ENV により paper_trading と live を切替）
  - run_monitoring.py — SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔調整可能）
- 設定関連:
  - config_setup.py — 対話式 .env 作成・更新ウィザード
  - validate_config.py — .env / config/*.yaml の事前検証用 CLI
- モニタリング:
  - system_monitor, trade_monitor, risk_monitor, monitoring_engine による定期チェック
  - monitoring_db: SQLite に監視ログを永続化（system_status / trade_logs / risk_logs / positions / dashboard）
  - Kill Switch：条件を満たすと data/kill.flag を書き込み ExecutionEngine を停止する仕組み
- ポートフォリオ構築:
  - 候補選定（スコアソート）、等配分／スコア加重配分、セクター制限、ポジションサイズ算出（単元株丸め・aggregate cap）
- リサーチ／AI:
  - DuckDB を用いたファクター計算（momentum / volatility / value）や前方リターン、IC 計算
  - ニュース NLP（OpenAI を利用）で銘柄ごとのセンチメントスコアを ai_scores テーブルに書き込み
  - 市場レジーム判定（ETF + マクロニュースの LLM スコアを合成）
- ツール:
  - tools/paper_verification_report.py — Paper Trading DB を解析して PASS/FAIL 判定付きレポートを生成

セットアップ手順
----------------
1. Python 環境を準備
   - 推奨: Python 3.10+（プロジェクトルートの pyproject.toml 等に合わせてください）
   - 仮想環境作成:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - このリポジトリは外部ライブラリに依存する箇所があります。最低限必要なパッケージ例:
     - duckdb
     - psutil
     - openai
     - PyYAML (validate_config の YAML 検証に任意で使用)
   - 例:
     - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt があればそちらを使用してください）

3. .env を作成
   - 対話式ウィザードを利用:
     - python -m kabusys.config_setup
   - 手動で作成する場合は .env.example を元にプロジェクトルートに .env を置く
   - 必須環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要なデータベースパスのデフォルト:
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db（paper_trading 実行時）

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります:
     - python -m kabusys.validate_config --strict

5. データディレクトリやログディレクトリの作成
   - デフォルトでは data/ と logs/ を使用します。自動作成されることが多いですが、権限等により作成できない場合があるので事前に作っておくと安心です。
   - logs/ にアプリ別ログファイル（例: logs/execution.log, logs/monitoring.log）が出力されます。

使い方
------
起動スクリプト（モジュールとして実行）:

- ExecutionEngine を起動
  - 本番（live）:
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - ペーパートレード（MockBroker を利用し専用 DB に記録）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 起動時に data/stop_requested.flag が存在すると起動を停止します。
  - 実行中は data/execution.pid に PID を書きます（pid ファイルパスは Settings でカスタマイズ可能）。

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き（秒、デフォルト 60）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - run_monitoring は常に本番用の sqlite_path を使用して監視ログを記録します（KABUSYS_ENV に依存しません）。
  - 停止は data/stop_requested.flag を作成することで行えます（監視ループが検出して終了します）。

- .env ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict オプションで警告を fail 扱いにできます

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
    - または環境変数 PAPER_TRADING_SQLITE_PATH を設定

重要な環境変数（抜粋）
--------------------
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（paper_trading 時に使用）
- OPENAI_API_KEY — OpenAI API キー（AI モジュール利用時）
- MONITOR_POLL_INTERVAL — monitoring のポーリング間隔（秒、デフォルト 60）
- LOG_LEVEL / LOG_DIR — ログ設定（logging_setup で使用）
- KILL_FLAG_CLEAR_ON_START — ExecutionEngine 起動時に kill.flag を自動クリアするか（"1" で有効、危険）

停止・Kill Switch の仕組み
-------------------------
- 実行系を外部から停止する方法:
  - data/stop_requested.flag を作成すると run_execution/run_monitoring のループが検知して安全に停止します（スクリプトによる終了手順）。
- Kill Switch:
  - 監視モジュールの判定で DRAWDOWN やポジション上限などの条件を満たした場合、KillSwitch が data/kill.flag を書き込みます。
  - ExecutionEngine は kill.flag の存在を検出して安全停止するロジックを持ちます（設定や起動フローにより自動クリア設定がある場合あり。設定を確認してください）。

ディレクトリ構成
----------------
以下は主要なソースツリー（src/kabusys）を抜粋したものです。実際のリポジトリルートはプロジェクトルートに pyproject.toml/.git がある想定です。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings クラス（.env 自動ロード機構含む）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前チェック CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI 連携）
    - regime_detector.py      — 市場レジーム判定（ETF + マクロニュース）
  - monitoring/
    - monitoring_db.py        — SQLite テーブル定義 / 永続化 API
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py        (通知用抽象化)
  - execution/
    - execution_engine.py     — メイン実行エンジン（EngineConfig など）
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - data/                      — 実行時に使用する data/ 配下（DB ファイル, flag, pid など）
  - utils/
    - logging_setup.py        — 共通ログ設定
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ

開発・運用上の注意点
--------------------
- 本リポジトリには本番口座と接続するコード（発注処理）を含みます。KABUSYS_ENV の設定を必ず確認してください（live は本当に発注します）。
- .env 等のシークレット情報は決して Git 等にコミットしないでください。
- OpenAI を使う機能は API キーと通話料金が必要です。開発中はモックやテスト用の差し替えを行ってください（ソース内でテストフックを用意している箇所があります）。
- monitoring / execution は stop flag / kill flag による安全停止・外部制御を前提としています。運用スクリプトや systemd ジョブを組む際はこれらのフラグ運用ルールを合わせてください。
- SQLite / DuckDB のファイルパスは Settings で上書き可能です。ペーパートレードは本番 DB と分離するよう設計されています（PAPER_TRADING_SQLITE_PATH を利用）。

貢献・拡張
----------
- 新しい戦略ロジックや AI モジュールの追加は research/ または ai/ 配下にモジュールを追加し、必要に応じて ExecutionEngine に組み込んでください。
- 設定項目を増やす場合は config_setup.py と config.py の双方を更新してください。
- テストを作成する際は Settings 自動ロードを抑制するために環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用できます。

補足
----
- ここに書かれているコマンドはプロジェクトルート（pyproject.toml/.git がある場所）で実行してください。
- 実際の依存パッケージや Python バージョンはプロジェクトの配布ファイル（pyproject.toml / requirements.txt）を参照してください。

以上。必要であれば README にサンプル .env のテンプレートや systemd ユニットの例、よくあるトラブルシュートを追加できます。どの情報を拡充しますか？