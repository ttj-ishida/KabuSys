# KabuSys

日本株向け自動売買システムの軽量実装（ライブラリ / 実行スクリプト群）。

このリポジトリは取引エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI を用いたニューススコアリングなどの主要機能を含むモジュール群を提供します。

---

## プロジェクト概要

- Python で実装されたモジュール群（src/kabusys 以下）。
- SQLite を監視ログや発注履歴（paper_trading 用に分離可能）に使用。
- DuckDB をファクター計算・リサーチ用の分析 DB として利用。
- OpenAI（gpt-4o-mini 想定）を用いたニュースセンチメント評価 / レジーム判定を実装。
- LINE Messaging API を用いた一方向プッシュ通知機能を備える。
- 監視ループ（MonitoringEngine）と実行ループ（ExecutionEngine）の起動スクリプトを提供。

---

## 主な機能一覧

- Execution
  - 発注マネジメント、リスク制御、リコンシリエーション（再同期）
  - paper_trading モードでは MockBrokerClient を利用し本番 DB と分離
- Monitoring
  - システム状態（CPU / メモリ / ディスク / 実行プロセス）監視
  - 注文滞留・約定異常の検出
  - ドローダウン／ポジション上限監視（Kill Switch により ExecutionEngine 停止指示）
  - LINE によるアラート通知
  - Streamlit ダッシュボード用スクリプト
- Portfolio
  - 候補選定、等重／スコア加重、リスク調整（セクター制限、レジーム乗数）
  - 株数算出（単元丸め、aggregate cap 等）
- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB 利用）
  - 将来リターン計算、IC（Spearman）やファクター統計
- AI
  - ニュース記事を LLM でスコアリングして ai_scores テーブルに保存
  - マクロニュース＋ETF MA200 を組み合わせた市場レジーム判定
- Tools
  - Paper Trading 向け検証レポート生成スクリプト

---

## 必要条件（開発環境の例）

- Python 3.10+
- 必要パッケージ（pip でインストール）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボードを使う場合）
- SQLite は標準ライブラリで扱えます

例:
```bash
pip install duckdb psutil requests openai streamlit
```

---

## 環境変数（主要）

このプロジェクトは .env ファイルまたは環境変数から設定を読み込みます（自動ロード順: OS 環境変数 > .env.local > .env）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須（実行するコンポーネントに応じて必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須: Settings.jquants_refresh_token）
- KABU_API_PASSWORD — kabuステーション API 用（必須: Settings.kabu_api_password）

任意 / 既定値:
- KABUSYS_ENV — 起動環境: one of `development`, `paper_trading`, `live`（デフォルト: `development`）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知設定（未設定時は通知を行わない）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — paper_trading の約定モード（`instant` / `partial` / `never` / `reject`、デフォルト: `instant`）
- PID_FILE_PATH — ExecutionEngine PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — Kill Switch フラグパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト: 60）

注意: Settings クラスにバリデーションがあり、無効な値は例外になります。

---

## セットアップ手順（ローカルで動かす場合）

