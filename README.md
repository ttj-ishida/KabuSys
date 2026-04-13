KabuSys — README
===============

概要
----
KabuSys は日本株の自動売買／研究／監視を目的とした Python ベースの小規模フレームワークです。本リポジトリには以下の主要機能が含まれます。

- 実売買ロジック（ExecutionEngine）と注文管理（OrderManager / Reconciler）
- 監視・アラート周り（SystemMonitor / TradeMonitor / RiskMonitor / AlertManager）
- ポートフォリオ構築ユーティリティ（候補選定、重み付け、ポジションサイズ計算、セクター制約）
- リサーチ用ファクター計算（momentum / volatility / value）
- ニュースの NLP スコアリング（OpenAI を用いたセンチメント計算）
- Paper Trading 検証レポート生成ツール・Streamlit ダッシュボード

主な設計方針：
- DB（SQLite / DuckDB）を読み書きするが、分析処理は外部 API に依存しないように設計。
- 実行環境（KABUSYS_ENV）により paper_trading と live を明確に分離。
- OpenAI など外部 API 呼び出しはリトライとフォールバックを備え、フェイルセーフを重視。

主な機能一覧
--------------
- Execution
  - run_execution.py：ExecutionEngine を起動（KABUSYS_ENV により paper_trading 用クライアントを選択）
  - OrderManager / Reconciler：起動時リコンシリエーション、注文送信・同期
- Monitoring
  - run_monitoring.py：SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定可）
  - SystemMonitor / TradeMonitor / RiskMonitor：システム状態、滞留注文、ドローダウン等を監視
  - AlertManager：LINE Push による通知（トークン・ユーザID が必要）
  - KillSwitch：kill.flag による ExecutionEngine 停止シグナル発行
  - streamlit_dashboard.py：Streamlit で監視ダッシュボード表示
- Portfolio
  - 候補選定（select_candidates）・重み計算（等金額 / スコア重み）・ポジションサイズ計算・セクター上限適用
- Research
  - factor_research：momentum / volatility / value のファクター計算（DuckDB 経由で prices_daily 等を参照）
  - feature_exploration：将来リターン計算、IC（Spearman）計算、ファクター統計サマリ
- AI
  - news_nlp.score_news：OpenAI を使ったニュース記事の銘柄別センチメント集計・ai_scores への書き込み
  - regime_detector.score_regime：ETF（1321）MA とマクロニュースを組み合わせた市場レジーム判定
- Tools
  - tools.paper_verification_report：paper_trading 用 DB を対象に検証レポートを標準出力へ生成

セットアップ手順
----------------
前提
- Python 3.10+（typing の | 記法、match 等互換性のため）
- SQLite（標準ライブラリに同梱）
- 必要な Python パッケージ：duckdb, psutil, openai, requests, streamlit

仮想環境作成（推奨）
- python -m venv .venv
- source .venv/bin/activate もしくは .venv\Scripts\activate (Windows)

依存関係インストール（例）
- pip install duckdb psutil openai requests streamlit

（注）プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを利用してください。

環境変数 / .env
- Settings クラスは .env/.env.local を自動読み込みします（プロジェクトルートに .git または pyproject.toml がある場合）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- 主要な環境変数（例）:
  - KABUSYS_ENV: development / paper_trading / live （デフォルト: development）
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
  - KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
  - OPENAI_API_KEY: OpenAI API キー（AI 機能実行時に必要）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（任意）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - PAPER_FILL_MODE: paper_trading の約定モード（instant / partial / never / reject）
  - PID_FILE_PATH, KILL_FLAG_PATH, CPU/MEM/DISK 閾値 等（Settings 内で参照）

初期 DB 作成
- run_monitoring や run_execution を起動すると monitoring DB テーブル（system_status / trade_logs / positions / risk_logs / dashboard）を自動で作成・マイグレーションします（init_monitoring_db を経由）。

使い方
-------
1) 監視（Monitoring）を起動
- デフォルトポーリング間隔は 60 秒。環境変数で上書き可：
  - export MONITOR_POLL_INTERVAL=30
