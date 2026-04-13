# KabuSys

日本株向けの自動売買システム（ライブラリ / 実行スクリプト群）

このリポジトリは、発注エンジン、監視・アラート、ポートフォリオ構築、リサーチ、AI（ニュースセンチメント）などを含む統合的な自動売買基盤の一部実装です。コードはモジュール化されており、本番（live）・ペーパー（paper_trading）・開発（development）の環境切替、SQLite / DuckDB を用いたデータ永続化、外部API（OpenAI 等）連携、監視ダッシュボードなどを提供します。

主な設計方針
- DB（DuckDB / SQLite）を用いたデータ処理と永続化
- 環境変数 / .env による設定（自動読み込み機能あり）
- モジュールは可能な限り純粋関数または副作用を最小化
- フェイルセーフ（API失敗時のフォールバックやログ保護）を重視

---

## 機能一覧

- 実行（Execution）
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
  - Broker クライアントの抽象化／ファクトリ（paper_trading 環境では MockBroker を使用）
  - OrderManager / OrderRepository による注文管理
  - Reconciler による起動時の自動復旧（OrderSent の同期・ポジション差分チェック）
  - リスク管理（RiskManager、各種制約の実装）

- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/Disk/プロセス生存・データ鮮度監視（src/kabusys/run_monitoring.py を参照）
  - TradeMonitor: 注文滞留・約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視
  - MonitoringDB: SQLite ベースの監視用テーブル群（system_status / trade_logs / positions / risk_logs / dashboard）
  - AlertManager: LINE Messaging API を使ったプッシュ通知
  - KillSwitch: フラグファイルによる ExecutionEngine 停止シグナル
  - Streamlit ダッシュボード（src/kabusys/monitoring/streamlit_dashboard.py）

- ポートフォリオ構築（Portfolio）
  - 銘柄選定（スコア順ソート）、等重/スコア加重
  - セクター上限チェック、レジーム乗数
  - 株数算出（risk_based / equal / score）、単元株丸め、投下資金スケーリング

- リサーチ（Research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
  - DuckDB 経由で prices_daily / raw_financials を参照して計算

- AI（OpenAI 連携）
  - news_nlp: ニュース記事をまとめて LLM へ送り銘柄別センチメントを ai_scores テーブルへ書き込み
  - regime_detector: ETF（1321）MA200乖離とマクロニュースを合成して市場レジーム判定（bull/neutral/bear）
  - OpenAI は gpt-4o-mini を使用する設定になっています（API Key 必須）

- ユーティリティ
  - process_priority: Windows / POSIX を吸収したプロセス優先度 / CPU affinity 設定ユーティリティ
  - 環境設定管理（src/kabusys/config.py）: .env 自動読み込み、必須キー取得ラッパー、デフォルト値

---

## 前提 / 推奨環境

- Python 3.10+
- 必要パッケージ（最低限）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード利用時)
- SQLite（標準ライブラリに同梱）
- ネットワーク接続（必要に応じて OpenAI / LINE API）

（実際の運用では仮想環境・プロセスマネージャ（systemd 等）での管理を推奨します）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリを取得
   - git clone ... / あるいは適切にコードを配置

2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit

   （プロジェクトに requirements.txt がある場合はそちらを利用してください）

4. 環境変数 / .env を用意
   - プロジェクトルート（.git または pyproject.toml のある場所）に `.env` または `.env.local` を置くと自動で読み込まれます（読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 代表的な環境変数（例）:
     - KABUSYS_ENV=development | paper_trading | live
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PAPER_FILL_MODE=instant | partial | never | reject
     - MONITOR_POLL_INTERVAL=(秒、デフォルト60)
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag

5. データディレクトリ作成（必要に応じて）
   - mkdir -p data

---

## 実行方法

各スクリプトはモジュール実行可能です（Python の -m を利用）。

- 監視ループ（SystemMonitor）を起動
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は Settings.env に関係なく production 用の sqlite_path を使用します（監視ログは本番 DB を参照／更新）。
  - 実行例:
    - python -m kabusys.run_monitoring

- 実行エンジン（ExecutionEngine）を起動
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH）を利用して本番 DB と完全に分離します。
  - 実行例:
    - python -m kabusys.run_execution

