# KabuSys

日本株向け自動売買フレームワークの軽量実装。ポートフォリオ構築、発注エンジン、監視、調査（research）、AI によるニュース評価などを含むモジュール群で構成されています。

概要
- 設計方針: モジュールは単一責務で小さく保たれ、DB は SQLite / DuckDB を併用。外部 API（kabuステーション、J-Quants、OpenAI 等）との接続を想定しつつ、paper_trading（模擬売買）モードで実行可能。
- 自動発注（ExecutionEngine）、監視（MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch）、ポートフォリオ構築（選定・配分・サイズ計算）、研究用ファクター計算、ニュース NLP によるセンチメント評価などを提供。

主な機能一覧
- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - Broker クライアントの抽象化（本番 / mock 切替）
  - OrderManager / OrderRepository / Reconciler（再起動時リコンシリエーション）
  - リスク管理（RiskManager の設定を含む）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス生存確認、データ鮮度チェック
  - TradeMonitor: 滞留注文・約定異常価格の検出
  - RiskMonitor: ドローダウン・ポジション上限監視
  - KillSwitch: 条件に応じた停止フラグの書き込み
  - AlertManager: LINE Push による通知（クールダウン管理）
  - Streamlit ダッシュボード（read-only接続で監視 DB を可視化）
- Portfolio
  - 候補選定、等重/スコア重み計算、セクターキャップ、レジーム乗数、ポジションサイズ計算（単元株丸め等）
- Research
  - ファクター計算（momentum, volatility, value）、将来リターン、IC 計算、統計サマリ
  - DuckDB を用いた高速集計
- AI
  - news_nlp: OpenAI を用いたニュースの銘柄別センチメント評価（ai_scores テーブル書き込み）
  - regime_detector: MA200 とマクロニュースで市場レジーム判定（bull/neutral/bear）
- ツール
  - paper_verification_report: Paper Trading DB を解析して検証レポートを生成

セットアップ手順（ローカル開発用）
1. リポジトリをクローン
   - git clone ...（プロジェクトルートを取得）

2. Python 仮想環境作成
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb psutil requests openai streamlit
   - （プロジェクトで使う他のパッケージがあれば追加でインストールしてください）

4. 環境変数設定
   - プロジェクトルートの .env / .env.local を作成することで自動読み込みされます（既存 OS 環境変数が優先され、.env.local は .env を上書きします）。
   - 主要な環境変数:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
     - PAPER_FILL_MODE: paper_trading 時の約定モード（instant|partial|never|reject、デフォルト: instant）
     - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
     - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - PID_FILE_PATH: Execution PID ファイルパス（デフォルト: data/execution.pid）
     - KILL_FLAG_PATH: kill.flag パス（デフォルト: data/kill.flag）
     - LOG_LEVEL: ログレベル（DEBUG/INFO/...）
     - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）

5. データディレクトリ作成（必要に応じて）
   - mkdir -p data

基本的な使い方
- 実行エンジン（ExecutionEngine）を起動
  - 本番/開発/ペーパーは KABUSYS_ENV によって切替
  - python -m kabusys.run_execution
  - 起動時に data/execution.pid が作成され、stop/kill フラグにより外部から停止可能
  - paper_trading モード（KABUSYS_ENV=paper_trading）は MockBrokerClient を使い、専用 DB（data/paper_trading.db）に記録します

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（秒、デフォルト 60）
  - 監視は MonitoringDB（SQLite）へ書き込み、kill.flag や stop_requested.flag の存在で制御されます

- Streamlit ダッシュボード（監視 DB の可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD （開始日）
    - --to YYYY-MM-DD （終了日）
    - --db PATH （DB パス指定、環境変数 PAPER_TRADING_SQLITE_PATH より優先）

ファイル / 重要なフラグ類
- data/stop_requested.flag: run_execution / run_monitoring の停止判定に使われる（存在で停止）
- data/kill.flag: KillSwitch による ExecutionEngine 停止要求。Execution 起動時にオプションでクリアする動作あり。
- data/execution.pid: 実行中エンジンの PID 管理用

