README
======

概要
----
KabuSys は日本株向けの自動売買・研究・監視を行うための軽量な Python ライブラリ／アプリケーション群です。本リポジトリは以下の機能群を提供します。

- 実行エンジン（ExecutionEngine）: 注文送信、リスク管理、オーダー管理
- 監視サブシステム: システム稼働監視、注文ログ監視、リスク監視、Kill Switch
- 研究モジュール: ファクター計算・特徴量解析・IC 計算
- ポートフォリオ構築: 候補選定・重み計算・ポジションサイズ決定・セクター制御
- AI 周り: ニュースの LLM ベースセンチメント評価（OpenAI）とレジーム判定
- ユーティリティ: 環境設定ウィザード、設定検証、ログ設定など
- Tools: ペーパートレード検証レポート生成などのスクリプト

設計方針のポイント
- DB は DuckDB（分析）と SQLite（監視・発注ログ）を併用
- 本番とペーパートレードは SQLite ファイルを分離（PAPER_TRADING_SQLITE_PATH）
- .env ベースで設定管理。config_setup.py による対話的生成と validate_config による事前検証を推奨
- OpenAI を用いる機能は API キーで保護。API エラーはフェイルセーフ動作（ゼロフォールバック等）

主な機能一覧
----------------
- 実行 / 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV による paper_trading 切替）
  - run_monitoring.py: SystemMonitor を周期ポーリングして system_status 等を記録
