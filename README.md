KabuSys — 日本株自動売買システム（README）
======================================

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした小規模な Python パッケージ群です。本リポジトリには以下の主要機能が含まれます。

- 注文の作成・送信・再同期（ExecutionEngine / OrderManager / Reconciler）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- ファクター計算・リサーチユーティリティ（モメンタム／バリュー／ボラティリティ等）
- ニュース NLP（OpenAI を用いた銘柄別センチメントスコア）
- 市場レジーム判定（ETF マウントとマクロニュースの統合）
- 監視（System / Trade / Risk Monitor）、監視 DB（SQLite）への永続化、LINE 通知、Streamlit ダッシュボード
- Paper Trading モード（本番 DB と分離してモックブローカーで動作）

主な特徴
-------
- モジュール設計により、研究（DuckDB ベースの価格財務データ処理）と実行（ブローカー API）を分離
- 監視コンポーネントは独立した SQLite DB にログを残し、Streamlit で可視化可能
- Paper Trading 用に DB を分離し、実売買と完全に切り分けて検証可能
- OpenAI（gpt-4o-mini など）を使ったニュースセンチメント・レジーム判定をサポート（API キーが必要）
- プロセス優先度や CPU affinity のユーティリティを備え、運用面を考慮

セットアップ
----------
1. リポジトリをクローン／チェックアウト
   - 例: git clone <repo-url>

2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - 必要な主要パッケージ（例）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - 例:
     - pip install duckdb psutil requests openai streamlit

   ※ 実際の requirements.txt がある場合はそちらを使ってください。

4. 環境変数設定
   - 簡易的にはプロジェクトルートに .env を作り環境変数を定義できます（自動ロードされます）。
   - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主な環境変数（代表）
- JQUANTS_REFRESH_TOKEN — J-Quants 用トークン（必須）
- KABU_API_PASSWORD — kabuステーション API 用パスワード（必須）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（AI 機能利用時）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用（未指定時は通知は行われずログ出力のみ）
- KABUSYS_ENV — 起動環境（development | paper_trading | live）デフォルト: development
  - paper_trading の場合、Execution はモックブローカーを使用し、PAPER_TRADING_SQLITE_PATH に記録します。
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — Paper Trading の約定挙動（instant | partial | never | reject。デフォルト: instant）
- PID_FILE_PATH — ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — Kill スイッチ用フラグファイル（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト: 60）

使い方（実行例）
----------------

- 監視プロセスを起動（SystemMonitor のポーリングループ）
  - 環境変数 MONITOR_POLL_INTERVAL によってポーリング間隔を変更可能（秒）
  - 実行例:
    - KABUSYS_ENV=development python -m kabusys.run_monitoring
    - または python src/kabusys/run_monitoring.py （パッケージのインポートパスに注意）

  - 補足:
    - Monitoring は KABUSYS_ENV に関わらず監視用の sqlite_path を使用します（監視ログは常に同じ DB に集約）。

- 実行エンジン（ExecutionEngine）を起動
  - Paper Trading モードで試す例:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
      - paper_trading の場合、モックブローカーを使用し、data/paper_trading.db に記録されます（本番 DB と完全分離）。
  - Live モードの起動は KABUSYS_ENV=live、必要な本番用環境変数を設定して実行してください。

- Paper Trading 検証レポート生成
  - data/paper_trading.db を読み、指標（稼働率・注文成功率・レイテンシ等）を集計します。
  - 実行例:
    - python -m kabusys.tools.paper_verification_report
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - --db オプションで SQLite ファイルパスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- Streamlit 監視ダッシュボード
  - 実行例（起動時に DB パスを渡す）:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- AI 機能（ニュース NLP / レジーム判定）
  - OpenAI API キー（OPENAI_API_KEY）が必要です。
  - ライブラリ API を直接呼び出すことでバッチ処理できます（例: kabusys.ai.score_news）。
  - 例（Python REPL）:
    - from datetime import date
      from kabusys.ai import score_news
      score_news(duckdb_conn, date(2026, 4, 1), api_key="...")

注意・運用メモ
-------------
- .env 自動読み込み:
  - 自動ロード順: OS 環境変数 > .env.local > .env
  - テストなどで無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

- MONITOR_POLL_INTERVAL:
  - run_monitoring のポーリング間隔を秒で上書きできます（0 以下の値は無効としてデフォルト 60 秒に戻る）。

- PID / Kill スイッチ:
  - ExecutionEngine は起動時に PID を書き込み、監視系は PID の存在有無を参照してプロセス稼働を判定します。
  - KillSwitch はデータ面（ドローダウンやポジション上限）から判定して data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。

- Paper Trading:
  - Paper Trading は本番 DB とデータ分離されます。PAPER_FILL_MODE は "instant" / "partial" / "never" / "reject" のいずれかを指定可能。

- OpenAI 呼び出し:
  - ニュース NLP / レジーム判定は外部 API を使うため、API エラー時はフォールバック動作（エラーを吸収して継続）する設計です。ただし API キーは必須です。

ディレクトリ構成（抜粋）
----------------------
src/kabusys/
- __init__.py                — パッケージ定義
- config.py                  — 環境変数 / 設定管理
- run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py           — ExecutionEngine 起動スクリプト
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート CLI
- ai/
  - news_nlp.py               — ニュース NLP（OpenAI）処理
  - regime_detector.py        — 市場レジーム判定
- monitoring/
  - monitoring_db.py          — 監視ログ用 SQLite ラッパー
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - monitoring_engine.py
  - streamlit_dashboard.py
- execution/
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - (ブローカー関連や engine 実装がここに入る想定)
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- utils/
  - process_priority.py

（注）上記はコードベースから抜粋した主要ファイル群です。実際のリポジトリにはさらに細かいモジュールや補助ファイルが含まれます。

開発・拡張のヒント
-------------------
- DuckDB 経由でのファクター計算はテーブル（prices_daily, raw_financials, raw_news 等）に依存します。データ投入用の ETL は kabusys.data.pipeline 等（本リポジトリに存在する想定）を参照してください。
- OpenAI 呼び出し部分はリトライ・バリデーションを備えています。テスト時は _call_openai_api を patch して外部 API をモック化できます。
- 監視 DB（SQLite）は init_monitoring_db でスキーマ自動作成・マイグレーションします。既存 DB の互換性に配慮した設計です。

問い合わせ / 貢献
-----------------
- バグ報告や機能要望は issue を作成してください。
- プルリクエストは歓迎します。大きな設計変更は事前に issue で相談してください。

以上。必要があれば README にサンプル .env や具体的なコマンド例（systemd ユニットや Dockerfile 例など）を追加します。どの情報を追加したいか教えてください。