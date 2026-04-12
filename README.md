# KabuSys

日本株向け自動売買システムのモジュール群（ライブラリ＋実行用スクリプト）です。  
この README はリポジトリ内の主要機能・セットアップ・使い方・ディレクトリ構成をまとめたものです。

注意: ここではコードベースから読み取れる仕様に基づいて記載しています。実運用前に .env の確認・テストを行ってください。

---

## プロジェクト概要

KabuSys は以下のような機能を持つ自動売買プラットフォームのコンポーネント群です。

- 取引実行エンジン（ExecutionEngine）の起動スクリプトと起動補助（再起動時のリコンシリエーション等）
- モニタリング（System / Trade / Risk）およびそれらを束ねる MonitoringEngine
- Paper Trading（検証用）と本番（live）環境を分離する設定
- ポートフォリオ構築（候補選定・配分・リスク調整・ポジションサイズ計算）の純粋関数群
- 研究用モジュール（ファクター計算・特徴量探索）
- AI 関連（ニュースの NLP スコアリング、レジーム判定） — OpenAI API を利用
- 監視用ダッシュボード（Streamlit）と各種ツール（例: Paper Trading 検証レポート生成）

主要ランタイム依存: Python 3.10+（少なくとも typing の union | を使用するため）、duckdb, psutil, openai, requests, streamlit など。

---

## 機能一覧

- 実行 / 監視
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により paper_trading を分離）
  - run_monitoring.py: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL 環境変数で間隔変更可）
- モニタリング
  - SystemMonitor: CPU/メモリ/ディスク、プロセス PID ファイル、データ鮮度を監視
  - TradeMonitor: 滞留注文、約定異常価格の検出
  - RiskMonitor: ドローダウン・ポジション上限監視とリスクログ記録、ハイウォーターマーク管理
  - KillSwitch: 条件を満たしたらフラグファイルを書いて ExecutionEngine の停止を促す
  - AlertManager: LINE Messaging API を利用した通知（クールダウンあり）
  - MonitoringDB: 監視データ（system_status / trade_logs / positions / risk_logs / dashboard）を SQLite に永続化
  - streamlit_dashboard.py: Streamlit で閲覧する監視ダッシュボード
- Execution（発注周り）
  - OrderManager / OrderRepository / Reconciler 等の起動時復旧や注文状態管理
- ポートフォリオ構築
  - 選定・重み付け（等金額、スコア加重）/ セクター制限 / レジーム乗数 / 株数決定（lot サイズ丸め・利用可能現金でのスケーリング）
- 研究用
  - factor_research: モメンタム・ボラティリティ・バリューなどを DuckDB 上で計算
  - feature_exploration: 将来リターン計算、IC（スピアマン）などの統計
- AI
  - news_nlp: raw_news を集約して OpenAI に投げ、銘柄ごとのセンチメントを ai_scores に書き込む
  - regime_detector: ETF とマクロニュースを組み合わせて market_regime を判定

---

## セットアップ手順（ローカル開発 / テスト向け）

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo>

2. Python 環境を準備
   - 推奨: Python 3.10+
   - 仮想環境作成例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 主要な依存パッケージ（例）:
     - pip install duckdb psutil openai requests streamlit
   - 実プロジェクトでは requirements.txt / pyproject.toml を参照して下さい（該当ファイルがない場合は上記を基準に追加してください）。

4. 環境変数 (.env)
   - プロジェクトはルートの .env / .env.local を自動ロードします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須環境変数（実行時に必要になるもの）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主な環境変数一覧（デフォルトや使い方を示します）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE: paper_trading 時の fill 動作 ("instant" | "partial" | "never" | "reject")（デフォルト: instant）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager 用
     - PID_FILE_PATH / KILL_FLAG_PATH: PID / kill flag のファイルパス（デフォルト data/…）
     - LOG_LEVEL: ログレベル（DEBUG/INFO/...）
     - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒, デフォルト 60）
   - .env の書式は bash 風（export を許容）。コメントやクォートに柔軟に対応します（config モジュール参照）。

5. データディレクトリ作成
   - data ディレクトリや DB ファイルの親ディレクトリを作成しておく:
     - mkdir -p data

