# KabuSys

KabuSys は日本株向けの自動売買／リサーチ／監視ツール群です。  
このリポジトリには、発注実行エンジン、監視コンポーネント、ポートフォリオ構築ロジック、リサーチ（ファクター計算）およびニュース NLP / レジーム判定などの補助モジュールが含まれます。

以下はコードベース（src/kabusys 内）の README です。

## プロジェクト概要
- 目的: 日本株自動売買フレームワークの基盤機能を提供する（発注管理、リコンシリエーション、リスク監視、監視ダッシュボード、ファクター計算、ニュースセンチメント評価など）。
- 設計指針:
  - DB（SQLite / DuckDB）での永続化とログ保管
  - 本番 / Paper Trading 等の環境分離（KABUSYS_ENV）
  - LLM（OpenAI）を活用したニュース NLP / マクロセンチメント（外部 API はフェイルセーフ）
  - テスト容易性を意識した純粋関数と副作用の限定

## 主な機能一覧
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番・ペーパートレードの切替、Broker クライアントの抽象化、Execution スレッド運用、停止フラグ対応
- Monitoring（run_monitoring.py / monitoring パッケージ）
  - SystemMonitor: CPU/メモリ/ディスク、プロセス生存、データ鮮度監視
  - TradeMonitor: 注文滞留（stale order）・約定価格異常検知
  - RiskMonitor: ドローダウン監視・ポジション上限監視、ダッシュボード更新
  - KillSwitch: 条件に応じた停止フラグ（data/kill.flag）出力
  - AlertManager: LINE Push によるアラート送信（クールダウン管理）
  - Streamlit ダッシュボード（監視データの可視化）
- ポートフォリオ構築（portfolio）
  - 候補選定、重み計算（等分・スコア加重）、セクター制限、ポジションサイズ計算（ロット丸め・スケールダウン）
- リサーチ（research）
  - ファクター計算（Momentum / Volatility / Value）、将来リターン、IC（情報係数）、統計サマリー
- AI 支援（ai）
  - news_nlp.score_news: raw_news を集約して OpenAI にセンチメント評価を依頼し ai_scores テーブルへ書き込み
  - regime_detector.score_regime: ETF の MA200 乖離とマクロ記事の LLM センチメントを合成して日次レジーム判定（bull/neutral/bear）
- ツール
  - paper_verification_report: Paper Trading DB の検証レポート生成（稼働率、注文成功率、レイテンシ等）

## セットアップ手順（開発環境）
1. Python 3.9+ を用意（duckdb などのバイナリ互換に注意）
2. 必要なパッケージをインストール
   - 例:
     pip install duckdb psutil requests openai streamlit
   - （必要に応じて仮想環境を推奨）
3. プロジェクトルートに移動し、.env を用意（任意）
   - 自動で `.env` と `.env.local` がロードされます（OS 環境変数が優先）
   - 自動ロードを無効にする場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
4. データディレクトリ（data）を作成
   - デフォルト DB 等は data 以下に作成される想定です（data/monitoring.db, data/kabusys.duckdb, data/paper_trading.db など）

### 重要な環境変数（主なもの）
- KABUSYS_ENV: 実行環境（development | paper_trading | live） — デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須な箇所で参照）
- KABU_API_PASSWORD: kabuステーション API パスワード
- OPENAI_API_KEY: OpenAI API を使用する AI 機能で必要
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite パス（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant | partial | never | reject）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH: PID / kill フラグのパス
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

例 .env（簡易）
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_password

## 使い方（主要コマンド）
プロジェクトパッケージが Python モジュールとして動作する想定です。プロジェクトルート（src が PYTHONPATH に含まれる状態）で実行してください。

- 監視ループ起動（Monitoring）
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き（秒）
  - 実行:
    python -m kabusys.run_monitoring
  - 動作:
    - プロセス優先度を high に設定（可能な場合）
    - monitoring DB（settings.sqlite_path）と DuckDB に接続
    - SystemMonitor.check_once をポーリング実行。stop フラグファイル (data/stop_requested.flag) により終了

- 実行エンジン起動（ExecutionEngine）
  - Paper Trading モード:
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    → MockBrokerClient を使用し data/paper_trading.db に書き込み（本番 DB とは分離）
  - Live / development:
    KABUSYS_ENV=live python -m kabusys.run_execution
  - 動作:
    - プロセス優先度を high に設定（可能な場合）
    - Broker クライアント生成、OrderManager / RiskManager / Reconciler 組立て、Engine をスレッドで実行
    - data/stop_requested.flag を監視し、存在すればエンジン停止

