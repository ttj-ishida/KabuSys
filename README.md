KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株向けの自動売買 / 研究 / 監視ツール群を含む小規模なトレーディングフレームワークです。  
主な目的は以下のとおりです。

- 日次のファクター計算・リサーチ（DuckDB を用いる）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ決定）
- ExecutionEngine による発注（本番 / ペーパートレード切替）
- 監視サブシステム（システム状態・注文状態・リスク監視、Kill Switch）
- ニュース NLP / レジーム判定（OpenAI の LLM を利用可能）
- ペーパートレード検証レポートの自動生成

主な特徴
--------
- 環境切替: KABUSYS_ENV による development / paper_trading / live の切替
  - paper_trading では MockBroker を使用し、paper_trading 用の SQLite に完全分離して記録
- 監視: SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - kill.flag による安全停止（Kill Switch）
  - stop_requested.flag によるループ停止
- ロギング: 共通の setup_logging によるコンソール＋日次ローテートログ
- DuckDB を使ったリサーチ用テーブル（prices_daily / raw_financials 等）
- OpenAI を利用したニュースセンチメント（score_news）・レジーム判定（score_regime）
- ユーティリティ CLI: .env ウィザード（config_setup）、設定検証（validate_config）、ペーパートレード検証レポート

準備・セットアップ
------------------

前提
- Python 3.10 以上（typing の | 演算子などを使用）
- システムに sqlite3 は標準モジュールで利用可
- 推奨パッケージ（最低限）:
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML（validate_config の YAML 検証で使用）
インストール例:
  pip install duckdb psutil openai PyYAML

リポジトリ初期化
1. リポジトリルートに移動（パッケージは src/kabusys を想定）
2. 仮想環境を作成して依存をインストール

環境変数 (.env)
- .env はルートに配置して自動読み込みされます（.env.local を上書きで読み込み可能）。
- .env を対話式に作成/更新するには:
    python -m kabusys.config_setup
- 生成後、設定検証を行う:
    python -m kabusys.validate_config
  --strict を付けると警告も FAIL 扱い（exit code 1）

主な必須環境変数
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — News NLP / Regime Detector を使う場合（任意だが使うなら必須）
その他（デフォルトあり）
- KABUSYS_ENV (development|paper_trading|live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db (paper_trading 用)
- LOG_LEVEL — デフォルト: INFO
- PAPER_FILL_MODE — paper_trading の取引模擬挙動（instant, partial, never, reject）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag をクリアするか（開発時のみ 1 推奨）

使い方（起動 / CLI）
--------------------

1) ExecutionEngine（発注エンジン）の起動
- 本番/ペーパーは KABUSYS_ENV に依存
- 起動:
    python -m kabusys.run_execution
- 挙動:
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、PAPER_TRADING_SQLITE_PATH に記録
  - 起動前に data/stop_requested.flag があれば起動せず終了
  - ExecutionEngine は PID ファイル（data/execution.pid 等）を管理

2) Monitoring（監視ループ）の起動
- 起動:
    python -m kabusys.run_monitoring
- 説明:
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - 監視は常に本番用 sqlite_path を使用（環境に依らず）
  - stop_requested.flag が存在するとループを終了

3) .env ウィザード（対話式）
    python -m kabusys.config_setup

4) 設定検証
    python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いで exit code 1

5) ペーパートレード検証レポート
- 使用例:
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db（--db で上書き可能）
  - レポート項目: 稼働率、注文成功率、送信率、レイテンシ（P95）等

6) AI / リサーチ機能（スクリプトや別プロセスから呼び出し）
- ニューススコアリング:
    from kabusys.ai import score_news
    score_news(duckdb_conn, target_date, api_key=None)  # api_key を渡すか OPENAI_API_KEY を設定
- レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key=None)

