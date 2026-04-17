# KabuSys

KabuSys は日本株の自動売買／リサーチ／監視を目的とした軽量な Python モジュール群です。本リポジトリ内のモジュールは、戦略・ポートフォリオ構築、実行エンジン、監視（モニタリング）、研究用ユーティリティ、AI を使ったニュース解析などを含みます。

以下はこのコードベースの概要、機能、セットアップと起動方法、主要ファイル構成の説明です。

---

## プロジェクト概要

- 目的: 日本株向けの自動売買システム（注文生成・発注・リコンシリエーション）、監視（システム状態・注文異常・リスク）、研究（ファクター計算・特徴量解析）、および AI（ニュースセンチメント・レジーム判定）を提供する。
- 設計方針:
  - DuckDB / SQLite を用いたデータ処理（ローカル DB にデータを持つ）
  - 本番 / paper_trading を環境変数で切り替え（DB を分離）
  - 外部 API（kabuステーション、J-Quants、OpenAI）を利用可能だが、実行時にキーが未設定でもフェイルセーフで動作する箇所がある
  - 自動起動スクリプト（run_monitoring, run_execution）と CLI 風ツール（paper_verification_report, streamlit ダッシュボード等）を提供

---

## 主な機能一覧

- 実行（Execution）
  - ExecutionEngine を起動してブローカーへ注文を送信
  - Paper Trading モード（KABUSYS_ENV=paper_trading）では MockBrokerClient を使用し、paper_trading 用 SQLite DB（デフォルト: data/paper_trading.db）に記録
  - Reconciler による再起動時の同期（OrderSent の突合、ポジション差分検出）

- 監視（Monitoring）
  - SystemMonitor: CPU / メモリ / ディスク / プロセス死活チェック、価格データ鮮度チェック
  - TradeMonitor: 注文滞留（stale order）、約定異常価格検出
  - RiskMonitor: ドローダウン・ポジション上限の監視、Dashboard の永続化とリスクログ
  - KillSwitch / AlertManager: 重大リスクで kill.flag を書き込み、LINE へ通知（トークンが設定されている場合）
  - Streamlit ベースの簡易ダッシュボード（read-only で監視 DB を表示）

- ポートフォリオ構築
  - 候補選定（スコア順ソート）
  - 等重・スコア重み付け
  - セクターキャップ適用・レジーム乗数
  - ポジションサイズ計算（各種制約に対応、単元株丸め付き）

- 研究（Research）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン算出、IC（Information Coefficient）計算、統計サマリ

- AI（OpenAI を利用）
  - ニュースを LLM（gpt-4o-mini 等）でセンチメントスコア化し ai_scores に格納（複数記事の統合評価、バッチ処理、リトライ・バリデーション実装）
  - マクロニュース＋ETF MA200 を合成した市場レジーム（bull/neutral/bear）判定と DB 書き込み

- 補助ツール
  - paper_verification_report: Paper Trading の検証レポート生成（稼働率・注文成功率・レイテンシ等）
  - streamlit_dashboard: 監視 DB を可視化するダッシュボード

---

## セットアップ手順

1. Python 環境を準備（推奨: python 3.9+）
   - 仮想環境を作る例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - リポジトリに requirements.txt がない場合は最低限以下をインストールしてください。
     - duckdb
     - psutil
     - openai
     - requests
     - streamlit
   - 例:
     - pip install duckdb psutil openai requests streamlit

3. 環境変数 / .env
   - ルートに .env または .env.local を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化）。
   - 主な環境変数（重要・よく使うもの）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - OPENAI_API_KEY (AI 機能使用時に必要)
     - KABUSYS_ENV (development / paper_trading / live) — デフォルト: development
     - PAPER_FILL_MODE (paper_trading の約定動作: instant|partial|never|reject) — デフォルト: instant
     - PAPER_TRADING_SQLITE_PATH (paper_trading DB path) — デフォルト: data/paper_trading.db
     - SQLITE_PATH (monitoring DB path) — デフォルト: data/monitoring.db
     - DUCKDB_PATH (DuckDB path) — デフォルト: data/kabusys.duckdb
     - LOG_LEVEL (DEBUG|INFO|...) — デフォルト: INFO
     - MONITOR_POLL_INTERVAL (run_monitoring のポーリング間隔 [秒]) — デフォルト: 60
     - KILL_FLAG_PATH, PID_FILE_PATH など（デフォルトは data 以下）

4. データディレクトリ
   - デフォルトで使用する SQLite / DuckDB ファイルは data/ 配下に置かれます。必要に応じてディレクトリを作成してください。
     - mkdir -p data

---

## 使い方（実行例）

