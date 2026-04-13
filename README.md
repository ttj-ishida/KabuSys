# KabuSys — README

このリポジトリは日本株自動売買システム「KabuSys」のコードベースです。  
以下は開発者向けの概要、機能、セットアップと実行方法、主要なディレクトリ構成の説明です。

注意: 本READMEは掲示されたソースコードの内容に基づいて作成しています。実環境で動かす前に .env の確認や権限・APIキーの管理を必ず行ってください。

プロジェクト概要
- KabuSys は日本株の自動売買に関する以下の機能を備えたモジュール群を提供します。
  - 注文作成・送信・状態管理（Execution）
  - 監視・アラート（Monitoring）
  - ポートフォリオ構築・ポジションサイズ計算（Portfolio）
  - ファクター計算・リサーチ用ユーティリティ（Research）
  - ニュース NLP / 市場レジーム判定（AI）
  - ユーティリティ（プロセス優先度、設定読み込みなど）
  - Paper Trading 用の検証ツール（tools）
- 設定は環境変数およびプロジェクトルートの .env / .env.local から読み込みます（自動読み込みを無効にする環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD あり）。

主な機能一覧
- Execution（発注基盤）
  - Broker クライアント抽象化（実口座 / PaperTrading 切替）
  - OrderManager / OrderRepository による注文状態管理
  - Reconciler による起動時の自動同期（注文・ポジションの照合）
  - RiskManager によるリスク制御（レート制限・ドローダウン等）
- Monitoring（監視）
  - SystemMonitor: CPU/Mem/Disk や Execution プロセス生存、データ鮮度監視
  - TradeMonitor: 注文滞留・約定異常検出
  - RiskMonitor: ドローダウン・ポジション上限の監視とログ記録
  - KillSwitch: 条件に応じて flag ファイルを書き ExecutionEngine に停止シグナルを送る
  - AlertManager: LINE Messaging API への一方向プッシュ通知（クールダウン管理付き）
  - Streamlit ダッシュボード（簡易 UI）
- Portfolio（ポートフォリオ構築）
  - 候補選定（スコア順ソート）
  - 等金額・スコア加重配分
  - セクター制限、レジーム乗数の適用
  - ポジションサイズ計算（単元株丸め、aggregate cap でスケーリング）
- Research（調査）
  - Momentum / Volatility / Value 等ファクター計算（DuckDB を使用）
  - 将来リターン計算、IC（情報係数）計算、統計サマリ
- AI（LLM 連携）
  - ニュースのセンチメントを OpenAI API で評価し ai_scores テーブルへ格納
  - マクロニュース + ETF MA を用いた市場レジーム判定（gpt-4o-mini を利用する想定）
  - API 呼び出しはリトライ、バリデーション、部分失敗耐性を備える
- Tools
  - Paper Trading 検証レポート生成スクリプト（期間指定で集計・PASS/FAIL 判定）
  - その他ユーティリティ

必須・推奨となる環境変数（代表）
- 必須（実行する機能により異なる）
  - JQUANTS_REFRESH_TOKEN — J-Quants API（必要時）
  - KABU_API_PASSWORD — kabuステーション API
- AI 関連
  - OPENAI_API_KEY — OpenAI API を使う機能（news_nlp / regime_detector）
- データベース・パス（デフォルトを上書き可）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視ログ、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 時の DB、デフォルト: data/paper_trading.db）
- 動作環境切替
  - KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
    - paper_trading の場合、MockBroker を使用し paper_sqlite を使って本番 DB と分離
- その他
  - PID_FILE_PATH（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（デフォルト: data/kill.flag）
  - PAPER_FILL_MODE（paper_trading の fill 動作: instant | partial | never | reject）
  - LOG_LEVEL（INFO 等）
- 自動 .env ロードを無効化する場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

セットアップ手順（開発環境向け）
1. Python 環境を用意
   - Python 3.9+ を想定（実際の要件はプロジェクトで合わせてください）。
