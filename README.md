# KabuSys

日本株向け自動売買（バックテスト / Paper Trading / 実運用）を想定したモジュール群のリポジトリです。  
この README ではプロジェクト概要、主要機能、ローカルセットアップ、起動方法、ディレクトリ構成を日本語でまとめています。

---

## プロジェクト概要

KabuSys は次の要素で構成された自動売買プラットフォームの骨格です。

- 注文作成・ブローカー連携を担う ExecutionEngine
- 監視（System / Trade / Risk）・アラート・キルスイッチ
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- リサーチ用ファクター計算・特徴量解析（DuckDB 利用）
- AI を使ったニュースセンチメント評価 / 市場レジーム判定（OpenAI API 使用）
- Paper Trading 用の分離された DB と検証レポート生成ツール
- Streamlit ベースの監視ダッシュボード（読み取り専用）

設計方針としては「外部副作用を最小にする」「ルックアヘッドバイアス回避」「DB の冪等初期化と簡易マイグレーション」を重視しています。

---

## 主な機能一覧

- Execution
  - ブローカー抽象化（本番／モック切替）
  - OrderManager（状態遷移、重複防止）
  - Reconciler（起動時の注文・ポジション照合）
  - RiskManager（発注制限など、Engine で使用）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク・プロセス PID・データ鮮度監視
  - TradeMonitor: 滞留注文、約定価格異常をチェック
  - RiskMonitor: ドローダウン監視、ポジション上限監視
  - KillSwitch: しきい値で kill.flag を書き込み Execution を停止
  - AlertManager: LINE Push でアラート送信（トークン未設定ならログのみ）
  - MonitoringEngine: 上記をまとめて定期実行
  - streamlit ダッシュボード（読み取り専用）
- Portfolio
  - 候補選定 / 等金額・スコア重み付け
  - セクター制限、レジーム乗数
  - ポジションサイズ計算（単元株丸め、利用可能現金でのスケーリング）
- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - 将来リターン、IC（Spearman）や統計サマリ
- AI
  - news_nlp: OpenAI でニュースを銘柄ごとにセンチメント化して ai_scores に書込
  - regime_detector: ETF MA200 とマクロニュースを合成して日次レジーム判定
- Tools
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）
  - 各種ユーティリティ（プロセス優先度設定等）

---

## セットアップ手順

前提: Python 3.9+（typing の一部機能 / psutil 等を使用）。プロジェクトルートに `src/` がある構成を想定しています。

1. リポジトリをクローンし、ワークディレクトリへ移動
   - 例: git clone ... && cd your-repo

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 必要な主要パッケージ:
     - duckdb
     - psutil
     - openai
     - requests
     - streamlit
   - 例:
     - pip install duckdb psutil openai requests streamlit

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを利用してください）

4. 環境変数 / .env
   - プロジェクトは起動時に自動で `.env` / `.env.local` を読み込みます（OS 環境変数 > .env.local > .env）。
   - 自動読み込みを無効にするには:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 必須の環境変数（実運用や一部機能で必須）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - Optional / デフォルト値があるもの:
     - OPENAI_API_KEY（AI モジュールを使う場合は必須）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（アラート送信）
     - PAPER_FILL_MODE（paper_trading の挙動）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 時の DB）
     - SQLITE_PATH（監視用 DB、デフォルト: data/monitoring.db）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - .env の例:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - KABUSYS_ENV=paper_trading
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

5. data ディレクトリ
   - 起動時に使用する PID / flag / DB を置く `data/` を作成しておくと便利（多くの起動スクリプトが `data/` を参照します）。
   - 例:
     - mkdir -p data

---

## 使い方（主要コマンド）

※ すべてプロジェクトルート（src を含む）で実行することを想定しています。モジュールは `python -m kabusys.<module>` で直接実行できます。

- ExecutionEngine（本番／Paper Trading の実行）
  - KABUSYS_ENV によって動作が切り替わります:
    - production/live: 実ブローカークライアントを使用（設定に応じて）
    - paper_trading: MockBrokerClient を使い、DB を data/paper_trading.db に記録（本番 DB と分離）
  - 起動:
    - python -m kabusys.run_execution
  - 停止:
    - 実行中に `data/stop_requested.flag` を作成すると、実行ループは検出して停止します（または手動でプロセスを終了）。
  - PID / stop files:
    - data/execution.pid （Engine の PID）
    - data/stop_requested.flag （手動停止要求）
    - data/kill.flag （KillSwitch が書き込む停止理由）

