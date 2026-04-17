# KabuSys

日本株自動売買システムの一部を実装したコードベースの README です。  
このドキュメントはリポジトリ内のソースコードを基に、プロジェクト概要、機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめています。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買・研究・監視を行うシステムです。本リポジトリには以下の主要領域が含まれます。

- Execution（ExecutionEngine、注文管理、リスク管理など）
- Monitoring（システム監視、トレード監視、リスク監視、Kill Switch、LINE 通知）
- Research（ファクター計算、特徴量解析、将来リターン・IC 計算）
- Portfolio（候補選定、重み付け、ポジションサイジング、セクター制約）
- AI（ニュース NLP によるセンチメント評価、レジーム判定）
- Tools（ペーパートレード検証レポート生成など）
- 設定管理ツール（.env ウィザード、設定検証 CLI）

設計上のポイント：
- DuckDB を用いたリサーチ用データ処理
- SQLite を監視ログ・ペーパートレード履歴用に使用（環境により分離）
- OpenAI API（gpt-4o-mini など）をニュース解析や市場レジーム判定に利用（オプション）
- Kill Switch（フラグファイル）により安全に ExecutionEngine を停止可能
- プロセス優先度設定、CPU affinity 設定などのユーティリティを提供

---

## 機能一覧

主な機能（抜粋）:

- 設定関連
  - 対話式 .env ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）

- 実行（Execution）
  - ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - Paper trading モード（KABUSYS_ENV=paper_trading）では MockBrokerClient を使用し、paper_trading 用 SQLite DB を利用

- 監視（Monitoring）
  - SystemMonitor（CPU/メモリ/Disk、データ鮮度、pid チェック）
  - TradeMonitor（滞留注文、約定価格異常）
  - RiskMonitor（ドローダウン・ポジション上限検出、dashboard 更新）
  - KillSwitch（条件に応じて data/kill.flag を書き込み）
  - AlertManager（LINE Messaging API による通知）
  - 監視ループ起動スクリプト（python -m kabusys.run_monitoring）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）

- 研究（Research）
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン・IC 計算、ランク付け、統計サマリー（DuckDB 経由）

- ポートフォリオ（Portfolio）
  - 候補選定、等配分/スコア加重、リスクベースのポジションサイジング
  - セクター集中制限、レジーム乗数

- AI
  - ニュースを LLM でセンチメント評価し ai_scores に保存（kabusys.ai.news_nlp.score_news）
  - 市場レジーム判定（kabusys.ai.regime_detector.score_regime）
  - OpenAI API 呼び出しはリトライやエラー処理を考慮して実装

- ツール
  - ペーパートレード検証レポート生成（python -m kabusys.tools.paper_verification_report）
    - オプション: --from, --to, --db

---

## セットアップ手順（ローカル開発想定）

1. Python 環境準備
   - 推奨: Python 3.10+
   - 仮想環境を作成して有効化:
     - python -m venv .venv
     - Unix/macOS: source .venv/bin/activate
     - Windows: .venv\Scripts\activate

2. 必要パッケージをインストール
   - 本リポジトリに requirements.txt が無い場合、最低限以下をインストールしてください。
     - duckdb
     - psutil
     - requests
     - openai
     - PyYAML（config YAML 検証時に任意）
   - 例:
     - pip install duckdb psutil requests openai PyYAML

3. .env の作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - または手動で .env を作成。例（秘密情報は伏せてください）:
     - JQUANTS_REFRESH_TOKEN=your_jquants_token_here
     - KABU_API_PASSWORD=your_kabu_password_here
     - KABU_API_BASE_URL=http://localhost:18080/kabusapi
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - KABUSYS_ENV=development
     - LOG_LEVEL=INFO
     - KILL_FLAG_CLEAR_ON_START=0

   - 自動ロードの振る舞い:
     - 起動時に .env / .env.local を自動読み込みします（OS 環境変数が優先）。
     - 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

4. DB ディレクトリ作成（必要なら）
   - data ディレクトリを作成:
     - mkdir -p data

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります。

---

## 使い方（主要コマンド・環境変数）

実行例と注意点をまとめます。

- 設定ウィザード
  - python -m kabusys.config_setup
  - .env を対話式に作成・更新します。

- 設定検証
  - python -m kabusys.validate_config
  - オプション: --strict

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 説明:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60）。
    - 監視は Settings によらず本番の sqlite_path を使用（monitoring ログは単一 DB に残す想定）。
    - 停止方法: プロセス内で data/stop_requested.flag（プロジェクトルート/data/stop_requested.flag）を作成するとループは終了します。

- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - 説明:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録（本番 DB と分離）。
    - 起動前に data/stop_requested.flag が存在する場合は起動しません。
    - 実行中に stop フラグが立つとエンジンを停止します。
    - PID 管理: data/execution.pid が使われます。

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 引数:
    - --from: レポート開始日
    - --to: レポート終了日
    - --db: SQLite DB パス（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可能）
  - 出力: 標準出力にサマリ（稼働率、注文成功率、レイテンシ等）を表示

- AI 関連（ニューススコア、レジーム判定）
  - OpenAI API キーが必要（OPENAI_API_KEY 環境変数、または各関数に api_key を渡す）
  - ニューススコア:
    - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

- フラグファイル
  - stop_requested.flag: run_monitoring / run_execution が参照する停止フラグ（プロジェクト data 以下）
  - kill.flag: KillSwitch が条件に応じて作成するファイル。ExecutionEngine は kill.flag を検出して停止する想定
  - execution.pid: 実行エンジンの PID を記録するために使用

- その他環境変数（主なもの）
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — デフォルト: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード用 DB（デフォルト: data/paper_trading.db）
  - LOG_LEVEL — デフォルト: INFO
  - MONITOR_POLL_INTERVAL — 監視ループの秒数（デフォルト: 60）
  - OPENAI_API_KEY — OpenAI を使う処理で参照される

---

## 実運用上の注意

- 本番環境（KABUSYS_ENV=live）では敏感情報や自動クリア設定（KILL_FLAG_CLEAR_ON_START）に注意してください。validate_config には本番向けの警告チェックがあります。
- Run スクリプトはプロセス優先度を "high" に設定しようとしますが、権限や OS によっては設定できないことがあります（ログに警告が出ます）。
- AI 呼び出し（OpenAI）は API レート制限・ネットワーク障害などに備えリトライやフォールバックを実装していますが、API キーやコストに注意してください。
- データ鮮度チェックは DuckDB から取得する prices_daily の最終日で判定します。DuckDB のデータ更新・取得パイプラインとの整合性を保ってください。

---

## ディレクトリ構成（主要ファイル）

リポジトリ内の主要ディレクトリとファイルを抜粋します（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数・設定読み込みロジック
  - config_setup.py               — .env 対話式ウィザード
  - validate_config.py            — 設定検証 CLI
  - run_monitoring.py             — 監視ポーリングループ起動スクリプト
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - ai/
    - news_nlp.py                 — ニュース NLP（OpenAI）によるスコアリング
    - regime_detector.py          — 市場レジーム判定（AI + MA200）
  - monitoring/
    - monitoring_db.py            — SQLite の監視 DB 層（テーブル定義・CRUD）
    - monitoring_engine.py        — 監視コンポーネント束ね
    - system_monitor.py           — システム状態・データ鮮度監視
    - trade_monitor.py            — 注文滞留・約定異常監視
    - risk_monitor.py             — ドローダウン・ポジション上限監視
    - kill_switch.py              — Kill Switch（kill.flag 書き込み）
    - alert_manager.py            — LINE 通知
  - portfolio/
    - portfolio_builder.py        — 候補選定・重み付け
    - position_sizing.py          — 株数決定・単元丸め・制約適用
    - risk_adjustment.py          — セクターキャップ・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py          — ファクター計算（momentum/value/volatility）
    - feature_exploration.py      — 将来リターン・IC・統計
    - __init__.py
  - monitoring/                    (上に示した)
  - utils/
    - process_priority.py         — プロセス優先度・CPU affinity ユーティリティ
    - __init__.py
  - execution/                     — Execution 関連コンポーネント（OrderManager 等）
    - （リポジトリに実装されているファイル群があればここに存在します）

※ 実際の追加ファイル（execution 関連の細部実装や data/ スクリプト等）はリポジトリ全体を参照してください。

---

## よくある操作例

- 開発環境で監視を 30 秒間隔にしたい:
  - export MONITOR_POLL_INTERVAL=30
  - python -m kabusys.run_monitoring

- ペーパートレード DB を指定して検証レポートを出す:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10 --db data/paper_trading.db

- 設定検証（厳密モード）:
  - python -m kabusys.validate_config --strict

---

この README はコードベースの主要な要素をまとめたものです。実運用・デプロイ時はさらに以下を検討してください：

- 運用監視（プロセスマネージャ systemd / supervisord など）
- ログ集約とローテーション
- 秘密情報の安全保管（Vault 等）
- テスト（ユニットテスト、E2E）と CI/CD パイプライン

必要であれば README を拡張して、設定例ファイル（.env.example）やデプロイ手順、主要な関数 API リファレンスを追加できます。どの情報を追加したいか教えてください。