README.md

KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買フレームワークです。システムは次の主要機能で構成されます:
- 発注エンジン（ExecutionEngine）: 実際の注文処理とリスク管理（本番 / ペーパートレードに対応）
- 監視（Monitoring）: システム状態・データ鮮度・注文状況・リスクを継続的に監視しアラート／Kill Switch を発動
- ポートフォリオ構築: 候補選定、重み付け、ポジションサイズ計算、セクター制約など純粋関数群
- リサーチ: DuckDB を用いたファクター計算・特徴量解析
- AI 支援モジュール: ニュース NLP（OpenAI を用いたセンチメント）、市場レジーム判定
- 運用補助ツール: .env 対話ウィザード、設定検証、Paper Trading 検証レポートなど

主な設計方針:
- 本番・ペーパートレードを明確に分離（ペーパートレードは専用 SQLite DB）
- DuckDB を用いたリサーチ処理（SQL と Python を併用）
- 外部 API（OpenAI など）は明示的に API キーで管理、失敗時はフェイルセーフで継続

機能一覧
--------
- 環境設定ウィザード（kabusys.config_setup）: 対話形式で .env を生成/更新
- 設定検証 CLI（kabusys.validate_config）: 起動前に必須環境変数や YAML 設定のチェック
- 実行エンジン起動スクリプト（kabusys.run_execution）:
  - KABUSYS_ENV に応じて本番 / ペーパートレードのブローカークライアントを切替え
  - paper_trading は data/paper_trading.db に完全分離して記録
  - 実行中は PID ファイル（data/execution.pid）を書き出し、stop フラグで停止可能
- 監視ループ起動スクリプト（kabusys.run_monitoring）:
  - SystemMonitor / TradeMonitor / RiskMonitor 等の定期実行
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）
  - 停止フラグ（data/stop_requested.flag）でループを終了
- MonitoringDB（SQLite）: system_status / trade_logs / positions / risk_logs / dashboard テーブルと永続化 API
- Kill Switch（data/kill.flag）: ドローダウンやポジション上限超過で ExecutionEngine を停止させる仕組み
- ポートフォリオ構築ユーティリティ:
  - 候補選定（select_candidates）
  - 等重・スコア加重（calc_equal_weights / calc_score_weights）
  - ポジションサイズ計算（calc_position_sizes）
  - セクターキャップ / レジーム乗数（apply_sector_cap / calc_regime_multiplier）
- リサーチ:
  - momentum / volatility / value 等ファクター計算（DuckDB）
  - 将来リターン計算、IC（Information Coefficient）等
- AI モジュール:
  - news_nlp.score_news: OpenAI でニュースをスコアリングして ai_scores に書き込み
  - regime_detector.score_regime: ETF MA とマクロニュースを組み合わせてレジーム判定
- ツール:
  - paper_verification_report: Paper Trading の検証レポート生成（稼働率・成功率・レイテンシ等）

セットアップ手順
--------------
前提:
- Python 3.10 以上（typing の | 演算子を利用）
- 任意の仮想環境を推奨（venv / conda 等）

1. リポジトリをクローン / 配置
   - プロジェクトルートは .git または pyproject.toml を基準に自動検出されます。

2. 依存パッケージをインストール
   - 必須パッケージ（例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証で任意）
   - インストール例:
     pip install duckdb psutil openai PyYAML

   ※ requirements.txt がある場合は:
     pip install -r requirements.txt

3. ディレクトリ作成
   - デフォルトで使用するディレクトリ:
     - data/ (SQLite DB やフラグファイル)
     - logs/ (ログファイル)
   - 例:
     mkdir -p data logs

4. .env の作成（推奨）
   - 対話ウィザードを実行して .env を作成:
     python -m kabusys.config_setup
   - またはサンプルを手動で作成 (.env.example を参照)。
   - 主なキー（秘密情報は必ず管理する）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト: data/paper_trading.db)
     - OPENAI_API_KEY (AI 機能を使う場合)
     - KABUSYS_ENV (development / paper_trading / live)
     - LOG_LEVEL (DEBUG/INFO/...)
     - KILL_FLAG_CLEAR_ON_START (0/1)

5. 設定検証（起動前チェック）
   python -m kabusys.validate_config
   --strict を付けると警告も失敗扱いになります:
   python -m kabusys.validate_config --strict

使い方
------
基本的な起動例:

- 監視ループを起動:
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数で間隔を秒単位で設定可能（例: export MONITOR_POLL_INTERVAL=30）
  - 停止するにはプロジェクトルートの data/stop_requested.flag を作成（監視ループは検知して終了）

