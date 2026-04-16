# KabuSys

日本株向けの自動売買システム（ライブラリ + 実行コンポーネント）です。本リポジトリは戦略の研究・ファクター計算・ポートフォリオ構築、注文実行、監視、Paper Trading 検証、及びニュース NLP / レジーム判定などの機能を備えます。

---

## プロジェクト概要

KabuSys は以下の領域をカバーするモジュール群で構成されています。

- データ処理・リサーチ: duckdb を用いたファクター計算、将来リターン計算、特徴量探索
- ポートフォリオ構築: 候補選定、重み計算、リスク調整、ポジションサイズ計算
- 実行エンジン: Broker クライアント経由での発注 / 注文管理 / リコンシリエーション
- 監視: システム稼働、注文滞留、リスク (ドローダウン・ポジション上限) を監視し、LINE 経由で通知
- AI 関連: ニュース記事を LLM（OpenAI）でスコアリング、マクロニュースとETF MA による市場レジーム判定
- ツール: Paper Trading 検証レポート生成、Streamlit ダッシュボード

設計上、研究（research）モジュールは本番ブローカー等にアクセスしないよう分離されています。Paper Trading（KABUSYS_ENV=paper_trading）時は発注を MockBroker に置換し、本番 DB と分離された SQLite を利用します。

---

## 主な機能一覧

- モニタリング
  - CPU / メモリ / ディスクの測定と履歴保存
  - 実行プロセス存在チェック（PID ファイル）
  - データ鮮度チェック（prices_daily の最終日）
  - 注文の滞留検出、約定価格異常検出
  - リスクログ、ダッシュボード更新、kill.flag 書き込み（自動停止トリガー）
  - LINE によるアラート通知（cooldown 管理）

- 実行エンジン
  - Broker クライアント抽象化（本番 / モックの切替）
  - OrderManager / OrderRepository による状態管理
  - Reconcilier による再起動後の自動復旧（Order / Position 照合）
  - リスク管理（発注制限、回路遮断等）

- ポートフォリオ構築
  - 候補選定 (score / rank)
  - 等分配・スコア加重の重み計算
  - セクター制限の適用
  - ポジションサイズ計算（リスクベース、lot 単位丸め、aggregate cap）

- 研究／ファクター計算
  - Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - 将来リターン計算、IC（Spearman）評価、統計サマリー

- AI
  - ニュースセンチメントの LLM スコアリング（gpt-4o-mini 想定、JSON mode）
  - マクロニュース + ETF MA200 を統合したレジーム判定
  - API リトライ・バリデーション・部分書き込みによる耐障害性

- ツール
  - Paper Trading 検証レポート生成スクリプト
  - Streamlit による監視ダッシュボード

---

## セットアップ手順

1. Python 環境準備（推奨: venv）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   ```

2. 必要ライブラリをインストール
   （リポジトリに requirements.txt がない場合は以下パッケージが必要になる想定です）
   ```bash
   pip install duckdb psutil requests openai streamlit
   ```
   - duckdb: 研究・分析用
   - psutil: プロセス/メトリクス
   - requests: LINE API 送信
   - openai: LLM 呼び出し
   - streamlit: ダッシュボード

3. プロジェクトルートに .env を作成（自動ロード）
   - config モジュールはプロジェクトルート（.git または pyproject.toml を基準）から `.env` / `.env.local` を自動読み込みします。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. 推奨する主要環境変数（例）
   - JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
   - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
   - OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
   - KABUSYS_ENV — 実行環境 (development | paper_trading | live)（デフォルト: development）
   - PAPER_FILL_MODE — paper_trading 時の約定モード (instant | partial | never | reject)（default: instant）
   - PAPER_TRADING_SQLITE_PATH — Paper DB（default: data/paper_trading.db）
   - SQLITE_PATH — 監視 DB（default: data/monitoring.db）
   - DUCKDB_PATH — DuckDB ファイル（default: data/kabusys.duckdb）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=yyyyy
   OPENAI_API_KEY=sk-...
   KABUSYS_ENV=paper_trading
   PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   ```

---

## 使い方

以下は主要な起動・実行方法です。

