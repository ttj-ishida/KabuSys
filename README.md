KabuSys — 日本株自動売買システム
=================================

このリポジトリは日本株向けの自動売買システム（KabuSys）のうち、実行エンジン、監視、ポートフォリオ構築、リサーチ、AI（ニュースNLP / レジーム検出）等の主要コンポーネントを含むモジュール群です。README は開発者・運用者向けにセットアップ方法、主要機能、使い方、ディレクトリ構成を日本語でまとめたものです。

要点
-----
- KABUSYS_ENV によって動作モードを切り替えられます（development / paper_trading / live）。
- 監視コンポーネントは SQLite（監視用 DB）と DuckDB（時系列データ・リサーチ用）を使用します。
- Paper trading モードは本番 DB と完全に分離された専用 SQLite（data/paper_trading.db）を使用します。
- OpenAI（gpt-4o-mini）を用いたニュースセンチメントやレジーム検出機能があります（API キー必須）。
- プロセス優先度や CPU affinity のユーティリティを備えています（psutil を使用）。

主な機能
--------
- 実行エンジン起動（run_execution.py）
  - ブローカー抽象化（本番/モック切替）
  - 注文管理（OrderManager）・リスク管理（RiskManager）・リコンシリエーション（Reconciler）
- 監視（monitoring）
  - SystemMonitor：プロセス状態・CPU/メモリ/ディスク・データ鮮度の監視
  - TradeMonitor：滞留注文、約定異常価格の検出
  - RiskMonitor：ドローダウン・ポジション数の監視と alert の記録
  - MonitoringEngine：上記モニタを束ねてポーリング
  - AlertManager：LINE Messaging API による通知（オプション）
  - Streamlit ダッシュボード（簡易 UI）
- ポートフォリオ構築（portfolio）
  - 候補選定、等重／スコア加重、ポジションサイジング、セクター制約、レジーム乗数
- リサーチ（research）
  - ファクター計算（モメンタム・ボラティリティ・バリュー）
  - 将来リターン、IC（Information Coefficient）、統計サマリ
  - DuckDB を利用した SQL+Python 実装
- AI（ai）
  - news_nlp.score_news：ニュース記事から銘柄ごとのセンチメントを生成して ai_scores に書き込む
  - regime_detector.score_regime：MA とマクロニュースのセンチメントで市場レジームを判定
- 運用補助ツール
  - tools/paper_verification_report.py：Paper Trading の検証レポート生成
  - プロセス優先度設定ユーティリティ（utils/process_priority.py）
  - 環境変数の自動読み込み（config.py は .env/.env.local をプロジェクトルートから読み込む）

前提・依存パッケージ
-------------------
- Python 3.9+（typing の構文や一部ライブラリ互換を想定）
- 必要な主要パッケージ（例）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード利用時)
- 実際の環境では requirements.txt を用意するか、以下のようにインストールしてください（例）:
  - python -m pip install duckdb psutil requests openai streamlit

セットアップ手順
----------------
1. リポジトリをクローンしてソースツリーに移動
   - git clone ... && cd <repo>

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit

4. データディレクトリを作成
   - mkdir -p data

5. 環境変数設定
   - プロジェクトルートに .env を置くか、環境変数で設定します。
   - 自動ロード:
     - config.py はプロジェクトルート（.git か pyproject.toml）を検出して .env/.env.local を自動で読み込みます。
     - 自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主な環境変数（重要）
--------------------
- KABUSYS_ENV: 動作モード（development / paper_trading / live）。デフォルト: development
- SQLITE_PATH: 監視用 SQLite（monitoring）パス。デフォルト: data/monitoring.db
- DUCKDB_PATH: DuckDB ファイルパス。デフォルト: data/kabusys.duckdb
- PAPER_TRADING_SQLITE_PATH: paper_trading モード時の SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: PaperBroker の約定モード（instant / partial / never / reject）。デフォルト: instant
- OPENAI_API_KEY: OpenAI API キー（ai モジュール利用時必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（実運用時必須）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用 refresh token（ある場合）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: Kill Switch のフラグファイル（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: Monitoring ポーリング間隔（秒）。デフォルト: 60

