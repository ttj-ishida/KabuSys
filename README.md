# KabuSys

日本株自動売買システムのライブラリ・実行スクリプト群。本リポジトリは以下の機能群（注文実行、監視、ポートフォリオ構築、リサーチ、AI連携など）を提供します。

- バックグラウンドで実行する ExecutionEngine / Monitoring の起動スクリプト
- 環境設定ウィザード・設定検証ツール
- Paper Trading 検証レポート生成ツール
- ファクター計算、ポートフォリオ構築、リスク調整、ポジションサイズ計算などの純粋関数群
- ニュースの LLM スコアリング / 市場レジーム判定（OpenAI 使用可）
- 監視ログ（SQLite）永続化、各種モニタ、Kill Switch 実装

以下に利用方法や構成をまとめます。

注意: .env や API キーなどの秘密情報は絶対にリポジトリへコミットしないでください。

---

## 機能一覧

- Execution
  - 実際の発注処理（本番/ペーパーを切替）
  - BrokerClientFactory によるブローカー切替（KABUSYS_ENV に依存）
  - リスク管理（Rate limit、最大ポジション率など）
- Monitoring
  - システム稼働状況（CPU / Memory / Disk / プロセス生存）を定期記録
  - 注文滞留・約定異常・リスク（ドローダウン、ポジション上限）監視
  - Kill Switch による安全停止（条件により data/kill.flag を作成）
- Portfolio construction
  - 候補選定、等分配・スコア加重、セクター上限、レジーム乗数、ポジションサイズ計算
- Research
  - DuckDB ベースのファクター計算（モメンタム/ボラティリティ/バリュー）
  - 将来リターン計算、IC（Information Coefficient）などの統計ツール
- AI
  - ニュースの LLM センチメント集計（OpenAI）
  - マクロニュース + ma200 を使った市場レジーム判定
- ユーティリティ
  - .env 対話式作成ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading レポート（tools/paper_verification_report.py）
  - ログ設定・プロセス優先度設定ユーティリティ

---

## セットアップ手順（ローカル開発向け）

1. Python 環境を用意（推奨: 3.10+）
2. 依存ライブラリをインストール
   - duckdb, psutil, openai, (PyYAML は config 検証で推奨) など
   - 例: pip install -r requirements.txt （requirements.txt がある場合）
3. プロジェクトルートへ移動（.git または pyproject.toml が存在するディレクトリ）
4. 環境変数の初期作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - ウィザードは .env を作成します（デフォルト: PROJECT_ROOT/.env）
5. 設定検証（必須環境変数のチェック）
   - python -m kabusys.validate_config
   - 本番時は --strict を付けると警告も失敗として扱います
6. データディレクトリの確認
   - デフォルトで使用されるファイル:
     - DuckDB: data/kabusys.duckdb
     - SQLite（監視用）: data/monitoring.db
     - Paper Trading DB: data/paper_trading.db
     - ログディレクトリ: logs/
   - 必要に応じて .env の DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を変更

---

## 主要環境変数（抜粋）とデフォルト

- KABUSYS_ENV: 実行環境。development / paper_trading / live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: （必須）J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD: （必須）kabuステーション API パスワード
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視 DB）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...。デフォルト: INFO）
- LOG_DIR: ログ保存ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI を使う機能で使用（news_nlp / regime_detector）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant/partial/never/reject。デフォルト: instant）
- MONITOR_POLL_INTERVAL: monitoring のポーリング間隔（秒。デフォルト 60）※ run_monitoring 用

その他は config_setup ウィザードで確認できます。

---

## 使い方（起動スクリプト）

- 環境の準備: .env を作成・確認 → validate_config でチェック
- 実行（サンプル）

1. Monitoring を起動（稼働状況をポーリング）
   - MONITOR_POLL_INTERVAL を指定して間隔を変更できます（秒）
   - 例:
     - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
   - 停止方法:
     - プロセスの KeyboardInterrupt（Ctrl+C）
     - またはプロジェクト内の data/stop_requested.flag を作成するとループが終了します

2. Execution を起動（発注エンジン）
   - KABUSYS_ENV によって動作が変わります:
     - paper_trading: MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と分離）
     - live / development: 実ブローカーとの連携（設定に依存）
   - 例:
     - python -m kabusys.run_execution
   - 停止方法:
     - data/stop_requested.flag を作成するか、Kill Switch（data/kill.flag）により停止指示が入るとエンジン停止を試みます
   - 実行時は data/execution.pid を PID ファイルに書きます

