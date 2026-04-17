# KabuSys

KabuSys は日本株向けの自動売買システム（プロトタイプ）です。本リポジトリは以下の主要機能を提供します。

- 注文実行エンジン（ExecutionEngine）と発注管理
- 監視コンポーネント（System / Trade / Risk）とアラート送信（LINE）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ算出）
- 研究用モジュール（ファクター計算、IC/相関解析）
- ニュース NLP / レジーム検出（OpenAI を利用したセンチメント評価）
- DuckDB / SQLite によるデータ保管とレポート出力
- Streamlit ダッシュボード（監視用 UI）
- Paper Trading 用の分離された DB（本番 DB と完全分離）

以下はこのコードベースの README（日本語）です。

## 主な機能

- Execution 系
  - 注文作成、ブローカー同期、リコンシリエーション（再起動後の自動復旧）
  - RiskManager によるポジション上限や投資利用率の管理
- Monitoring 系
  - CPU / メモリ / ディスク / Execution プロセス存在確認
  - 注文の滞留検出、約定価格の異常検出、ドローダウン検出
  - Kill switch（条件を満たした場合に停止フラグを書き出す）と LINE 通知
  - monitoring.db（SQLite）への永続化（init_monitoring_db でスキーマ管理）
  - Streamlit ダッシュボードで監視状況を可視化
- Portfolio 系（純粋関数）
  - 候補選定（select_candidates）
  - 等分配 / スコア加重配分（calc_equal_weights, calc_score_weights）
  - リスク調整（セクター上限、レジーム乗数）
  - ポジションサイズ決定（lot 単位、aggregate cap を考慮）
- Research 系（DuckDB 利用）
  - Momentum / Volatility / Value ファクター計算
  - 将来リターン、IC（Spearman）計算、ファクター統計要約
- AI 系
  - news_nlp.score_news: raw_news を集約して OpenAI に投げ、ai_scores を更新
  - regime_detector.score_regime: MA200 とマクロニュースの LLM センチメントを合成して market_regime を更新
  - どちらも OpenAI API キー（OPENAI_API_KEY）が必要

## 必要条件（推奨）

- Python >= 3.10
- pip 等のパッケージ管理
- 主な依存パッケージ（実行環境に応じてインストールしてください）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード利用時）
  - その他（標準ライブラリで賄えるものが多い）

例（仮の requirements.txt が無い場合の参考）:
pip install duckdb psutil requests openai streamlit

## 環境変数と設定読み込み

- 設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から読み込まれます。
- 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
- 必須となる主要な環境変数（代表例）:
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
  - KABU_API_PASSWORD — kabu ステーション API 用（必須）
  - OPENAI_API_KEY — OpenAI を使う機能で必須（news_nlp / regime_detector）
- その他（主なものとデフォルト）:
  - KABUSYS_ENV: {development, paper_trading, live}（デフォルト: development）
  - LOG_LEVEL: DEBUG|INFO|...（デフォルト: INFO）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - PAPER_FILL_MODE: instant|partial|never|reject（paper_trading 用、デフォルト: instant）
  - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START など監視関連

注意: Settings モジュールが環境変数の妥当性チェックを行います。未設定の必須変数は起動時に ValueError を投げます。

## セットアップ手順（ローカル開発向け）

1. Python 仮想環境の作成（例）
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate

2. 必要パッケージのインストール
   pip install duckdb psutil requests openai streamlit

3. プロジェクトルートに `.env` を作成（参考: `.env.example` を用意する想定）
   - 必要な環境変数（上の「環境変数と設定読み込み」を参照）を設定
   - Paper Trading 用 DB を使う場合は KABUSYS_ENV=paper_trading を設定

4. ディレクトリ `data/` を作る（実行時に自動生成されることもありますがパーミッションに注意）
   mkdir -p data

5. （オプション）DuckDB / SQLite に初期テーブルを準備する
   - run_monitoring/run_execution の起動時に init_monitoring_db() が呼ばれ、必要テーブルは自動作成・マイグレーションされます。

## 実行方法（代表的なコマンド）

- 監視ループを起動（Monitoring）
  python -m kabusys.run_monitoring

  オプション/環境変数:
  - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）。1 未満や無効値は 60 にフォールバック。
  - 監視は Settings に従い、monitoring は環境にかかわらず本番 sqlite_path を使用します（意図的）。

  停止:
  - プロジェクトルートの data/stop_requested.flag を作成するとループが停止します。

