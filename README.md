# KabuSys

KabuSys は日本株の自動売買とそれに付随する監視・リサーチ・AI ツール群をまとめた小規模なフレームワークです。本リポジトリには取引エンジン、監視コンポーネント、ポートフォリオ構築ロジック、リサーチ/ファクター計算、ニュース NLP（OpenAI）連携などが含まれます。

以下はコードベースから生成した README です。

---
目次
- プロジェクト概要
- 機能一覧
- 必要条件 / 依存関係
- セットアップ手順
- 環境変数（主なもの）
- 使い方（起動/ツール）
- ディレクトリ構成
- 注意事項

---

プロジェクト概要
- 日本株自動売買（Kabuステーション等を想定）のコアロジックと運用周りのユーティリティ群。
- 発注管理（OrderManager）、再起動時のリコンシリエーション（Reconciler）、リスク管理、監視（MonitoringEngine）やアラート（LINE push）を備える。
- DuckDB / SQLite を用いたデータ分析・監視ログ保存。
- Paper Trading 用の分離された DB をサポートし、実際のブローカーとは切り分けて検証可能。
- ニュースセンチメント解析やレジーム判定は OpenAI（gpt-4o-mini 等）を利用可能（API キー必要）。

機能一覧
- ExecutionEngine 起動 / 発注管理
  - OrderManager、OrderRepository、RiskManager、Reconciler を組み合わせた実行エンジン設計
  - Paper Trading モード（モックブローカー・専用 SQLite）
- 監視システム
  - SystemMonitor: CPU/メモリ/ディスク/プロセス健全性、データ鮮度チェック
  - TradeMonitor: 滞留注文・約定異常価格の検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード永続化
  - MonitoringEngine: 各モニタを束ねてポーリング、KillSwitch による停止フラグ作成
  - AlertManager: LINE Messaging API による通知（クールダウン管理）
  - Streamlit ダッシュボード（監視情報表示）
- ポートフォリオ構築（純粋関数群）
  - 候補選定、等金額/スコア加重、セクターキャップ、レジーム乗数、ポジションサイズ計算
- Research（DuckDB 利用）
  - ファクター（モメンタム / ボラティリティ / バリュー）計算
  - 将来リターン計算、IC（情報係数）や統計サマリー
- AI（ニュース NLP / レジーム判定）
  - raw_news から銘柄ごとに記事を集約し OpenAI へバッチ送信してセンチメントを ai_scores に格納
  - マクロニュース + ETF MA200 を組み合わせた市場レジーム判定
- ツール
  - paper_verification_report: Paper Trading DB を集計して Pass/Fail 判定の検証レポート出力

必要条件 / 依存関係（代表）
- Python 3.9+
- 必要なパッケージの例:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード利用時)
- （実行環境により追加の OS 権限が必要：プロセス優先度設定や cpu_affinity 等）

セットアップ手順（ローカル開発向け）
1. リポジトリをクローンし、Python 仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）
2. 必要パッケージをインストール（例）
   - pip install duckdb psutil requests openai streamlit
   - （requirements.txt があれば pip install -r requirements.txt）
3. データディレクトリを作成
   - mkdir -p data
   - デフォルトでは monitoring DB は data/monitoring.db、duckdb は data/kabusys.duckdb、paper trading DB は data/paper_trading.db
4. 環境変数を設定
   - .env または .env.local に必要な環境変数を設定（下記「環境変数」参照）
   - 自動で .env を読み込む仕組みが組み込まれている（プロジェクトルートが .git または pyproject.toml によって検出される）。
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主な環境変数（必須/推奨）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須: Settings.jquants_refresh_token）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
- KABUSYS_ENV: 実行環境 ("development" / "paper_trading" / "live")（デフォルト: development）
  - paper_trading のときはブローカークライアントがモックに切り替わり DB は PAPER_TRADING_SQLITE_PATH に記録
