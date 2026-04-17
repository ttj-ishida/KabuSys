# KabuSys

日本株自動売買システムの一部をまとめた Python パッケージです。本リポジトリには監視（Monitoring）、実行エンジン（Execution）、ポートフォリオ構築、リサーチ（ファクター計算）、AI（ニュース NLP / レジーム判定）などの主要コンポーネントが含まれます。

以下はコードベースから抽出した README.md（日本語）です。

---

目次
- プロジェクト概要
- 機能一覧
- 必要要件・インストール
- セットアップ手順
- 使い方（主要コマンド）
- 環境変数一覧（主なもの）
- ファイル・ディレクトリ構成（抜粋）
- 運用上の注意点

---

プロジェクト概要
- KabuSys は日本株自動売買システムの基盤ライブラリ群です。
- 監視（System / Trade / Risk）、ExecutionEngine の起動スクリプト、ポートフォリオ構築ロジック、ファクター計算、ニュースの NLP スコアリング、レジーム判定などのモジュールを含みます。
- SQLite（監視用 DB 等）と DuckDB（時系列・ファクタ計算用）を組み合わせてデータを扱います。
- 実行環境（本番 / paper_trading / development）に応じた動作切り替えが可能です。

機能一覧
- 監視（monitoring）
  - SystemMonitor: CPU/メモリ/ディスク、実行プロセス状態、データ鮮度を監視してログを残す
  - TradeMonitor: 注文滞留（stale orders）・約定異常価格を検出してリスクログを記録
  - RiskMonitor: ドローダウンや保有銘柄数の閾値監視、ダッシュボード更新
  - KillSwitch: 条件成立時に data/kill.flag を書き込んで ExecutionEngine を停止させる
  - AlertManager: LINE Messaging API によるアラート通知（クールダウン管理）
  - Streamlit ダッシュボード：監視 DB を読み取って可視化
- 実行（execution）
  - ExecutionEngine 起動スクリプト（run_execution.py）: Broker クライアント・OrderManager・RiskManager 等の組み立てとセッション実行
  - Reconciler: 起動時の注文／ポジションの突合せ・自動復旧処理
  - OrderManager / OrderRepository: 注文状態管理と DB 永続化
- ポートフォリオ（portfolio）
  - 候補選定、等重 / スコア加重配分、リスク調整（セクターキャップ・レジーム乗数）、ポジションサイズ計算（単元丸め・aggregate cap）
- リサーチ（research）
  - ファクター計算（モメンタム、バリュー、ボラティリティ等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI（ai）
  - news_nlp: raw_news を OpenAI API でスコア化して ai_scores に書き込む
  - regime_detector: ma200 とマクロニュースの LLM 評価を合成して market_regime を判定

必要要件・インストール
- Python 3.9+（型ヒント等を利用）
- 主な依存ライブラリ（例）
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit（ダッシュボード利用時）
- 仮想環境（推奨）
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

インストール例（最低限のパッケージ）
- pip install duckdb psutil openai requests
- streamlit を使う場合: pip install streamlit

（プロダクション用途では requirements.txt を用意して pip install -r requirements.txt を推奨）

セットアップ手順
1. リポジトリをクローンして作業ディレクトリへ移動
2. 仮想環境を作成・有効化（上記参照）
3. 依存パッケージをインストール
4. data ディレクトリを作成
   - mkdir -p data
5. 環境変数設定
   - プロジェクトルートに .env（または .env.local）を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば自動ロードを無効化）。
   - 必須変数の一例:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - OPENAI_API_KEY（AI 機能を使う場合）
   - 監視用 DB/DuckDB のパスは環境変数で上書き可能（詳細は下の環境変数一覧参照）
6. DB の初期化
   - run_monitoring/run_execution の起動処理内で init_monitoring_db が自動的にテーブル作成・マイグレーションを行います。手動で行う必要は原則ありません。

使い方（主要コマンド）
- 監視ループ起動（SystemMonitor を単独でポーリング）
  - モジュール実行:
    - python -m kabusys.run_monitoring
  - 実行時の挙動:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60 秒）
    - 監視は KABUSYS_ENV に関わらず settings.sqlite_path（本番用 monitoring DB）を使用します
    - 終了: Ctrl+C またはプロジェクトルート/data/stop_requested.flag をファイルとして作成すると安全に停止します

- ExecutionEngine 起動（売買エンジン）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH / default: data/paper_trading.db）を使用して本番 DB と分離
    - 起動時に data/stop_requested.flag が存在すると起動せずに終了
    - 実行中に data/stop_requested.flag が作成されるとエンジンを停止
    - ExecutionEngine は pid ファイル（デフォルト data/execution.pid）を生成します

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）
  - レポートでは稼働率、注文成功率、送信率、レイテンシ等を表示・判定します

- Streamlit ダッシュボード（監視）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用で監視 DB を開き、Overview/Positions/Orders/System を表示します

