README
======

概要
----
KabuSys は日本株自動売買システムのコアライブラリ群です。本リポジトリは以下の主要機能を含みます:
- 注文作成／送信／状態同期のための Execution 層（OrderManager, ExecutionEngine 等）
- 監視（Monitoring）：システム稼働状態、注文滞留、リスク（ドローダウン・ポジション上限）をチェックしログ／アラートを出す
- ポートフォリオ構築（銘柄選定・重み付け・ポジションサイジング）
- リサーチ（ファクター計算・特徴量探索）
- AI を使ったニュースセンチメントおよび市場レジーム判定（OpenAI API 統合）
- ツール類（Paper Trading 検証レポート、Streamlit ダッシュボード 等）

ライブラリは純粋関数群（ポートフォリオ計算等）、永続化層（SQLite / DuckDB）、外部 API 連携（ブローカー / OpenAI / LINE）で構成されています。

主な機能
--------
- 実行系
  - 注文作成・送信・同期（OrderManager, Reconciler）
  - 起動時の再同期（Reconciler）でクラッシュからの復旧対応
- 監視系
  - SystemMonitor: CPU/MEM/DISK、プロセス死活、データ鮮度を監視して monitoring DB に記録
  - TradeMonitor: 注文滞留、約定価格の異常を検出してリスクログへ記録
  - RiskMonitor: ドローダウン・ポジション数上限を監視し必要に応じて kill.flag を書く
  - AlertManager: LINE Messaging API による通知（クールダウン管理）
  - Streamlit ダッシュボードで監視情報を可視化
- ポートフォリオ構築
  - 候補選定 / 等配分 / スコア配分 / リスクベースの株数決定 / セクターキャップ / レジーム乗数
- リサーチ
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 経由で prices_daily/raw_financials を参照）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- AI
  - ニュースを OpenAI (gpt-4o-mini) に投げて銘柄別センチメントを ai_scores に書き込む
  - マクロ記事と ETF MA200 を組み合わせて市場レジーム（bull/neutral/bear）を判定しテーブルへ保存
- ツール
  - Paper Trading 検証レポート生成（期間指定可）
  - Monitoring 用 Streamlit ダッシュボード

セットアップ手順
----------------
推奨 Python バージョン: 3.10 以上（型アノテーションで | を使用しているため）

1. リポジトリをクローン
   - git clone <repo-url>
   - 作業ディレクトリはプロジェクトルート（.git / pyproject.toml が存在する場所）

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   必要な主要パッケージ（例）:
   - duckdb
   - psutil
   - openai
   - requests
   - streamlit
   インストール例:
   - pip install duckdb psutil openai requests streamlit

   （プロジェクトに requirements.txt があれば pip install -r requirements.txt を使用してください。）

4. 環境変数設定
   - .env / .env.local をプロジェクトルートに置くと自動で読み込まれます（OS 環境変数が優先）。
   - 自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
   - 主要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須な場合）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
     - KABUSYS_ENV: execution の動作モード。development / paper_trading / live（デフォルト development）
     - PAPER_TRADING_SQLITE_PATH: paper trading 用 SQLite（デフォルト data/paper_trading.db）
     - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
     - LOG_LEVEL: ログレベル（DEBUG/INFO/...）
     - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、run_monitoring 用。デフォルト 60）

   .env のパースは .env/.env.local の文章中のコメントやクォートをある程度正しく扱います（config._load_env_file を参照）。

5. 初回 DB 作成
   - run_monitoring や run_execution を実行すると monitoring DB（SQLite）のテーブルは自動で作成（init_monitoring_db）されます。
   - DuckDB ファイル（prices_daily 等のテーブル）は外部 ETL/ロードで準備してください（研究・ファクター計算で参照）。

使い方
------

実行系（ExecutionEngine）
- 本番 / ペーパー実行のエントリポイント:
  - python -m kabusys.run_execution
  - 実行時に Settings に基づいて KABUSYS_ENV を確認します。KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い、paper_trading 用 SQLite（デフォルト data/paper_trading.db）に記録します。live や development の場合は本番 sqlite_path を使います。
  - 起動時にプロセス優先度を "high" に設定します（set_process_priority）。

監視（Monitoring）
- SystemMonitor のポーリングループ起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60 秒）。0 以下や不正値は無視されデフォルトにフォールバックします。
  - 監視は Settings に基づく sqlite_path（監視 DB）を使用します（Monitoring は環境に関係なく本番 sqlite_path を参照）。

Streamlit ダッシュボード
- 監視データの可視化:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 引数 --db で読み取り専用で開く DB を指定できます（デフォルト data/monitoring.db）。
  - 監視エンジンが DB を作成して更新している必要があります。

