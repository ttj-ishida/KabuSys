KabuSys — 日本株自動売買システム (README)
======================================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした Python パッケージです。本リポジトリには取引実行エンジン、監視（モニタリング）コンポーネント、ポートフォリオ構築ロジック、研究（ファクター計算）モジュール、AI を利用したニュース NLP / レジーム判定などのユーティリティが含まれます。

主な設計方針:
- DuckDB / SQLite によるローカルデータ参照・永続化
- Paper Trading（ペーパートレード）と Live（本番）を環境変数で切替
- OpenAI を用いたニュースセンチメント等の拡張モジュール（API キー必須）
- 運用を想定したログ・プロセス優先度設定・Kill Switch 機能

機能一覧
--------
- 実行エンジン起動スクリプト（run_execution）:
  - KABUSYS_ENV に応じて実ブローカー／MockBroker を利用
  - Paper Trading 時は data/paper_trading.db に完全分離して記録
- 監視（Monitoring）:
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - system_status / trade_logs / risk_logs / dashboard / positions テーブルを提供
  - kill.flag による ExecutionEngine 強制停止（Kill Switch）
- ポートフォリオ構築:
  - 候補選定、重み付け（等金額・スコア加重）、ポジションサイズ計算、セクターキャップ、レジーム乗数
- 研究（Research）:
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算・IC（Information Coefficient）等の統計ユーティリティ
- AI（OpenAI）:
  - ニュース記事のセンチメントを LLM で評価して ai_scores に書き込み
  - マクロニュース + ETF ma200 乖離を使った市場レジーム判定
- ツール:
  - 設定ウィザード（config_setup）：対話式で .env を生成
  - 設定検証（validate_config）：起動前チェック（必須 env 等）
  - Paper Trading 検証レポート生成ツール（paper_verification_report）

前提・依存
----------
推奨環境:
- Python 3.10 以上（typing の | 記法等を使用）
- 推奨パッケージ（代表例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config/*.yaml の検証を行う場合）
- SQLite（標準ライブラリ）利用
- ネットワークアクセス（OpenAI 使用時）

セットアップ手順
----------------
1. リポジトリをクローン / 展開
2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai PyYAML
   - ※requirements.txt がない場合は上記パッケージを個別に導入してください
4. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - あるいは .env を手動作成（.env.example を参照）
   - 自動ロード: プロジェクトルートにある .env / .env.local は kabusys.config により起動時自動読込されます。
     - 自動ロードを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告も失敗にしたい場合: python -m kabusys.validate_config --strict

主要な環境変数（抜粋）
----------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須） — kabuステーション API 用パスワード
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード DB、デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI モジュール使用時に必要）
- LOG_LEVEL（例: INFO）
- MONITOR_POLL_INTERVAL（監視ループの秒間隔、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（本番での kill.flag 自動クリアに注意）

使い方
------
基本コマンド（パッケージルートから実行）:

- 実行エンジン（ExecutionEngine）起動:
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し data/paper_trading.db に記録
  - 実行中に data/stop_requested.flag を作成すると安全に停止します
  - ExecutionEngine は pid ファイル（デフォルト data/execution.pid）を生成します

- 監視（Monitoring）起動:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（秒）
  - 監視は常に本番 sqlite_path（SQLITE_PATH）を使用します（設定にかかわらず）

- 設定ウィザード（.env 生成）:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いで exit(1)

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を指定する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI モジュール（プログラム内 API 呼び出し）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")  # api_key は省略可（環境変数 OPENAI_API_KEY を参照）
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

運用上の注意
------------
- Paper Trading:
  - KABUSYS_ENV=paper_trading の場合、発注はモック経由で行われ、DB は data/paper_trading.db に記録されます（本番 DB と完全分離）。
- Kill Switch:
  - KillSwitch は data/kill.flag を書き込むことで ExecutionEngine 停止を促します。ファイルの自動クリアを有効にする KILL_FLAG_CLEAR_ON_START=1 は本番環境では推奨されません。
- ロギング:
  - ログはデフォルト logs/<app_name>.log に日次ローテーションで保存されます（30日分）。
  - 権限やディレクトリ作成に失敗するとコンソール出力のみになります。
- プロセス優先度:
  - run_execution / run_monitoring 起動時に set_process_priority("high") を試みます。権限不足等で失敗する場合は警告が出ます。

ディレクトリ構成
----------------
（主要ファイルを抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                        — 環境変数・設定管理（.env 自動読み込みロジック）
    - config_setup.py                  — .env 対話ウィザード
    - validate_config.py               — 起動前の設定検証ツール
    - run_execution.py                 — ExecutionEngine 起動スクリプト
    - run_monitoring.py                — Monitoring 起動スクリプト
    - tools/
      - paper_verification_report.py   — Paper Trading 検証レポート生成
    - execution/                        — 実行エンジン関連（broker, engine, order_manager など）
    - monitoring/
      - monitoring_db.py               — SQLite の永続化層（テーブル作成・CRUD ラッパ）
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
      - news_nlp.py                     — ニュース NLP（OpenAI）
      - regime_detector.py              — 市場レジーム判定（OpenAI）
    - utils/
      - logging_setup.py                — ログ設定ユーティリティ
      - process_priority.py             — プロセス優先度 / CPU affinity
    - data/                             — データファイル（例: monitoring.db, paper_trading.db 等）

付記 / 開発者向けメモ
-------------------
- DuckDB 接続を受け取る関数は SQL と Python を組み合わせて高速に集計する設計です。テーブル名（prices_daily / raw_financials / raw_news 等）が前提になります。
- モジュールは「DB 参照のみ」や「純粋関数」などの責務分離を意識して作られています（テストしやすい設計）。
- OpenAI 呼び出しは再試行（指数バックオフ）やレスポンスの厳密なバリデーションを行い、API 側の不調時にはフェイルセーフで処理を続行するよう設計されています。
- config/ 以下の YAML は生成スクリプトや検証ツールと併用することで、本番運用に必要な設定を管理します（PyYAML があると validate_config で内容検証が行われます）。

問題点・拡張案（参考）
-------------------
- 単元株（lot_size）は現状固定で 100 を想定。銘柄別の lot を持たせるとより正確。
- position_sizing の価格欠損時のフォールバックロジック改善（前日終値等）。
- AI モジュールでのモデル / プロンプト管理を外部化すると運用しやすくなります。

ライセンス・その他
------------------
- 本 README はコードからの推測に基づくドキュメントです。実際の運用時は .env.example や config/*.yaml を確認してください。

お問い合わせ
------------
実装上の不明点・追加のドキュメント化が必要な箇所があれば指示ください。README の改善やコマンド例の追加、API ドキュメント化を対応します。