- 実行エンジンを起動（Execution）
  python -m kabusys.run_execution

  ポイント:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading.db に書き込みます（本番 DB と完全分離）。
  - Engine は data/execution.pid を作成します。stop は data/stop_requested.flag で行います。
  - 起動直後に kill.flag が存在する場合は起動を中止します（kill は KillSwitch により生成）。

- Streamlit ダッシュボード（監視 UI）
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

  - 引数 `--db` で monitoring DB のパスを指定できます（デフォルト data/monitoring.db）。
  - Streamlit は DB を読み取り専用で開きます（URI mode=ro を使用）。

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  または DB 指定:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

  - PAPER_TRADING_SQLITE_PATH 環境変数で既定 DB を変更できます。存在しない DB はエラー表示します。

- AI 関連（プログラム的に呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続（conn）と対象日（date）を渡す。OPENAI_API_KEY が必要（引数で上書き可）。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 同様に OpenAI API キーが必要。

  これらは CLI エントリポイントを備えていないため、スクリプトやジョブ内で呼び出します。

## 重要なファイル / フラグ

- data/stop_requested.flag — run_monitoring / run_execution の外部停止用フラグ（存在を検知して安全に停止）
- data/kill.flag — KillSwitch が書き込み、ExecutionEngine を停止するためのフラグ
- data/execution.pid — ExecutionEngine が作成する PID ファイル（SystemMonitor がプロセス存否をチェック）
- monitoring DB（SQLite）: data/monitoring.db（デフォルト）
- paper trading DB（SQLite）: data/paper_trading.db（KABUSYS_ENV=paper_trading 時に使用）

## トラブルシューティング／注意事項

- process priority / CPU affinity
  - 起動時にプロセス優先度を "high" に設定しようとします（psutil を利用）。権限不足時は警告が出て処理は継続します。
- OpenAI 呼び出し
  - API の rate limit / ネットワークエラー / 5xx はリトライ／フォールバック挙動を含みますが、API キー未設定時は例外を投げます。
- DB マイグレーション
  - monitoring_db.init_monitoring_db は起動時に冪等的にテーブル作成・簡易マイグレーション（カラム追加）を行います。
- Paper Trading
  - paper_trading モードは本番 DB と分離する設計です（デフォルト: data/paper_trading.db）。本番データを汚さないよう注意してください。
- .env の読み込み順
  - OS 環境変数 > .env.local > .env の順で読み込まれます。OS 側の既存変数は保護されます。

## 主要なディレクトリ構成

（主要ファイル群のみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動読み込み）
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成ツール
  - monitoring/
    - monitoring_db.py       — monitoring DB のスキーマ / 永続化 API
    - system_monitor.py      — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py       — 注文滞留・約定異常監視
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 書き込みユーティリティ
    - alert_manager.py       — LINE Push API 経由の通知
    - monitoring_engine.py   — 各 Monitor を束ねるループ
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - execution_engine.py    — ExecutionEngine（メインロジック） ※（実装ファイルは抜粋されていませんが存在）
    - order_manager.py       — 注文作成 / 発注フロー
    - order_repository.py    — Orders DB アクセス（SQLite）
    - reconciler.py          — 再起動時の自動復旧/リコン
    - risk_manager.py        — 発注前のリスクチェック
    - broker_factory.py      — ブローカークライアント生成（Mock / Live 切替）
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 株数決定・単元調整・aggregate cap
    - risk_adjustment.py     — セクターキャップ / レジーム乗数
  - research/
    - factor_research.py     — Momentum/Volatility/Value 等のファクター計算
    - feature_exploration.py — 将来リターン・IC・統計サマリ等
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）で ai_scores 更新
    - regime_detector.py     — マーケットレジーム判定（MA200 + マクロ NLP）
  - utils/
    - process_priority.py    — プロセス優先度・CPU affinity 設定ユーティリティ
  - data/                    — 実行時生成（stop/kill フラグ、DB など）

（上記は主要なモジュールの概観です。詳細は各ファイルの docstring を参照してください。）

## 開発上のヒント

- 単体関数群（portfolio, research）は副作用がなくユニットテストが容易です。まずこれらからテストを書くとよいでしょう。
- DuckDB を使う関数はコネクションを引数で受け取るため、テスト用に in-memory DuckDB を作って検証できます。
- OpenAI など外部 API については呼び出し箇所をモックしてテストする設計になっています（内部で _call_openai_api を分離している等）。

---

この README はコード内の docstring・コメントを基に作成しています。実運用では環境変数の管理 (.env.example の整備)、requirements.txt の明記、CI 用のテストスクリプトの追加などを推奨します。必要であれば README に含める具体的な .env.example や systemd / supervisor 用の起動サンプルも作成しますのでお知らせください。