3. .env の対話式作成
   - python -m kabusys.config_setup

4. 設定検証
   - python -m kabusys.validate_config
   - --strict で警告も失敗扱いにできます

5. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - または環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定可能

6. AI 機能（プログラム的に呼び出し）
   - OpenAI API を利用するために OPENAI_API_KEY を設定
   - 例（Python から）:
     - from kabusys.ai import score_news
     - score_news(duckdb_conn, target_date, api_key=os.environ["OPENAI_API_KEY"])
   - news_nlp は gpt-4o-mini を想定（モデル名は定数で管理）

---

## 停止・Kill スイッチ

- 停止フラグ（プロセス終了のための簡易制御）
  - data/stop_requested.flag: run_monitoring / run_execution がループ内で監視している停止フラグ
  - data/kill.flag: KillSwitch が条件を満たしたときに作成され、ExecutionEngine に停止指示を送るために使用
  - KILL_FLAG_CLEAR_ON_START=1 を .env に設定すると起動時に kill.flag を自動でクリアできます（本番環境では 0 推奨）

---

## ロギング

- 共通ロギングユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="...") を使用
- 出力:
  - コンソール（stdout）
  - 日次ローテーションのファイルログ（logs/<app_name>.log、30日保持）
- ログレベルは LOG_LEVEL 環境変数で制御可能

---

## ディレクトリ構成（主なファイル/モジュール）

プロジェクトの主要な構成は src/kabusys 以下にあります。代表的なツリーを示します（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / Settings
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_monitoring.py       — Monitoring ポーリングループ起動スクリプト
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py      — ログ初期化ユーティリティ
    - process_priority.py   — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py      — SQLite テーブル初期化 / 永続化 API
    - system_monitor.py     — システム状態・データ鮮度監視
    - trade_monitor.py      — 注文 / 約定監視（存在する想定）
    - risk_monitor.py       — ドローダウン・ポジション上限監視
    - kill_switch.py        — kill.flag 書込・評価
    - monitoring_engine.py  — 監視コンポーネントのオーケストレーション
    - alert_manager.py      — アラート送信（LINE 等、存在する想定）
  - execution/
    - execution_engine.py   — ExecutionEngine（存在する想定）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - portfolio/
    - portfolio_builder.py  — 候補選定・重み計算
    - position_sizing.py    — 株数決定・単元丸め・キャップ
    - risk_adjustment.py    — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py    — モメンタム/ボラティリティ/バリュー計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計
  - ai/
    - news_nlp.py           — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py    — 市場レジーム判定（OpenAI + MA200）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - data/                    — 実行時に使用する DB / flag / pid 等（プロジェクトルート）

（注）上記は主要モジュールの抜粋です。各ディレクトリ内にはさらに補助モジュールが存在します。

---

## 開発時の注意点・設計方針（抜粋）

- .env の自動読み込みは Settings モジュールで行われ、プロジェクトルート（.git または pyproject.toml）を基準に探索します。テスト時には KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
- Monitoring の DB（monitoring.db）は実行環境にかかわらずデフォルトの sqlite_path を使用します。一方、Execution は paper_trading モードで専用 DB を使って本番 DB と分離します。
- LLM 呼び出し（news_nlp / regime_detector）は OpenAI のエラー（429 / timeout / 5xx）に対してエクスポネンシャルバックオフでリトライする設計です。API キーが未設定の場合はエラー（ValueError）を投げます。
- DuckDB 接続を受け取り SQL を組み合わせてデータ処理を行い、研究/リサーチ処理は本番口座や発注 API へアクセスしないよう分離されています。
- ログは stdout とファイルの両方へ出力。ファイル出力に失敗した場合はコンソールのみで継続します。

---

## 例: よくあるコマンド

- 環境変数ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- Monitoring 起動（デフォルト間隔 60 秒）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Execution 起動
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - KABUSYS_ENV=live python -m kabusys.run_execution
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

README は以上です。追加で「デプロイ手順」「systemd ユニット例」「監視アラート送信先の設定方法」など特定の運用ドキュメントが必要であれば、用途に合わせてサンプルを作成します。どの情報を優先して載せますか？