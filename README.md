# KabuSys

日本株自動売買システムのコードベース。ここに含まれるモジュールは、信号生成（research / ai）、ポートフォリオ構築（portfolio）、発注実行（execution）、監視（monitoring）、ユーティリティ群を提供します。

以下はこのリポジトリの README.md（日本語）です。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買基盤を想定したライブラリ／実行環境です。  
主な目的は次のとおりです。

- DuckDB / SQLite を用いたデータ格納・分析（価格データ、ニュース、財務データ等）
- ファクター計算・特徴量探索（research）
- ポジション選定・重み付け・株数決定（portfolio）
- 発注エンジン（ExecutionEngine）による実売買／ペーパートレードのサポート（execution）
- システム監視と自動停止（monitoring）／アラート生成（LINE等対応用トークンは環境変数で指定）
- OpenAI を用いたニュースセンチメント計算・レジーム判定（ai）
- 検証・レポート生成ツール（tools）

設計上の特徴として、ルックアヘッドバイアス防止やフェイルセーフ（API失敗時はスキップまたはデフォルト値で継続）を重視しています。

---

## 機能一覧

- config:
  - .env の自動読み込み、Settings クラスによる環境変数の集中管理
  - 対話式ウィザードで .env を生成する CLI（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
- execution:
  - ExecutionEngine（本番／ペーパートレード切替、MockBrokerClient 対応）
  - OrderRepository / OrderManager / RiskManager / Reconciler 等の実行周りコンポーネント
- monitoring:
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - MonitoringDB（SQLite）による監視ログ永続化
  - Kill Switch（一定条件で data/kill.flag を書き込み Execution を停止）
  - run_monitoring スクリプト（ポーリングループ）
- research:
  - ファクター計算（momentum, volatility, value 等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- portfolio:
  - 候補選定、等金額・スコア加重の重み計算
  - セクター集中制限、レジーム乗数、ポジションサイズ計算（単元株丸め、aggregate cap）
- ai:
  - ニュースのセンチメントスコア化（OpenAI を用いる）
  - 市場レジーム判定（ma200 + LLM マクロセンチメント）
- tools:
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

---

## セットアップ手順

