KabuSys — 日本株自動売買システム
=================================

この README はリポジトリ内の主要スクリプト・モジュールの使い方とセットアップ手順をまとめたものです。内部実装に合わせた運用メモとしても使えるように、日本語で要点を整理しています。

概要
----
KabuSys は日本株の自動売買・モニタリング・リサーチを目的とした小型フレームワークです。主要機能は次のとおりです。

- ExecutionEngine：ブローカークライアント経由で注文発行（本番 / ペーパートレード切替対応）
- Monitoring：システム健全性、注文ステータス、リスク（ドローダウン・ポジション上限）を定期監視・アラート
- Portfolio construction：候補選定・重み計算・ポジションサイズ算出等の純粋関数群
- Research：DuckDB を使ったファクター計算、特徴量探索（IC 等）
- AI モジュール：ニュース NLP によるセンチメント、レジーム判定（OpenAI API 使用、オプション）
- ツール群：ペーパートレード検証レポート生成、.env ウィザード、設定検証 CLI など

主な機能一覧
--------------
- 起動スクリプト
  - python -m kabusys.run_execution: ExecutionEngine の起動（KABUSYS_ENV により paper_trading モードあり）
  - python -m kabusys.run_monitoring: Monitoring のポーリングループ起動（MONITOR_POLL_INTERVAL により間隔指定可能）