- PAPER_FILL_MODE: paper trading の約定モード ("instant" | "partial" | "never" | "reject")（default: instant）
- PAPER_TRADING_SQLITE_PATH: paper trading 用 SQLite パス（default: data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（default: data/monitoring.db）
- PID_FILE_PATH: 実行エンジン PID ファイル（default: data/execution.pid）
- KILL_FLAG_PATH: kill.flag path（default: data/kill.flag）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、default: 60）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

使い方（主要コマンド・実行例）
- 監視ループを起動（production では常駐）
  - python -m kabusys.run_monitoring
  - 説明: SystemMonitor を初期化し、MONITOR_POLL_INTERVAL 秒ごとにチェックを実施。stop フラグファイル data/stop_requested.flag があると終了。
- Execution エンジンを起動
  - python -m kabusys.run_execution
  - 説明: ブローカークライアントを生成し ExecutionEngine をデーモンスレッドで走らせる。KABUSYS_ENV=paper_trading の場合は専用の paper DB を使用しモックブローカーが使われる。data/stop_requested.flag をチェックして安全に停止する。
- Paper Trading 検証レポートを生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH より優先）
  - レポートは標準出力へ表示。主要指標（稼働率、注文成功率、送信率、P95 レイテンシ）を評価して PASS/FAIL 判定を出力。
- Streamlit ダッシュボード（監視 UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 説明: 監視用 SQLite を read-only モードで開き、ダッシュボードを提供。MonitoringEngine が先に動いている必要がある。
- AI 機能（ニュース NLP / レジーム判定）をプログラムから利用
  - kabusys.ai.score_news(conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)
  - DuckDB 接続（duckdb.connect(...））を渡して呼び出す。OPENAI_API_KEY の設定が必須。
- Kill Switch / 停止フラグ
  - KillSwitch は監視で検出された致命的リスク（ドローダウンやポジション上限超過）により data/kill.flag を書き込み、それを検知した ExecutionEngine は安全停止する。flag を手動で消す場合は削除する（KillSwitch.clear() が実行時に使える）。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数・Settings 管理（.env ロード機能含む）
  - run_monitoring.py            — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - alert_manager.py
    - kill_switch.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他発注関連ファイル: broker_factory 等)
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - utils/
    - process_priority.py
  - data/ (ランタイムで使用・生成される想定)
    - monitoring.db (default)
    - kabusys.duckdb (default)
    - paper_trading.db (paper trading 用)
    - execution.pid, kill.flag, stop_requested.flag, etc.

注意事項 / 運用メモ
- 環境分離:
  - KABUSYS_ENV=paper_trading の場合、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と分離されるよう設計されています。AI 呼び出しやブローカー操作はモックに切り替えられます。
- .env の自動読み込み:
  - プロジェクトルート（.git または pyproject.toml を検出）から .env / .env.local を自動読込します。既存の OS 環境変数は保護されます。自動読込を無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し:
  - API 経由の処理は外部依存であり、レート制限やエラー対処（指数バックオフ）を実装しています。API キーは環境変数 OPENAI_API_KEY または関数引数で指定してください。
- プロセス優先度:
  - run_monitoring / run_execution は起動時に set_process_priority("high") を試みます。権限不足の場合は警告に留まり無視されます。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db() は冪等でテーブル作成・簡単なカラム追加マイグレーションを行います。既存データの扱いは慎重に行ってください。
- 安全措置:
  - KillSwitch は重大リスクを検出した場合にフラグファイルを書き、ExecutionEngine に安全停止を促します。運用上の判断は必ず人間が行ってください。

拡張 / 開発のヒント
- research/*.py の関数群は DuckDB 接続を受け取り純粋に計算を行うように設計されています。データが揃っていれば単体でテストしやすいです。
- portfolio/*.py の関数は副作用なしの純粋関数群なので、ユニットテストしやすく、Strategy の試作に便利です。
- AI 連携部分は外部 API に依存するため、ユニットテストでは _call_openai_api をモックすることを推奨します（コード内にその旨が明記されています）。

以上がリポジトリの概要、セットアップ、使い方およびディレクトリ構成の要約です。必要であれば .env.example のテンプレートや運用ガイド（デーモン化、systemd ユニット例、バックアップ手順など）も作成できます。どの情報を補足しましょうか？