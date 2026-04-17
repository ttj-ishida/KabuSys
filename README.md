# KabuSys

KabuSys は日本株向けの自動売買 / リサーチ / 監視フレームワークです。本リポジトリは以下の主要機能を含み、実運用（live）およびペーパートレーディング（paper_trading）両方に対応する設計になっています。

- 注文の発行・状態管理・再同期（ExecutionEngine, OrderManager, Reconciler）
- リスク管理（RiskManager, RiskMonitor）
- 監視・アラート（SystemMonitor, TradeMonitor, AlertManager, KillSwitch）
- ポートフォリオ構築（選定・重み付け・ポジションサイズ計算）
- リサーチ用ファクター計算（momentum / volatility / value 等）
- ニュースの NLP スコアリング / 市場レジーム判定（OpenAI を利用）
- Paper Trading の検証レポート生成と Streamlit ダッシュボード

以下に使い方、セットアップ、ディレクトリ構成等をまとめます。

## 機能一覧（概要）
- Execution
  - ExecutionEngine を起動して注文発行・管理を行う
  - Paper Trading モードではブローカーをモック化し、DB を分離して動作
  - 起動時リコンシリエーション（Reconciler）で注文・ポジションを同期
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク、プロセス生存、データ鮮度をチェック
  - TradeMonitor：滞留注文や約定価格の異常を検出
  - RiskMonitor：ドローダウンやポジション上限の監視とログ化
  - KillSwitch：条件により実運用プロセス停止用のフラグ（data/kill.flag）を作成
  - AlertManager：LINE によるプッシュ通知（オプション）
  - Streamlit ダッシュボード（監視の可視化）
- Portfolio
  - 候補選定（select_candidates）
  - 等金額／スコア加重の重み計算
  - セクター制約の適用（apply_sector_cap）
  - ポジションサイズ算出（calc_position_sizes）
- Research
  - DuckDB 上の prices_daily / raw_financials を用いたファクター計算（momentum/volatility/value）
  - 将来リターン・IC・ファクター統計量計算
- AI
  - news_nlp: raw_news を集約して OpenAI（gpt-4o-mini 等）でセンチメントを算出し ai_scores に保存
  - regime_detector: MA200 とマクロニュースセンチメントを合成して日次レジーム判定

## 必要要件（主な Python パッケージ）
（プロジェクトで使用されている主な依存）
- Python 3.10+
- duckdb
- psutil
- requests
- streamlit（ダッシュボード利用時）
- openai（AI 機能を使う場合）
- sqlite3（標準ライブラリ）

（requirements.txt がない場合は仮に下記を pip インストールしてください）
pip install duckdb psutil requests streamlit openai

## セットアップ手順（開発・実行のための最小手順）
1. リポジトリをクローンし、仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install -r requirements.txt
   - または: pip install duckdb psutil requests streamlit openai

3. data ディレクトリを作成（実行時に自動作成されますが手動作成しておくと安心）
   - mkdir -p data

4. 環境変数の設定
   - プロジェクトルートに .env または .env.local を置くと自動的に読み込まれます（既存 OS 環境変数が優先されます）。
   - 主要な環境変数（最低限）
     - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必要な場合）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - KABUSYS_ENV: 実行環境（development | paper_trading | live）。デフォルトは development。
     - OPENAI_API_KEY: OpenAI を用いる際に必要（news_nlp / regime_detector）
   - その他（任意・上書き可能）
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
     - PAPER_FILL_MODE: paper_trading の Fill モード（instant | partial | never | reject）
     - PAPER_TRADING_SQLITE_PATH: ペーパー用 SQLite パス（デフォルト data/paper_trading.db）
     - SQLITE_PATH: 監視 DB パス（デフォルト data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - PID_FILE_PATH, KILL_FLAG_PATH, LOG_LEVEL など（config.Settings を参照）

5. 初期 DB 作成（必要に応じて）
   - 監視 DB は起動時に自動でテーブル作成（init_monitoring_db）されますが、手動で初期化する場合:
     - python -c "import sqlite3; from kabusys.monitoring.monitoring_db import init_monitoring_db; init_monitoring_db(sqlite3.connect('data/monitoring.db'))"

## 実行方法（代表的なコマンド例）
- ExecutionEngine を起動（本番 / ペーパー両対応）
  - 本番（KABUSYS_ENV=live）
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - ペーパートレーディング（Paper Trading）
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - Paper モードでは paper_sqlite_path（デフォルト data/paper_trading.db）に記録されます

