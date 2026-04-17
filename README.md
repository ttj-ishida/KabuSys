KabuSys — 日本株自動売買システム (README)
=======================================

概要
----
KabuSys は日本株向けの自動売買／研究プラットフォーム向けのライブラリ群です。  
主な目的は次のとおりです。

- 戦略のファクター計算・特徴量解析（research）
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- 発注エンジン（ExecutionEngine）と注文管理（execution） — 本番／ペーパートレード対応
- 監視（Monitoring）・アラート（LINE）・Kill Switch による安全停止
- Paper Trading の検証レポート生成ツール
- OpenAI を用いたニュース NLP（センチメント評価）とレジーム判定

重要な設計方針（抜粋）
- 本番／ペーパートレード切替（KABUSYS_ENV）
- DuckDB を分析用 DB として利用、SQLite を監視／注文ログ用に利用
- .env による設定管理・対話的ウィザード・起動前検証用 CLI を提供
- OpenAI 呼び出しはフェイルセーフ（失敗時はスコア 0 等で継続）

主な機能
---------
- 設定管理
  - .env 自動読み込み・対話式生成（kabusys.config_setup）
  - 起動前検証 CLI（kabusys.validate_config）
- 実行系
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番 / paper_trading 切替（ペーパートレードは専用 SQLite に記録）
- 監視系
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - 監視データの永続化（SQLite / monitoring_db）
  - Kill Switch（大幅ドローダウン等で data/kill.flag を書き込み停止）
  - LINE 通知（AlertManager）
- 研究・ポートフォリオ
  - ファクター計算（momentum / volatility / value）
  - 特徴量解析（forward returns, IC, 統計サマリー）
  - ポートフォリオ構築（候補選定・重み算出・ポジションサイズ算出）
- AI（OpenAI）
  - ニュースセンチメント（news_nlp.score_news）
  - 市場レジーム判定（regime_detector.score_regime）
- ツール
  - Paper Trading の検証レポート生成（tools/paper_verification_report.py）

セットアップ手順
----------------

1. リポジトリをクローン / ソースを入手
   - この README はパッケージのソースが src/kabusys 配下にあることを前提としています。

2. Python 環境（推奨: venv）を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必要最低限:
     - duckdb
     - psutil
     - requests
     - openai（AI 機能を使う場合）
     - PyYAML（config 検証で YAML をチェックしたい場合）
   - 例:
     - pip install duckdb psutil requests openai PyYAML

4. .env を用意（対話式ウィザード推奨）
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に手動で作成
   - 重要な環境変数（最低限設定が必要）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - OPENAI_API_KEY（AI 機能を利用する場合）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知を有効にする場合）

   - 例（.env の一部）
     JQUANTS_REFRESH_TOKEN=your_token_here
     KABU_API_PASSWORD=your_kabu_password_here
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     OPENAI_API_KEY=sk-...

5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

6. データディレクトリの作成
   - デフォルトでは data/ 以下に DB・PID・フラグが作成されます。適宜ディレクトリ作成を行ってください。
   - 例: mkdir -p data

使い方
------

起動・停止の概要
- ExecutionEngine（注文実行）起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使い、PAPER_TRADING_SQLITE_PATH に記録されます。
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
  - 実行中は data/execution.pid に PID を書きます。
  - 停止: data/stop_requested.flag を作成すると次のループ間隔でエンジンが停止します（run_execution は flag を検出して engine.stop() します）。
  - 外部から強制停止（Kill Switch）: data/kill.flag が監視により書き込まれると ExecutionEngine は停止シグナルを受け取ります（KillSwitch を使用）。Kill flag は明示的にクリアできます（KillSwitch.clear()／手動でファイル削除）。

- Monitoring（監視）起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
    例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は Settings.sqlite_path（デフォルト data/monitoring.db）を本番 DB として使用します（KABUSYS_ENV に依らず同一パスを使います）。
  - run_monitoring は data/stop_requested.flag を検知するとループを終了します。

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで SQLite ファイルを指定できます（環境変数 PAPER_TRADING_SQLITE_PATH より優先）。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

