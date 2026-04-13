# KabuSys

日本株向け自動売買システムのサンプル実装（ライブラリ / 実行スクリプト群）。  
このリポジトリは戦略の研究・検証、実行エンジン、監視・アラート、AI を使ったニュース評価などのコンポーネントで構成されています。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要スクリプト・ツール）
- 環境変数一覧（主要項目）
- ディレクトリ構成（主要ファイルの説明）
- 注意事項

---

## プロジェクト概要

KabuSys は以下の目的で設計されたモジュール群です。

- ファクター計算 / 研究（DuckDB 上の価格データを参照）
- ポートフォリオ構築（候補選定・重み付け・リスク調整・株数計算）
- 実行エンジン（ブローカーとの送信、注文状態管理、再起動時のリコンシリエーション）
- 監視（プロセス状態／資源使用率／注文滞留／ドローダウン検出）とアラート（LINE Push）
- AI（OpenAI を用いたニュースセンチメント評価・市場レジーム判定）
- 運用補助ツール（Paper Trading 検証レポート、Streamlit ダッシュボード等）

設計上のポイント：
- DuckDB / SQLite を用いたローカル DB ベース（データ分析用に DuckDB、監視・発注ログに SQLite）
- 環境変数 / .env からの設定読み込み（自動ロードあり。無効化可能）
- Paper Trading 環境は本番 DB と分離される設計（KABUSYS_ENV に応じる）
- 外部 API 呼び出し（OpenAI、LINE、ブローカー等）は抽象化／フェイルセーフ対応あり

---

## 機能一覧

主な機能（一部抜粋）：

- 研究：
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- ポートフォリオ：
  - 候補選定（スコア・ランクベース）
  - 等金額 / スコア加重配分
  - リスク調整（セクター上限、レジーム乗数）
  - 株数計算（リスクベース、単元丸め、aggregate cap）
- 実行：
  - OrderManager / OrderRepository による注文ライフサイクル管理
  - BrokerClientFactory による実アカウント／モック切替（paper_trading）
  - Reconciler による再起動後の自動同期
- 監視：
  - SystemMonitor: CPU/メモリ/ディスク/データ鮮度/実行プロセス存在確認
  - TradeMonitor: 滞留注文検出、約定価格異常検出
  - RiskMonitor: ドローダウン、ポジション数上限監視、ダッシュボード更新
  - KillSwitch: フラグファイルによる ExecutionEngine 停止シグナル
  - AlertManager: LINE Messaging API へプッシュ通知（クールダウン機能）
  - Streamlit ダッシュボード（監視データ表示）
- AI：
  - news_nlp.score_news(): ニュース記事を OpenAI でセンチメント評価し ai_scores に保存
  - regime_detector.score_regime(): ETF の MA とマクロニュースを合成してレジーム判定
- ツール：
  - tools.paper_verification_report: Paper Trading 結果から検証レポート生成

---

## セットアップ手順

最低限の手順（ローカルでの動作確認向け）：

1. Python（推奨: 3.10+）を用意します。
2. 仮想環境作成（任意）：
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール：
   - pip install duckdb psutil requests streamlit openai
   - （プロジェクトに requirements.txt があればそれを使ってください）
4. データディレクトリ作成（デフォルトパス）：
   - mkdir -p data
5. 環境変数の準備：
   - プロジェクトルートに .env や .env.local を置くと自動で読み込まれます（既存 OS 環境変数は保護）。
   - 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
6. DB 初期化：
   - 各起動スクリプトが起動時に必要テーブルを冪等に作成します（init_monitoring_db 等）。

---

## 使い方（主要スクリプト）

パッケージはモジュールとして実行できます。プロジェクトルートから実行することを想定しています。

- 監視ループ（SystemMonitor を単独でポーリング）
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は常に production の sqlite_path を使用（run_monitoring の設計上）。
  - 実行例：
    - python -m kabusys.run_monitoring
    - または python src/kabusys/run_monitoring.py
  - 注意: 実行時にプロセス優先度を high に設定しようとします（プラットフォーム依存で失敗する場合はログに出力されます）。

- 実行エンジン（ExecutionEngine）
  - KABUSYS_ENV=paper_trading の場合はモックブローカーを使用し、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ記録します。
  - 実行例：
    - python -m kabusys.run_execution
  - 起動時にブローカークライアント、OrderManager、RiskManager、Reconciler を組み立て、セッションを実行します。

