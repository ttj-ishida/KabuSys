# KabuSys

日本株向け自動売買システムの一部をまとめたリポジトリ（ライブラリ + 起動スクリプト群）。  
このREADME はソース内の実装に基づいてプロジェクトの概要、機能、セットアップ、使い方、ディレクトリ構成を日本語で説明します。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要なコンポーネント群を提供します。主な役割は次のとおりです。

- 実行エンジン（ExecutionEngine）: ブローカークライアント経由で発注・注文管理を行う。
- 監視（Monitoring）: システム状態、注文状況、リスク（ドローダウンや保有数）を定期監視しアラートや Kill Switch を制御。
- 研究（Research）: DuckDB 上の株価・財務データからファクターを算出する機能（モメンタム、ボラティリティ、バリュー等）。
- ポートフォリオ構築: 候補選定、重み計算、ポジションサイジング、セクター制約などの純関数群。
- AI 支援: ニュースの NLP スコアリング、レジーム判定（OpenAI を使用可能）。
- ユーティリティ: ロギング設定、プロセス優先度設定、設定ウィザードと検証ツールなど。
- 運用ツール: ペーパートレード検証レポート生成スクリプト等。

設計方針として、データ処理は可能な限り DuckDB / SQLite 上で行い、発注や外部 API 呼び出しは明示的に分離されています。ペーパートレードは本番 DB と完全に分離されます。

---

## 主な機能一覧

- 設定管理
  - .env 自動読み込み / 対話式設定ウィザード（kabusys.config_setup）
  - 起動前の設定検証 CLI（kabusys.validate_config）
- 実行系
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - Paper Trading モード（KABUSYS_ENV=paper_trading）では MockBroker を使用し data/paper_trading.db に記録
- 監視系
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - 監視ログの永続化（SQLite）
  - Kill Switch（条件を満たすと data/kill.flag を書き込み ExecutionEngine を停止）
  - run_monitoring.py による継続ポーリング起動（MONITOR_POLL_INTERVAL で間隔変更可）
- 研究・分析
  - ファクター算出（momentum, volatility, value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- ポートフォリオ構築
  - 候補選定、等重 / スコア重み、リスクベースのポジション決定、セクターキャップ適用
- AI 機能（OpenAI）
  - ニュース記事をまとめて銘柄ごとにセンチメントを算出し ai_scores テーブルへ保存（kabusys.ai.news_nlp）
  - レジーム判定（kabusys.ai.regime_detector）
- 運用ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
- ユーティリティ
  - 統一ログ設定（ログの stdout 出力 + 日次ローテートファイル出力）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

---

## セットアップ手順（ローカル開発向け）

※ 実行前に Python 環境を作成してください（推奨: venv）。

1. リポジトリをクローンし Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（プロジェクトに requirements.txt がある場合はそちらを使用してください）。主な依存例:
   - duckdb
   - psutil
   - openai
   - pyyaml (config 検証であれば任意)
   - （その他: sqlite3 は標準ライブラリ）
   例:
   - pip install duckdb psutil openai pyyaml

3. .env 作成
   - 対話式で作成: python -m kabusys.config_setup
     - J-Quants のリフレッシュトークンや kabuステーション API パスワード、OpenAI キー（使う場合）などを設定します。
   - 手動で作成する場合は .env.example を参照して .env を作成してください（.env.example がない場合は config_setup を利用）。

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

5. データディレクトリ準備
   - デフォルトでは次のファイル／ディレクトリを使用します:
     - data/monitoring.db（SQLite）
     - data/kabusys.duckdb（DuckDB）
     - logs/（ログ出力）
   - 必要に応じて .env の DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を変更してください。

注意: 起動スクリプトは自動で DB テーブル作成やマイグレーションを行う箇所を含みます（監視 DB は init_monitoring_db で作成）。

---

## 使い方

以下は主要な実行方法の例です。

1. 設定ウィザード（.env の生成／更新）
   - python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config
   - 厳密モード: python -m kabusys.validate_config --strict

3. ExecutionEngine の起動（発注エンジン）
   - python -m kabusys.run_execution
   - 挙動:
     - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
     - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
     - 実行中は data/execution.pid に PID を書きます。
     - 停止は data/stop_requested.flag（手動作成）や Kill Switch（data/kill.flag）で制御されます。

4. Monitoring の起動（監視ループ）
   - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定できます（デフォルト 60 秒）。
   - 監視は本番 sqlite_path を使用（KABUSYS_ENV に依存しない）。
   - 監視ループの停止は data/stop_requested.flag（作成で停止）または Ctrl+C。

5. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB 指定:
     - --db PATH で PAPER_TRADING_SQLITE_PATH を上書き可能