- Paper Trading 検証レポート生成
  - 例:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプションで --db で DB パス指定、指定なければ PAPER_TRADING_SQLITE_PATH または data/paper_trading.db を使用

- Streamlit 監視ダッシュボード
  - 実行方法（例）:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - read-only モードで SQLite を開き、ダッシュボードを表示

- AI / レジーム判定（プログラム的に使用）
  - ニューススコアリング:
    from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date, api_key="...")
  - レジームスコア:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key="...")

  - どちらも OPENAI_API_KEY（または引数 api_key）が必要。API 呼び出し失敗時はフェイルセーフな挙動（デフォルト値やスキップ）を行います。

## 停止・強制停止フロー
- Monitoring / Execution はプロジェクトルート下の data/stop_requested.flag を監視しています。存在すると安全にループを抜けます。
- KillSwitch は data/kill.flag を作成し、ExecutionEngine に停止シグナルを送ります（監視コンポーネントがリスク閾値を検出した場合など）。
- Execution 起動時に KILL_FLAG_CLEAR_ON_START が 1 に設定されていれば起動時に既存の kill.flag を削除できます（Settings.kill_flag_clear_on_start）。

## 注意・運用メモ
- Settings は .env / .env.local / OS 環境変数の順で読み込みます（自動ロードを無効化可）。プロジェクトルートは .git または pyproject.toml により検出されます。
- Paper Trading は本番 DB と分離される設計（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI API 呼び出しはリトライ（指数バックオフ）やレスポンス検証を行いますが、API キー管理とコストには注意してください。
- process_priority の設定は OS に依存します（Windows / Linux / macOS の差分を吸収するが、権限不足で設定できない場合は警告を出力してスキップします）。
- DuckDB / SQLite 関連でファイルロックやバージョン差に注意。Streamlit からは読み取り専用 URI モードで開くことを推奨しています。

## ディレクトリ構成（主要ファイル）
以下は src/kabusys 配下の主なファイルと簡単な説明です。

- src/kabusys/
  - __init__.py             — パッケージ定義（version 等）
  - config.py               — 環境変数 / 設定管理（Settings クラス）
  - run_monitoring.py       — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py        — ExecutionEngine 起動スクリプト
- src/kabusys/monitoring/
  - monitoring_db.py        — SQLite 用監視 DB 初期化 / ラッパー（MonitoringDB）
  - system_monitor.py       — CPU/MEM/DISK・プロセス・データ鮮度監視
  - trade_monitor.py        — 注文滞留 / 約定異常監視
  - risk_monitor.py         — ドローダウン / ポジション上限監視
  - kill_switch.py          — kill.flag 操作
  - alert_manager.py        — LINE 通知ラッパー
  - monitoring_engine.py    — 監視コンポーネント統合
  - streamlit_dashboard.py  — Streamlit ベースの監視ダッシュボード
- src/kabusys/execution/
  - order_manager.py        — 発注ワークフロー API
  - reconciler.py           — 起動時リコンシリエーション
  - (その他 Execution 関連モジュールを含む)
- src/kabusys/portfolio/
  - portfolio_builder.py    — 候補選定・重み計算
  - position_sizing.py      — 株数計算・スケールダウン・ロット丸め
  - risk_adjustment.py      — セクター上限・レジーム乗数
- src/kabusys/research/
  - factor_research.py      — Momentum / Volatility / Value などのファクター計算
  - feature_exploration.py  — 将来リターン・IC・統計サマリー
- src/kabusys/ai/
  - news_nlp.py             — raw_news を LLM に投げて ai_scores を生成
  - regime_detector.py      — MA200 + マクロセンチメント合成でレジーム判定
- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading DB の検証レポート生成

（実際のリポジトリはさらに細分化されたサブモジュールや実装ファイルを含みます）

## よくある質問 / トラブルシューティング
- DB ファイルが開けない / 見つからない:
  - デフォルトは data/*.db。適切なパスを指定するか、--db オプションや環境変数で上書きしてください。
- OpenAI 呼び出しでエラー:
  - OPENAI_API_KEY を確認。ネットワークやレート制限時はリトライが入りますが、致命的な場合はその機能のみスキップされます。
- LINE 通知が送れない:
  - LINE_CHANNEL_ACCESS_TOKEN と LINE_USER_ID を設定してください。未設定の場合はログに警告が出て、送信はスキップされます。

---

以上が現時点のコードベースに対する README です。必要であれば、導入手順の自動化（requirements.txt / poetry / Dockerfile）や具体的な .env.example のテンプレート作成、主要ワークフローの図解を追加できます。どの情報を優先して追加しますか？