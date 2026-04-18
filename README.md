README
======

概要
----
KabuSys は日本株の自動売買および研究用ツール群をまとめた Python パッケージです。本コードベースは次の主要機能を含みます:

- 実行エンジン（ExecutionEngine）の起動スクリプトとペーパートレード分離
- システム監視（監視ログの永続化・アラート・Kill Switch）
- ポートフォリオ構築（候補選定・重み付け・株数算出）
- ファクター計算・特徴量探索（DuckDB を用いたリサーチ用モジュール）
- ニュース NLP（OpenAI を用いたセンチメント集約）
- 開発用ユーティリティ（.env ウィザード、設定検証、検証レポート等）
- ロギング／プロセス優先度設定ユーティリティ

主な設計方針:
- 実トレード（live）とペーパートレード（paper_trading）を明確に分離
- DuckDB を分析用 DB、SQLite を監視・注文ログ用に使用
- 外部 API 呼び出し（OpenAI 等）は明示的にキーを受け取るか環境変数で設定
- ルックアヘッドバイアスを防ぐ実装（date/datetime の取り扱いに注意）

特徴一覧
--------
- 起動スクリプト
  - python -m kabusys.run_execution : ExecutionEngine を起動（KABUSYS_ENV により paper/live 動作が切替）
  - python -m kabusys.run_monitoring : SystemMonitor のポーリングループを起動
