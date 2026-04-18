README
=====

概要
----
KabuSys は日本株向けの自動売買・調査基盤ライブラリです。本リポジトリは以下のような機能群から構成されています。

- 実行エンジン（ExecutionEngine）と監視（Monitoring）用の起動スクリプト
- 注文管理・リスク管理・再整合（reconciler）等の Execution コンポーネント
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ算出）
- ファクター計算・研究用ユーティリティ（DuckDB ベース）
- ニュース NLP / レジーム判定（OpenAI を利用する LLM 統合）
- 監視ログの永続化（SQLite ベース）と監視ループ
- ペーパートレード用検証・レポート生成ツール

機能一覧
--------
主な機能（抜粋）:

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動。KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 用 DB に記録。
  - run_monitoring.py: SystemMonitor をポーリングして監視ログを記録。MONITOR_POLL_INTERVAL で間隔変更可。
- 設定管理・CLI
  - config_setup.py: .env を対話式に生成/更新するウィザード。
  - validate_config.py: .env や config/*.yaml の簡易検証 CLI。
- 監視
  - monitoring_engine.py: System / Trade / Risk Monitor を束ねるポーリングエンジン。
  - monitoring_db.py: SQLite に監視ログを永続化するモジュール（テーブルの自動作成・マイグレーション含む）。
  - kill_switch.py: 条件に応じて data/kill.flag を書き込み ExecutionEngine に停止シグナルを送る仕組み。
- ポートフォリオ構築
  - portfolio_builder, position_sizing, risk_adjustment: 候補抽出、重み算出、株数決定、セクター制限など。
- 研究・ファクター計算
  - researchモジュール: DuckDB を用いたモメンタム/バリュー/ボラティリティ等のファクター計算、IC や統計要約。
- AI 統合
  - ai/news_nlp.py: raw_news を集約して OpenAI に問い合わせ、銘柄ごとのセンチメント（ai_score）を ai_scores テーブルに保存。
  - ai/regime_detector.py: ETF の MA 乖離とマクロニュースの LLM センチメントを合成して市場レジームを判定、market_regime テーブルへ保存。
- ツール
  - tools/paper_verification_report.py: ペーパートレード DB を集計して検証レポートを生成。

セットアップ手順
--------------
1. リポジトリルートで仮想環境を作成・有効化（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 主要依存（例）:
     - duckdb, psutil, openai, PyYAML（validate_config の YAML 検証に必要）
   ※ requirements.txt が未提供の場合は上記パッケージを個別にインストールしてください。

3. .env の準備
   - 対話式で作成:
     - python -m kabusys.config_setup
   - または手動でルートに .env を作成（.env.example を参考にすることを推奨）。
   - .env に含める代表的な環境変数は下記「環境変数一覧」を参照。

4. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）になります。

5. データ・ログディレクトリ
   - デフォルトでは data/ と logs/ を使用します。必要に応じて権限やディレクトリ作成を行ってください。

環境変数一覧（主なもの）
-----------------------
以下はコードから読み取れる代表的な環境変数とデフォルト値/説明です。

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (OpenAI を使う機能で必要)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - paper_trading: Execution は MockBrokerClient を使用し、data/paper_trading.db を使用
- PAPER_FILL_MODE (paper_trading 時の約定モード, default: "instant") 値: instant|partial|never|reject
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- LOG_LEVEL (デフォルト: INFO)
- LOG_DIR (デフォルト: logs/)
- LINE_CHANNEL_ACCESS_TOKEN（任意、アラート送信に使用）
- LINE_USER_ID（任意、アラート送信先）
- PID_FILE_PATH (デフォルト: data/execution.pid)
- KILL_FLAG_PATH (デフォルト: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (0/1, デフォルト: 0)
- MONITOR_POLL_INTERVAL (run_monitoring.py のポーリング間隔秒。デフォルト: 60)

使い方
------
基本的な実行例:

- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定してペーパートレードモードで起動すると、実口座との操作は行わず data/paper_trading.db に記録されます。

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で変更できます（例: MONITOR_POLL_INTERVAL=30）。

- 設定ウィザード（.env 生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 系のバッチ（例）
  - ai.news_nlp.score_news や ai.regime_detector.score_regime はプログラムから呼び出すことができます（OpenAI キー必須）。
  - 例（Python）:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key="...")

停止・Kill Switch
- 実行制御用のフラグ:
  - data/stop_requested.flag: run_monitoring/run_execution などの起動スクリプトが存在を検知して安全に停止します。
  - data/kill.flag: KillSwitch により書き込まれ、ExecutionEngine への停止要求として扱われます。
- kill.flag は起動時に自動でクリアされない設定（KILL_FLAG_CLEAR_ON_START=1 にするとクリア可。注意: 本番では推奨されません）。

ログ
----
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力されます（30日分保持）。
- コンソールにも stdout 経由で出力されます（setup_logging 関数）。

ディレクトリ構成
----------------
（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                  — 環境変数/設定管理
    - config_setup.py            — .env 対話式ウィザード
    - validate_config.py         — 設定検証 CLI
    - run_execution.py           — ExecutionEngine 起動スクリプト
    - run_monitoring.py          — SystemMonitor 起動スクリプト
    - tools/
      - paper_verification_report.py — ペーパートレード検証レポート
    - ai/
      - news_nlp.py              — ニュース NLP（OpenAI 統合）
      - regime_detector.py       — 市場レジーム判定（LLM + MA）
    - monitoring/
      - monitoring_db.py         — SQLite 永続化層
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py         — （存在する想定）
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py         — （存在する想定）
    - execution/                 — Execution 関連（broker_factory 等）
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - utils/
      - logging_setup.py
      - process_priority.py
      - __init__.py
    - data/                      — 実行時に利用する DB / flag / pid 等（既定: data/*.db, data/*.flag）
    - logs/                      — ログ（既定: logs/*.log）

補足・運用上の注意
-----------------
- KABUSYS_ENV の値が live の場合は本番動作となるため、JQUANTS_REFRESH_TOKEN や KABU_API_PASSWORD などの機密情報の管理、Kill Switch や LINE 通知設定を必ず確認してください。
- OpenAI を利用する機能は API キーが必要です。課金やレートリミットに注意してください。エラー時はフェイルセーフ（スコア 0.0 等）で継続する設計です。
- DuckDB / SQLite のパスは .env または環境変数で指定できます。監視用 DB は environment に依らず production sqlite_path を参照する箇所があるため、実行前に設定を確認してください。
- ローカル実行時は .env を絶対にリポジトリにコミットしないでください（config_setup の冒頭コメント参照）。

ライセンス / バージョン
-----------------------
パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）

---
何か追加で README に含めたい内容（例: 実行例ログ、設定例 .env、詳細な API ドキュメントなど）があれば教えてください。必要に応じて追記・調整します。