- 実行エンジンを起動:
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合はモックブローカーを使用し、data/paper_trading.db を使用します
  - 実行中は data/execution.pid が作成されます
  - 停止させるには data/stop_requested.flag を作成（または Kill Switch により kill.flag が書き込まれると停止）

- 環境設定ウィザード:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config

- Paper Trading 検証レポート:
  python -m kabusys.tools.paper_verification_report
  期間指定:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  DB を指定:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

停止 / Kill Switch / フラグ
- 停止フラグ:
  - data/stop_requested.flag を作成すると run_monitoring / run_execution のポーリングループが検知して安全に終了します。
- Kill Switch:
  - リスク条件（ドローダウン超過、ポジション上限超過等）で kill.flag（デフォルト data/kill.flag）が書き込まれると ExecutionEngine に停止シグナルを送ります。
  - Settings.kill_flag_clear_on_start=1 を設定すると起動時に自動で kill.flag をクリアしますが、本番では推奨されません。

環境変数の主要説明
- KABUSYS_ENV: development | paper_trading | live
  - paper_trading: ブローカーは Mock に切替え、DB は paper_trading 用を使用
  - live: 本番運用（注意深く設定を確認すること）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード DB（デフォルト data/paper_trading.db）
- DUCKDB_PATH: DuckDB（デフォルト data/kabusys.duckdb）
- OPENAI_API_KEY: AI 機能（news_nlp / regime_detector）利用時に必須
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- LOG_LEVEL, LOG_DIR: ログレベル / ログ保存先

ライブラリ / API の利用
- 本リポジトリのモジュールはライブラリとしても利用できます。主要な公開関数例:
  - kabusys.portfolio.select_candidates / calc_equal_weights / calc_score_weights / calc_position_sizes
  - kabusys.research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic
  - kabusys.ai.score_news (AI スコアリング)
  - kabusys.ai.regime_detector.score_regime
- DuckDB 接続を渡して関数を呼び出す設計になっています（外部 API への副作用は最小化）

ディレクトリ構成
----------------
（src/kabusys 配下の主要ファイル・ディレクトリ）

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 起動前設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート
  - ai/
    - news_nlp.py              — ニュース NLP / OpenAI スコアリング
    - regime_detector.py       — 市場レジーム判定
  - portfolio/
    - portfolio_builder.py     — 候補選定・重み付け
    - position_sizing.py       — 株数計算・スケーリング
    - risk_adjustment.py       — セクター上限・レジーム乗数
  - research/
    - factor_research.py       — ファクター計算（momentum/volatility/value）
    - feature_exploration.py   — 将来リターン / IC / 統計サマリー
  - monitoring/
    - monitoring_db.py         — SQLite 永続化層（テーブル初期化 / API）
    - system_monitor.py        — システム状態監視
    - risk_monitor.py          — ドローダウン / ポジション上限監視
    - trade_monitor.py         — （注文関連の監視; 他ファイル参照）
    - kill_switch.py           — kill.flag の管理
    - monitoring_engine.py     — 各 Monitor を束ねるエンジン
  - execution/                 — ExecutionEngine および発注関連（broker / order_manager 等）
  - utils/
    - logging_setup.py         — 統一的ログ設定
    - process_priority.py      — プロセス優先度設定ユーティリティ

追加情報 / 運用上の注意
----------------------
- 本番（KABUSYS_ENV=live）運用時は .env の管理を厳密に行い、LINE などの通知設定を必ず確認してください。
- Kill Switch やフラグファイルの自動クリア設定（KILL_FLAG_CLEAR_ON_START）を本番で有効にするのは危険です。デフォルトは 0（クリアしない）。
- OpenAI 等の外部 API 利用はコストが発生するため、API キーの管理・レート制御に注意してください。AI モジュールは失敗時にフォールバック動作をするよう実装されていますが、期待どおりのスコアが得られない可能性があります。
- ログは logs/<app_name>.log に日次ローテーションで出力されます。ログディレクトリの権限・容量管理を行ってください。

貢献・開発
----------
- 新しい機能追加やバグ修正はモジュール単位で行ってください。DuckDB を用いた処理はテストしやすく設計されています。
- 単体テストや CI を導入する場合は、環境依存（.env 自動ロード等）を無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD を利用できます。

ライセンス
---------
- 本プロジェクトのライセンス情報はリポジトリの LICENSE を参照してください（存在する場合）。

以上がプロジェクトの概要と使い方です。必要であれば README に含める具体的な .env.example テンプレートや運用チェックリストも作成します。どの情報をより詳細に盛り込みたいか教えてください。