- 設定管理
  - .env 自動ロード（プロジェクトルート検出）および対話式ウィザード（config_setup）
  - validate_config: .env と config/*.yaml の事前チェック
- 監視
  - system_monitor: CPU/メモリ/Disk、プロセス生存、データ鮮度を監視し SQLite に記録
  - trade_monitor / risk_monitor: 注文・ドローダウン・ポジション上限を監視（risk_monitor はダッシュボード更新・アラート登録）
  - KillSwitch: 条件に応じて data/kill.flag を書き込み、ExecutionEngine 停止をトリガー
  - monitoring_engine: 複数モニタを束ねて定期実行
- ポートフォリオ
  - 候補選定 (select_candidates)、等金額/スコア重み (calc_equal_weights / calc_score_weights)
  - ポジションサイズ算出 (calc_position_sizes)、セクターキャップ適用 (apply_sector_cap)、レジーム乗数 (calc_regime_multiplier)
- リサーチ
  - ファクター計算（momentum, volatility, value）: duckdb 経由で prices_daily / raw_financials を参照
  - forward returns, IC 計算, 統計サマリ等
- AI（OpenAI）
  - news_nlp.score_news: raw_news を集約して LLM に投げ、ai_scores テーブルへ書き込み
  - regime_detector.score_regime: ETF とマクロニュースを使って市場レジーム判定し market_regime に書き込み
- ツール
  - paper_verification_report: ペーパートレード DB を解析して PASS/FAIL レポートを生成

前提条件（推奨）
----------------
- Python 3.9+
- 必要パッケージ（pip インストール）
  - duckdb
  - psutil
  - openai
  - PyYAML（validate_config の YAML 検証を有効化する場合）
- SQLite（Python 標準モジュールで利用可能）
- 環境変数、.env の設定（下記参照）

セットアップ手順
----------------
1. リポジトリをクローンしてパッケージインストール（開発環境）
   - python -m venv .venv
   - source .venv/bin/activate
   - pip install -r requirements.txt
     （requirements.txt がない場合は個別に duckdb, psutil, openai をインストール）

2. 初期 .env を作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - ウィザード完了後、生成された .env を確認してください（.env は Git にコミットしないでください）

3. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱い（exit code 1）

4. DB / ディレクトリ
   - デフォルトでは data/ ディレクトリに各種ファイルが作成されます:
     - data/kabusys.duckdb (DuckDB、環境変数 DUCKDB_PATH で変更可)
     - data/monitoring.db (SQLite、環境変数 SQLITE_PATH で変更可)
     - data/paper_trading.db (ペーパートレード用 SQLite、PAPER_TRADING_SQLITE_PATH で変更可)
   - logs/ ディレクトリは自動作成（LOG_DIR 環境変数で変更可）

主要環境変数
------------
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

よく使う任意 / デフォルト:
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR（デフォルト: INFO）
- LOG_DIR: ログディレクトリ（デフォルト: logs）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- PAPER_FILL_MODE: instant / partial / never / reject（デフォルト: instant）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 使用時）
- MONITOR_POLL_INTERVAL: SystemMonitor ポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 本番環境での kill.flag 自動クリア（デフォルト 0）

使い方
------

起動スクリプト
- ExecutionEngine を起動（環境に応じて本番/ペーパー切替）
  - python -m kabusys.run_execution
  - 実行中は data/stop_requested.flag の存在で停止処理を行う。停止は監視側 or 手動でフラグ作成で可能。

- Monitoring を起動（デフォルト 60 秒間隔、MONITOR_POLL_INTERVAL で上書き可）
  - python -m kabusys.run_monitoring

設定関連
- 対話式 .env 作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]

ツール
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

AI モジュール（プログラム的に利用）
- OpenAI キーが必要（OPENAI_API_KEY 環境変数、または関数引数）
- ニュース NLP を実行（例、DuckDB 接続を得て呼び出す）:
  - from kabusys.ai.news_nlp import score_news
  - score_news(conn=duckdb_conn, target_date=date(2026,4,1), api_key="sk-...")

- レジーム判定:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn=duckdb_conn, target_date=date(2026,4,1), api_key="sk-...")

ライブラリ関数利用例（ポートフォリオ）
- 候補選定・重み:
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights
  - candidates = select_candidates(buy_signals, max_positions=10)
  - weights = calc_equal_weights(candidates)
- ポジションサイズ算出:
  - from kabusys.portfolio import calc_position_sizes
  - sizes = calc_position_sizes(weights, candidates, portfolio_value, available_cash, current_positions, open_prices)

ログ設定
- 共通の logging 設定は kabusys.utils.logging_setup.setup_logging を使用
- 起動スクリプトは内部で setup_logging(app_name="execution" or "monitoring") を呼び出します
- ログは stdout と logs/<app_name>.log（日時ローテーション）へ出力

停止・Kill Switch
- ExecutionEngine の外部停止:
  - KillSwitch は条件に応じて data/kill.flag を書くことで停止をトリガーします（monitoring 側が評価）
  - また、run_execution/run_monitoring は data/stop_requested.flag を監視してプロセス停止を行います（手動で作成可能）
- 起動時に kill.flag を自動クリアするかどうかは KILL_FLAG_CLEAR_ON_START で制御

ディレクトリ構成
----------------
（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数/設定読み込みロジック
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - utils/
    - __init__.py
    - logging_setup.py      — ログ初期化ユーティリティ
    - process_priority.py   — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py      — SQLite 永続化層
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py      — （存在する想定、ログ参照）
    - kill_switch.py
    - alert_manager.py      — （存在する想定、通知処理）
  - execution/
    - (ExecutionEngine 関連モジュール群)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - data/                   — 実行時に生成されることが想定されるディレクトリ（デフォルト）
    - monitoring.db
    - paper_trading.db
    - kabusys.duckdb
    - kill.flag
    - stop_requested.flag
    - execution.pid
  - logs/                   — ログ出力先（デフォルト）

トラブルシューティング
----------------------
- .env が見つからない / 必須変数が未設定:
  - python -m kabusys.config_setup で作成後、python -m kabusys.validate_config で検証してください。
- ログディレクトリ作成に失敗する:
  - 権限を確認するか、環境変数 LOG_DIR を書き込み可能なディレクトリに設定してください。
- OpenAI API 呼び出しで失敗する:
  - OPENAI_API_KEY が正しく設定されているか確認。レート制限や一時的なネットワーク障害は再試行ロジックがありますが、キーが無いと処理は失敗します。
- DuckDB / SQLite のパスが異なる:
  - 環境変数 DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH でパスを調整してください。
- プロセス優先度の設定が失敗する:
  - psutil の権限不足やプラットフォーム非対応時は警告を出しスキップします。root 権限が必要な操作がある点に注意。

開発メモ / 注意点
-----------------
- 本プロジェクトは本番口座（live）での動作に慎重な設計をしています。KABUSYS_ENV=live 設定時は必須変数や通知設定（LINE 等）を必ず確認してください。
- .env は秘匿情報を含むため絶対にリポジトリへコミットしないでください。
- AI 関連は外部 API を使うため、利用には API キーとコスト管理が必要です。

追加情報
--------
- 各モジュールのドキュメントはソース内の docstring に詳述されています。実装の詳細（例: ポジションサイズ算出のアルゴリズム、AI のプロンプト設計等）は該当ファイルを参照してください。
- 不明点があれば、該当モジュールの docstring を参照の上、直接スクリプトを小さなテストで実行して動作を確認してください。

以上。README を参照して環境構築・起動を行ってください。必要であれば README の英語版や詳細セットアップ手順（systemd / supervisor 用のサービス定義例等）も作成します。