使い方（主なコマンド例）
-----------------------

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可。
  - 監視は Settings の sqlite_path（デフォルト data/monitoring.db）を使用します（環境に関係なく本番パスを使用する設計）。

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に書き込みます（本番 DB と完全分離）。
  - 例（paper_trading）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Streamlit ダッシュボード起動（監視 UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取ってダッシュボードを表示します（読み取り専用で開きます）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH で指定できます。

- AI 関連（ニューススコア / レジーム判定） — ライブラリ API
  - ニューススコア付与（Python API 呼び出し例）:
    - from datetime import date
      from kabusys.ai.news_nlp import score_news
      import duckdb
      conn = duckdb.connect("data/kabusys.duckdb")
      score_news(conn, date(2026, 4, 1), api_key="YOUR_OPENAI_KEY")
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
      score_regime(conn, date(2026, 4, 1), api_key="YOUR_OPENAI_KEY")
  - 注意: OpenAI 呼び出しは API キーが必要で、ネットワークエラーやレート制限を想定したリトライ処理が組み込まれています。

運用上のポイント / 実装メモ
-------------------------
- PID / Kill flag
  - ExecutionEngine は起動時に PID ファイルを書き込み、SystemMonitor はそれを監視します。kill.flag（Settings.kill_flag_path）を書き込むことで ExecutionEngine 停止シグナルを送るしくみがあります。
- DB 初期化
  - monitoring_db.init_monitoring_db を呼ぶことで必要なテーブル・インデックスが冪等的に作成されます。
- Paper trading 分離
  - 実行エンジンは KABUSYS_ENV=paper_trading のとき paper_sqlite_path を使い、本番 monitor DB と切り離します。安全にモック取引を検証できます。
- 環境ファイルのパース仕様
  - config.py の .env ローダはシェル形式の export 対応、シングル/ダブルクォート・エスケープ、コメントの扱いなどに細かな対応があります。自動ロードはプロジェクトルートが検出できない場合スキップされます。
- プロセス優先度
  - run_* 起動スクリプトは最初に set_process_priority("high") を呼び、優先度を上げようとします（psutil の権限や OS に依存して成功しない場合は警告でスキップされます）。

ディレクトリ構成（抜粋）
-----------------------
下記は主要モジュールの一覧（src/kabusys 配下の主要ファイル群を抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数/.env 読み込みと Settings
  - run_execution.py                 — ExecutionEngine 起動スクリプト
  - run_monitoring.py                — SystemMonitor ポーリング起動スクリプト

- src/kabusys/monitoring/
  - monitoring_db.py                 — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py                — システム状態・データ鮮度監視
  - trade_monitor.py                 — 注文滞留・約定異常監視
  - risk_monitor.py                  — ドローダウン・ポジション上限監視
  - kill_switch.py                   — kill.flag 制御
  - alert_manager.py                 — LINE Push 通知ラッパ
  - monitoring_engine.py             — 各監視を束ねるエンジン
  - streamlit_dashboard.py           — Streamlit ダッシュボード

- src/kabusys/execution/
  - order_manager.py
  - reconciler.py
  - order_repository.py (省略)
  - execution_engine.py (省略)
  - broker_factory.py (省略)
  - その他注文関連モジュール

- src/kabusys/portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py

- src/kabusys/research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py

- src/kabusys/ai/
  - news_nlp.py                       — ニュースセンチメント取得（OpenAI）
  - regime_detector.py                — MA + マクロセンチメントでレジーム判定
  - __init__.py

- src/kabusys/tools/
  - paper_verification_report.py      — Paper Trading 検証レポート

- src/kabusys/utils/
  - process_priority.py               — psutil を使った優先度/affinity ユーティリティ

補足
----
- 本リポジトリは運用・監視を重視した設計（冪等性、フェイルセーフ、部分失敗時の保護）をしています。実際に本番で稼働させる際は、環境変数の安全な管理、OpenAI やブローカー API のレート制限、バックアップ・監査ログ等の運用面配慮が必要です。
- ここに含まれるコードは説明用途に合わせた抜粋・実装であり、実運用に投入する前に追加のテスト・セキュリティレビューを行ってください。

問題があれば、どの部分（例: デプロイ手順、.env の例、requirements.txt の作成、特定モジュールの API 仕様など）をもう少し詳しく書くか教えてください。必要があればサンプル .env.example を作成します。