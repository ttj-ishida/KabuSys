# KabuSys

日本株自動売買システムの軽量なモジュール群です。  
本リポジトリには、実行エンジン / 監視機能 / ポートフォリオ構築ロジック / リサーチ用ファクター計算 / AI（ニュース NLP）モジュールなどが含まれます。

以下はコードベース（src/kabusys 以下）を基にした README です。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（起動方法・ツール）
- 環境変数（主な設定）
- ディレクトリ構成（主要ファイルの説明）
- 運用上の注意点

---

プロジェクト概要
- KabuSys は日本株の自動売買システムを構成するコンポーネント群です。
- 主要な責務:
  - ExecutionEngine（発注・注文状態管理・リコンシリエーション）
  - Monitoring（システム・注文・リスクの監視、LINE 通知、ダッシュボード）
  - Portfolio construction（候補選定・重み付け・株数決定）
  - Research（ファクター計算・特徴量解析）
  - AI モジュール（ニュース NLP によるセンチメント評価、レジーム判定）
  - 開発 / 検証用ツール（Paper Trading 検証レポート等）

主な機能一覧
- 実行系
  - OrderManager / ExecutionEngine（ブローカー経由の発注・状態同期）
  - Reconciler（再起動時の自動復旧・ポジション照合）
  - Paper Trading モード（本番 DB と分離された paper_trading DB を使用）
- 監視系
  - SystemMonitor（CPU/メモリ/ディスク・データ鮮度・プロセス生存の監視）
  - TradeMonitor（滞留注文、約定価格の異常検知）
  - RiskMonitor（ドローダウン、ポジション上限監視）
  - KillSwitch（条件に応じて停止フラグを書き出し ExecutionEngine を止める）
  - AlertManager（LINE PUSH による通知、クールダウン管理）
  - Streamlit ダッシュボード（監視データの可視化）
- Portfolio（純粋関数群）
  - 候補選択、等金額／スコア加重配分、単元株丸め、セクター制約、レジーム乗数
- Research
  - DuckDB を使ったファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン、IC（Information Coefficient）、統計サマリー
- AI
  - ニュースを OpenAI（gpt-4o-mini）で評価して ai_scores に保存
  - レジーム判定（ETF MA200 とマクロニュースの組合せ）
- ツール
  - Paper Trading 検証レポート生成スクリプト（期間指定可能）

セットアップ手順（開発環境 / 実行環境）
1. Python 3.10+ を用意してください。
2. 依存パッケージをインストールします（適宜 requirements.txt を用意している前提）。
   例（主要ライブラリ）:
   ```
   pip install duckdb psutil openai requests streamlit
   ```
   - duckdb: リサーチ / AI の DB クエリ用
   - psutil: プロセス優先度 / CPU メトリクス
   - openai: ニュース NLP / レジーム判定（API 呼び出し）
   - requests: LINE API 呼び出し
   - streamlit: ダッシュボード
3. プロジェクトルートに .env/.env.local を配置して環境変数を設定できます。
   - 自動ロード: OS 環境変数 > .env.local > .env の優先度で読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
4. データディレクトリ（例: data/）を作成してください。デフォルト DB パス等は Settings クラスに定義されています。

使い方（起動方法・コマンド例）
- 実行エンジン（ExecutionEngine）を起動する
  - 本番/開発/紙トレードは KABUSYS_ENV で切り替え（development / paper_trading / live）
  - 起動:
    ```
    python -m kabusys.run_execution
    ```
  - paper_trading モード:
    ```
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
    - paper_trading の場合、MockBrokerClient を用い、データは data/paper_trading.db（または env で上書き）に保存されます。
  - 実行時に data/stop_requested.flag が存在すると起動・継続を止めます（停止フラグ）。
  - 実行時にプロセス優先度を "high" に設定します（set_process_priority を使用）。

- 監視プロセス（Monitoring）を起動する
  - 起動:
    ```
    python -m kabusys.run_monitoring
    ```
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能。デフォルト 60 秒。
  - 監視は Settings.env に関わらず本番 sqlite_path を使用する設計になっています（monitoring 用 DB は production パスを参照）。

- Streamlit ダッシュボード
  - 監視 DB を読み取り専用で表示:
    ```
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```
  - 引数 --db で監視 DB パスを指定できます。

- Paper Trading 検証レポート生成
  - スクリプト:
    ```
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - デフォルト DB パス: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可能）
  - 出力: 稼働率、注文成功率、送信率、P95 レイテンシ等のサマリと PASS/FAIL 判定

環境変数（主要な設定）
- 一般
  - KABUSYS_ENV: 稼働モード（development / paper_trading / live）。default=development
  - LOG_LEVEL: ログレベル（DEBUG/INFO/...）。default=INFO
