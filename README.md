README
=====

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤の骨組み（ライブラリと起動スクリプト群）です。
主な目的は以下を支援することです。

- 戦略のリサーチ（DuckDB を用いたファクター計算・特徴量解析）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- 発注実行エンジン（本番 / ペーパートレード分離）
- 監視・アラート（リソース、データ鮮度、注文/リスク監視）
- ニュースの LLM ベース評価（OpenAI を利用したセンチメント API 呼び出し）
- 運用補助ツール（.env ウィザード、設定検証、検証レポート生成 など）

設計上のポイント
- 環境変数 / .env による設定管理（config_setup.py で対話的に作成可能）
- Paper Trading（ペーパートレード）は本番 DB と分離（data/paper_trading.db）
- 監視は専用の SQLite（monitoring.db）へ永続化
- OpenAI を使った NLP 部分は API キー必要。失敗時はフェイルセーフ（スコア 0 等）で続行
- ログは stdout と日次ローテーションファイル出力（logs/）で管理

主な機能一覧
- コンポーネント / ユーティリティ
  - 環境設定: config.py, config_setup.py
  - 設定検証: validate_config.py
  - ログ設定: utils/logging_setup.py
  - プロセス優先度制御: utils/process_priority.py
- 実行系
  - run_execution.py: ExecutionEngine 起動（本番 / ペーパートレード切替）
  - run_monitoring.py: SystemMonitor のポーリングループ起動（監視）
- 監視
  - monitoring/monitoring_db.py: 監視用 DB スキーマ + 永続化 API
  - monitoring/system_monitor.py: リソース・データ鮮度・実プロセス監視
  - monitoring/trade_monitor.py, risk_monitor.py, monitoring_engine.py, kill_switch.py, alert_manager.py（監視チェーン）
- ポートフォリオ構築
  - portfolio/portfolio_builder.py: 候補選定・重み計算（等金額・スコア加重）
  - portfolio/position_sizing.py: 株数決定・単元丸め・aggregate cap
  - portfolio/risk_adjustment.py: セクター上限・レジーム乗数
- リサーチ
  - research/factor_research.py: Momentum/Value/Volatility 等のファクター計算（DuckDB）
  - research/feature_exploration.py: 将来リターン・IC・統計要約
- AI（OpenAI）
  - ai/news_nlp.py: ニュースを LLM でスコアリングし ai_scores に書き込み
  - ai/regime_detector.py: ETF MA + マクロニュースで市場レジーム判定
- ツール
  - tools/paper_verification_report.py: ペーパートレード DB の検証レポート生成

セットアップ手順（開発/ローカル）
--------------------------------
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <project-root>

2. Python 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   - 必要パッケージ（参考）
     - duckdb
     - psutil
     - openai
     - PyYAML（validate_config の YAML 検証を有効にする場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

4. 初期設定 (.env) を作成
   - 対話式:
     - python -m kabusys.config_setup
   - もしくは .env.template / .env.example を参考に .env を作成してプロジェクトルートに置く

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告を FAIL 扱いにするには --strict を付与

基本的な環境変数（主なもの）
------------------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能を使う場合に必要)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db) — KABUSYS_ENV=paper_trading 時に使用
- KABUSYS_ENV (development | paper_trading | live; デフォルト: development)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL; デフォルト: INFO)
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (任意、アラート用)
- KILL_FLAG_CLEAR_ON_START (0/1; デフォルト: 0)
- PAPER_FILL_MODE (ペーパートレード時の約定挙動: instant | partial | never | reject; デフォルト: instant)
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング間隔秒。デフォルト 60)
- LOG_DIR (ログ出力先ディレクトリの上書き。デフォルト logs/)

使い方（主なコマンド）
--------------------

- 環境ウィザード（.env を作る）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視ループ起動（SystemMonitor）
  - デフォルト: ポーリング 60 秒（MONITOR_POLL_INTERVAL で変更可）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は project_root/data/stop_requested.flag を検知すると終了します

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に書き込みます
  - 起動中に project_root/data/stop_requested.flag が作られるとエンジンを停止します
  - Execution の PID は data/execution.pid（デフォルト）に保存されます

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI 機能（プログラムから呼び出す）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

