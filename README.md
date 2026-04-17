# KabuSys

日本株向けの自動売買システム（ライブラリ / 実行スクリプト群）

このリポジトリは、売買ロジック・ポートフォリオ構築・実行エンジン・監視・研究ツール群を含むモジュール群です。DuckDB / SQLite をデータ基盤に使い、OpenAI を用いたニュース NLP やレジーム判定などの機能も備えています。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（起動例）
- 環境変数一覧（重要）
- ファイル/ディレクトリ構成

---

プロジェクト概要
- 日本株を対象とした自動売買プラットフォームのコアライブラリ。
- 以下の主要コンポーネントを含みます。
  - ExecutionEngine: 注文作成・ブローカー通信・リスク管理・リコンシリエーション
  - Monitoring: システム状態・注文状態・リスク（ドローダウン等）の監視、LINE 通知
  - Portfolio/Strategy: 候補選定、重み付け、ポジションサイズ計算、セクター制限などの純関数群
  - Research: ファクター計算・特徴量探索ツール（DuckDB を利用）
  - AI: OpenAI を使ったニュースセンチメント（news_nlp）や市場レジーム判定（regime_detector）
  - Tools: 検証レポート生成スクリプト等

主な機能一覧
- 実行
  - 実際のブローカー接続または Paper Trading（モック）で発注を行う実行エンジン（run_execution.py）
  - 再起動時のリコンシリエーション機能（Reconciler）
- 監視
  - 定期ポーリングによる CPU / メモリ / ディスク / プロセス監視（run_monitoring.py）
  - 注文滞留・約定異常・ドローダウン監視
  - kill.flag による安全停止シグナルの書き込み
  - LINE によるアラート通知（AlertManager）
  - Streamlit を使った監視ダッシュボード（streamlit_dashboard.py）
- ポートフォリオ構築（純粋関数）
  - 候補選定、等重／スコア重み付け、ポジションサイズ計算、セクター制限、レジーム乗数
- 研究用ツール
  - モメンタム・ボラティリティ・バリューファクター計算（DuckDB）
  - 将来リターン・IC・統計サマリ
- AI連携
  - OpenAI を用いたニュースセンチメント評価（銘柄毎）と market_regime 判定
  - リトライ・バックオフ・レスポンス検証を考慮した実装

---

セットアップ手順（開発 / 実行環境）
1. Python（推奨: 3.10 以上）を用意
2. リポジトリをチェックアウト
3. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
4. 必要パッケージをインストール（例）
   - pip install -r requirements.txt
   ※ requirements.txt が無い場合は主に以下を使います:
     - duckdb, psutil, requests, openai, streamlit
5. （任意）.env ファイルをプロジェクトルートに配置
   - 設定は環境変数または .env / .env.local で読み込まれます。
   - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

基本的なディレクトリ（プロジェクトルートが .git / pyproject.toml を基準に自動検出されます）

- data/ — 実行時の DB やフラグファイル（実行前に作成される場合あり）
  - data/monitoring.db (SQLITE_PATH default)
  - data/paper_trading.db (PAPER_TRADING_SQLITE_PATH default)
  - data/kabusys.duckdb (DUCKDB_PATH default)
  - data/execution.pid, data/kill.flag, data/stop_requested.flag
- src/kabusys/ — パッケージ本体（下記に詳細）

使い方（主要スクリプト・コマンド例）

- 実行エンジンを起動（本番・paper_trading による動作切替）
  - 実行:
    - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を利用し paper_trading 用の SQLite（data/paper_trading.db）を使います。本番 DB と分離されます。
    - 起動前に data/stop_requested.flag が存在すると起動せず終了します。
    - 実行中は data/execution.pid に PID が書かれます。プロセス優先度は High に設定しようと試みます。

- 監視ループを起動
  - 実行:
    - python -m kabusys.run_monitoring
  - 設定:
    - ポーリング間隔は MONITOR_POLL_INTERVAL 環境変数で上書き可能（秒）。デフォルト: 60
    - 監視は環境（KABUSYS_ENV）に関係なく本番用 sqlite_path（SQLITE_PATH）を使用します（監視データは共通で扱う想定）。
    - stop_requested.flag が存在するとループを終了します。

- Streamlit ダッシュボード起動
  - コマンド:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - オプション:
    - --db 引数で別パスの monitoring DB を指定可能

- Paper Trading 検証レポート生成
  - コマンド:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db または 環境変数 PAPER_TRADING_SQLITE_PATH を使用

