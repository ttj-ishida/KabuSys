# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買システム（プロトタイプ）です。バックエンドの発注エンジン、監視・アラート、ポートフォリオ構築ユーティリティ、リサーチ用ファクター計算、AI を用いたニュースセンチメント評価などを含みます。

---

## プロジェクト概要

- 発注系（ExecutionEngine）: ブローカークライアント経由で注文を作成・管理し、再起動時にリコンシリエーションを行う。
- 監視系（MonitoringEngine）: システム状態・注文滞留・リスクなどを定期ポーリングしてログ／アラート／Kill Switch を管理する。
- ポートフォリオ構築: 候補選定、重み付け、ポジションサイズ計算、セクター制約・レジーム調整等の純粋関数群。
- リサーチ: DuckDB を用いたファクター計算、将来リターン計算、IC 評価などのユーティリティ。
- AI モジュール: OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価と市場レジーム判定。
- ツール群: Paper Trading の検証レポート生成、Streamlit ダッシュボードなど。

---

## 主な機能一覧

- 実行（Execution）
  - 本番 / ペーパー取引モード切替（KABUSYS_ENV）
  - ブローカー抽象化（MockBroker / 実ブローカーに対応するファクトリ）
  - 注文状態管理、重複防止、キャンセル・同期機能、リコンシリエーション
- 監視（Monitoring）
  - CPU / メモリ / ディスク利用の定期ログ
  - Execution プロセス死活監視（PIDファイル）
  - 注文の滞留・約定異常検出
  - ドローダウン・ポジション上限などのリスク監視
  - LINE による通知（AlertManager）
  - Kill Switch（条件到達時に data/kill.flag を書き込み Execution を停止）
  - Streamlit ダッシュボード（可視化）
- ポートフォリオ構築
  - 候補選定（スコア降順）、等配分 / スコア加重配分
  - セクターキャップ適用
  - ポジションサイズ計算（リスクベース、単元丸め、利用可能資金へのスケール）
- リサーチ
  - Momentum / Volatility / Value ファクター計算（DuckDB）
  - 将来リターン計算、IC（Spearman）などの統計解析ユーティリティ
- AI
  - ニュースを LLM で評価して ai_scores テーブルへ書込
  - マクロニュース＋ETF MA200 を用いた市場レジーム判定
- 開発支援ツール
  - Paper Trading 検証レポート（集計・Pass/Fail 判定）
  - Streamlit ダッシュボード

---

## 前提（Prerequisites）

- Python 3.10+
- SQLite（標準ライブラリに同梱）
- 必要な Python パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
- （任意）LINE 通知用に LINE チャネルアクセストークン
- OpenAI 呼び出しを行う場合は OPENAI_API_KEY

インストール例:
```bash
python -m pip install duckdb psutil requests openai streamlit
```

※ 実運用時は requirements.txt / 仮想環境を利用してください。

---

## 環境変数・設定

このプロジェクトは .env / .env.local / OS 環境変数から設定を読み込みます（自動読み込み。テストなどで無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

主な環境変数（デフォルトを併記）:

- KABUSYS_ENV: environment（development / paper_trading / live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: （必須）J-Quants API 用トークン
- KABU_API_PASSWORD: （必須）kabuステーション API パスワード
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 機能、regime/news）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（未設定だと送信スキップ）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper trading の約定モード（instant|partial|never|reject。デフォルト: instant）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START など
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒。default 60）