- 設定関連
  - config_setup.py: .env を対話式に生成 / 更新
  - validate_config.py: .env および config/*.yaml の事前チェック
  - config.py: 環境変数 / 設定読み取りユーティリティ
- 監視
  - monitoring/monitoring_db.py: SQLite スキーマ初期化と読み書き API
  - monitoring/system_monitor.py, trade_monitor.py, risk_monitor.py, monitoring_engine.py, kill_switch.py, alert_manager.py 等
- ポートフォリオ
  - portfolio.portfolio_builder: 候補選定・等重/スコア重み算出
  - portfolio.position_sizing: 株数算出（単元丸め、最大ポジション・利用率等）
  - portfolio.risk_adjustment: セクター上限・レジーム乗数
- 研究（Research）
  - research.factor_research: Momentum / Volatility / Value 等のファクター計算（DuckDB 経由）
  - research.feature_exploration: 将来リターン計算、IC、統計サマリ
- AI
  - ai.news_nlp.score_news: raw_news を LLM でスコア化して ai_scores に書込
  - ai.regime_detector.score_regime: ETF MA とマクロニュースの LLM 評価を合成して market_regime に書込
- ツール
  - tools.paper_verification_report: ペーパートレード結果を検証して判定（PASS/FAIL）を出力

セットアップ手順
----------------
1. Python 環境の作成（推奨: 仮想環境）
   - python3 -m venv .venv
   - source .venv/bin/activate

2. 必要パッケージのインストール（例）
   - pip install duckdb psutil openai
   - validate_config の一部機能（config YAML の検証）には PyYAML が必要:
     - pip install pyyaml

   （requirements.txt がない場合は上記を適宜インストールしてください。SQLite は標準ライブラリで使用可。）

3. .env の作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - 手動で作る場合は .env.example を参考にプロジェクトルートに .env を配置

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告を厳密扱いにする場合:
     - python -m kabusys.validate_config --strict

5. データディレクトリの確認
   - デフォルトの DB / PID / フラグファイル等:
     - DuckDB: data/kabusys.duckdb
     - SQLite(監視): data/monitoring.db
     - PaperTrade SQLite: data/paper_trading.db
     - PID ファイル: data/execution.pid
     - Kill flag: data/kill.flag
     - Stop flag: data/stop_requested.flag
   - 必要に応じて環境変数で上書き（下記参照）

主な環境変数
----------------
（主なものを抜粋。詳しくは kabusys.config.Settings を参照）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (OpenAI 呼び出し時に使用)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
  - paper_trading: MockBroker を使い paper_trading.db に書き込む
- PAPER_FILL_MODE (instant | partial | never | reject) — ペーパートレードの約定モード
- PAPER_TRADING_SQLITE_PATH (デフォルト data/paper_trading.db)
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- SQLITE_PATH (デフォルト data/monitoring.db)
- LOG_LEVEL (DEBUG/INFO/...)
- LOG_DIR (デフォルト logs/)
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング間隔秒。デフォルト 60)
- KILL_FLAG_CLEAR_ON_START (0/1) — 起動時に kill.flag を自動クリアするか（本番は 0 推奨）

使い方
------

設定作成と検証
- .env を作成:
  - python -m kabusys.config_setup
- 設定チェック:
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いで exit(1)

実行エンジン起動（Execution）
- 通常起動:
  - python -m kabusys.run_execution
- KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、データは PAPER_TRADING_SQLITE_PATH に記録されます:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

監視サブシステム起動（Monitoring）
- python -m kabusys.run_monitoring
- ポーリング間隔を環境変数で上書き:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

ペーパートレード検証レポート
- python -m kabusys.tools.paper_verification_report
- 日付フィルタ:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB を指定:
  - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

AI / レジーム判定・ニューススコア
- OpenAI API キーが必要（環境変数 OPENAI_API_KEY または引数で指定）
- ニューススコア生成（プログラム的に呼ぶ場合）:
  - from kabusys.ai import score_news
  - score_news(duckdb_conn, target_date, api_key="...")
- レジーム判定は ai.regime_detector.score_regime を使えます（同様に API キー要）

ログ
- ロギングは logs/<app_name>.log に日次ローテーションで出力（デフォルト 30 日保持）
- コンソールは stdout に出力されます

停止 / Kill Switch / フラグ
- 実行中のプロセスを停止させるにはフラグファイルを使用します:
  - data/stop_requested.flag: run_monitoring / run_execution の監視ループが存在を検知すると停止します
  - data/kill.flag: KillSwitch が書き込むことで ExecutionEngine を停止するトリガーになります（存在を確認して停止）
- kill.flag を手動で削除するか、KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアされることがあります（本番では注意）

ディレクトリ構成
----------------
リポジトリの主要なファイル構成（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py             — ニュースを OpenAI でスコア化
    - regime_detector.py      — マーケットレジーム判定
  - monitoring/
    - monitoring_db.py        — SQLite スキーマ・永続化 API
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - utils/
    - __init__.py
    - logging_setup.py        — 統一ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定

実運用上の注意
----------------
- 本番環境（KABUSYS_ENV=live）では環境変数の取り扱い・LINE 通知設定などを十分に確認してください。validate_config はいくつかのガードを提供しますが、設定ミスは実資金の損失につながります。
- OpenAI の呼び出しはレイテンシや料金リスクがあるため、API エラー時のフォールバック動作（ゼロスコア等）を想定してください。
- データベースファイル（特に本番用 SQLite）はバックアップや排他アクセスに注意してください。DuckDB は分析用で大規模読み込みを想定しています。
- ログディレクトリ・データディレクトリのパーミッションや容量を監視してください。ログのローテーションはデフォルトで 30 日分を保持します。

貢献 / 開発
-------------
- コードはモジュールごとに分かれており、ユニットテストを追加しやすい構成になっています。主要な関数は副作用を避けるよう設計されています（例: research / portfolio の純粋関数群）。
- 新しい外部依存を追加する場合は README および setup スクリプト／requirements に反映してください。

免責
----
本プロジェクトは教育・研究用途を想定したサンプル実装です。実際の資金を扱う前に十分なレビューとテストを行ってください。運用に伴う損失について作者は責任を負いません。

---
必要に応じて、README に含める具体的な実行例や環境変数の詳細（.env.example 相当）を追加しますか？