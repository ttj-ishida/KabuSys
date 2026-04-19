README
======

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤の一部を実装した Python パッケージです。本リポジトリには以下の主要機能が含まれます:

- ExecutionEngine（発注エンジン）と Execution 周辺ユーティリティ
- 監視（Monitoring）コンポーネント（システム状態・注文状態・リスク監視・Kill Switch）
- ポートフォリオ構築（銘柄選定・重み付け・ポジションサイジング・セクター制約）
- 研究（ファクター計算・特徴量探索）
- AI を使ったニュースセンチメント / 市場レジーム判定（OpenAI）
- 各種 CLI ツール（.env ウィザード・設定検証・Paper Trading 検証レポート等）

機能一覧
--------
主な機能（抜粋）:

- Execution
  - 実際のブローカークライアントまたはペーパートレード用の MockBroker を使って注文実行
  - リスク管理（RiskManager）・OrderManager・Reconciler などの組み合わせ
  - 起動時に PID ファイルを書き、停止フラグで安全停止
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク・プロセス生存・データ鮮度を監視
  - TradeMonitor: 注文の滞留や約定異常などを検出（実装ファイル参照）
  - RiskMonitor: ドローダウンやポジション数超過を検出・ログ
  - KillSwitch: 条件に応じて data/kill.flag を書き、ExecutionEngine を停止
  - MonitoringEngine: 複数モニタをまとめてポーリング実行
- Portfolio（純粋関数）
  - 銘柄選定（select_candidates）
  - 等配分・スコア配分（calc_equal_weights / calc_score_weights）
  - ポジション数算出（calc_position_sizes）
  - セクター上限適用（apply_sector_cap）・レジーム乗数（calc_regime_multiplier）
- Research
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB 使用）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI（OpenAI）
  - ニュース記事を LLM でスコアリングして ai_scores テーブルへ書込む（score_news）
  - マクロニュースと ETF の MA を用いた市場レジーム判定（score_regime）
- Tools
  - .env ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

前提 / 必要環境
----------------
- Python 3.9+ を想定（typing の記述に合わせて）
- 必要な外部パッケージ（主なもの）:
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（config 検証で YAML 内容チェックを行う場合）
- 標準ライブラリ: sqlite3, logging, threading 等

セットアップ手順
----------------
1. リポジトリをクローンしてワークディレクトリへ移動
   - git clone ...
   - cd <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml
   - （プロジェクトに requirements.txt があればそれを使ってください）

4. .env の初期作成
   - 対話式ウィザードで .env を生成:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に手動で作成

   自動ロード:
   - config.py はプロジェクトルート（.git または pyproject.toml がある場所）を基準に .env/.env.local を自動読み込みします。
   - 自動読み込みを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

5. ディレクトリ作成
   - data/ と logs/ は実行時に自動で作られることがありますが、手動で作成して権限を確認しておくとよいです。
     - mkdir -p data logs

6. 設定検証
   - python -m kabusys.validate_config
   - 本番チェックに厳密に Fail を出す場合は --strict を付けます。

重要な環境変数（抜粋）
---------------------
必須:
- JQUANTS_REFRESH_TOKEN - J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD      - kabuステーション API パスワード（必須）

運用・パス系（デフォルト値）:
- KABUSYS_ENV           - 実行環境: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH           - DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           - 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL             - ログレベル（デフォルト: INFO）
- LOG_DIR               - ログ保存先（デフォルト: logs/）
- OPENAI_API_KEY        - OpenAI を使う機能に必要（score_news / score_regime など）
- MONITOR_POLL_INTERVAL - 監視ループのポーリング間隔（秒、デフォルト 60）

Kill / Stop フラグ:
- data/kill.flag        - Kill Switch が発動した際に書き込まれる（ExecutionEngine の停止指示）
- data/stop_requested.flag - run_monitoring/run_execution が監視する停止リクエストフラグ
- KILL_FLAG_CLEAR_ON_START - (0/1) 起動時に kill.flag を自動クリアする挙動（本番では 0 推奨）

使い方（起動例）
----------------

- 実行エンジン（ExecutionEngine）起動:
  - python -m kabusys.run_execution
  - run_execution は KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading.sqlite を利用します。
  - 既に data/stop_requested.flag が存在すると起動せず終了します。

- 監視ループ（Monitoring）起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用します（監視データは本番 DB と同一に保存されます）。

- 設定ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - オプションで期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB ファイルを明示する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（programmatic）
  - OpenAI API キー (OPENAI_API_KEY) を設定しておくことで、以下の関数を呼んで利用できます:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続を受け取り、適切なテーブル（raw_news, news_symbols, ai_scores, prices_daily など）を参照します。

停止 / Kill フラグに関する注意
---------------------------
- KillSwitch は RiskMonitor の検出などで data/kill.flag を書き込みます。ExecutionEngine はこのファイルの存在を見て安全停止します。
- 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動でクリアしますが、本番では危険なため 0 を推奨します。
- 管理者が手動でプロセスを停止したい場合は data/stop_requested.flag を作成すると run_execution/run_monitoring は検知して終了します。

ディレクトリ構成
----------------
（主要なファイル／ディレクトリを抜粋）

- src/kabusys/
  - __init__.py            — パッケージ初期化、バージョン情報
  - config.py              — 環境変数 / .env 自動ロード・Settings クラス
  - config_setup.py        — 対話式 .env ウィザード
  - validate_config.py     — 設定検証 CLI
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - run_monitoring.py      — Monitoring ポーリングループ起動スクリプト
  - execution/             — Execution 関連（BrokerFactory, ExecutionEngine, OrderManager, RiskManager, Reconciler 等）
  - monitoring/
    - monitoring_db.py     — SQLite 永続化層（監視ログ）
    - system_monitor.py    — システム・データ鮮度監視
    - trade_monitor.py     — 注文監視（滞留等検出）
    - risk_monitor.py      — ドローダウン・ポジション上限監視
    - kill_switch.py       — Kill Switch ロジック（kill.flag 書込）
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py     — （アラート通知管理：LINE 連携等）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py   — 株数決定・スケーリング
    - risk_adjustment.py   — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py   — Momentum/Value/Volatility ファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py          — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py   — 市場レジーム判定（OpenAI + MA）
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成
  - utils/
    - logging_setup.py     — ログ設定ユーティリティ（コンソール + 日次ファイル）
    - process_priority.py  — プロセス優先度 / CPU affinity 設定ユーティリティ

その他の備考 / 運用上のヒント
-----------------------------
- Monitoring は監視用のテーブル構造を管理する init_monitoring_db を提供します。DB のマイグレーション処理（カラム追加等）も軽微なものは実装されています。
- ログは logs/<app_name>.log に日次ローテーションで蓄積されます。ログディレクトリに書込み権限があることを確認してください。
- OpenAI を使う AI 機能は外部 API 呼び出しのため失敗やレート制限に対するリトライ処理が組まれていますが、API キーと利用料には注意してください。
- config.validate_config は本番起動前のチェックに便利です。--strict モードで警告も FAIL 扱いにできます。
- Paper Trading と本番 DB は分離する設計になっています。Execution は KABUSYS_ENV=paper_trading のとき paper_trading.db を使い、Monitoring は常に本番 sqlite_path を使う点に注意してください。

ライセンス・貢献
----------------
- 本 README ではライセンス情報は記載していません。実際のリポジトリでは LICENSE ファイルをご確認ください。
- バグ報告・プルリクエストはリポジトリの issue / PR フローに従ってください。

以上。README の補足や特定機能（例：Execution の詳細な起動オプション、テーブルスキーマ、サンプル .env）の追記が必要であれば指示してください。