- AI 機能（ニュース NLP / レジーム判定）
  - 実行例（ライブラリ関数）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")  ※ api_key を渡すか環境変数 OPENAI_API_KEY を設定
  - 注意:
    - OPENAI_API_KEY が必要です。未設定時は ValueError を発生させます（関数により異なる）。
    - LLM 呼び出しはリトライや失敗時のフェイルセーフが組み込まれていますが、API 利用料金に注意してください。

環境変数（主要なもの）
- KABUSYS_ENV: 起動環境（development | paper_trading | live）デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時に必須）
- PAPER_FILL_MODE: paper_trading 時の約定モード（instant | partial | never | reject）デフォルト: instant
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite パス（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH: 実行 PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動削除するか（"1" で有効）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング秒（default 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: "1" をセットすると自動で .env ファイルを読み込まない

簡単な .env 例
（プロジェクトルートに .env を置くと自動読み込みされます。安全上、シークレットは本番で Vault 等を使ってください。）
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
SQLITE_PATH=data/monitoring.db
DUCKDB_PATH=data/kabusys.duckdb
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...
LOG_LEVEL=INFO
```

実行時の停止制御・PID
- data/stop_requested.flag: run_* スクリプトがループ中に存在を検知すると優雅に終了します（外部から停止指示を与える用途）。
- data/kill.flag: KillSwitch が発動した際に書き込まれるフラグ（Execution 停止シグナルとして利用）。
- data/execution.pid: ExecutionEngine 起動時に PID を書き込む（SystemMonitor が存在チェックする）。

注意点・運用上のポイント
- Monitoring の DB（SQLITE_PATH）は環境に関わらず本番の monitoring DB を使う設計になっています（監視は一元化）。
- Paper Trading は実行エンジン側で DB を切り分ける（PAPER_TRADING_SQLITE_PATH）。
- OpenAI を用いる処理は API レート制限やエラーに備えたリトライ実装があるものの、API キーとコスト管理に注意してください。
- process priority / CPU affinity の設定は psutil を使っています。権限がない場合は警告を出してスキップします。
- DuckDB / SQLite のスキーマはコード内でマイグレーション済（init_monitoring_db が冪等にテーブルとカラムを作成/追加します）。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - run_execution.py                — ExecutionEngine 起動スクリプト
  - run_monitoring.py               — Monitoring ポーリングループ起動スクリプト
  - config.py                       — 環境変数/設定読み込み
  - utils/
    - process_priority.py           — プロセス優先度・CPU affinity ユーティリティ
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py (実装ファイルは存在)
    - broker_factory.py
    - broker_api.py
    - order_record.py
    - ... (実行系の補助モジュール)
  - monitoring/
    - monitoring_db.py              — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py                    — OpenAI を使ったニュースセンチメント
    - regime_detector.py             — マーケットレジーム判定
  - tools/
    - paper_verification_report.py   — Paper Trading の検証レポート生成
  - data/ (実行時に作成される想定)
    - monitoring.db
    - paper_trading.db
    - kabusys.duckdb
    - execution.pid
    - kill.flag
    - stop_requested.flag

（上記は主なファイルを抜粋しています。細部はソースツリーを参照してください。）

---

トラブルシューティング
- DB が開けない / ファイルがない:
  - デフォルト path（data/...）を作成してアクセス権を確認してください。
- OpenAI 関連のエラー:
  - OPENAI_API_KEY が設定されているか、API の利用制限を確認してください。
- プロセス優先度/CPU affinity が設定できない:
  - 実行ユーザに権限が無い、またはプラットフォーム非対応の場合は警告が出てスキップされます。

---

貢献・拡張案
- ブローカープラグイン（実口座用実装の追加）
- 銘柄別 lot_size マスタ対応（position_sizing の TODO）
- より詳細なマイグレーション機構（Alembic 相当）
- Prometheus Exporter / Grafana ダッシュボード連携

---

ライセンス・著作権
- 本リポジトリのライセンス情報はプロジェクトルートの LICENSE を参照してください（ここには記載がありません）。

---

最後に
- まずは .env を整え、DuckDB / SQLite のデータファイルの配置を確認してから run_monitoring/run_execution をそれぞれ起動してください。
- Paper Trading で動作検証を行い、その後本番接続（live 環境）へ移行する運用を推奨します。

必要であれば、README に含めるサンプル .env.example や systemd サービス定義、docker-compose 例なども作成します。ご希望があれば教えてください。