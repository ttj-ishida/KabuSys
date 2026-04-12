# KabuSys

日本株向け自動売買フレームワーク（ライブラリ＆実行コンポーネント群）

このリポジトリは、アルゴリズムによる銘柄選定・ポジションサイズ計算、発注管理、実行エンジン、監視・アラート、研究用ツール群を含んだ自動売買用のコードベースです。AIを用いたニュースセンチメント判定や、市場レジーム判定などの機能も備えています。

---
## 目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（起動例）
- 環境変数・設定項目
- ディレクトリ構成（主なファイルと説明）
- 補足・運用上の注意

---

## プロジェクト概要
KabuSys は日本株を対象とする自動売買システムのコア部品群を提供します。主な目的は以下です。
- シグナルから銘柄選定・配分・株数決定までのポートフォリオ構築ロジック
- 発注の状態管理（OrderManager）とブローカーとの同期（Reconciler）
- 実稼働／Paper Trading 切替を備えた ExecutionEngine（起動スクリプトあり）
- 実行監視（System / Trade / Risk）とアラート送信（LINE）
- DuckDB / SQLite を用いたファクター計算・研究ユーティリティ
- OpenAI を用いたニュース NLP（センチメント）、市場レジーム判定
- 運用ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

---

## 主な機能一覧
- ポートフォリオ構築
  - 候補選定（スコア順）、等金額／スコア加重配分
  - セクター集中制限の適用
  - レジームに応じた乗数（Bull/Neutral/Bear）
  - 株数・単元丸め・利用可能現金に基づくスケール調整
- 実行（Execution）
  - ブローカー抽象化（本番・モック切替）
  - OrderManager による作成→送信→同期の堅牢なワークフロー
  - 起動時リコンシリエーション（Reconciler）
  - リスク管理（RiskManager）による発注抑止等（設定可能）
- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/ディスク/プロセス／データ鮮度監視
  - TradeMonitor: 注文滞留、約定価格異常の検出
  - RiskMonitor: ドローダウン・ポジション上限の監視とリスクログ記録
  - KillSwitch: フラグファイルで ExecutionEngine 停止シグナル発行
  - AlertManager: LINE push による通知（クールダウン管理）
  - Streamlit ダッシュボードで可視化
- 研究・データ処理
  - DuckDB を使ったファクター計算（モメンタム／ボラティリティ／バリュー等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- AI（OpenAI 連携）
  - ニュース記事をまとめて銘柄ごとにセンチメント評価（gpt-4o-mini 想定）
  - マクロ記事＋ETF MA 乖離を合成した市場レジーム判定
- 運用ツール
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）
  - Monitoring の起動スクリプト（run_monitoring.py）
  - Execution の起動スクリプト（run_execution.py）

---

## セットアップ手順
以下はローカルで動かすための最低限の手順例です。プロジェクトに requirements.txt がある場合はそちらを優先してください。

1. リポジトリをクローン／チェックアウト
   - git clone <repo-url>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージインストール（例）
   - pip install duckdb psutil requests openai streamlit

   ※ sqlite3 は標準ライブラリ、duckdb は外部依存です。OpenAI を使う場合は openai パッケージが必要です。

4. データディレクトリ作成（デフォルトの DB 保存先）
   - mkdir -p data

5. 環境変数設定
   - 環境変数は .env / .env.local をプロジェクトルートに置けば自動読み込みされます（自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（本番機能を使う場合）
   - OpenAI を使う機能を利用する場合: OPENAI_API_KEY
   - Paper Trading で分離された DB を使う場合は PAPER_TRADING_SQLITE_PATH を指定できます。

---

## 簡単な使い方（起動例）
いくつかの主要コマンド例を示します。プロセス優先度設定などは起動スクリプト内で自動的に行われます。

- ExecutionEngine を起動（本番 or paper_trading は KABUSYS_ENV に依存）
  - KABUSYS_ENV=development python -m kabusys.run_execution
  - Paper Trading:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
    - （Paper Trading モードでは専用の SQLite（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient が利用されます）

- Monitoring を起動（ポーリングループ）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60秒）。
  - 監視は常に production の sqlite_path（Settings.sqlite_path）を使います（環境に依らず本番監視 DB を参照する設計）。