- API / 認証
  - JQUANTS_REFRESH_TOKEN: J-Quants API（必須）
  - KABU_API_PASSWORD: kabuステーション等の API パスワード（必須）
  - OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時、必須）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
- DB / ファイルパス
  - DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（monitoring）パス（default: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 sqlite（default: data/paper_trading.db）
  - PID_FILE_PATH: ExecutionEngine の pid ファイルパス（default: data/execution.pid）
  - KILL_FLAG_PATH: KillSwitch が書き込む停止フラグ（default: data/kill.flag）
- その他
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、default: 60）
  - PAPER_FILL_MODE: paper_trading の約定モード（instant / partial / never / reject）
    - 無効値は Settings でエラーになります

ディレクトリ構成（主要ファイルの説明）
- src/kabusys/
  - __init__.py: パッケージ定義、__version__ 等
  - config.py: Settings クラス（環境変数読み込みロジック、.env 自動ロード、各種設定プロパティ）
  - run_execution.py: ExecutionEngine 起動スクリプト（メイン）
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト
  - execution/:
    - execution_engine.py (Engine 実装) — （コードベースに含まれている想定の中心エンジン）
    - order_manager.py: OrderManager（発注フロー）
    - order_repository.py: OrderRepository（DB）
    - reconciler.py: 再起動時の同期ロジック
    - broker_factory.py / broker_api.py: ブローカークライアント生成・API プロトコル
    - order_record.py: OrderRecord, OrderState 等
  - monitoring/:
    - monitoring_db.py: SQLite テーブル初期化・永続化 API（MonitoringDB）
    - system_monitor.py: システムステータス監視（CPU/メモリ/ディスク/プロセス/データ鮮度）
    - trade_monitor.py: 注文滞留・価格異常監視
    - risk_monitor.py: ドローダウン・ポジション上限監視
    - kill_switch.py: 停止フラグの読み書きユーティリティ
    - alert_manager.py: LINE PUSH 通知（クールダウン付き）
    - monitoring_engine.py: 各 Monitor を束ねるループ / run_once 用 API（テスト容易）
    - streamlit_dashboard.py: Streamlit での監視 UI
  - portfolio/
    - portfolio_builder.py: 候補選定・等分配・スコア重み
    - position_sizing.py: 株数決定（risk_based / equal / score）
    - risk_adjustment.py: セクターキャップ、レジーム乗数
  - research/
    - factor_research.py: モメンタム / ボラティリティ / バリュー等の計算（DuckDB）
    - feature_exploration.py: 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py: ニュースを OpenAI でスコア化して ai_scores へ書き込み
    - regime_detector.py: マクロセンチメント + ETF MA でレジームを判定
  - tools/
    - paper_verification_report.py: Paper Trading の検証レポート生成スクリプト
  - utils/
    - process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ

運用上の注意点 / 実装上の備考
- .env 自動ロード:
  - プロジェクトルートは .git または pyproject.toml を基準に自動検出します。
  - 自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等で実行可能です。既存 DB に対して追加カラムの簡易マイグレーションを含みます。
- Kill / Stop の仕組み:
  - 実行の停止や起動抑止に data/stop_requested.flag, data/kill.flag が利用されます。運用時はファイルの存在チェック・削除に注意してください。
- Paper Trading の分離:
  - KABUSYS_ENV=paper_trading の場合、発注系は本番 DB と完全に分離され paper 用 sqlite に書き込みます（安全に検証可能）。
- OpenAI 関連:
  - news_nlp や regime_detector は OPENAI_API_KEY が必要です。API 呼び出しは再試行やフェイルセーフを組み込んでいますが、API の利用コストに注意してください。
- プロセス優先度:
  - 起動スクリプトは実行開始時に set_process_priority("high") を呼びます。権限によっては設定に失敗する場合があります（ログに WARN が出ます）。
- テストとモック:
  - AI 呼び出しや外部 API 呼び出しはテスト確保のためモック可能な形で実装されています（内部 _call_openai_api 等を patch する設計）。

---

追加情報 / ヘルプ
- コード内の docstring やログ出力には挙動の説明が豊富に含まれています。実装関数・クラスを直接参照すると詳細な仕様が確認できます。
- 具体的な実行フローや Engine のパラメータ調整は execution/*.py の実装を参照してください。

必要であれば、README に以下を追加で追記します:
- requirements.txt のサンプル
- デプロイ / systemd ユニットファイル例（run_execution / run_monitoring）
- 具体的な .env.example（推奨キーの雛形）
- よくあるトラブルシューティング（DB ロック、OpenAI エラー、pid ファイル関連）

どの追加情報をREADMEに盛り込みますか？