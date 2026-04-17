# KabuSys

日本株自動売買システム（KabuSys）のコードベース README。  
本ドキュメントはリポジトリ内の主要モジュール・起動方法・設定方法・ディレクトリ構成をまとめたものです。

注意: 本 README はソースコードからの抜粋に基づいて作成しています。実運用前に .env の設定や依存パッケージの確認を必ず行ってください。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買・研究プラットフォームです。主な機能としては次の通りです。

- 注文発行・状態管理（ExecutionEngine / OrderManager）
- リコンシリエーション（Reconciler）による再起動後の自動復旧
- 監視（MonitoringEngine） — システム状態、注文滞留、リスク（ドローダウン／ポジション上限）監視
- リスク管理（RiskManager）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ算出）
- 研究用モジュール（ファクター計算、特徴量探索、IC 計算）
- AI 補助（ニュースセンチメント評価 / レジーム判定） — OpenAI を利用
- 運用支援ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）
- 永続化: SQLite（監視 / 注文ログ等）、DuckDB（時系列・研究用データ）

設計方針の一部:
- 本番 DB と Paper Trading を分離（paper_trading 環境では別 SQLite を使用）
- ルックアヘッドバイアスに注意した日付処理（AI/レジーム判定等）
- フェイルセーフ: API エラー時は処理をスキップまたはデフォルト値で継続

---

## 機能一覧（主なモジュール）

- kabusys.config
  - 環境変数 / .env の読み込みと Settings クラス
  - 自動 .env ロードはプロジェクトルートを基準に行われる（無効化可）

- kabusys.execution
  - ExecutionEngine（起動／セッション管理）
  - OrderManager、OrderRepository、Reconciler（注文管理・整合性維持）
  - Broker クライアントファクトリ（実ブローカー／モックの切替）

- kabusys.monitoring
  - MonitoringEngine（ポーリングループ）
  - SystemMonitor（CPU/メモリ/ディスク、データ鮮度、PID チェック）
  - TradeMonitor（滞留注文、約定異常価格検出）
  - RiskMonitor（ドローダウン、ポジション上限検知）
  - KillSwitch（条件に応じて停止フラグを書き込み）
  - AlertManager（LINE による通知）
  - monitoring_db（SQLite スキーマと DB アクセスラッパー）
  - streamlit_dashboard（ダッシュボード表示）

- kabusys.portfolio
  - 銘柄選定、等重・スコア重み、リスク調整、ポジションサイズ算出

- kabusys.research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン・IC 計算・統計サマリ

- kabusys.ai
  - news_nlp: ニュースの LLM によるセンチメント算出（ai_scores テーブルへ保存）
  - regime_detector: MA200 とマクロセンチメントを使った市場レジーム判定（market_regime テーブルに書込）

- kabusys.tools
  - paper_verification_report: Paper Trading の検証レポート生成スクリプト

- kabusys.utils
  - process_priority: プロセス優先度（Windows / POSIX を吸収）
  - その他ユーティリティ群

---

## セットアップ手順（開発 / 実行前）

前提:
- Python 3.10 以上（型記法に X | Y を使用）
- OS により追加パッケージが必要な場合あり（例: psutil のビルド依存）

1. リポジトリをクローン、作業ディレクトリへ移動
   - git clone ... && cd <repo>

2. 仮想環境作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージのインストール（例）
   - pip install -r requirements.txt
   - requirements.txt がない場合は少なくとも以下をインストールしてください:
     - duckdb, psutil, openai, requests, streamlit

4. .env の準備
   - プロジェクトルートに `.env` または `.env.local` を置くことで設定を上書き可能
   - 自動ロードはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）

5. データディレクトリを作成（必要に応じて）
   - mkdir -p data

6. DB 初期化は各起動スクリプトが冪等に実行します（monitoring 用テーブル作成等は init_monitoring_db() が行う）

---

## 環境変数（主なもの）

- KABUSYS_ENV: 起動環境
  - development（デフォルト） / paper_trading / live
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（ai 機能利用時に必須）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant|partial|never|reject、デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite パス（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
- PID_FILE_PATH: 実行エンジンの PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch が書き込むフラグファイル（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト: 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 .env ロードを停止