ディレクトリ構成（主要ファイルの説明）
- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数読み込み・Settings（.env 自動ロードロジック含む）
  - run_execution.py — ExecutionEngine 起動スクリプト（pid / stop フラグ処理、paper_trading 分離）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - execution/
    - execution_engine.py (起動エンジン本体) ※（コードベースに一部モジュール参照あり）
    - order_manager.py — 注文生成・状態管理 API
    - order_repository.py — Orders DB 抽象（SQLite）
    - reconciler.py — 起動時のリコンシリエーションロジック
    - broker_factory.py / broker_api.py — ブローカークライアント抽象化
    - order_record.py — 注文レコード / 状態遷移ロジック
  - monitoring/
    - monitoring_db.py — SQLite 監視ログの永続化（スキーマ初期化・CRUD）
    - system_monitor.py — CPU/メモリ/ディスク・データ鮮度・PID チェック
    - trade_monitor.py — 注文滞留・約定異常チェック
    - risk_monitor.py — ドローダウン/ポジション上限監視
    - kill_switch.py — 停止フラグ書き込みユーティリティ
    - alert_manager.py — LINE Push 通知クライアント（クールダウン管理）
    - monitoring_engine.py — 各 monitor を束ねるオーケストレーター
    - streamlit_dashboard.py — Streamlit ダッシュボード UI
  - portfolio/
    - portfolio_builder.py — 候補選択・重み計算
    - risk_adjustment.py — セクターキャップ・レジーム乗数
    - position_sizing.py — 発注株数決定・単元丸め・集約 cap
  - research/
    - factor_research.py — momentum/volatility/value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py — OpenAI を使ったニュースの銘柄別センチメント評価（ai_scores 生成）
    - regime_detector.py — MA200 + マクロニュースで市場レジーム判定
  - tools/
    - paper_verification_report.py — paper_trading DB を集計して PASS/FAIL レポート出力
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

運用上の注意
- DB ファイルの扱い:
  - monitoring 用 SQLite（SQLITE_PATH）と DuckDB（DUCKDB_PATH）は独立して管理してください。
  - paper_trading は実口座 DB と分離するため PAPER_TRADING_SQLITE_PATH を使用します。
- 環境（KABUSYS_ENV）:
  - development: 開発用（デフォルト）
  - paper_trading: 模擬売買（MockBrokerClient を使用、DB 分離）
  - live: 本番
- OpenAI API 使用:
  - OPENAI_API_KEY が必要。API 失敗時のフォールバックが多めに実装されていますが、キー未設定だと例外になる関数もあります（明示的に確認してください）。
- PID / stop / kill フラグ:
  - 起動中のプロセスは pid ファイルを生成します。監視側・運用ツールは stop_requested.flag や kill.flag の存在でプロセスを制御します。これらはファイルベースなのでコンテナ/ホストのパスを適切にマウントしてください。

トラブルシューティング（よくある項目）
- .env が読み込まれない
  - プロジェクトルート（.git または pyproject.toml を基準）を検出できない場合、自動ロードはスキップされます。必要なら環境変数を直接設定するか KABUSYS_DISABLE_AUTO_ENV_LOAD を使って自前でロードしてください。
- MONITOR_POLL_INTERVAL の値が無効
  - run_monitoring は環境変数を int に変換します。0 以下や非数値はデフォルト 60 秒へフォールバックします。
- Streamlit の DB 読み取りエラー
  - streamlit は読み取り専用（URI ?mode=ro）で接続します。DB が存在しない、またはロック等で開けない場合は起動に失敗します。MonitoringEngine を先に起動して DB ファイルを作成してください。

開発 / テスト
- 各モジュールは純粋関数や副作用の少ないクラスに分離されているため、ユニットテストを書きやすい設計です（OpenAI / broker 呼び出し等はモック可能）。
- news_nlp や regime_detector の API 呼び出し部分は別関数化されており、テスト時に差し替えや patch が可能です。

ライセンス / 貢献
- 本 README には記載していません。リポジトリの LICENSE ファイルを参照してください。

補足
- より詳細な設計・アルゴリズムの説明（PortfolioConstruction.md, StrategyModel.md 等）がプロジェクトに含まれている想定です。実装に関する設計ドキュメントを参照してください。

以上がこのコードベースの概要と利用方法です。README に追加してほしい実行例や .env.example のテンプレートが必要であれば教えてください。