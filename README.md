# KabuSys — 日本株自動売買システム

このリポジトリは日本株の自動売買・バックテスト・リサーチ用ユーティリティ群を収録したパッケージです。モジュール構成は、発注エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI（ニュースNLP・レジーム判定）などに分かれています。

主な設計方針
- 本番/ペーパートレードを環境で切替可能（KABUSYS_ENV）
- DBは DuckDB（分析） と SQLite（監視・トレードログ）を用途に応じて利用
- .env ウィザード / 設定検証ツールを提供し起動前チェックを支援
- OpenAI API を利用した NLP モジュール（外部 API キー必要）
- モジュールは副作用を最小にし、テストしやすい純粋関数／クラスを重視

---

機能一覧
- 環境設定ウィザード: .env を対話式に作成/更新（kabusys.config_setup）
- 設定検証: .env / config/*.yaml の事前チェック（kabusys.validate_config）
- 実行エンジン起動スクリプト: 発注エンジンを起動（kabusys.run_execution）
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し paper_trading DB に隔離
- 監視ループ起動スクリプト: システム監視（CPU/メモリ/ディスク/プロセス/データ鮮度）を定期実行（kabusys.run_monitoring）
- モニタリング/アラート: system_status / trade_logs / risk_logs / dashboard 保存（monitoring_db）
- Kill Switch: リスク条件で data/kill.flag を書き込み、ExecutionEngine を安全停止
- ペーパートレード検証レポート生成 CLI（kabusys.tools.paper_verification_report）
- ポートフォリオ構築: 候補選定、重み計算、ポジションサイズ決定（portfolio パッケージ）
- リサーチ: ファクター計算・特徴量解析（research パッケージ）
- AI モジュール:
  - news_nlp.score_news: ニュースを OpenAI でセンチメント化し ai_scores テーブルへ書込
  - regime_detector.score_regime: ma200 とマクロセンチメントを合成して market_regime を判定
- ユーティリティ: ロギング設定、プロセス優先度・CPU affinity 設定 など（utils）

---

セットアップ手順（ローカル開発向け）

前提
- Python 3.10 以上を推奨（typing の | 合成に依存）
- SQLite は標準ライブラリで使用可能
- 外部ライブラリ: duckdb, psutil, openai（必須機能に応じて）、PyYAML（設定 YAML を検証する場合）
  例:
    pip install duckdb psutil openai PyYAML

.env の作成
1. リポジトリルートでウィザードを実行:
    python -m kabusys.config_setup
   - 対話に従い .env を生成します（デフォルトは project_root/.env）。
2. 必須環境変数:
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - OPENAI_API_KEY（AI 機能を使う場合に必須）
   ほかは .env ウィザードで説明あり。

自動 .env ロード
- .env / .env.local は自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- .env の雛形は config_setup で作成できます。

設定の検証
    python -m kabusys.validate_config
- --strict を付けると警告があっても失敗（exit 1）扱いになります。

依存 DB ファイル
- DuckDB（分析）: デフォルト data/kabusys.duckdb（環境変数 DUCKDB_PATH で変更可）
- Monitoring SQLite: デフォルト data/monitoring.db（環境変数 SQLITE_PATH で変更可）
- Paper Trading SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading のとき使用。PAPER_TRADING_SQLITE_PATH で変更可）

ログ
- ログは stdout とファイルの両方へ出力（kabusys.utils.logging_setup）。
- ファイルログは logs/<app_name>.log に日次ローテーションで保存（デフォルト 30 日保持）。
- LOG_DIR 環境変数でログディレクトリを変更可能。

---

環境変数（代表的なもの）
- KABUSYS_ENV: execution 環境（development / paper_trading / live） デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必要）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定モード（instant / partial / never / reject） デフォルト: instant
- LOG_LEVEL: ログレベル（DEBUG/INFO/...） デフォルト: INFO
- LOG_DIR: ログ保存ディレクトリ（デフォルト logs/）
- PID_FILE_PATH: 実行エンジンの PID ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH: Kill Switch フラグファイル（デフォルト data/kill.flag）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒） デフォルト: 60
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（1=クリア）※本番では 0 推奨

注意点
- Monitoring は監視用 DB に関して「環境にかかわらず」 Settings.sqlite_path を使う設計（run_monitoring のコメント参照）。
- Execution は KABUSYS_ENV=paper_trading の場合、paper_trading 用 DB に切り替える（本番 DB と分離）。

---

よく使うコマンド（例）

1. .env 作成（ウィザード）
    python -m kabusys.config_setup

2. 設定検証
    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict

3. 監視ループ起動（デフォルトポーリング 60s）
    python -m kabusys.run_monitoring
   - 短い間隔にしたい場合:
       export MONITOR_POLL_INTERVAL=10
       python -m kabusys.run_monitoring
   - 停止:
     - プロセスに Ctrl+C
     - もしくはプロジェクトルート/data/stop_requested.flag を作成するとループが検知して終了します。

4. 実行エンジン起動
    python -m kabusys.run_execution
   - ペーパートレードで起動:
       export KABUSYS_ENV=paper_trading
       python -m kabusys.run_execution
   - 実行はデーモン化されずスレッドで動きます。停止は data/stop_requested.flag の作成、または Kill Switch による data/kill.flag 設定、Ctrl+C 等。

5. Paper Trading 検証レポート生成
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - --db で DB パス指定可能（優先順: --db > PAPER_TRADING_SQLITE_PATH > デフォルト）。

6. AI モジュール呼び出し（Python から）
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, date(2026,4,1), api_key="sk-...")

---

実装上の注意／運用メモ
- stop_requested.flag（data/stop_requested.flag）は run_* スクリプトがループ中に検出して安全終了するためのファイルです。手動停止用に使用できます。
- kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）は実行エンジンを停止させるためのシグナルです。KillSwitch が条件を満たすと書き込まれます。起動時に自動クリアする挙動は KILL_FLAG_CLEAR_ON_START で制御します（本番はクリアしない設定推奨）。
- MonitoringDB.init_monitoring_db は DB のマイグレーションを最小限実行し、テーブル/カラムがなければ作成します。
- OpenAI 呼び出しはレート制限や一時エラーに対してリトライ（指数バックオフ）実装があります。APIキーは必ず適切に保護してください。
- PyYAML がない場合、validate_config は YAML 内容検証をスキップします（警告が出ます）。

---

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/設定読み込み (Settings)
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py       — monitoring DB 層（SQLite）
    - system_monitor.py      — システム監視
    - trade_monitor.py       — （発注監視実装がここに存在）
    - risk_monitor.py        — ドローダウン・ポジション監視
    - monitoring_engine.py   — 各 Monitor を束ねる
    - kill_switch.py         — Kill Switch 実装（flag ファイル操作）
    - alert_manager.py       — （アラート送信管理）
  - execution/
    - execution_engine.py    — ExecutionEngine（起動/セッション管理）
    - broker_factory.py      — Broker クライアント生成（実/モック）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI 呼び出し）
    - regime_detector.py     — 市場レジーム判定（OpenAI + MA）
  - tools/
    - paper_verification_report.py
  - data/                    — 実行時に使う DB/flag/pid/等（運用環境）
  - logs/                    — ログ出力（デフォルト）

（注）上記は本リポジトリ内の主要モジュールと役割を抜粋したものです。実際の運用では execution/ 内の各コンポーネント（BrokerClient 実装など）を環境に合わせて用意する必要があります。

---

トラブルシューティング（よくあるケース）
- .env の必須変数が足りない → python -m kabusys.validate_config で確認
- ログファイルが作成されない → LOG_DIR 権限を確認。logging_setup は作成失敗時にコンソール出力にフォールバックします。
- OpenAI 呼び出しで 401/キーエラー → OPENAI_API_KEY を再確認
- run_monitoring / run_execution がすぐ終了する → data/stop_requested.flag や data/kill.flag の存在を確認（不要なら削除）

---

ライセンス・バージョン
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）

---

その他
- この README はソース内の docstring・コメントに基づいて作成しています。実行時の詳細や追加オプションは各モジュールの docstring および CLI のヘルプ（python -m module -h）を参照してください。