- 監視ループを起動（SystemMonitor を定期実行）
  - 簡単起動:
    - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を変更:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 停止方法:
    - プロセスに SIGINT (Ctrl+C) を送るか、プロジェクトルートの data/stop_requested.flag を作成すると次ループで安全停止します。

- 実行エンジンを起動（ExecutionEngine）
  - 本番 / 開発:
    - python -m kabusys.run_execution
  - Paper Trading（DB を分離してモックブローカーを使用）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 停止方法:
    - data/stop_requested.flag を作成するとエンジンは検知して停止します。
    - 重大リスク時に data/kill.flag が書き込まれると起動を拒否または停止されます。
  - 実行中の PID は data/execution.pid（デフォルト）に書かれます。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH より優先）
  - 例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit ダッシュボード（監視 DB の表示）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - read-only モードで監視 DB を開き、Overview / Positions / Orders / System のタブを表示します。

- AI 関連（プログラムから呼び出す）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")
  - 注意: OPENAI_API_KEY を環境変数に設定するか、api_key 引数で渡してください。API 呼び出しはリトライやフェイルセーフを備えていますが、料金とレートに注意してください。

---

## 主要ファイル / ディレクトリ構成

（実際のソースは src/kabusys 配下にあります。ここでは主なモジュールを抜粋して示します）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込みロジック（.env 自動ロード）
  - run_monitoring.py        — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート生成スクリプト
  - ai/
    - news_nlp.py             — ニュースを LLM でスコア化して ai_scores に書き込む
    - regime_detector.py      — マクロ + ETF MA200 で市場レジーム判定
  - monitoring/
    - monitoring_db.py        — SQLite を用いた監視ログ永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - alert_manager.py
    - kill_switch.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - reconciler.py
    - order_manager.py
    - order_repository.py     — (注文関連 DB 操作、OrderRecord 等)
    - execution_engine.py
    - broker_*                — ブローカークライアント関連（Factory, API 抽象等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - data/                     — 実行時に使う SQLite / DuckDB / flag / pid 等（ディレクトリ）
    - monitoring.db (デフォルト SQLITE_PATH)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
    - kabusys.duckdb (DUCKDB_PATH)
    - stop_requested.flag
    - kill.flag
    - execution.pid

（上記は主なファイルを抜粋したもので、さらに細かいモジュールが含まれます）

---

## 重要な運用・動作ノート

- .env の自動ロード:
  - ルートディレクトリ（.git または pyproject.toml のある場所）にある .env を自動で読み込みます。
  - OS 環境変数は保護され、.env は既存の OS 環境変数を上書きしません（.env.local は上書き可）。
  - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- DB と環境分離:
  - KABUSYS_ENV=paper_trading に設定すると、実行エンジンは paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用します。本番 DB と完全分離されます。
  - 監視（monitoring）は環境にかかわらずデフォルトの sqlite_path（monitoring DB）を用います（設計により本番監視は一元化される想定）。

- プロセス優先度と PID 管理:
  - run_monitoring / run_execution は起動時にプロセス優先度を設定しようとします（psutil を使用）。権限が足りない場合は警告が出ますが続行します。
  - 実行エンジンは PID ファイル（data/execution.pid）を使い stale PID の検出・削除を行います。PID ファイルは実行エンジン起動中に作成されます。

- 停止フラグ / kill flag:
  - data/stop_requested.flag を作成すると、run_monitoring/run_execution は次回ループで安全に停止します（外部からの停止指示用）。
  - KillSwitch（リスク基準により）data/kill.flag を書き込み、ExecutionEngine の起動拒否や停止トリガーとして運用できます。

- モニタリングのポーリング間隔:
  - 環境変数 MONITOR_POLL_INTERVAL で秒数を指定できます（デフォルト 60 秒）。不正な値（0 以下や非整数）はデフォルトにフォールバックします。

---

## 開発者向けメモ / テスト・拡張

- DuckDB 接続を渡して pure 関数群（research、ai の一部）を呼ぶことで、外部 API に依存せず比較的簡単にユニットテストが可能です。
- OpenAI 呼び出し箇所はリトライやフェイルセーフを装備していますが、テスト時は _call_openai_api をモックすることが推奨です（コード内でもその旨コメントあり）。
- DB スキーマのマイグレーションは monitoring_db.init_monitoring_db 内で簡易的に行っています（既存テーブルにカラムがなければ追加する等）。

---

必要であれば、README に以下の情報を追加できます:
- 具体的な .env.example のテンプレート
- より詳しい運用手順（systemd unit ファイル例、ログローテーション、バックアップ）
- CI / テスト実行（ユニットテストのコマンド例）
- 各コンポーネントの詳細クラス図やシーケンス図

補足・追加したい項目があれば教えてください。