サンプル .env（最低限の例）:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
```

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成・有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   ```bash
   python -m pip install --upgrade pip
   python -m pip install duckdb psutil requests openai streamlit
   ```

4. 環境変数を設定（.env または OS 環境変数）
   - .env.example があれば参照して `.env` を作成してください。
   - 自動読み込みはプロジェクトルートに `.env` / `.env.local` があれば行われます。

5. データディレクトリの作成（必要なら）
   ```bash
   mkdir -p data
   ```

---

## 使い方（代表的な起動方法）

### 監視ループを起動（Monitoring）
- デフォルトの動作: 本番 sqlite (settings.sqlite_path) を使用して監視を行います。ポーリング間隔は MONITOR_POLL_INTERVAL（秒）。
```bash
python -m kabusys.run_monitoring
# または間隔変更:
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```
監視は data/stop_requested.flag を作成すると停止します（stop フラグファイル検知により終了）。

### 実行エンジンを起動（ExecutionEngine）
- 本番／ペーパーは KABUSYS_ENV によって切替。paper_trading の場合、MockBrokerClient として paper DB（PAPER_TRADING_SQLITE_PATH）を使用します。
```bash
python -m kabusys.run_execution
```
- 実行開始時に data/execution.pid が作成されます。停止は data/stop_requested.flag を作成するか、Kill Switch により data/kill.flag が書き込まれます。

### Paper Trading の検証レポート生成
- ペーパートレード DB を使って集計・判定レポートを標準出力に出します。
```bash
python -m kabusys.tools.paper_verification_report
# 期間を指定:
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB を明示:
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```

### Streamlit ダッシュボード（監視）
- 監視 DB を読み取り専用で開いてダッシュボードを表示します（MonitoringEngine を先に起動してデータを蓄積してください）。
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

### AI 機能（ニューススコア / レジーム判定）
- OpenAI API キー（OPENAI_API_KEY）が必要です。
- プログラムからは kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼び出して使用します（DuckDB 接続を渡す）。

---

## 注意点・設計上のポイント

- Settings モジュールは .env の自動ロード機能を持ち、OS 環境変数を優先します。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
- Monitoring は環境にかかわらず本番 sqlite_path を使用する設計になっている箇所があり（運用上の意図に注意）、paper_trading 時は run_execution が paper 用 DB を使用します。
- Paper Trading 時の振る舞いは PAPER_FILL_MODE で制御できます（instant / partial / never / reject）。
- OpenAI を使う関数はリトライや失敗フォールバック（スコア=0 など）を実装しており、API 失敗時も例外で落ちないよう配慮されています。
- PID / flag ファイル（data/*.pid / data/kill.flag / data/stop_requested.flag）でプロセス制御・停止を行います。これらのパスは Settings で設定可能です。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py — パッケージメタ情報
  - config.py — 環境変数 / 設定ロジック（.env 自動ロード含む）
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - execution/
    - order_manager.py — 注文管理ロジック（OrderManager）
    - reconciler.py — 再起動時の同期 / リコンシリエーション
    - order_repository.py, order_record.py, broker_factory.py など（発注関連）
  - monitoring/
    - monitoring_db.py — SQLite のテーブル初期化と永続化層（MonitoringDB）
    - system_monitor.py — システム状態・データ鮮度チェック
    - trade_monitor.py — 注文滞留・約定異常チェック
    - risk_monitor.py — ドローダウン / ポジション上限チェック
    - kill_switch.py — kill.flag を書くロジック
    - alert_manager.py — LINE へのプッシュ通知
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py — Streamlit ベースの可視化
  - portfolio/
    - portfolio_builder.py — 候補選定、重み計算
    - position_sizing.py — 発注株数計算、aggregate cap ロジック
    - risk_adjustment.py — セクターキャップ / レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計要約
  - ai/
    - news_nlp.py — raw_news に対する LLM ベースのセンチメント評価
    - regime_detector.py — MA200 + マクロニュースで市場レジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - data/ (実行時に使用する DB / PID / flag 等を配置)
    - monitoring.db (デフォルト)
    - paper_trading.db (ペーパートレード用)
    - kabusys.duckdb (DuckDB)
    - execution.pid, kill.flag, stop_requested.flag, ...

---

## 開発・テストに関する補足

- DuckDB 接続を受け取る関数群（research／ai）は副作用を最小化しているため、テスト用の小さな DuckDB ファイルを用意するとユニットテストが容易です。
- Settings の自動ロードはプロジェクトルートの検出（.git または pyproject.toml）に基づくため、配布後も CWD に依存しないよう設計されています。
- OpenAI 呼び出し部分は内部で retry を実装しているほか、ユニットテスト時に _call_openai_api をモックすることを想定しています。

---

必要であれば README にサンプル .env.example ファイル、CI 設定や Dockerfile、より詳細な起動手順（systemd ユニット、コンテナ化）なども追記できます。どの部分を優先して補足しましょうか？