主な環境変数（抜粋）
- KABUSYS_ENV: development | paper_trading | live（動作モード）
  - paper_trading: 発注は MockBroker、データは PAPER_TRADING_SQLITE_PATH に保存
  - live: 実際に発注されます（注意して使用）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- DUCKDB_PATH: DuckDB 分析 DB（デフォルト: data/kabusys.duckdb）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアする（デフォルト 0。production では 0 推奨）

フラグ / PID / 停止関連ファイル
- data/execution.pid — ExecutionEngine の PID（run_execution により管理）
- data/stop_requested.flag — run_monitoring / run_execution が監視する停止フラグ（存在したら終了）
- data/kill.flag — KillSwitch が書き込む停止フラグ（ExecutionEngine 停止のトリガー）
- 注意: KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では推奨されません）。

ディレクトリ構成（主なファイル）
--------------------------------
以下は src/kabusys 配下の主要モジュールと役割の要約です。

- src/kabusys/
  - __init__.py                  — パッケージ定義、__version__
  - config.py                    — Settings / .env 自動読み込み・環境変数管理
  - config_setup.py              — .env を対話式に生成するウィザード
  - validate_config.py           — 起動前の設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor ポーリングループ起動スクリプト

  - ai/
    - news_nlp.py                — ニュースを OpenAI で評価して ai_scores に書き込む
    - regime_detector.py         — マクロ + ma200 で市場レジームを判定
    - __init__.py

  - monitoring/
    - monitoring_db.py           — SQLite テーブル初期化・永続化 API
    - system_monitor.py          — CPU/メモリ/ディスク・データ鮮度・PID チェック
    - trade_monitor.py           — 滞留注文・約定異常のチェック
    - risk_monitor.py            — ドローダウン・ポジション上限チェック
    - alert_manager.py           — LINE 通知（クールダウン管理）
    - kill_switch.py             — Kill Switch（kill.flag の書込み）
    - monitoring_engine.py       — 各 Monitor を束ねポーリングするエンジン

  - portfolio/
    - portfolio_builder.py       — 候補選定・重み計算（等配分・スコア重み）
    - position_sizing.py         — 株数決定・スケールダウン・lot 単位丸め
    - risk_adjustment.py         — セクターキャップ、レジーム乗数
    - __init__.py

  - research/
    - factor_research.py         — Momentum / Volatility / Value 等のファクター計算（DuckDB）
    - feature_exploration.py     — 将来リターン / IC / 統計サマリー
    - __init__.py

  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
    - __init__.py

  - utils/
    - process_priority.py        — プロセス優先度 / CPU affinity 設定ユーティリティ
    - __init__.py

補足・運用上の注意
-----------------
- データ鮮度: SystemMonitor は DuckDB の prices_daily の最終日付を参照し、3 日以内を許容します（FRESHNESS_DAYS = 3）。週末や祝日を考慮していますが、異常が続く場合はアラートが発生します。
- 監視 DB のマイグレーション: init_monitoring_db は必要に応じてカラム追加（peak_value / latency_ms）を行います。
- OpenAI 呼び出し:
  - API キー（OPENAI_API_KEY）が必要です。失敗時はフォールバック動作（0.0 等）で継続する設計です。
  - 大量呼び出し時はレート制限に注意し、retry/backoff ロジックが組み込まれています。
- psutil によるプロセス優先度設定は OS に依存します。権限不足により設定に失敗する場合は警告が出ますが、処理自体は継続します。
- production 環境では KABUSYS_ENV=live、KILL_FLAG_CLEAR_ON_START=0 を強く推奨します。kill.flag を自動クリアすると危険です。

よく使うコマンドまとめ
---------------------
- .env 作成（ウィザード）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジン起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

ライセンス・貢献
----------------
- 本パッケージのライセンス情報・貢献手順はリポジトリのルートにある LICENSE / CONTRIBUTING を参照してください（存在する場合）。

問い合わせ・バグ報告
-------------------
- 不具合・改善提案は issue を作成してください。運用上の重要点（特に本番発注に関わる設定）については十分注意して取り扱ってください。

以上が KabuSys の概要・セットアップ・使用方法のまとめです。必要であれば、特定モジュール（例: position_sizing のパラメータ説明や news_nlp の API レスポンス仕様）の詳細ドキュメントも作成します。どの部分を深掘りしますか？