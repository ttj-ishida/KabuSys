# KabuSys

日本株向け自動売買システムのコアライブラリ群（実装スニペット）。  
この README はリポジトリ内のコードを基に作成した概要・使い方ドキュメントです。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（起動／コマンド例）
- 環境変数（主要）
- ディレクトリ構成（主要ファイルの説明）
- 運用メモ（フラグファイル・PID・監視）

---

プロジェクト概要
- KabuSys は日本株の自動売買システムのコアモジュール群を提供します。  
  主に以下の関心を持つコンポーネントを含みます：
  - 注文管理（OrderManager / ExecutionEngine）
  - ブローカー抽象（BrokerClientFactory 等）
  - ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
  - リサーチ（ファクター計算、将来リターン、IC 等）
  - AI 連携（ニュースの NLP スコアリング、レジーム判定 via OpenAI）
  - 監視（SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine）
  - 運用ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

主な機能一覧
- Execution:
  - ExecutionEngine を中心とした発注・リスク管理・リコンシリエーション機能
  - Paper Trading モード（実ブローカーと分離された専用 SQLite DB）
- Portfolio:
  - 候補選定（スコア順ソート）
  - 等重・スコア重み付け、リスクベースの株数計算
  - セクターキャップ、レジーム乗数
- Research:
  - Momentum / Volatility / Value ファクター計算（DuckDB 利用）
  - 将来リターン・IC 計算、統計サマリー
- AI:
  - ニュースを集約して OpenAI（gpt-4o-mini）でセンチメントを算出・保存
  - マクロ記事＋MA200乖離で市場レジーム（bull/neutral/bear）を算出
- Monitoring:
  - システム状態（CPU/メモリ/ディスク）・プロセス生存・データ鮮度監視
  - 注文滞留・約定異常検出
  - ドローダウン / ポジション上限監視とアラート（LINE Push）
  - Kill Switch（条件を満たすと data/kill.flag を出力して ExecutionEngine を停止）
  - Streamlit ベースの監視ダッシュボード
- 運用ツール:
  - Paper Trading 検証レポート生成スクリプト（期間指定可）

セットアップ手順（開発 / ローカル実行向け）
1. 必要な環境
   - Python 3.9+（ソースは型注釈や modern 標準ライブラリを使用）
   - SQLite（標準ライブラリで利用）
   - 推奨パッケージ（pip でインストール）:
     - duckdb
     - psutil
     - requests
     - streamlit (ダッシュボード利用時)
     - openai (AI 機能利用時)
   例:
     - pip install duckdb psutil requests streamlit openai

2. リポジトリの取得
   - git clone <repo>
   - プロジェクトルート（pyproject.toml / .git の位置）で作業することを推奨

3. インストール（任意）
   - 開発用途でパッケージとして扱うなら、pyproject.toml がある想定で:
     - pip install -e .   （プロジェクトがパッケージ化されている場合）
   - あるいは実行時に PYTHONPATH=src を指定:
     - export PYTHONPATH=$(pwd)/src

4. 環境変数の設定
   - プロジェクトルートに .env を作成（.env.example を参考に）
   - 自動ロード:
     - デフォルトで .env を自動ロード（ただし OS 環境変数が優先）
     - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 主要な環境変数については後述（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY, KABUSYS_ENV 等）

5. データディレクトリ
   - デフォルトの DB / PID / フラグパスは project_root/data 以下
   - 必要に応じてディレクトリを作成:
     - mkdir -p data

使い方（起動 / コマンド例）
- 実行前の注意:
  - パッケージがインストールされていない場合は PYTHONPATH=src を指定するか、pip install -e . を行ってください。
  - 「実行」系スクリプトは main 関数を持つため、python -m で実行できます（パッケージ化または PYTHONPATH の設定が必要）。

1. 監視ループ（Monitoring）
   - 起動スクリプト:
     - python -m kabusys.run_monitoring
   - 説明:
     - SystemMonitor を用いて定期的に状態を記録します。
     - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能。デフォルトは 60 秒。
     - 監視は常に Settings.sqlite_path（本番 DB）を使用します（環境に依存せず本番 DB に記録）。

2. 実行エンジン（ExecutionEngine）
   - 起動スクリプト:
     - python -m kabusys.run_execution
   - 説明:
     - KABUSYS_ENV=paper_trading を指定すると MockBrokerClient を使用し、デフォルトで data/paper_trading.db に記録して本番 DB と分離されます。
     - 実行中は data/execution.pid に PID ファイルを作成（stop リクエスト検出のため）。
     - 起動時に data/stop_requested.flag が存在すると起動しません（安全措置）。