- Streamlit ダッシュボード（監視DBの可視化、read-only 推奨）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI モジュールの利用例（ライブラリ呼び出し）
  - from kabusys.ai import score_news
  - score_news(duckdb_conn, target_date, api_key="...")

---

## 環境変数・設定項目（主なもの）
（Settings クラス（src/kabusys/config.py）に定義されているものを抜粋）

- KABUSYS_ENV: 起動環境（development | paper_trading | live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE アラート用（未設定時は通知は行われない）
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading での約定挙動（instant|partial|never|reject）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: Kill switch 用フラグファイル（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring でのポーリング間隔（秒、デフォルト 60）

（詳細は src/kabusys/config.py を参照してください。）

---

## ディレクトリ構成（主なファイルと説明）
以下は本リポジトリの主要モジュール／ファイルとその役割です（抜粋）。

- src/kabusys/
  - __init__.py
    - パッケージのエントリポイント、バージョン情報
  - config.py
    - 環境変数と設定の管理（.env 自動読み込み、Settings クラス）
  - run_execution.py
    - ExecutionEngine 起動スクリプト（プロセス優先度設定、DB 接続、エンジン起動）
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト
- src/kabusys/execution/
  - order_manager.py
  - reconciler.py
  - order_repository.py (参照されるがここでは省略)
  - execution_engine.py (参照されるがここでは省略)
  - broker_factory.py / broker_api.py
    - ブローカーとのやり取り（抽象化）、Paper Trading 向けモックの切替
- src/kabusys/monitoring/
  - monitoring_db.py
    - SQLite スキーマ初期化・永続化用ラッパー（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - monitoring_engine.py
  - streamlit_dashboard.py
- src/kabusys/portfolio/
  - portfolio_builder.py
    - 候補選定・重み付け（等金額・スコア重み）
  - position_sizing.py
    - 株数決定（risk_based / equal / score）
  - risk_adjustment.py
    - セクターキャップ、レジーム乗数
- src/kabusys/research/
  - factor_research.py
    - モメンタム・ボラティリティ・バリュー等のファクター計算（DuckDB 使用）
  - feature_exploration.py
    - 将来リターン計算、IC、統計サマリ
- src/kabusys/ai/
  - news_nlp.py
    - OpenAI を用いたニュースの銘柄別センチメント付与、ai_scores への格納
  - regime_detector.py
    - ETF MA 乖離 + マクロニュースセンチメントを合成した市場レジーム判定
- src/kabusys/tools/
  - paper_verification_report.py
    - Paper Trading の実運用検証レポート生成ツール
- src/kabusys/utils/
  - process_priority.py
    - プロセス優先度／CPU affinity 設定ラッパー（Windows / POSIX 対応）
- その他（データ層）
  - data/ (運用時に生成される DB ファイル等)
    - data/kabusys.duckdb  （DuckDB）
    - data/monitoring.db    （SQLite: 監視ログ）
    - data/paper_trading.db （Paper Trading 用 SQLite、分離された DB）

---

## 補足・運用上の注意
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml の階層）を探索して行います。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_execution/run_monitoring は起動時にプロセス優先度を "high" に設定しようとしますが、権限やプラットフォームによってはスキップされます（警告ログのみ）。
- 監視（Monitoring）は設計上、環境にかかわらず本番用の sqlite_path を参照します。Paper Trading 用 DB と混同しないよう注意してください（run_execution は KABUSYS_ENV によって paper/trade DB を分離して使用します）。
- OpenAI API を利用する機能は API キーが必須です。API 呼び出しに失敗した場合は多くの箇所でフェイルセーフ（スコア=0 やスキップ）となるよう設計されていますが、結果の有効性・コスト等は運用者で管理してください。
- kill.flag の存在を利用して ExecutionEngine を安全に停止させる仕組みがあります。flag の書き込み／削除により遠隔停止を実現できます（KillSwitch）。
- DB スキーマ変更（マイグレーション）は monitoring_db.init_monitoring_db で一部自動化されていますが、重大な変更がある場合は注意深い検証を行ってください。

---

もし README に追加したい情報（例: requirements.txt の内容、実行フロー図、データスキーマ詳細、運用チェックリストなど）があれば指定してください。必要に応じてサンプル .env.example も作成できます。