- Monitoring（監視ループ）を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する場合:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Streamlit ダッシュボード（監視可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート出力
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- 停止 / キル方法
  - 実行ループ終了用の "stop flag" は stop_requested.flag（run_monitoring/run_execution の内部で参照）です（実装上は data/stop_requested.flag を使用）。
  - KillSwitch（監視が判断して書き込む）による停止要求は data/kill.flag に理由を書き込みます。ExecutionEngine は起動時にこのフラグを確認し、フラグがある場合は起動を抑止します。
  - 手動でフラグを削除するには:
    - rm data/kill.flag

## 主要な設定項目と環境変数
- KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: （必須: J-Quants を使う場合）
- KABU_API_PASSWORD: kabuステーション の API パスワード（必須）
- OPENAI_API_KEY: OpenAI を使う場合に必須
- PAPER_FILL_MODE: ペーパートレーディング時の約定モード（instant|partial|never|reject、デフォルト instant）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（デフォルト）
- SQLITE_PATH: data/monitoring.db（監視 DB）
- DUCKDB_PATH: data/kabusys.duckdb
- MONITOR_POLL_INTERVAL: 監視ループ間隔（秒）
- LOG_LEVEL: ログのレベル（DEBUG/INFO/...）

設定は .env / .env.local に記載しておくと自動読み込みされます。.env 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

## 主要ファイルとディレクトリ構成
（抜粋。実際は src/kabusys 以下に複数のモジュールがあります）

- src/kabusys/
  - __init__.py (パッケージ定義)
  - config.py (環境変数・設定管理)
  - run_execution.py (ExecutionEngine 起動スクリプト)
  - run_monitoring.py (SystemMonitor ポーリング実行)
  - tools/
    - paper_verification_report.py (Paper Trading レポート生成)
  - ai/
    - news_nlp.py (ニュース NLP スコアリング)
    - regime_detector.py (市場レジーム判定)
  - monitoring/
    - monitoring_db.py (SQLite スキーマ・アクセス)
    - system_monitor.py (CPU/メモリ/ディスク・データ鮮度監視)
    - trade_monitor.py (注文滞留・約定異常検出)
    - risk_monitor.py (ドローダウン・ポジション上限監視)
    - kill_switch.py (kill.flag の作成/管理)
    - alert_manager.py (LINE 通知)
    - monitoring_engine.py (複数モニタを束ねる)
    - streamlit_dashboard.py (Streamlit ダッシュボード)
  - execution/
    - order_manager.py, reconciler.py, order_repository.py, など（注文発行〜管理ロジック）
  - portfolio/
    - portfolio_builder.py (候補選定・重み)
    - position_sizing.py (株数算出)
    - risk_adjustment.py (セクター制約・レジーム乗数)
  - research/
    - factor_research.py (ファクター計算)
    - feature_exploration.py (IC 等)
  - data/ (実行時に利用するデータファイル類: monitoring.db / paper_trading.db / kabusys.duckdb 等)

簡易ツリー（抜粋）
- src/
  - kabusys/
    - run_execution.py
    - run_monitoring.py
    - config.py
    - execution/
    - monitoring/
    - portfolio/
    - research/
    - ai/
    - tools/
    - data/  (実行時に作成される)

## 開発時の注意点 / 補足
- 環境自動ロード:
  - config.py はプロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を自動で読み込みます。テストや特別なケースでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等でテーブルを作成し、既存スキーマに足りないカラムがあれば ALTER TABLE により追加します。
- AI/外部 API:
  - news_nlp / regime_detector は OpenAI API を呼びます。API キーがない場合は該当機能は使えません（score_news / score_regime は例外を投げます）。
  - API 呼び出しはリトライ処理やフェイルセーフを備えていますが、API 利用状況に応じたレート管理は行ってください。
- プロセス優先度:
  - run_* スクリプトは最初に set_process_priority("high") を呼びます（psutil を利用）。権限がない環境では警告を出してスキップされます。
- Kill / Stop フラグ:
  - 実行ループの停止には data/stop_requested.flag（run_monitoring/run_execution でチェック）と、監視による停止要求は data/kill.flag に書き込まれます。フラグ管理は慎重に行ってください。

## よくあるコマンドまとめ
- 実行環境: export KABUSYS_ENV=paper_trading
- 実行（Paper Trading）
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution
- 監視起動
  - python -m kabusys.run_monitoring
- ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10

---

この README はコードベースから抜粋して要点をまとめたものです。より詳細な実装や追加設定は各モジュール（src/kabusys 以下）の docstring やログメッセージを参照してください。必要であれば .env.example の雛形や運用手順書、デプロイ手順のサンプルも作成します。どのドキュメントを優先して欲しいか教えてください。