1. リポジトリをクローン
   - 例: git clone <repo-url>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 本リポジトリの requirements.txt がある場合はそれを使ってください。ない場合は主要依存を個別にインストール:
     - pip install duckdb psutil openai
     - PyYAML は config/*.yaml 検証を使う場合に必要: pip install pyyaml

   依存ライブラリ（主なもの）:
   - duckdb
   - psutil
   - openai
   - (任意) PyYAML

4. .env の作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - あるいは .env.example を参考に手動で作成してプロジェクトルートに配置

   主要な環境変数（例／デフォルト）:
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト: data/monitoring.db)
   - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
   - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
   - OPENAI_API_KEY（ai 機能を使う場合に必要）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート通知用・任意）
   - KILL_FLAG_CLEAR_ON_START (0|1) — 本番では 0 推奨

5. 設定検証
   - python -m kabusys.validate_config
   - 警告も厳密に扱いたい場合は --strict

6. データディレクトリ（data）やログディレクトリ（logs）が自動作成されますが、権限等に注意してください。

---

## 使い方

各主要スクリプト・サブコマンドはモジュールとして実行できます。

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます
  - 停止フラグ: プロジェクトルート/data/stop_requested.flag が作られると起動中のループは検知して終了します
  - 実行中は pid ファイルが data/execution.pid に書かれます（ExecutionEngine が管理）

- 監視サービス起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60）
  - 監視は Settings.sqlite_path（monitoring.db）を使用します（環境に関わらず本番 sqlite_path を使用する設計）
  - 監視によって条件が満たされると data/kill.flag が生成され、ExecutionEngine 側の KillSwitch により発注が停止されます

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to   YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数の代替）
  - デフォルト DB: data/paper_trading.db

- AI（ニュース NLP・レジーム判定）
  - OpenAI API キーが必要（OPENAI_API_KEY 環境変数または該当関数呼び出し引数）
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を利用
  - モデル: gpt-4o-mini（コード内で指定）

ログの設定:
- setup_logging 関数によりコンソール（stdout）出力と日次ローテートのログファイル（logs/<app_name>.log）が設定されます。
- LOG_DIR や LOG_LEVEL は環境変数で上書き可能。

停止／強制停止:
- ExecutionEngine の停止は主に次のいずれかで行います:
  - data/stop_requested.flag を作成 → run_execution スクリプトは起動時ループ内で検知して終了する（monitoring からも検知される）
  - data/kill.flag （KillSwitch が書き込む）→ ExecutionEngine 側で検出して注文を停止する
- 注意: KILL_FLAG_CLEAR_ON_START=1 を本番で使うのは危険（自動的に Kill Switch をクリアしてしまう）

環境例（簡易）:
- export KABUSYS_ENV=development
- export JQUANTS_REFRESH_TOKEN=xxxxx
- export KABU_API_PASSWORD=xxxxx
- export OPENAI_API_KEY=sk-xxxx  # ai を使う場合

---

## 主要ファイル／ディレクトリ構成

（src/kabusys 以下を想定）

- kabusys/
  - __init__.py
  - config.py                — 環境変数・Settings 管理（.env 自動読み込み）
  - config_setup.py          — .env 対話式ウィザード CLI
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト

  - execution/
    - broker_factory.py      — ブローカークライアント生成（Mock 含む）
    - execution_engine.py    — 実行エンジン本体
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py

  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — 発注ログ監視（stale orders / anomaly fills）※ファイル内に定義あり
    - risk_monitor.py        — ドローダウン・ポジション数監視
    - monitoring_engine.py   — 各モニタを束ねる
    - kill_switch.py         — kill.flag の書き込み管理
    - alert_manager.py       — （アラート送信管理。LINE 等の接続は環境変数で設定）

  - portfolio/
    - portfolio_builder.py   — 候補選定・スコアソート
    - position_sizing.py     — 株数決定・aggregate cap
    - risk_adjustment.py     — セクター制限・レジーム乗数
    - __init__.py

  - research/
    - factor_research.py     — momentum / volatility / value 等のファクター計算
    - feature_exploration.py — 将来リターン計算・IC・統計サマリ
    - __init__.py

  - ai/
    - news_nlp.py            — ニュースセンチメント（OpenAI へのバッチ送信・検証・書き込み）
    - regime_detector.py     — レジーム判定（ma200 + LLM）
    - __init__.py

  - tools/
    - paper_verification_report.py — ペーパートレードの検証レポート生成
    - __init__.py

  - data/                    — デフォルトの DB / フラグファイル等（runtime に生成）
    - monitoring.db (SQLite)
    - paper_trading.db (SQLite)
    - kabusys.duckdb (DuckDB)
    - execution.pid
    - stop_requested.flag
    - kill.flag

  - logs/                    — デフォルトログ出力先（setup_logging により作成）

---

## 運用上の注意／ベストプラクティス

- 本番環境では KABUSYS_ENV=live を設定する前に必ず validate_config で検証してください。LINE の通知設定や kill フラグの取り扱いは特に重要です。
- .env は機密情報（API トークン等）を含むため、Git にコミットしないでください。
- OpenAI API を使う機能は API 利用料・レート制限に注意してください。リトライやバックオフはコード内で実装されていますが、運用・コスト監視は別途必要です。
- データベースのパスを環境変数（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）で適切に分離しておくと、本番とテストが混ざらないようにできます。
- ログディレクトリ作成に失敗した場合はファイル出力が無効化され、コンソール出力のみになります。ファイル出力が必要な場合は権限・ディスク容量を確認してください。

---

README に書かれている以外のユーティリティや拡張機能（例: scripts/generate_config.py）については、リポジトリ内のスクリプトやドキュメントを参照してください。

不明点や README の改善希望があれば、どの部分を詳しく説明すべきか教えてください。