- 監視ループを起動（Monitoring）
  ```bash
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（秒、デフォルト 60）。
  - 停止: プロジェクトルートの `data/stop_requested.flag` を作成すると監視ループが終了します（監視スクリプトは同パスを参照します）。
  - 監視は Settings に関わらず本番の sqlite_path を使用してログを保存します。

- 実行エンジンを起動（ExecutionEngine）
  ```bash
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` のときは MockBrokerClient を使用し、Paper 専用 DB（PAPER_TRADING_SQLITE_PATH）へ記録します。本番 DB と完全に分離されます。
  - 起動時に `data/stop_requested.flag` が存在すると起動しません。実行中に stop flag を作成すると安全に停止します。
  - 実行エンジンの PID は `data/execution.pid`（デフォルト）に書き込まれます。

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB: `data/paper_trading.db`（環境変数 PAPER_TRADING_SQLITE_PATH または `--db` で指定可能）
  - 稼働率 / 注文成功率 / レイテンシ等を算出し PASS/FAIL を出力します。

- Streamlit 監視ダッシュボード
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - データベースに読み取り専用で接続してダッシュボードを表示します。MonitoringEngine が書き込みしている DB を参照してください。

- AI 関連機能（ライブラリとして呼び出し）
  - ニュース NLP（ai.news_nlp.score_news）
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    n_written = score_news(conn, target_date=date(2026, 04, 01), api_key="sk-...")
    ```
  - レジーム判定（ai.regime_detector.score_regime）
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026, 04, 01), api_key="sk-...")
    ```
  - どちらも API キーは引数または環境変数 `OPENAI_API_KEY` を利用します。API 呼び出しはリトライやフェイルセーフ（失敗時はフォールバック値）を備えています。

- ライブラリ関数の利用（研究・ポートフォリオ）
  - 例: ファクター計算
    ```python
    import duckdb
    from datetime import date
    from kabusys.research import calc_momentum

    conn = duckdb.connect("data/kabusys.duckdb")
    result = calc_momentum(conn, date(2026, 4, 1))
    ```

---

## フラグ / ファイルによる制御

- data/stop_requested.flag
  - run_monitoring / run_execution がループ中に検出すると終了処理を行います（外部からの停止要求に利用）。

- data/kill.flag
  - KillSwitch によって書き込まれることがあり、ExecutionEngine に対する停止（重大リスクトリガー）を示します。
  - KillSwitch は drawdown やポジション上限超過等をトリガーに書き込まれます。

- data/execution.pid
  - ExecutionEngine が起動時に書き込む PID ファイル。SystemMonitor はこの PID を参照して実行プロセスが生存しているか確認します。stale（無効）であれば削除してログに記録します。

---

## 主要な環境変数一覧（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能利用時必須)
- KABUSYS_ENV (development | paper_trading | live) — default: development
- PAPER_FILL_MODE (instant | partial | never | reject) — paper_trading 時の約定動作
- PAPER_TRADING_SQLITE_PATH — Paper 用 SQLite（default: data/paper_trading.db）
- SQLITE_PATH — 監視 DB（default: data/monitoring.db）
- DUCKDB_PATH — DuckDB ファイル（default: data/kabusys.duckdb）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト: 60）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, LOG_LEVEL, CPU/MEM/DISK 閾値 等

詳細は `src/kabusys/config.py` を参照してください。

---

## ディレクトリ構成

以下は主要なファイルとディレクトリの概観（src/kabusys をルートとする）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - data/                    — 実行時に生成される DB・flag 等（プロジェクトルート直下）
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI 呼び出し）
    - regime_detector.py     — レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py       — SQLite 監視テーブル作成 / DB 操作ラッパ
    - system_monitor.py      — システム状態 / データ鮮度チェック
    - trade_monitor.py       — 注文滞留・約定異常チェック
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 書き込みロジック
    - alert_manager.py       — LINE Push 通知
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - reconciler.py
    - order_repository.py
    - order_record.py
    - execution_engine.py
    - broker_factory.py
    - broker_api.py
    - ... (実行関連)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - tools/
    - paper_verification_report.py
    - __init__.py
  - utils/
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
    - __init__.py
  - monitoring/ (上記)
  - ai/ (上記)

注: 上記はリポジトリ内の主要ファイルに基づく抜粋です。実装の詳細は各ファイルの docstring を参照してください。

---

## 運用上の注意・ベストプラクティス

- KABUSYS_ENV を `paper_trading` にして動作確認を行い、本番運用時は `live` を使ってください。
- OpenAI API キーやブローカー資格情報は `.env` で管理し、リークに注意してください。
- `MONITOR_POLL_INTERVAL` は監視頻度と負荷のトレードオフを考慮して設定してください。
- PID / flag ファイルは外部ツール（systemd / supervisor）からの制御に使えます。
- DuckDB / SQLite のファイルは定期バックアップを推奨します（特に execution のログや positions 等）。
- LINE 通知はトークン・ユーザIDが未設定の場合は送信されずログのみ出力されます（デフォルトフェイルセーフ）。

---

## 開発・テスト

- モジュールは可能な限り純粋関数 / DI（依存注入）で設計されており、ユニットテストが書きやすくなっています。
- AI 呼び出し関数は `_call_openai_api` 等をパッチ/モック可能に設計してあります（unittest.mock.patch によるテスト推奨）。
- MonitoringEngine は `run_once()` を持つので単体テストで各 Monitor の結合動作を検証できます。

---

必要に応じて README に記載するサンプル .env.example、requirements.txt、運用手順（systemd ユニット例）等を追加できます。追加希望があれば教えてください。