監視 / Kill Switch の仕組み
-------------------------
- KillSwitch は RiskMonitor 等の結果から条件を満たすと data/kill.flag を書き込みます（ExecutionEngine は起動時にこのフラグを検出して停止などの挙動を取ります）。
- stop_requested.flag（data/stop_requested.flag）は run_monitoring/run_execution のループ停止用フラグです（手動で作成してシャットダウン可能）。
- KILL_FLAG_CLEAR_ON_START=1 を設定すると ExecutionEngine 起動時に kill.flag を自動でクリアします（本番では 0 推奨）。

ログ
---
- 共通の setup_logging を使用し、コンソール（stdout）と日次ローテートファイルログ（logs/<app_name>.log）へ出力します。
- ログレベル: LOG_LEVEL 環境変数または引数で制御。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要モジュール構成（抜粋）です:

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / .env 自動読み込みロジック
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト

  - ai/
    - news_nlp.py             — ニュースを LLM でスコアリング
    - regime_detector.py      — 市場レジーム判定

  - monitoring/
    - monitoring_db.py        — SQLite 用の永続化層（テーブル作成・読み書き）
    - system_monitor.py       — システム状態 / データ鮮度監視
    - trade_monitor.py        — 発注 / 注文状態監視（存在）
    - risk_monitor.py         — ドローダウン / ポジション上限監視
    - kill_switch.py          — kill.flag 書き込みユーティリティ
    - monitoring_engine.py    — 各 Monitor を束ねるポーリングエンジン
    - alert_manager.py        — 通知管理（LINE 等、存在する想定）

  - execution/
    - execution_engine.py     — ExecutionEngine（存在）
    - broker_factory.py       — ブローカークライアント選定（Mock/Real）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py

  - portfolio/
    - portfolio_builder.py    — 候補選定、重み計算
    - position_sizing.py      — 株数計算、資金割当
    - risk_adjustment.py      — セクターキャップ、レジーム乗数

  - research/
    - factor_research.py      — モメンタム / ボラ / バリュー等の計算（DuckDB）
    - feature_exploration.py  — 将来リターン、IC、統計サマリ

  - data/                     — 実行時に使われるデータファイル
    - monitoring.db (デフォルト)
    - paper_trading.db (paper mode)
    - kabusys.duckdb
  - tools/
    - paper_verification_report.py

注意事項 / トラブルシューティング
---------------------------------
- 必須の環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）が未設定だと起動時にエラーになります。まず python -m kabusys.config_setup → python -m kabusys.validate_config で確認してください。
- OpenAI を使用する機能は OPENAI_API_KEY が必要です。API のクォータや料金に注意してください。
- validate_config は PyYAML が無いと config/*.yaml の中身チェックをスキップします（警告）。
- DuckDB / SQLite のパスの親ディレクトリが存在しない場合、起動時に自動作成される場合がありますが、ログ出力ディレクトリ (logs/) は自動作成されます。作成に失敗するとファイルログは無効化されコンソールのみになります。
- MONITOR_POLL_INTERVAL を 0 など不正な値にするとデフォルト（60秒）にフォールバックします。

開発者向けメモ
----------------
- 設定は config.py の Settings クラス経由で参照してください（型チェックやバリデーションを内包）。
- Monitoring / Execution の起動ロジックは run_monitoring.py / run_execution.py を参照。stop フラグは data/stop_requested.flag、Kill Switch は data/kill.flag を利用します。
- DuckDB 接続は research / ai モジュールで受け渡して使います。DB スキーマ（prices_daily, raw_financials, raw_news など）に依存するため、テスト用 DB を用意してください。

ライセンス・貢献
----------------
- 本ドキュメントはコードベースに基づくREADME の簡易版です。ライセンス等はリポジトリルートの LICENSE を参照してください（存在する場合）。

以上。必要に応じて「インストール依存リスト」「具体的な .env の例」「起動例の systemd ユニット / docker-compose 設定」などを追加で作成できます。何を追加したいか教えてください。