停止 / Kill スイッチ
-------------------
- ExecutionEngine を外部から停止させるフロー:
  - KillSwitch（kabusys.monitoring.kill_switch）が監視条件に応じて data/kill.flag に理由を書き込むと ExecutionEngine は停止シグナルを検知して安全停止します
  - 管理者が手動で停止したい場合は project_root/data/stop_requested.flag を作成すると run_monitoring/run_execution のループが検知して終了します
  - kill.flag は Settings.kill_flag_clear_on_start が "1" の場合、起動時に自動でクリアされる設定が可能（本番では 0 を推奨）

ログ
----
- 共通ログ設定を utils/logging_setup.setup_logging から行います
- デフォルトは logs/<app_name>.log に日次ローテーションで出力（30日分保持）
- コンソールへは stdout にも出力されます

ディレクトリ構成（主要ファイル）
--------------------------------
- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / Settings 管理
  - config_setup.py                — .env 対話ウィザード
  - validate_config.py             — 設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート
  - ai/
    - news_nlp.py                   — ニュース NLP スコアリング
    - regime_detector.py            — 市場レジーム判定
  - portfolio/
    - portfolio_builder.py          — 候補選定・重み計算
    - position_sizing.py            — 株数決定・スケーリング
    - risk_adjustment.py            — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py            — ファクター計算（momentum/value/vol）
    - feature_exploration.py         — 将来リターン・IC 等
  - monitoring/
    - monitoring_db.py              — SQLite schema + DB ラッパー
    - system_monitor.py             — システム・データ鮮度監視
    - risk_monitor.py               — ドローダウン / ポジション上限監視
    - kill_switch.py                — kill.flag の生成/管理
    - monitoring_engine.py          — 各 Monitor を束ねる
    - trade_monitor.py              — 注文滞留や約定異常の監視（存在）
    - alert_manager.py              — LINE 等への通知（実装想定）
  - utils/
    - logging_setup.py              — ログ設定ユーティリティ
    - process_priority.py           — 優先度 / affinity 設定ユーティリティ
  - data/                            — デフォルト DB / フラグ / pid を配置する想定ディレクトリ
    - monitoring.db (default SQLite)
    - paper_trading.db
    - kabusys.duckdb
    - kill.flag, stop_requested.flag, execution.pid

注意事項 / 運用上のヒント
------------------------
- 本番環境（KABUSYS_ENV=live）では kill/stop フラグの扱いに注意してください。KILL_FLAG_CLEAR_ON_START を 1 にすると起動時に自動クリアされるため誤設定は危険です（デフォルト 0 推奨）。
- run_monitoring は MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。不正な値が渡された場合はデフォルトにフォールバックします。
- Paper Trading を行う際には PAPER_TRADING_SQLITE_PATH を明示するか KABUSYS_ENV=paper_trading を設定してください。本番 DB と完全に分離されます。
- OpenAI を用いる機能は API コストとレート制限に注意してください。API エラー/制限にはエクスポネンシャルバックオフ処理を実装していますが、運用計画を作成してください。
- DuckDB / SQLite のファイルはプロジェクト外部へバックアップや適切なパーミッションで配置してください。

貢献・拡張案
-------------
- monitoring/alert_manager の LINE 実装強化（リトライ・テンプレート）
- orders / broker クライアントの充実（kabuステーション以外のブローカー対応）
- リスク管理ルールの追加（ETF/オプション等の拡張）
- テストカバレッジの拡充（特に AI 周りの HTTP 呼び出しのモック化）

ライセンス
----------
プロジェクトのライセンスはリポジトリ側の LICENSE を参照してください。

お問い合わせ
------------
実装上の質問・バグ報告はリポジトリの issue にお願いします。README に書かれていない内部仕様については該当モジュールの docstring を参照してください。