2. 依存パッケージをインストール
   - 代表的な依存: duckdb, psutil, openai, requests, streamlit
   - 例:
     - pip install duckdb psutil openai requests streamlit
   - 開発用に requirements.txt がある場合はそれを利用してください（本コードコピーでは明示されていません）。
3. プロジェクトルートに .env を作成（.env.example を参考に）
   - 例:
     - KABUSYS_ENV=development
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - JQUANTS_REFRESH_TOKEN=...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
4. データディレクトリを作成
   - mkdir -p data
5. 初期 DB（監視 DB）は実行時に自動作成されます（init_monitoring_db が冪等で作成／マイグレーションを実行）。

基本的な使い方 / 実行例
- 実行スクリプトはモジュールとして起動できます（パッケージとしてインストールされている前提）:
  - 監視ループを起動（SystemMonitor を定期実行）
    - 環境変数で間隔を変更: MONITOR_POLL_INTERVAL（秒、デフォルト 60）
    - 実行:
      - python -m kabusys.run_monitoring
    - または直接ファイルから:
      - python src/kabusys/run_monitoring.py
  - ExecutionEngine（発注エンジン）を起動
    - Paper Trading（分離 DB）で起動する場合:
      - export KABUSYS_ENV=paper_trading
      - python -m kabusys.run_execution
    - 実稼働（live）でも動作します（注意してキーや DB を設定）
  - Paper Trading 検証レポート生成
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - --db で SQLITE パスを指定可能（PAPER_TRADING_SQLITE_PATH より優先）
  - Streamlit ダッシュボード（監視用）
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 環境変数の主なカスタマイズ例:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - KABUSYS_ENV=paper_trading PAPER_FILL_MODE=partial python -m kabusys.run_execution

注意点 / 運用に関する補足
- Monitoring は KABUSYS_ENV にかかわらず sqlite_path（本番監視 DB）を使用する設計になっています（run_monitoring 内の仕様）。
- ExecutionEngine は KABUSYS_ENV=paper_trading の場合 paper_sqlite_path を使い、本番 DB と分離します。
- OpenAI 等外部 API を使う機能は API キーが必須で、失敗時はフェイルセーフ（スコア=0 など）で続行する実装が多いですが、鍵が無いとそもそも実行時に ValueError を投げる関数もあります。
- PID ファイル（デフォルト data/execution.pid）を Execution 側で利用し、SystemMonitor がプロセス生存を確認します。stale PID は削除されログ・リスクイベント記録が行われます。
- KillSwitch はリスク条件を満たすと data/kill.flag を書き込みます。ExecutionEngine 側はこのファイルの存在を検出して停止する想定です。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml の存在）を基準に行われます。自動ロードを行いたくない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（主要ファイルの抜粋）
- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数 / 設定管理
  - run_monitoring.py                — SystemMonitor ポーリングループ起動
  - run_execution.py                 — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py            — プロセス優先度・CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py               — SQLite テーブル作成 / 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (broker_factory, execution_engine, order_repository 等が存在)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py                     — ニュースの LLM センチメント
    - regime_detector.py              — 市場レジーム判定
    - __init__.py
  - tools/
    - paper_verification_report.py    — Paper Trading 検証レポート
    - __init__.py

付録（よく使う設定 / 環境変数の要約）
- KABUSYS_ENV: development | paper_trading | live
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading の約定挙動 ("instant" | "partial" | "never" | "reject")
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
- KABU_API_PASSWORD, JQUANTS_REFRESH_TOKEN: 外部 API 用

最後に
- この README は提供されたソースコードに基づく概要ドキュメントです。実運用前に各種設定値・依存パッケージ、API キーの取り扱い、権限・ネットワーク制約、法令順守等を確認してください。
- 追加のドキュメント（設計書、運用手順、データベーススキーマ説明など）がある場合は、その参照を併せて行ってください。