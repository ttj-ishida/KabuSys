# KabuSys

日本株自動売買システムのコアライブラリおよび起動スクリプト群。

このリポジトリは、シグナル生成・ポートフォリオ構築・注文実行・監視・AIベースのニュース評価・研究用ユーティリティなどを含む自動売買プラットフォームの一部です。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要コマンド）
- 主要環境変数（.env）
- 実装上の注意点
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株向けの自動売買システム用ライブラリ群です。
- 戦略のためのファクター計算、ポートフォリオ構築、ポジションサイジング、注文処理（ExecutionEngine）、監視・アラート、AI（ニュースセンチメント・レジーム判定）など、売買フローの各フェーズをモジュール化しています。
- 実行環境は development / paper_trading / live を想定しており、paper_trading モードでは本番 DB と完全に分離したペーパートレード用 DB を使用します。

機能一覧
- 設定管理
  - .env 読み込み（.env / .env.local 自動読み込み、必要時無効化可）
  - 設定ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
- 実行エンジン起動スクリプト
  - run_execution.py: ExecutionEngine を起動（実取引/ペーパー切替）
  - run_monitoring.py: SystemMonitor のポーリングループ起動（監視ログを SQLite に保存）
- 監視（monitoring）
  - SystemMonitor: プロセス生存確認、CPU/メモリ/ディスク、データ鮮度チェック
  - TradeMonitor: 注文滞留・約定異常価格の検出
  - RiskMonitor: ドローダウン・ポジション数上限の監視とリスクイベント記録
  - KillSwitch: 条件に応じて kill.flag を書いて ExecutionEngine を停止させる仕組み
  - MonitoringDB: 監視ログの永続化（SQLite）
- ポートフォリオ構築（portfolio）
  - 候補選定、等重 / スコア加重、セクター上限適用、レジーム乗数、ポジションサイズ計算（単元丸め、aggregate cap）
- リサーチ（research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- AI 関連（ai）
  - news_nlp: OpenAI を使った銘柄ごとのニュースセンチメント評価（ai_scores へ書込）
  - regime_detector: ETF（1321）MA とマクロニュースの LLM センチメントを合成して市場レジーム判定
- ツール
  - tools.paper_verification_report: ペーパートレード DB から検証レポートを生成（稼働率・注文成功率・レイテンシ等）

セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. Python と仮想環境
   - 推奨: Python 3.10 以上（コードは 3.10 の構文（X | None 等）を使用）
   - 仮想環境作成例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - main の依存: duckdb, psutil, openai
   - 開発／追加: PyYAML（設定検証で YAML を検証したい場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt がある場合はそれを使用してください）

4. .env の準備
   - 対話式ウィザードで初期 .env を作成:
     - python -m kabusys.config_setup
   - 設定を確認:
     - python -m kabusys.validate_config
   - .env はリポジトリにコミットしないでください（秘密情報が含まれます）。

5. データディレクトリ
   - デフォルトの DB 等は data/ 以下を想定します（例: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db）
   - 必要に応じて .env の DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を変更してください。

主要な使い方（コマンド）
- 設定ウィザード（.env の作成・更新）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code 1）
- ExecutionEngine を起動（実行）
  - python -m kabusys.run_execution
  - 概要:
    - KABUSYS_ENV に応じて本番/ペーパーを切替
    - paper_trading の場合は MockBrokerClient を使用し data/paper_trading.db に注文を記録
    - 停止制御: data/stop_requested.flag の検出で停止
    - PID ファイル: data/execution.pid（デフォルト）
- Monitoring を起動（ループ）
  - python -m kabusys.run_monitoring
  - 概要:
    - SystemMonitor を一定間隔で実行して monitoring DB（sqlite）に記録
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可（デフォルト 60）
    - 停止フラグ: PROJECT_ROOT/data/stop_requested.flag を検出して終了
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH 環境変数より優先）
  - レポートでは稼働率・注文成功率・送信率・P95レイテンシ等を算出し PASS/FAIL を出力