- 設定管理
  - python -m kabusys.config_setup: .env を対話式に作成・更新するウィザード
  - python -m kabusys.validate_config: .env および config/*.yaml の事前検証ツール
- モニタリング
  - system_monitor, trade_monitor, risk_monitor を組み合わせた MonitoringEngine（アラート発行、kill.flag 書き込み等）
  - kill.flag を用いた ExecutionEngine 停止機構（Kill Switch）
- ポートフォリオ関連（純粋関数）
  - 銘柄選定: select_candidates
  - 重み計算: calc_equal_weights / calc_score_weights
  - ポジションサイズ算出: calc_position_sizes（lot 単位丸め、aggregate cap 等）
  - セクターキャップ・レジーム乗数: apply_sector_cap / calc_regime_multiplier
- リサーチ
  - ファクター計算: calc_momentum / calc_volatility / calc_value
  - 将来リターンや IC 計算: calc_forward_returns / calc_ic / factor_summary
- AI（オプション）
  - ニュースを LLM（OpenAI）でスコア化し ai_scores に保存（news_nlp.score_news）
  - マクロニュース＋ETF MA200 を組み合わせた市場レジーム判定（regime_detector.score_regime）
- ツール
  - ペーパートレード検証レポート生成: python -m kabusys.tools.paper_verification_report

セットアップ手順
----------------
1. リポジトリを取得して Python 環境を作成する（推奨: venv / pyenv / conda 等）
   - 例:
     python -m venv .venv
     source .venv/bin/activate

2. 必要なパッケージをインストールする
   - 実行に必要な主なパッケージ:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML (validate_config の YAML 検証を使う場合)
   - 例:
     pip install duckdb psutil openai pyyaml

   ※ requirements.txt は同梱されていない想定のため、プロジェクトで必要なパッケージを追加して管理してください。

3. .env を用意する
   - 対話式で作る:
     python -m kabusys.config_setup
   - もしくは .env.example を参考に .env を作成し、必須環境変数を設定してください。
   - 必須環境変数例:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要な設定（例）:
     KABUSYS_ENV=development
     JQUANTS_REFRESH_TOKEN=your_token_here
     KABU_API_PASSWORD=your_password_here
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO
     KILL_FLAG_CLEAR_ON_START=0

4. DB 等の初期化
   - 起動スクリプトを実行すると必要テーブルの作成（冪等）が行われます（monitoring は init_monitoring_db を実行）。
   - DuckDB / SQLite のデフォルトパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite (paper_trading): data/paper_trading.db

使い方
------
基本的な起動方法とよく使うコマンドを示します。

- 設定ウィザード（.env の作成／更新）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code 1）になります。

- ExecutionEngine 起動
  - 標準起動:
    python -m kabusys.run_execution
  - KABUSYS_ENV が paper_trading の場合:
    - MockBrokerClient が使用され、データは data/paper_trading.db に保存されます（本番 DB と分離）。
  - 停止方法:
    - data/stop_requested.flag または data/kill.flag を書き込む（Monitoring 内の Kill Switch が kill.flag を書き込むと ExecutionEngine 停止へ繋がります）。
    - run_execution は data/execution.pid に PID を書く仕様（pid_file のパスは Settings で変更可）。

- Monitoring 起動
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト: 60 秒）。
  - Monitoring は起動時に Settings.sqlite_path（本番用 SQLite）を使って監視テーブルを初期化します（環境に関わらず本番 sqlite_path を使用）。

- ペーパートレード検証レポート
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB パス指定可。デフォルト: data/paper_trading.db

- AI 機能（OpenAI）
  - OpenAI API キーを環境変数 OPENAI_API_KEY に設定するか、関数呼び出しで明示的に渡してください。
  - 例: news_nlp.score_news(duckdb_conn, target_date, api_key="...")

重要な運用ポイント / 環境変数
----------------------------
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
  - paper_trading: ブローカークライアントは Mock を使い、paper_sqlite_path に書き込みます
  - live: 本番運用モード（注意喚起が設定検証に含まれます）

- DB 関連:
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（ペーパートレード専用 DB、デフォルト: data/paper_trading.db）

- ログ:
  - デフォルト出力先: stdout（StreamHandler）と logs/<app_name>.log（日次ローテーション）
  - LOG_LEVEL 環境変数でログレベル変更
  - LOG_DIR を変更してファイル保存先を指定可能

- モニタリング制御:
  - MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒）
  - データクリア / 停止フラグ:
    - data/kill.flag: ExecutionEngine を停止するための Kill Switch（Monitoring が書き込む）
    - data/stop_requested.flag: run_monitoring/run_execution が監視している停止フラグ（外部で書けば安全に停止）
  - KILL_FLAG_CLEAR_ON_START（env）: ExecutionEngine 起動時に kill.flag を自動削除するか（開発用設定、0 推奨）

- Paper Trading の挙動:
  - PAPER_FILL_MODE（instant/partial/never/reject）で MockBroker の約定挙動を制御
  - paper_sqlite_path へ完全に分離して記録されるため、本番 DB を汚さない

- OpenAI / AI 機能:
  - OPENAI_API_KEY は必須（AI 機能を使う場合）
  - LLM 呼び出しはリトライとバックオフ処理を内包し、失敗時はフェイルセーフ（0.0 等）で継続する実装

ディレクトリ構成（主要ファイル）
------------------------------
以下はリポジトリ内の主要モジュールと簡単な説明です。パッケージルートは src/kabusys。

- src/kabusys/
  - __init__.py                — パッケージ定義、バージョン
  - config.py                  — Settings クラス（環境変数読み取り・自動 .env ロード）
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 起動前の設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - portfolio/
    - portfolio_builder.py     — 候補選定・重み計算
    - position_sizing.py       — 株数決定・スケールダウン・lot 丸め
    - risk_adjustment.py       — セクター上限・レジーム乗数
  - research/
    - factor_research.py       — Momentum/Volatility/Value のファクター計算
    - feature_exploration.py   — forward returns / IC /統計サマリー
  - ai/
    - news_nlp.py              — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py       — レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py         — SQLite テーブル初期化・永続化 API
    - monitoring_engine.py     — 各 Monitor を束ねるエンジン
    - system_monitor.py        — CPU/メモリ/ディスク/データ鮮度監視
    - trade_monitor.py         — （注文系の監視: 滞留注文・約定異常等）
    - risk_monitor.py          — ドローダウン / ポジション上限監視
    - kill_switch.py           — kill.flag 書き込みロジック
  - utils/
    - logging_setup.py         — ログ初期化（Stream + TimedRotatingFileHandler）
    - process_priority.py      — プロセス優先度・CPU affinity 設定ユーティリティ
  - data/                      — 実行時に利用するデフォルトディレクトリ（logs/, data/ 等は起動時自動作成）

注意事項 / ベストプラクティス
----------------------------
- .env は機密情報を含むため絶対に Git にコミットしないでください（config_setup.py のヘッダに注意喚起あり）。
- KABUSYS_ENV=live の場合は特に注意（validate_config が警告を出します）。Kill Switch 周りの設定（LINE 通知等）を十分に確認してください。
- Paper Trading モードでも実運用前にペーパーデータで十分な検証を行ってください（paper_verification_report を活用）。
- OpenAI API 利用はコストがかかります。news_nlp/regime_detector を運用に組み込む際は API 呼び出し量に注意してください。
- ログディレクトリ作成に失敗した場合はファイル出力が無効化され、コンソールログのみとなる点に注意（ログ設定はフォールバック実装あり）。

サンプル .env（抜粋）
-------------------
以下は最低限の例です（実運用では値を適切に置き換えてください）。

KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
PAPER_FILL_MODE=instant
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
OPENAI_API_KEY=sk-...

さらに知りたいこと / カスタマイズ
-------------------------------
- ブローカークライアント実装や ExecutionEngine の詳細な振る舞い（リスク設定・リコンシリエーション等）を確認したい場合は execution/ 以下のモジュールを参照してください。
- duckdb を使ったファクター計算は prices_daily / raw_financials 等のテーブル構成に依存します。データパイプラインやテーブル定義は data.pipeline 等のドキュメントに従ってください（コード内ドキュメント参照）。

問題・提案
---------
不明点や改善提案があれば README の Issue を起点に相談してください。必要であれば運用手順書やシステム図の追加も検討します。

以上。