例 (.env):
```dotenv
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-xxxx
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
```

---

## 使い方（起動 / ツール）

- 監視プロセス起動（Monitoring）
  - デフォルトは本番 SQLite（Settings.sqlite_path）を使用します（監視は環境にかかわらず本番 DB を参照する点に注意）。
  - 環境変数でポーリング間隔を変更:
    - MONITOR_POLL_INTERVAL=120 python -m kabusys.run_monitoring
  - 停止: プロジェクトルート直下 `data/stop_requested.flag` を作成するとループが検知して終了します。

- 実行エンジン起動（Execution）
  - 実注文機能を伴うエンジンを起動します。
  - Paper Trading に切り替えるには:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - paper_trading の場合、モックブローカーを使用し `data/paper_trading.db` に記録します（本番 DB とは完全に分離）。
  - 停止:
    - `data/stop_requested.flag` を作成すると起動中のエンジンが停止を受け付けます。
  - 実行中は PID を `data/execution.pid` に書きます。

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を read-only モードで開き、Positions / Orders / System / Overview を表示します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db（--db オプションまたは PAPER_TRADING_SQLITE_PATH で変更可）

- AI 機能
  - news_nlp.score_news / regime_detector.score_regime をプログラムから呼び出して利用
  - OpenAI API キー（OPENAI_API_KEY）が必須。API 呼び出しはリトライやエラーハンドリングを行いますが、キー未設定時は ValueError が発生します。

---

## 停止 / キル機構

- 停止フラグ:
  - `data/stop_requested.flag` を監視プロセス（run_monitoring / run_execution）がチェック。存在すると安全に終了する。
- KillSwitch:
  - リスク監視で条件を満たした場合、`data/kill.flag`（デフォルト）を作成して ExecutionEngine 停止を指示します。
  - KillSwitch は冪等に書き込みを行い、理由（文字列）をファイルに記録します。
- PID ファイル:
  - ExecutionEngine は起動時に PID を `data/execution.pid` に書きます。SystemMonitor はこの PID を参照してプロセス稼働チェックを行います。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py              — 環境変数 / Settings
  - run_monitoring.py      — 監視ループ起動スクリプト
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - streamlit_dashboard.py
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - (その他ブローカー関連)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - utils/
    - process_priority.py
  - data/                  — 実行時に使われる SQLite / DuckDB / flag / pid など（含まれない場合は作成する）
- requirements.txt (想定)

---

## 実運用上の注意点 / トラブルシュート

- Python バージョン: 3.10 以上推奨（`X | Y` 型注釈を使用）
- DB ファイル（SQLite / DuckDB）は実行ユーザーが読み書き可能であることを確認してください。
- Monitoring はコード内の設計により「監視 DB」を本番用の sqlite_path に常に接続します。テスト環境では `KABUSYS_ENV=paper_trading` にしても監視 DB が本番パスを参照しうる点に注意してください（run_execution では paper_trading の場合に別 DB を使う設計です）。
- OpenAI を用いる機能は API キーが必須。キーがない場合は明確な例外が出ます。
- Process priority / CPU affinity の設定は psutil を利用。権限不足により設定できない場合は警告が出てスキップされます。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml が存在する場所）を基準に行います。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 開発に関する補足

- 各モジュールは可能な限り純粋関数／副作用の分離を意識した実装になっています（例: portfolio.* は DB を参照しない純関数群）。
- AI・外部 API 呼び出しはリトライ／バックオフ・レスポンス検証を実装し、失敗時に例外を投げずにフェイルセーフ化する箇所が多くあります。
- DB マイグレーション（列追加等）は monitoring_db.init_monitoring_db() の中で簡易的に行っています。

---

必要であれば、README に次の内容を追加できます:
- requirements.txt の具体的な推奨パッケージ一覧
- .env.example の雛形
- 実際のシステム図（プロセス相互関係）
- 運用時のチェックリスト（起動順序、バックアップ、監視ルール詳細）