Paper Trading 検証レポート
- レポート生成スクリプト:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で PAPER_TRADING_SQLITE_PATH を上書き可能（デフォルト data/paper_trading.db）。
  - レポートでは稼働率・注文成功率・送信率・P95 レイテンシ等を算出し PASS/FAIL を出力します。

AI 関連
- ニューススコアリング:
  - 関数: kabusys.ai.score_news(conn, target_date, api_key=None)
  - OpenAI API キーは引数で渡すか OPENAI_API_KEY 環境変数を設定してください。
  - raw_news / news_symbols テーブルから記事を集計し、ai_scores テーブルへ書き込みます。
- レジーム判定:
  - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF 1321 の MA200 乖離とマクロ記事の LLM センチメントを合成して market_regime に書き込みます。
- いずれも API 呼び出しに失敗した場合はフェイルセーフ（0.0 や既定値で継続）します。

設定（Settings）についての補足
- .env と .env.local の扱い
  - 自動ロード順: OS 環境 > .env.local (override=True) > .env (override=False)
  - OS の既存環境変数は保護され、.env ファイルでは上書きされません（protected 機構）。
  - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- KABUSYS_ENV の有効値: development, paper_trading, live
  - paper_trading の場合は発注先がモックになり、paper_sqlite_path（デフォルト data/paper_trading.db）へ記録されます。
- 代表的な Settings プロパティ:
  - sqlite_path / duckdb_path / paper_sqlite_path / pid_file_path / kill_flag_path
  - paper_fill_mode: instant | partial | never | reject（Paper Trading の約定シミュレーション）

ディレクトリ構成（主要ファイル）
--------------------------------
以下は本コードベースの主要モジュールと役割（抜粋）です。

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン）
  - config.py — 環境変数・Settings 管理（.env 自動ロードロジック含む）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト（paper_trading 切替対応）
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite テーブル作成・簡易永続化 API
    - system_monitor.py — CPU/MEM/DISK、プロセス、データ鮮度チェック
    - trade_monitor.py — 注文滞留・約定異常チェック
    - risk_monitor.py — ドローダウン / ポジション上限チェック
    - kill_switch.py — kill.flag 制御（ExecutionEngine 停止シグナル）
    - alert_manager.py — LINE 通知
    - monitoring_engine.py — Monitor を束ねるループ / テスト用 run_once
    - streamlit_dashboard.py — Streamlit による監視 UI
  - execution/
    - order_manager.py — 注文作成 / send / state machine API
    - reconciler.py — 起動時の注文・ポジション同期（ブローカーと突合）
    - (その他ブローカー関連・order_repository 等は本リポジトリの他ファイルに存在)
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 株数決定・単元丸め・資金配分ロジック
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value などの計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py — ニュースの LLM センチメント化ロジック（OpenAI）
    - regime_detector.py — マクロ + ETF MA200 によるレジーム判定

注意事項 / 運用上のポイント
-----------------------
- DB の取り扱い
  - monitoring 用 SQLite（data/monitoring.db）は監視ログ用に自動作成されます。
  - paper_trading モードは本番 DB と分離され、paper_sqlite_path（data/paper_trading.db がデフォルト）を使用します。
  - DuckDB はリサーチ用途（prices_daily, raw_financials など）で使用されます。これらのテーブルは別途ロードしてください。
- PID / Kill flag
  - ExecutionEngine は pid_file_path（デフォルト data/execution.pid）を使用してプロセスの存在を管理します。SystemMonitor は stale PID を検出して削除しリスクログに記録します。
  - KillSwitch は Settings.kill_flag_path（デフォルト data/kill.flag）に理由を書き込んで ExecutionEngine に停止シグナルを送ります。
- OpenAI / 外部 API
  - OPENAI_API_KEY は必須（AI 機能を使う場合）。API 呼び出しはリトライ等のフェイルセーフを実装していますが、コストやレート制限に留意してください。
- 権限
  - set_process_priority は OS によっては権限不足で失敗することがあります（警告ログのみ）。CPU affinity 設定も同様。

貢献 / 拡張案
--------------
- ブローカーアダプタ追加（実口座 / 他ブローカー）
- 銘柄ごとの lot_size を取り扱う拡張（position_sizing）
- Streamlit ダッシュボードの UI 強化（グラフ・フィルタ）
- DuckDB のテーブル作成 / ETL スクリプトの追加
- 単体テストおよび CI ワークフローの整備

ライセンス
----------
（ここにライセンス表記を入れてください）

お問い合わせ
------------
不明点や運用上の質問があればリポジトリの Issue または開発者にお問い合わせください。

以上。