---

## 使い方（主要スクリプト）

- 監視ループを起動（監視用 SQLite は本番 sqlite_path を使う点に注意）
  - python -m kabusys.run_monitoring
  - 環境変数で間隔を変える: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 実行時にプロセス優先度を "high" に設定します（可能な場合）。

- 実行エンジンを起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にするとブローカークライアントはモックを使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録されます。
  - 起動時にプロセス優先度を "high" に設定します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- Streamlit ダッシュボード（監視）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開きます。MonitoringEngine が先に起動していることを推奨。

- AI 機能
  - news_nlp.score_news / regime_detector.score_regime は OpenAI API キーが必要です（引数または環境変数 OPENAI_API_KEY）。
  - 実行は DuckDB 接続を渡して呼び出します。API 呼び出しはリトライやフェイルセーフを含む実装になっています。

---

## 実行上の注意点 / トラブルシュート

- Paper Trading と本番 DB は分離されています。KABUSYS_ENV=paper_trading を必ず確認してください。
- run_monitoring は環境にかかわらず「本番の」sqlite_path を使用します（設計上の仕様）。
- MONITOR_POLL_INTERVAL は 1 以上の整数で指定してください。不正値時はデフォルト 60 秒にフォールバックします。
- .env は自動ロードされますが、OS 環境変数が優先されます。.env.local は .env を上書きします。
- プロセス優先度設定（set_process_priority）は psutil を使い、権限によって失敗することがあります。失敗時はログに WARNING が出ますが処理は続行します。
- OpenAI API を用いるコンポーネントはネットワーク/レート制限等を考慮したリトライロジックを持ちますが、キー未設定時は例外や早期終了となることがあります（明示的にエラーになります）。
- DuckDB/SQLite に関する互換性や executemany の空配列制限など、コード内に互換性対策が含まれています。DB スキーマは init_monitoring_db() で初期化（冪等）されます。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下を中心に抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / .env 自動ロード・Settings
    - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py  — Paper Trading 検証レポート生成
    - monitoring/
      - __init__.py
      - monitoring_db.py       — SQLite スキーマ初期化 + MonitoringDB（読み書き層）
      - system_monitor.py      — システム状態・データ鮮度チェック
      - trade_monitor.py       — 注文滞留・約定異常チェック
      - risk_monitor.py        — ドローダウン / ポジション上限監視
      - kill_switch.py         — kill.flag の書き込みロジック
      - alert_manager.py       — LINE 通知クライアント
      - monitoring_engine.py   — 各 Monitor を束ねてポーリング
      - streamlit_dashboard.py — Streamlit dashboard
    - execution/
      - order_manager.py
      - reconciler.py
      - ... (OrderRepository, broker_factory 等は別ファイル)
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
      - __init__.py
      - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
      - regime_detector.py     — 市場レジーム判定（OpenAI + ETF）
    - data/
      - pipeline.py (参照されるユーティリティ: get_last_price_date 等)
    - utils/
      - __init__.py
      - process_priority.py    — プロセス優先度 / CPU affinity

---

## 開発・拡張の指針（簡単に）

- DB スキーマ変更は monitoring_db.init_monitoring_db 内で冪等に実装してください。既存カラムの追加は PRAGMA 等で検出してマイグレーションするパターンが使われています。
- OpenAI 周りの呼び出しはテスト容易性のため _call_openai_api を内部で定義しており、ユニットテストでは mock しやすく実装しています（例: unittest.mock.patch）。
- DuckDB を利用する研究モジュールは SQL を直接投げています。パフォーマンスや互換性を考慮して一括クエリで計算する設計になっています。
- Paper Trading の再現性確保のため、Execution 側は paper_trading 用 DB / mock broker を使うよう切り分けられています。

---

必要であれば、README に以下を追加します（希望があれば教えてください）:

- インストール用 requirements.txt / pyproject.toml の例
- 実行例（systemd ユニット / Dockerfile / docker-compose）のテンプレート
- 詳細な環境変数の一覧（デフォルト値・必須/任意の明示）
- 各モジュールの API 仕様（関数引数・戻り値の詳細）

以上。