KabuSys — 日本株自動売買システム（簡易 README）
================================

概要
----
KabuSys は日本株の自動売買・研究パイプラインを想定した Python コードベースです。本リポジトリには以下の主要機能が含まれます。

- ExecutionEngine 起動スクリプト（発注処理）
- Monitoring（システム稼働／注文監視／Kill Switch）
- ポートフォリオ構築（銘柄選定・重み付け・株数決定）
- リサーチ（ファクター計算・特徴量解析）
- AI モジュール（ニュースを LLM でスコアリング、レジーム判定）
- 環境設定ウィザード / 設定検証ツール
- Paper Trading 用検証レポート生成ツール

特徴（主な機能）
----------------
- 実行環境分離
  - KABUSYS_ENV により development / paper_trading / live を切り替え。
  - paper_trading 時は MockBrokerClient を使用し、paper 用 DB（data/paper_trading.db）へ記録して本番 DB と分離。
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine。
  - Kill Switch（data/kill.flag）により ExecutionEngine を安全に停止。
  - stop フラグ（data/stop_requested.flag）で起動ループを止められる。
- ポートフォリオ構築
  - 候補選定、等金額／スコア重み、リスクベースのポジションサイズ計算、セクター上限適用など純粋関数で実装。
- リサーチ
  - DuckDB を用いたファクター（モメンタム・ボラティリティ・バリュー）計算、将来リターン／IC 計算等。
- AI
  - OpenAI（gpt-4o-mini を想定）を用いたニュースセンチメント集約（ai_scores への書き込み）、レジーム（bull/neutral/bear）判定。
  - API 呼び出しはリトライ・フェイルセーフあり。
- ロギング / プロセス優先度
  - 統一的なログ設定ユーティリティ（コンソール + 日次ローテートファイル）。
  - プロセス優先度設定 / CPU affinity ユーティリティ（psutil 使用）。

セットアップ手順
-----------------
以下は一般的なセットアップ手順です。プロジェクト固有の要件ファイルがある場合はそちらを参照してください。

1. Python 環境を準備
   - Python 3.9+（コード中の型ヒント等を前提）。仮想環境を推奨。

2. 依存パッケージをインストール
   - 必須: duckdb, psutil, openai
   - 任意（YAML 検証を行う場合）: PyYAML
   例:
     pip install duckdb psutil openai PyYAML

3. プロジェクトルートに移動（.git または pyproject.toml があるトップレベル）
   - Settings モジュールはプロジェクトルートを自動検出して .env / .env.local を読み込みます。

4. .env を作成・編集
   - 対話式ウィザードで作成:
       python -m kabusys.config_setup
   - もしくは .env.example を参考に手動で作成
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を使う場合:
     - OPENAI_API_KEY を設定

5. 設定検証（起動前に推奨）
     python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いにできます。

使い方（起動 / 操作）
---------------------

起動スクリプト
- ExecutionEngine（発注エンジン）起動:
    python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、paper DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用します。
  - 起動時に data/execution.pid に PID を書き込みます。
  - 停止: data/stop_requested.flag を作成すると安全にループを止めます。Kill Switch（data/kill.flag）は ExecutionEngine に停止シグナルを与えるために Monitoring が書き込むことがあります。

- Monitoring（ポーリングループ）起動:
    python -m kabusys.run_monitoring
  - デフォルトは 60 秒間隔でポーリング。環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒）。
  - Monitoring は環境に関わらず本番用 sqlite_path（Settings.sqlite_path）を使用して監視データを記録します。
  - 停止: data/stop_requested.flag を作成すると Monitoring のループが終了します。

停止 / Kill
- Kill Switch 書き込み:
  - Monitoring 内の KillSwitch が条件を満たすと data/kill.flag を生成し、ExecutionEngine を停止させる設計です。
- 手動で停止フラグを書き込む:
  - echo "reason" > data/kill.flag
  - touch data/stop_requested.flag

主要 CLI ツール
- 環境ウィザード:
    python -m kabusys.config_setup
- 設定検証:
    python -m kabusys.validate_config [--strict]
- Paper Trading 検証レポート生成:
    python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

主な環境変数（抜粋）
- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API を使う場合に必要
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant|partial|never|reject）
- LOG_LEVEL, LOG_DIR など（ロギング制御）

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 配下の主要なモジュール構成（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数 / Settings 管理（.env 自動ロード）
    - config_setup.py           — .env 対話式ウィザード
    - validate_config.py        — 設定検証 CLI
    - run_execution.py          — ExecutionEngine 起動スクリプト
    - run_monitoring.py         — Monitoring 起動スクリプト
    - tools/
      - paper_verification_report.py  — Paper Trading 検証レポート生成
    - utils/
      - logging_setup.py        — ログ設定ユーティリティ（コンソール + 日次ローテート）
      - process_priority.py     — プロセス優先度 / CPU affinity 設定
    - monitoring/
      - monitoring_db.py        — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
      - monitoring_engine.py    — 各 Monitor を束ねるエンジン
      - system_monitor.py       — CPU/メモリ/ディスク/プロセス/データ鮮度監視
      - risk_monitor.py         — ドローダウン・ポジション上限の監視
      - kill_switch.py          — kill.flag 管理
      - (TradeMonitor, AlertManager 等 他ファイルあり)
    - portfolio/
      - portfolio_builder.py    — 候補選定・重み計算
      - position_sizing.py      — 株数決定・集計キャップ
      - risk_adjustment.py      — セクター上限・レジーム乗数
    - research/
      - factor_research.py      — モメンタム/ボラティリティ/バリュー計算（DuckDB）
      - feature_exploration.py  — 将来リターン / IC / 統計サマリー
    - ai/
      - news_nlp.py             — ニュースセンチメント集約（OpenAI 呼び出し、ai_scores 書込）
      - regime_detector.py      — レジーム判定（MA + マクロセンチメント合成）
    - data/                      — 実行時に使用するファイル置き場（logs/, data/ 等）
      - stop_requested.flag
      - kill.flag
      - execution.pid
      - monitoring.db / paper_trading.db（デフォルト位置）

実運用上の注意
----------------
- .env は機密情報を含むため Git に絶対にコミットしないこと。
- KABUSYS_ENV=live の設定では通知設定（LINE 等）や kill フラグの扱いを慎重にすること（validate_config に警告あり）。
- OpenAI を使うモジュールは API キーが必要。API レート制限やコストに注意。
- Monitoring はデフォルトで本番の SQLite（SQLITE_PATH）を使用するため、監視用 DB のバックアップや運用設計を行ってください。
- ログは logs/<app_name>.log に日次ローテートで出力されます。LOG_DIR で出力先を変更可能です。

拡張・開発メモ
----------------
- DuckDB をデータ分析基盤として利用しており、リサーチモジュールは prices_daily / raw_financials / raw_news 等のテーブルに依存します。
- AI モジュールは出力を JSON Mode で期待しており、レスポンスの堅牢な検証・トリミング・リトライを実装しています。
- ポートフォリオ・サイズ決定・リスク調整は純粋関数で実装されているため単体テストが容易です。

ライセンス / バージョン
-----------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ による（例: 0.1.0）。
- ライセンス情報はリポジトリのトップレベルを参照してください（本 README では指定していません）。

最後に
------
この README はコードベースに含まれる主要コンポーネントを元に作成しています。実際の運用や開発時は、各モジュールの docstring や関数・クラスのコメントを参照してください。必要ならば README に含める起動サンプルや図、追加の運用手順（systemd / cron 設定例など）を追記できます。