6. AI 関連（プログラムから利用）
   - ニュース NLP スコアリング:
     - from kabusys.ai.news_nlp import score_news
     - score_news(conn, target_date, api_key=None)  # api_key が None の場合 OPENAI_API_KEY 環境変数を参照
   - レジーム判定:
     - from kabusys.ai.regime_detector import score_regime
     - score_regime(conn, target_date, api_key=None)
   - OpenAI API のキーは環境変数 OPENAI_API_KEY に設定するか、関数引数で渡します。

7. ログ
   - ログは stdout に出力されるほか、デフォルトで logs/<app_name>.log に日次ローテーションで保存されます。
   - LOG_DIR 環境変数でログディレクトリを変更できます。

8. 停止・Kill Switch
   - ExecutionEngine を強制停止したいとき:
     - data/stop_requested.flag を作成すると run_execution / run_monitoring のループが終了します（run_execution は検知して engine.stop() を呼ぶ）。
   - 自動的な停止トリガ（Kill Switch）:
     - RiskMonitor 等の条件に応じて KillSwitch が data/kill.flag に理由を書き込みます。ExecutionEngine はこれを検出して停止します。
   - Kill Flag を手動でクリアする場合:
     - data/kill.flag を削除してください。（起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動クリアしますが本番では推奨されません）

---

## 環境変数（主要）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用
  - KABU_API_PASSWORD — kabuステーション API パスワード

- 実行モード
  - KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
    - paper_trading: MockBroker を使用しペーパートレード DB（PAPER_TRADING_SQLITE_PATH）に記録
    - live: 本番モード（注意が必要）

- データベース / ファイル
  - DUCKDB_PATH — DuckDB ファイル（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
  - PID_FILE_PATH — Execution PID ファイル（デフォルト data/execution.pid）
  - KILL_FLAG_PATH — Kill flag（デフォルト data/kill.flag）

- ログ
  - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
  - LOG_DIR — ログ出力ディレクトリ（デフォルト logs/）

- モニタリング
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒。デフォルト 60）

- Paper Trading / Mock Broker
  - PAPER_FILL_MODE — instant | partial | never | reject（デフォルト instant）

- OpenAI
  - OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要なモジュールとスクリプトです（抜粋）。

- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数・設定管理（自動 .env ロード・Settings クラス）
    - config_setup.py           — 対話式 .env 作成ウィザード
    - validate_config.py        — 起動前の設定検証 CLI
    - run_execution.py          — ExecutionEngine 起動スクリプト
    - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
    - tools/
      - paper_verification_report.py — ペーパートレード検証レポート生成
    - ai/
      - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
      - regime_detector.py      — 市場レジーム判定（OpenAI、ETF + ニュース合成）
      - __init__.py
    - monitoring/
      - monitoring_db.py        — SQLite テーブル作成・永続化 API
      - system_monitor.py       — システム状態・データ鮮度監視
      - trade_monitor.py        — 注文ログ監視（存在）
      - risk_monitor.py         — ドローダウン・ポジション上限監視
      - kill_switch.py          — Kill Switch 書き込みロジック
      - monitoring_engine.py    — 複数 Monitor の統合ポーリング
      - alert_manager.py        — アラート送信（存在）
    - execution/                — ExecutionEngine、OrderManager 等（存在）
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py      — momentum / volatility / value 等の算出
      - feature_exploration.py  — forward returns / IC / 統計サマリー
      - __init__.py
    - utils/
      - logging_setup.py        — ログ初期化ユーティリティ
      - process_priority.py     — プロセス優先度 / CPU affinity 設定
      - __init__.py
    - data/                     — 実行時に生成される DB / flag / pid 等（プロジェクトルート/data）

（注）上の構成には一部参照されるモジュールやファイルが省略されている可能性があります。実際のリポジトリで全ファイルを確認してください。

---

## 運用上の注意

- 本番モード（KABUSYS_ENV=live）では Kill Switch や LINE 通知設定などを慎重に確認してください。validate_config は live の場合に警告を出します。
- OpenAI を使用する機能は外部 API 呼び出しを伴うため、API キー管理とコストに注意してください。API 呼び出し失敗時はフェイルセーフ（スコア 0.0 など）で継続する実装になっていますが、運用ポリシーを明確にしてください。
- run_execution / run_monitoring の停止制御は data/stop_requested.flag と data/kill.flag によって行われます。これらの flag の取り扱い（自動クリア設定など）に注意してください（KILL_FLAG_CLEAR_ON_START）。
- ログディレクトリの作成に失敗しても stdout 出力は行われます。CI/cron 等での実行時はログ出力先や権限を確認してください。

---

もし README に追加してほしい点（例: 具体的な設定例、docker-compose サンプル、詳細な API ドキュメント）があれば教えてください。必要に応じて追記します。