- AI 機能
  - OpenAI API を使う機能（news_nlp.score_news / regime_detector.score_regime）を使うには OPENAI_API_KEY が必要
  - 例: Python から呼び出す:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key="sk-...")

主要な環境変数（.env に設定）
- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用のリフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API パスワード
- 推奨 / 省略可（デフォルトあり）
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - DUCKDB_PATH: 分析用 DuckDB（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
  - LOG_LEVEL: ログレベル（INFO 等）
  - OPENAI_API_KEY: OpenAI を使う場合は必須（ai モジュール）
  - PAPER_FILL_MODE: ペーパートレード時の約定モード（instant|partial|never|reject、デフォルト instant）
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
  - KILL_FLAG_PATH / PID_FILE_PATH / その他監視パラメータ（Settings 経由で取得）

実装上の注意点 / 動作上の挙動
- run_execution:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し本番 DB と分離して data/paper_trading.db に記録します。
  - 起動時に data/stop_requested.flag が存在する場合は起動を中止します。
  - 実行中は data/execution.pid に PID を書きます（実装で指定された pid_file を使用）。
- run_monitoring:
  - 監視は常に本番 sqlite_path を使用して監視ログを記録します（KABUSYS_ENV に依らず production path を想定）。
  - プロセス優先度を上げる処理（set_process_priority("high")）を起動時に行います。権限や OS によっては警告が出ます。
- Kill Switch:
  - RiskMonitor 等の結果により KillSwitch がトリガーされると data/kill.flag が作成され、ExecutionEngine 側で検出すると停止します。
  - 本番では KILL_FLAG_CLEAR_ON_START を 0 にすることを推奨（自動クリアは危険）。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は idempotent（既存テーブルがない場合のみ作成）で、既存 DB に対して必要最低限のマイグレーション（列追加）を行います。
- AI 呼び出し:
  - OpenAI 呼び出しはバックオフ・リトライを実装していますが、APIキー・レート制限などの理由で失敗する可能性があります。失敗時はフェイルセーフで一部機能を 0 相当でフォールバックする設計です。

ディレクトリ構成（主要）
- src/kabusys/
  - __init__.py
  - config.py  — 環境変数・設定管理
  - config_setup.py  — .env 対話ウィザード
  - validate_config.py  — 設定検証 CLI
  - run_execution.py  — ExecutionEngine 起動スクリプト
  - run_monitoring.py  — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (実装ファイルあり)
    - monitoring_engine.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - __init__.py
    - process_priority.py
  - execution/        (注文実行関連 — OrderManager, ExecutionEngine, BrokerFactory 等、別ファイル群)
  - data/             (データアクセス / pipeline 等、別モジュール参照あり)
  - monitoring.db / paper_trading.db 等は data/ 以下に配置されるのがデフォルト

よくあるコマンド例
- .env 作成（ウィザード）
  - python -m kabusys.config_setup
- 設定チェック
  - python -m kabusys.validate_config
- 実行エンジン開始（ペーパートレード）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- 監視開始（別プロセスで実行）
  - python -m kabusys.run_monitoring
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10

補足
- .env は秘密情報を含むため決して Git にコミットしないでください。
- 本リポジトリの一部機能は外部サービス（OpenAI、kabuステーション、J-Quants）を必要とします。テスト/開発時は API キー等を用意するか、該当機能を無効化してください。
- 実運用（KABUSYS_ENV=live）では、設定検証ツールで警告や必須項目を必ず確認してください（validate_config の --strict オプション推奨）。

---

この README はコードの現状に基づいて作成しています。実際の運用や追加のスクリプト（例: Broker クライアント実装・ExecutionEngine の詳細・AlertManager の外部通知設定等）は別途ドキュメントを参照してください。質問や項目追加の要望があれば教えてください。