- Paper Trading 検証レポート生成
  - src/kabusys/tools/paper_verification_report.py をコマンドラインで実行して、過去期間の検証結果を標準出力に表示できます。
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数より優先）
  - 実行例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit ダッシュボード（監視用）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用で監視 SQLite を可視化します（MonitoringEngine を先に起動してデータを書き込んでください）。

- AI スコアリング / レジーム判定（ライブラリ関数）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーは引数で渡すか環境変数 OPENAI_API_KEY を設定してください。

注意点
- 起動スクリプトは起動直後にプロセス優先度を "high" に設定しようとします（psutil を使用）。設定に失敗した場合は警告を出して続行します。
- Monitoring の DB 初期化（init_monitoring_db）は冪等に実装されています（必要なテーブルがない場合に作成）。

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV
  - 値: development | paper_trading | live
  - デフォルト: development

- SQLITE_PATH
  - 監視 DB（デフォルト: data/monitoring.db）

- DUCKDB_PATH
  - DuckDB データベース（デフォルト: data/kabusys.duckdb）

- PAPER_TRADING_SQLITE_PATH
  - paper_trading 用 SQLite（デフォルト: data/paper_trading.db）

- PAPER_FILL_MODE
  - paper_trading 時の MockBroker の fill モード
  - 有効値: instant, partial, never, reject（デフォルト: instant）

- MONITOR_POLL_INTERVAL
  - SystemMonitor のポーリング間隔（秒、デフォルト: 60）。不正な値や 0 以下はデフォルト 60 にフォールバック。

- OPENAI_API_KEY
  - OpenAI 呼び出しに必要（news_nlp / regime_detector 等で使用）

- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID
  - AlertManager（LINE）を有効にするために必要

- KABUSYS_DISABLE_AUTO_ENV_LOAD
  - 1 を設定すると .env 自動読み込みを無効化（テスト等で使用）

---

## 開発時の注意 / 実装メモ

- config._find_project_root は .git または pyproject.toml を基準にプロジェクトルートを検出します。パッケージ配布後も機能するよう .__file__ から親ディレクトリを探索します。
- .env のパースは比較的リッチに実装されており、シングル／ダブルクォート、export プレフィックス、インラインコメント等に対応します。
- MonitoringDB の初期化スクリプトは既存 DB に対するマイグレーション（列追加）処理も含みます（例: dashboard.peak_value, trade_logs.latency_ms の追加確認）。
- AI モジュールは外部 API 呼び出しの失敗に対してフェイルセーフな動作（スコア 0.0、もしくはスキップ）を行うよう設計されています。
- リアクティブなアラート（LINE）には簡易なクールダウン実装があり、同一 (level, category) に対して短時間で繰り返し送られないようになっています。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
    - streamlit_dashboard.py
    - __init__.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他注文・ブローカー関連モジュール)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - process_priority.py
    - __init__.py
  - monitoring/ (上記)

- data/
  - デフォルト SQLite / DuckDB ファイル群（data/monitoring.db, data/paper_trading.db, data/kabusys.duckdb）

---

## よくある運用シナリオ（例）

- 本番稼働
  - KABUSYS_ENV=live を設定
  - ExecutionEngine（run_execution.py）を systemd 等でデーモン化して運用
  - MonitoringEngine（run_monitoring.py）を別プロセスで常時稼働させ、異常時は LINE 通知・kill.flag により Execution を停止

- ペーパートレード検証
  - KABUSYS_ENV=paper_trading を設定（paper DB に完全分離）
  - paper_verification_report で performance / 安定性を評価
  - AI スコアリングやリサーチ機能は本番 DB に影響を与えません（DuckDB のデータソースにのみアクセス）

---

## 貢献 / 拡張ポイント（開発者向けメモ）

- BrokerClientFactory を拡張して他ブローカー実装を追加可能
- position_sizing の lot_size を銘柄別に対応するなどの拡張
- モニタリング指標の追加（例: ネットワーク I/O、ディスク使用のより細かい閾値）
- AI モジュールのモデルやプロンプト改善、結果の保存粒度向上

---

README はここまでです。具体的な導入・運用手順や .env.example、requirements.txt、systemd ユニットファイル等は別途用意すると実運用で便利です。不明点や追加してほしいサンプル（.env.example、systemd サンプル、requirements.txt など）があればお知らせください。