- Monitoring（SystemMonitor の単独起動 / ポーリング）
  - 起動:
    - python -m kabusys.run_monitoring
  - ポーリング間隔の変更:
    - 環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）
      - export MONITOR_POLL_INTERVAL=30
  - 監視は MonitoringDB（SQLite）へ永続化します（デフォルト: data/monitoring.db）。起動時に必要なテーブルが自動で初期化されます。

- Streamlit ダッシュボード（監視情報の可視化）
  - 起動（読み取り専用で DB を開く）:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - UI 上で「Refresh」ボタンで再読み込みできます。

- Paper Trading 検証レポート
  - data/paper_trading.db（または --db で指定）を読み、各種指標（稼働率、注文成功率、P95 レイテンシ等）を出力します。
  - 実行:
    - python -m kabusys.tools.paper_verification_report
    - 期間指定:
      - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - DB 指定:
      - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI モジュール（ニューススコア / レジーム判定）
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY または引数で指定）。
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)

---

## 主要ファイル / 実行フローのポイント

- 設定管理: src/kabusys/config.py
  - .env/.env.local の自動読み込み（無効化可能）
  - Settings クラスで各種パス・フラグ・しきい値を提供

- 監視 DB 初期化: monitoring.monitoring_db.init_monitoring_db
  - 必要テーブルがなければ作成、軽微なマイグレーション（列追加）にも対応

- プロセス優先度: utils.process_priority.set_process_priority("high")
  - 実行スクリプトは起動時に優先度を上げようと試みます（アクセス権がなければ警告）

- 停止フラグ
  - data/stop_requested.flag を起点に run_execution/run_monitoring がループを抜けます
  - KillSwitch は条件に応じて data/kill.flag を作成し ExecutionEngine 側で検出して安全停止を促します

---

## ディレクトリ構成（抜粋）

プロジェクト内の主要モジュール構成を示します（src/kabusys 以下）。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - run_execution.py
    - run_monitoring.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - utils/
      - __init__.py
      - process_priority.py
    - monitoring/
      - __init__.py
      - monitoring_db.py
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
      - (broker_factory, execution_engine, order_repository 等の実装ファイル)
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - data/  (想定される runtime データディレクトリ)
      - monitoring.db (sqlite)
      - paper_trading.db (sqlite, paper_trading 用)
      - kabusys.duckdb (DuckDB)
      - execution.pid
      - stop_requested.flag
      - kill.flag

（上は抜粋です。実際のリポジトリではさらに小さなモジュールファイルがあります）

---

## 環境変数一覧 / 重要な設定（代表）

- KABUSYS_ENV (development | paper_trading | live) — 動作モード
- JQUANTS_REFRESH_TOKEN — （必須）J-Quants API 用トークン
- KABU_API_PASSWORD — （必須）kabu API パスワード
- OPENAI_API_KEY — OpenAI を使用する場合に必須
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START …（Settings 経由で参照）

詳細は src/kabusys/config.py を参照してください。

---

## 運用上の注意 / トラブルシューティング

- DB ファイルが見つからない / 開けない場合は、監視機能や Streamlit 起動が失敗します。パス／ファイル権限を確認してください。
- OpenAI API を使う機能は API キーが未設定だと ValueError を投げます。テスト時に外す場合は呼び出し側でハンドリングしてください。
- run_execution/run_monitoring は起動時にプロセス優先度の設定を試みます。権限が不足すると警告が出ますが処理自体は継続します。
- Paper Trading モードでは実ブローカーに一切アクセスせず、paper_trading 用 DB に注文ログを残します（本番 DB と完全分離）。
- kill.flag / stop_requested.flag の管理は運用ルールを決めた上で行ってください。起動時に kill.flag を消去する設定もあります（Settings.kill_flag_clear_on_start）。

---

## 開発・拡張のヒント

- Research / AI モジュールは外部副作用（口座発注等）に触れない設計です。DuckDB の prices_daily / raw_financials を用いてロジック検証ができます。
- テスト時は OpenAI 呼び出しや外部 HTTP をモックすることを想定した設計（内部の API 呼び出し点に容易に差し替え可能）。
- monitoring_db.py は簡易マイグレーションを含んでいます。スキーマ変更時は init_monitoring_db を使うことで互換性を保てます。

---

必要であれば、以下を含めた追加情報も作成できます。
- requirements.txt / pyproject.toml の推奨依存リスト
- デプロイ手順（systemd ユニットファイル例、Dockerfile 等）
- よくある運用手順（データバックアップ、DB マイグレーション手順）
- API ドキュメント（関数一覧・引数説明の自動生成）

どれを追加しましょうか？