- 実行例：
  - python -m kabusys.run_monitoring
  - (起動時にプロセス優先度を "high" に設定し、監視データを SQLite に追記します。)

2) 実行エンジン（ExecutionEngine）を起動
- paper_trading 環境では MockBrokerClient を使用し、paper 用 DB に書き込みます：
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution
- 本番（live）:
  - export KABUSYS_ENV=live
  - python -m kabusys.run_execution
- 起動時にプロセス優先度を "high" に設定します。ExecutionEngine は duckdb/SQLite を利用します。

3) Streamlit ダッシュボード
- 起動例：
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Read-only URI で SQLite を開く（ダッシュボードは監視 DB の可視化用）。

4) Paper Trading 検証レポート
- 使い方：
  - python -m kabusys.tools.paper_verification_report
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

5) AI 機能（ニュース NLP / レジーム判定）
- OpenAI API キーが必要（環境変数 OPENAI_API_KEY または関数引数で渡す）。
- ニューススコアリング:
  - from kabusys.ai.news_nlp import score_news
  - score_news(conn, target_date, api_key=None)
- レジーム判定:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date, api_key=None)

設定や注意点
- MONITOR_POLL_INTERVAL が 0 や負値の場合はデフォルト 60 秒にフォールバックします。
- Paper Trading は本番 DB と分離され、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します。
- PAPER_FILL_MODE（instant / partial / never / reject）で Paper ブローカーの挙動を制御します。
- Settings.kill_flag_clear_on_start が "1" の場合、起動時に kill.flag をクリアする挙動を持つコンポーネントがあります。
- OpenAI 呼び出しはエラー時にリトライやフォールバック（ゼロスコア）を行い、処理全体を停止させない設計です。

ディレクトリ構成
----------------
主要ファイル/モジュールの構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / Settings 管理（.env の自動読み込み）
  - run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポートツール
  - monitoring/
    - __init__.py
    - monitoring_db.py         — SQLite 永続化レイヤ（テーブル作成・CRUD ユーティリティ）
    - system_monitor.py        — システム & データ鮮度チェック
    - trade_monitor.py         — 注文滞留・約定異常検出
    - risk_monitor.py          — ドローダウン・ポジション上限監視
    - alert_manager.py         — LINE Push 通知
    - kill_switch.py           — kill.flag による停止シグナル
    - monitoring_engine.py     — 各 Monitor を束ねるループ
    - streamlit_dashboard.py   — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - reconciler.py
    - order_repository.py
    - order_record.py
    - broker_factory.py
    - execution_engine.py
    - ... (注文・ブローカ関連)
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - risk_adjustment.py
    - position_sizing.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - pipeline.py (価格データ取得/ヘルパー)
    - stats.py (zscore 正規化等)
  - utils/
    - __init__.py
    - process_priority.py      — プロセス優先度 / CPU affinity ユーティリティ
  - その他（DuckDB/SQLite を参照する SQL 実装ファイル等）

開発・拡張メモ
----------------
- DB スキーマは monitoring_db.init_monitoring_db で冪等に作成 / マイグレーションされます。
- AI モジュールは OpenAI のレスポンス形式に依存するため、SDK のバージョン差分に注意してください（JSON mode を使用）。
- ポートフォリオロジックは純粋関数群（副作用なし）で実装されているため、単体テストが書きやすい構造です。
- Process priority / CPU affinity 設定は psutil を使っており、権限不足時は警告ログでスキップします。

ライセンス・貢献
----------------
- 本コードベースのライセンス／貢献（CONTRIBUTING.md）が別途ある場合はそちらを参照してください。

補足（よく使うコマンドまとめ）
--------------------------------
- 監視起動:
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
- 実行エンジン起動（paper）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Paper レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

README に含めてほしい詳細があれば追記します（例: 環境変数テンプレート、DB マイグレーション手順、依存パッケージの exact list 等）。