- AI モジュール（手動実行）
  - news_nlp.score_news / regime_detector.score_regime を呼び出すには OpenAI API キー（OPENAI_API_KEY）が必要です
  - これらは DuckDB 接続を受け取り、テーブルに結果を書き込みます（ai_scores / market_regime）

環境変数一覧（主なもの）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）※Settings.env で検証
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API 用（必須）
- OPENAI_API_KEY: OpenAI API キー（ai/news_nlp/regime_detector を使う場合）
- SQLITE_PATH: 監視用 SQLite DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- PID_FILE_PATH: Execution PID ファイルパス（デフォルト data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag をクリアするか（"1" で有効）
- PAPER_FILL_MODE: paper_trading 用の約定挙動（instant|partial|never|reject、デフォルト instant）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（整数）

運用に関するファイル・フラグ
- data/stop_requested.flag
  - これを作成すると run_monitoring や run_execution のループは安全に終了します（監視用とエンジン用の両スクリプトで参照）。
- data/kill.flag
  - KillSwitch によって書き込まれる停止要求。ExecutionEngine がこのフラグを検出すると停止します。
  - KillSwitch は再書き込みを行わず、存在確認・削除メソッドを提供します。
- data/execution.pid
  - ExecutionEngine 起動時に PID を書き込む標準的なファイル。SystemMonitor はこのファイルを見て実プロセス存否をチェックします。

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py (パッケージ定義)
  - config.py (環境変数 / 設定管理 — .env の自動読み込みロジックを含む)
  - run_monitoring.py (SystemMonitor ポーリングループ起動スクリプト)
  - run_execution.py (ExecutionEngine 起動スクリプト)
  - utils/
    - process_priority.py (プロセス優先度 / CPU affinity 設定ユーティリティ)
  - monitoring/
    - monitoring_db.py (SQLite 用の監視ログ永続化層)
    - system_monitor.py (システム状態・データ鮮度監視)
    - trade_monitor.py (注文滞留・約定異常監視)
    - risk_monitor.py (ドローダウン・ポジション上限監視)
    - kill_switch.py (kill.flag 書き込みユーティリティ)
    - alert_manager.py (LINE API による通知)
    - monitoring_engine.py (複数モニタを束ねるエンジン)
    - streamlit_dashboard.py (Streamlit ベースの監視ダッシュボード)
  - execution/
    - reconciler.py (再起動時の注文・ポジション再同期)
    - order_manager.py (注文状態管理)
    - order_repository.py, order_record.py, broker_factory.py, broker_api.py 等（実行ロジック周辺）
  - portfolio/
    - portfolio_builder.py (候補選定・重み計算)
    - risk_adjustment.py (セクター制限・レジーム乗数)
    - position_sizing.py (株数決定・丸め・キャップ)
  - research/
    - factor_research.py (モメンタム等ファクター計算)
    - feature_exploration.py (将来リターン・IC・統計)
  - ai/
    - news_nlp.py (ニュース NLP による銘柄別スコアリング)
    - regime_detector.py (市場レジーム判定)
  - tools/
    - paper_verification_report.py (Paper Trading 検証レポート生成スクリプト)

設計上のポイント / 注意事項
- 設定の自動読み込み: config.py はプロジェクトルート（.git または pyproject.toml）を自動探索し .env / .env.local を読み込みます。テスト等で自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DB マイグレーション: monitoring_db.init_monitoring_db は自動でテーブル作成と簡単なマイグレーション（列追加）を行います。run_* スクリプトは起動時にこれを呼び出します。
- Paper Trading と本番 DB の分離: KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使い、本番用監視 DB と分離を図ります（run_execution の動作）。
- OpenAI API 呼び出し: news_nlp / regime_detector は OpenAI を利用します。API 呼び出しはリトライ処理やレスポンスのバリデーションが組み込まれていますが、API キーの保管・請求には注意してください。
- フェイルセーフ: AI API の失敗や外部エラー時は「スコア=0」「処理スキップ」「ログ警告」などのフェイルセーフが多用されています。運用時はログの監視を行ってください。
- 権限・プラットフォーム差分: process_priority は OS による差を吸収しますが、権限不足（nice/psutil 操作）で警告が出ることがあります。運用環境の権限を確認してください。

よくある運用コマンド（まとめ）
- 監視起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 実行エンジン起動（paper_trading）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

貢献 / 開発
- 新しい機能追加・修正はモジュール単位で行い、ユニットテストと静的型検査を追加してください。
- DB スキーマ変更を伴う場合は monitoring_db.init_monitoring_db のマイグレーションロジックを拡張してください。

ライセンス
- 本 README では明示していません。実プロジェクトでは LICENSE ファイルを追加してください。

---

何か README の内容を追記・修正したい箇所（例: 依存関係の固定バージョン、実行時の具体的な .env.example、運用手順ドキュメントなど）があれば教えてください。必要に応じて .env.example のサンプルや systemd ユニットファイル例、docker-compose 構成例なども作成できます。