1. リポジトリをクローン
2. Python 環境を用意（venv など）
3. 依存パッケージをインストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt  # (requirements.txt がある場合)
   # または最低限:
   pip install duckdb psutil requests openai streamlit
   ```
4. .env を作成（最低限必要な環境変数を設定）
   例:
   ```
   KABUSYS_ENV=paper_trading
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   ```
   - 自動ロードはプロジェクトルートの `.env` / `.env.local` を探索して行います。
5. データディレクトリ作成（デフォルトパス）
   ```bash
   mkdir -p data
   ```
   SQLite / DuckDB ファイルは初回起動時に自動作成・初期化されます。

---

## 使い方（主なエントリポイント）

- ExecutionEngine を起動
  - 通常（本番環境または paper_trading による分離）:
    ```bash
    python -m kabusys.run_execution
    ```
  - KABUSYS_ENV が `paper_trading` の場合、MockBroker を使用し `data/paper_trading.db` に記録します。

- Monitoring を起動（ポーリングループ）
  - ポーリング間隔を環境変数で上書き可能:
    ```bash
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring
    ```
  - Monitoring は環境設定にかかわらず監視用の本番 sqlite_path（Settings.sqlite_path）を使用します。

- Paper Trading 検証レポート（ツール）
  - 指定期間のレポートを生成して標準出力へ:
    ```bash
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    # DB を明示する場合:
    python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
    ```

- Streamlit 監視ダッシュボード
  - 起動:
    ```bash
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```
  - データベースを read-only で開く（Streamlit UI 内に説明あり）。

- AI / リサーチモジュール（プログラムから呼び出す）
  - ニューススコア付与:
    - Python から `kabusys.ai.score_news` を呼ぶ（DuckDB 接続と target_date を渡す）。OPENAI_API_KEY が必要。
  - レジームスコア:
    - `kabusys.ai.regime_detector.score_regime` を呼ぶ（DuckDB 接続と target_date を渡す）。

注意: 上記 AI 処理は OpenAI API の料金が発生します。API キーの提供に注意してください。

---

## 監視 / 停止制御の挙動（要点）

- Monitoring の SystemMonitor は PID ファイル（Settings.pid_file_path）を確認し、実行プロセスの有無を判定します。stale PID を検出すると削除してリスクログに記録します。
- KillSwitch は RiskMonitor の結果に応じて `data/kill.flag` を書き込み、ExecutionEngine に停止を促します（ExecutionEngine は起動時にこのフラグをチェック／クリアする設定が可能）。
- AlertManager は LINE に対して一定時間のクールダウンを設けて通知します。トークン/ユーザID が未設定なら送信をスキップします。

---

## ディレクトリ構成（抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / 設定管理 (Settings)
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
    - tools/
      - paper_verification_report.py — Paper Trading 検証レポート CLI
    - monitoring/
      - __init__.py
      - monitoring_db.py       — SQLite テーブル初期化・読み書き（MonitoringDB）
      - system_monitor.py      — システム監視
      - trade_monitor.py       — 注文滞留 / 価格異常検出
      - risk_monitor.py        — ドローダウン / ポジション上限監視
      - kill_switch.py         — kill.flag 管理
      - alert_manager.py       — LINE 通知
      - monitoring_engine.py   — 複数モニタの束ね（Polling）
      - streamlit_dashboard.py — Streamlit ダッシュボード
    - execution/
      - order_manager.py
      - reconciler.py
      - ...                    — ブローカ API・OrderRepository 等（部分的）
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
      - news_nlp.py            — ニュース NLP スコアリング
      - regime_detector.py     — 市場レジーム判定
      - __init__.py
    - utils/
      - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
      - __init__.py

（上記は主要ファイルの抜粋です。実際のリポジトリにはさらに詳細な実装や補助モジュールが含まれます。）

---

## 実行上の注意点 / ベストプラクティス

- paper_trading モードは本番用 DB と分離されるため、テストや検証におすすめです（Settings.is_paper）。
- OpenAI を使う機能は API 呼び出し・リトライ等の実装が入っていますが、APIキーとコスト管理は自己責任で行ってください。
- Monitoring は既定で本番用の sqlite_path を使用します（監視データは本番 DB を使う設計）。
- .env の自動ロードはプロジェクトルート（.git か pyproject.toml のある場所）を基準に行われます。CI / テスト環境で自動ロードを避けたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- process priority / affinity はプラットフォーム差異を吸収するコードがありますが、権限不足等で設定に失敗することがあります（警告ログを出してスキップ）。

---

## 開発に関する補足

- 複数箇所でフェイルセーフ（例: API 失敗時のフォールバック、DB マイグレーションの冪等化）が採用されています。
- DuckDB を分析向けに使っており、リサーチ関数は副作用を持たず入力の DuckDB 接続に依存して処理を行います。
- unit テストを用意する場合、OpenAI などの外部呼び出しはモックする設計になっています（_call_openai_api を patch などで差し替え可）。

---

必要であれば、README に含めるコマンド例（systemd / Supervisor 用のユニット例）、サンプル .env.example、あるいはより詳しい開発・デプロイ手順（Dockerfile / CI 設定例）を追加できます。どの情報を優先して拡張しますか？