- Streamlit ダッシュボード（監視確認）
  - 起動例：
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を read-only で開いてダッシュボード表示します。

- Paper Trading 検証レポート
  - 起動例：
    - python -m kabusys.tools.paper_verification_report
    - 期間指定例：
      - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - DB の指定：
      - --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH を上書き可能）

- AI / バッチ処理（ライブラリ関数）
  - ニューススコアリング例（コードから呼び出す）：
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key="...")  ※ DuckDB 接続を渡して使用
  - レジーム判定：
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key="...")

---

## 環境変数（主要項目）

※ Settings クラス（kabusys.config.Settings）が参照する環境変数の抜粋です。詳細はソースを参照してください。

- 認証 / API
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - OPENAI_API_KEY (OpenAI 呼び出しで使用)
  - LINE_CHANNEL_ACCESS_TOKEN（任意、AlertManager 用）
  - LINE_USER_ID（任意、AlertManager 用）

- 実行モード
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - paper_trading: run_execution は paper_sqlite_path を使用して DB を分離

- DB / ファイルパス
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (監視用, デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用, デフォルト: data/paper_trading.db)
  - PID_FILE_PATH (デフォルト: data/execution.pid)
  - KILL_FLAG_PATH (デフォルト: data/kill.flag)

- Paper Trading 動作
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）

- 監視パラメータ（Settings で float/int として取得）
  - CPU_THRESHOLD_PCT（デフォルト: 90.0）
  - MEMORY_THRESHOLD_PCT（デフォルト: 85.0）
  - DISK_THRESHOLD_PCT（デフォルト: 90.0）

- その他
  - LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1（自動 .env 読込を無効化）

.env の自動読み込み挙動：
- プロジェクトルート（.git または pyproject.toml を探索）を検出できる場合、.env を自動で読み込みます。
- 読み込み順序: OS 環境変数 (優先) > .env.local > .env
- OS 環境変数は保護され、.env.local の override でも上書きされません。

追加の起動時オプション：
- MONITOR_POLL_INTERVAL：run_monitoring のポーリング間隔（秒）。正の整数で指定。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主要モジュールと役割の簡単な説明です。

- kabusys/
  - __init__.py — パッケージ情報（__version__ など）
  - config.py — 環境変数 / .env ローディングと Settings クラス
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト（paper_trading 切替）
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成ツール
  - monitoring/
    - monitoring_db.py — SQLite テーブル作成・永続化 API（MonitoringDB）
    - system_monitor.py — CPU/メモリ/ディスク/プロセス/データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン／ポジション制限監視
    - kill_switch.py — フラグファイルを用いた停止シグナル管理
    - alert_manager.py — LINE Push 通知（クールダウン付き）
    - monitoring_engine.py — 各 Monitor を束ねるループ / run_once（テスト用）
    - streamlit_dashboard.py — Streamlit による簡易ダッシュボード
  - execution/
    - order_manager.py — 注文ステートマシンの外向き API
    - reconciler.py — 起動時の注文・ポジション再同期ロジック
    - （その他: broker_factory, execution_engine, order_repository 等が想定）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・集約キャップ処理
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — momentum/volatility/value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py — OpenAI を用いたニュースセンチメント集約・スコア保存
    - regime_detector.py — ETF MA とマクロニュースを合成した市場レジーム判定
  - data/ （外部データ・DB はここに置かれる想定）
    - data/kabusys.duckdb
    - data/monitoring.db
    - data/paper_trading.db

（上は主要ファイルのみ抜粋。実際のツリーは src/kabusys 内のモジュールを参照してください）

---

## 注意事項 / 運用上のヒント

- 本リポジトリのコードは実運用前提の完全実装ではなく、設計例・骨組みを示すものです。実際の資金を動かす前に必ず安全性・例外処理・テストを行ってください。
- OpenAI / ブローカー API キーなどの秘密情報は .env 等で管理し、バージョン管理に含めないでください。
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と分離するよう設計されています。設定ミスで本番 DB にアクセスしないよう注意してください。
- Process priority / CPU affinity の設定はプラットフォーム依存です。権限不足や未対応 OS の場合はログに警告が出ます。
- monitoring は run_monitoring の説明の通り「監視用」であり、ExecutionEngine 側が起動していないとプロセス検出関連の警告が出ます。

---

必要であれば README の英語版や、各コンポーネントの詳細（API 仕様、DB スキーマ、ユニットテスト方針、デプロイ手順等）も作成します。どの部分を詳細化するか指示してください。