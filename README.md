KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤のライブラリ兼実行スクリプト群です。  
主な設計方針は「本番と検証（ペーパートレード）を分離」「DuckDB による分析」「環境変数・.env による設定管理」「外部 LLM を利用したニュース評価」「監視・Kill Switch による安全停止」です。

主な機能
--------
- 実行エンジン起動スクリプト（run_execution）  
  - KABUSYS_ENV に応じて本番／ペーパートレードを切替（paper_trading では MockBrokerClient を使用し、専用 SQLite に記録）
  - プロセス優先度の設定、PIDファイル管理、停止フラグ対応
- 監視ループ（run_monitoring）  
  - System / Trade / Risk の定期チェック、監視ログの永続化（SQLite）
  - MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）
  - 停止フラグ（data/stop_requested.flag）検出で安全終了
- MonitoringDB（SQLite）層（monitoring_db）  
  - system_status, trade_logs, positions, risk_logs, dashboard のテーブルとマイグレーション
- Kill Switch（kill_switch）  
  - ドローダウンやポジション過剰時に data/kill.flag を書き込み ExecutionEngine を停止させる仕組み
- Risk / Trade / System の各種モニタ（monitoring パッケージ）
- ポートフォリオ構築ユーティリティ（portfolio パッケージ）  
  - 候補選定、重み計算、ポジションサイズ計算、セクター制限、レジーム乗数など
- 研究用モジュール（research）  
  - ファクター計算（momentum/volatility/value）、将来リターン、IC 計算、特徴量サマリ
- AI 連携モジュール（ai）  
  - ニュースの LLM（OpenAI）によるセンチメント評価（news_nlp）
  - マクロ + ETF MA を組み合わせた市場レジーム判定（regime_detector）
- ユーティリティ  
  - ログ設定（utils.logging_setup）、プロセス優先度設定（utils.process_priority）
- CLI サポート  
  - 環境設定ウィザード（config_setup）、設定検証（validate_config）、ペーパートレード検証レポート生成ツール（tools.paper_verification_report）

セットアップ手順
---------------
前提
- Python 3.10+（typing の | 記法などを使用）
- SQLite（標準で利用可能）／DuckDB（Python パッケージ）

インストール（例）
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール（最低限）
   - pip install duckdb psutil openai
   - 追加（推奨）
     - pip install PyYAML  （config/*.yaml の検証に必要）
   - （プロジェクトで requirements.txt があれば pip install -r requirements.txt を使用）

初期設定
1. .env を作成する（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードは J-Quants トークン、kabuAPI パスワード、DB パス、ログレベル等を対話式に作成します。
   - 生成された .env は絶対に VCS にコミットしないでください。

2. 設定検証
   - python -m kabusys.validate_config
   - --strict オプションで警告も失敗扱いにできます。

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN : J-Quants API 用（必須）
- KABU_API_PASSWORD     : kabuステーション API パスワード（必須）
- KABU_API_BASE_URL     : kabuAPI のベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY        : OpenAI 呼び出しに必要（ai モジュールを使う場合）
- KABUSYS_ENV           : 実行環境（development / paper_trading / live、デフォルト development）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH           : 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH : ペーパートレード専用 SQLite（paper_trading 時に使用、デフォルト data/paper_trading.db）
- LOG_LEVEL / LOG_DIR   : ログレベル・ログディレクトリ
- MONITOR_POLL_INTERVAL : 監視ポーリング間隔（秒、run_monitoring 用。デフォルト 60 秒）

使い方（実行例）
----------------
基本的な起動
- 実行エンジン（ExecutionEngine）起動:
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ記録します。
    - 起動時に data/stop_requested.flag が存在すると起動しません。
    - 実行中に data/stop_requested.flag を作成するとエンジンに停止指示が出ます。
    - PID ファイルは data/execution.pid（Settings.pid_file_path）に書き出されます。

- 監視ループ起動:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き可能（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は常に本番の sqlite_path を使用（監視は本番監視対象を監視するため）。

ツール
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD / --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数またはデフォルト data/paper_trading.db を使用）
  - 出力: 稼働率、注文成功率、送信率、レイテンシ（P95）などのサマリと PASS/FAIL 判定

AI / レジーム判定
- OpenAI を使う機能を実行する場合は OPENAI_API_KEY を設定してください（news_nlp、regime_detector）。
- news_nlp.score_news(), regime_detector.score_regime() は DuckDB 接続と target_date を受け取り、DB を更新します。

監視・停止関連
- 停止フラグ:
  - data/stop_requested.flag : run_execution/run_monitoring の外部停止フラグ（stop_requested を作るとループが安全終了）
  - data/kill.flag : KillSwitch が書き込むフラグ。ExecutionEngine はこれを検出して停止します。
- KillSwitch の評価は MonitoringEngine 内で行われ、リスク閾値（ドローダウンや保有上限）を超えた場合に kill.flag を作成します。

ログ
- ログは既定で logs/<app_name>.log に日次ローテーションで出力されます（30 日保持）。コンソールは stdout に出力されます。
- ログディレクトリは LOG_DIR 環境変数またはデフォルト "logs" を使用します。

ディレクトリ構成（主要ファイル）
-----------------------------
以下は src/kabusys 配下の主要モジュール一覧（抜粋）:

- kabusys/
  - __init__.py
  - config.py                 — 環境変数/.env 読み込み・Settings
  - config_setup.py           — .env 作成ウィザード（CLI）
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI）によるスコアリング
    - regime_detector.py      — マクロ + ETF MA によるレジーム判定
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層
    - monitoring_engine.py    — 各モニタの統合実行ループ
    - system_monitor.py       — システム・データ鮮度監視
    - risk_monitor.py         — ドローダウン・ポジション監視
    - kill_switch.py          — Kill Switch 管理
    - (trade_monitor, alert_manager 等が想定される)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ

運用上の注意・トラブルシューティング
-------------------------------------
- .env の設定ミス（必須トークン未設定など）が最も多い問題 → python -m kabusys.validate_config で事前チェックしてください。
- OpenAI を使う箇所は API キーとレート制限に注意。リトライロジックはあるものの高頻度コールは避けてください。
- Paper trading モードは本番 DB と分離されます。誤って本番口座を操作しないよう KABUSYS_ENV を確認してください。
- DuckDB / SQLite ファイルはデフォルトで data/ に置かれます。適切なバックアップとディスク容量管理を行ってください。
- ログディレクトリ作成に失敗した場合はコンソールのみ出力されます。権限やパスを確認してください。
- プロセス優先度の設定は OS に依存します。権限不足で設定できない場合は警告が出ますが処理は継続します。

ライセンス・バージョン
--------------------
- パッケージバージョンは kabusys.__version__（現状 "0.1.0"）で管理されています。
- ライセンス情報が必要な場合はプロジェクトのルートにある LICENSE を参照してください（ここには含まれていません）。

付録（便利なコマンド）
--------------------
- .env ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行エンジン起動: python -m kabusys.run_execution
- 監視ループ起動: python -m kabusys.run_monitoring
- ペーパー検証レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

質問・改善提案
--------------
README や実行フローで不明な点があれば、実際の運用シナリオ（ローカル / サーバー / CI）を教えてください。運用に合わせた起動例や systemd / supervisord 用のユニット例も作成できます。