3. Streamlit 監視ダッシュボード
   - 起動:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 説明:
     - 監視 DB を read-only で開き、Overview/Positions/Orders/System を表示します。

4. Paper Trading 検証レポート
   - 実行:
     - python -m kabusys.tools.paper_verification_report
     - オプション:
       - --from YYYY-MM-DD
       - --to YYYY-MM-DD
       - --db PATH  （PAPER_TRADING_SQLITE_PATH を上書き）
   - 説明:
     - data/paper_trading.db（デフォルト）を参照して、稼働率・注文成功率・レイテンシ等を集計し PASS/FAIL を判定します。

5. AI 機能（ニュース NLP / レジーム判定）
   - news_nlp.score_news(conn, target_date, api_key=None)
     - DuckDB 接続（prices_raw/raw_news/ai_scores 等のテーブルがある conn）を渡して実行。
     - OPENAI_API_KEY（または api_key 引数）が必要。
   - regime_detector.score_regime(conn, target_date, api_key=None)
     - ETF 1321 の MA200 とマクロ記事センチメントを合成して market_regime に書き込み。

主要な環境変数（抜粋）
- アプリ全般
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト: INFO）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると .env の自動ロードを抑止

- API / トークン
  - JQUANTS_REFRESH_TOKEN: （必須）J-Quants API 用
  - KABU_API_PASSWORD: （必須）kabuステーション API 用
  - OPENAI_API_KEY: OpenAI 呼び出し用（ai/news_nlp, ai/regime_detector）

- DB / ファイルパス
  - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH: Execution PID（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH: Kill Switch 用フラグ（デフォルト: data/kill.flag）

- Paper Trading / Broker 模擬挙動
  - KABUSYS_ENV=paper_trading に設定すると run_execution は MockBrokerClient を使用し、本番 DB と分離された paper_sqlite_path を使います。
  - PAPER_FILL_MODE: paper_trading 時の約定挙動（instant/partial/never/reject）

- Monitoring
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
  - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視の閾値（%）

ディレクトリ構成（主要ファイルと説明）
- src/kabusys/
  - __init__.py — パッケージ初期化、バージョン
  - config.py — .env 自動読み込み・Settings クラス（環境変数の集中管理）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト（paper_trading 切替）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算（等重・スコア重み）
    - position_sizing.py — 発注株数計算（risk_based, equal, score）
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — momentum/volatility/value ファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py — raw_news を LLM でスコアリングして ai_scores へ書き込み
    - regime_detector.py — MA200 と LLM を合成して市場レジーム判定
  - monitoring/
    - monitoring_db.py — SQLite テーブル初期化・永続化ヘルパー（system_status/trade_logs/...）
    - system_monitor.py — CPU/メモリ/ディスク・プロセス・データ鮮度の監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の書き込み（ExecutionEngine 停止トリガ）
    - alert_manager.py — LINE Push 通知ラッパー（クールダウン有）
    - monitoring_engine.py — 各 Monitor を束ねる実行エンジン
    - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード

運用メモ（フラグファイル・PID）
- 停止／起動管理
  - data/stop_requested.flag:
    - run_monitoring / run_execution はこのファイルの存在を検知してループを終了・エンジン停止します。外部から停止させたい場合はこのファイルを作成してください。
  - data/kill.flag:
    - KillSwitch が条件を満たすと理由を書き込んでこのファイルを作成します。ExecutionEngine は起動時等でこのフラグを確認して停止します。
  - data/execution.pid:
    - ExecutionEngine 実行時に PID を書き込む想定。SystemMonitor はこの PID を参照してプロセスが生存しているかチェックします。stale PID（プロセス不在）の場合はファイルを削除してアラートを登録します。

データベース・マイグレーションの注意
- monitoring_db.init_monitoring_db は冪等にテーブル・インデックスを作成し、既存 DB に対してカラム追加の簡易マイグレーション（例: trade_logs.latency_ms, dashboard.peak_value）を行います。

テスト／デバッグ向けヒント
- 自動 .env ロードを無効にする:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- ログレベルを上げる:
  - LOG_LEVEL=DEBUG
- Paper Trading で実際の注文 API に触らず検証したい場合:
  - KABUSYS_ENV=paper_trading を設定して run_execution を起動

最後に
- 本ドキュメントはリポジトリ内のコードベースを参照して生成しています。実際の環境へのデプロイ・本番運用を行う際は、公開鍵・シークレットの管理、監査ログ、テスト運用、ブローカー API の実行確認を十分に行ってください。

必要なら、README の CI / systemd / Docker 用の具体的な起動例や requirements.txt の雛形、よくある Q&A（エラー時の対処）等を追加で作成します。どの情報が欲しいか教えてください。