# KabuSys

KabuSys は日本株向けの自動売買 / 監視フレームワークです。本リポジトリは取引実行エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ（ファクター計算）および AI（ニュースセンチメント・レジーム判定）などの主要コンポーネントを含みます。

主にローカルの SQLite / DuckDB を使ってデータ永続化・解析を行い、実運用時は外部ブローカ API（kabuステーション等）や OpenAI API を併用します。Paper Trading（検証）用に本番 DB と分離された挙動を提供します。

---

## 主要機能（抜粋）

- Execution
  - ExecutionEngine による発注フロー（OrderManager / OrderRepository / RiskManager 等）
  - 再起動時の自動リコンシリエーション（Reconciler）
  - Paper Trading モード（MockBrokerClient／専用 SQLite DB）
- Monitoring
  - システム状態監視（CPU / メモリ / ディスク / プロセス PID チェック）
  - 注文滞留・約定異常の検出
  - ドローダウン／ポジション上限の監視と KillSwitch による停止要求
  - LINE 通知（AlertManager）
  - Streamlit ダッシュボード（読み取り専用で監視状況を可視化）
- Portfolio construction
  - 候補選定・重み付け（等配分・スコア加重）
  - セクター上限適用、レジーム乗数
  - ポジションサイズ計算（単元株丸め・リスクベース配分・aggregate cap）
- Research
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算、IC 計算、統計サマリー
- AI（オプション）
  - ニュースの NLP による銘柄別センチメント（OpenAI）
  - マクロニュース + ETF MA200 を用いた日次レジーム判定（bull/neutral/bear）
- ツール
  - Paper Trading 検証レポート生成スクリプト（期間指定可）

---

## 要件（推奨）

- Python 3.10+
- 必要となる主な Python パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボードを使う場合）
- SQLite（標準ライブラリで動作）

（実際の環境では requirements.txt を用意して pip install してください。例: pip install duckdb psutil requests openai streamlit）

---

## 環境変数（主なもの）

Settings クラスで読み込まれます。`.env` / `.env.local` をプロジェクトルートに置くことで自動読み込み（OS 環境変数を上書きしない挙動）されます。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数（抜粋）：

- KABUSYS_ENV: 起動環境
  - 値: `development` | `paper_trading` | `live`（デフォルト: development）
  - paper_trading の場合は MockBroker を使い、本番 DB と分離されます
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabu ステーション API 用パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合に必須）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
- SQLITE_PATH: 監視用 SQLite DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH: Execution エンジンの PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch が書き込むフラグファイル（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
- PAPER_FILL_MODE: Paper Trading の約定モード（`instant`|`partial`|`never`|`reject`）

注意: 必須の環境変数（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等）が未設定の場合、Settings が ValueError を投げます。`.env.example` を参照して `.env` を作成してください（リポジトリに .env.example がある想定）。

---

## セットアップ手順（ローカルでの例）

1. リポジトリをクローン
   - git clone ... && cd <repo>

2. Python 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit

   （実プロジェクトでは requirements.txt を用意して pip install -r requirements.txt を推奨）

4. .env を準備
   - プロジェクトルートに `.env`（または `.env.local`）を作成し、必要な環境変数を設定
   - 例:
     - KABUSYS_ENV=development
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb

   Settings は自動で .env / .env.local を読み込みます（ただし OS 環境変数が優先）。

5. データディレクトリ作成（必要に応じて）
   - mkdir -p data

6. DB 初期化
   - monitoring / engine を起動すると init_monitoring_db が呼ばれ自動でテーブルを作成します。手動で作りたい場合は簡単なスクリプトで init_monitoring_db を呼ぶことも可能です。

---

## 実行方法（代表例）

- ExecutionEngine を起動（デフォルト: Settings.env に従う）
  - 通常起動（本番・デフォルト DB を使用）
    - python -m kabusys.run_execution
  - Paper Trading モード（MockBroker、専用 DB を使用）
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - 必要に応じて PAPER_TRADING_SQLITE_PATH を指定

  挙動:
  - 起動時にプロセス優先度を High に設定しようとします（プラットフォームによる制限あり）
  - data/stop_requested.flag が存在すると起動せず終了します
  - 実行中に監視が kill.flag を書くことで停止要求を送ることができます（KillSwitch）

- Monitoring を起動（ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（監視用 DB は共有）

- Streamlit ダッシュボード（監視の可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用で DB を開きます（起動していない場合はエラーを表示）

- Paper Trading 検証レポート出力
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション `--db PATH` で別 DB を指定可能（環境変数 PAPER_TRADING_SQLITE_PATH > デフォルト）

- AI 機能（OpenAI を使用）
  - OPENAI_API_KEY を環境変数にセットしてから、ai モジュール関数を呼び出す（例: kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime）
  - OpenAI API 呼び出しはリトライやフェイルセーフの振る舞いを持ちますが、API キーが未設定だと ValueError が発生します

停止方法:
- 実行プロセスを安全に停止するためにプロジェクトルートの `data/stop_requested.flag` を作成することで、run_execution/run_monitoring のループが検知して終了します。
- Monitoring の KillSwitch はリスク条件に応じて `data/kill.flag` を書き、ExecutionEngine 側で検知して安全に停止します。

---

## 注意点 / 実運用のヒント

- Paper Trading は本番 DB と分離されます。`KABUSYS_ENV=paper_trading` を使用してください。
- Settings はプロジェクトルートの `.env` / `.env.local` を自動読み込みします。テストや CI では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動読み込みを無効にできます。
- run_monitoring の間隔は MONITOR_POLL_INTERVAL（秒）で調整します。0 以下や不正値は無視され、デフォルト 60 秒にフォールバックします。
- OpenAI API など外部 API を使う機能は API キー・レート制限・コストに注意してください。失敗時のフェイルセーフ（0.0 フォールバック等）が組み込まれていますが、運用ポリシーに基づく扱いを検討してください。
- PID ファイル（data/execution.pid）は ExecutionEngine が管理します。プロセス存在チェックと stale PID の検出/削除機能があります。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — Monitoring 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成ツール
  - execution/
    - broker_api.py (想定)        — ブローカー API インタフェース
    - broker_factory.py           — ブローカークライアント生成
    - execution_engine.py         — 実行エンジン本体
    - order_manager.py            — 発注管理
    - order_repository.py         — 注文 DB 永続化（SQLite）
    - reconciler.py               — 再起動時リコンシリエーション
    - risk_manager.py             — リスク制御
    - ...                         — その他関連
  - monitoring/
    - monitoring_db.py            — 監視用 SQLite テーブル / DB 操作
    - system_monitor.py           — システム状態監視
    - trade_monitor.py            — 注文滞留 / 約定監視
    - risk_monitor.py             — ドローダウン / ポジション上限監視
    - alert_manager.py            — LINE 通知
    - kill_switch.py              — kill.flag 制御
    - monitoring_engine.py        — 各 Monitor の統合ループ
    - streamlit_dashboard.py      — Streamlit ダッシュボード
  - portfolio/
    - portfolio_builder.py        — 候補選定 / 重み計算
    - risk_adjustment.py          — セクター制限 / レジーム乗数
    - position_sizing.py          — 発注株数計算
  - research/
    - factor_research.py          — ファクター計算（momentum/value/volatility）
    - feature_exploration.py      — 将来リターン / IC / 統計
  - ai/
    - news_nlp.py                 — ニュースセンチメント生成（OpenAI）
    - regime_detector.py          — レジーム判定（MA200 + マクロセンチメント）
  - data/  (実行時に生成される想定)
    - monitoring.db (data/monitoring.db)
    - kabusys.duckdb (data/kabusys.duckdb)
    - paper_trading.db (data/paper_trading.db)
    - execution.pid
    - stop_requested.flag
    - kill.flag

（上の一覧は実装の主要モジュールを抜粋したものです。詳細は src/kabusys 以下の各ファイルを参照してください。）

---

## よく使うコマンドまとめ（例）

- Execution 起動（本番／デフォルト）
  - python -m kabusys.run_execution
- Execution 起動（Paper Trading）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Monitoring 起動
  - python -m kabusys.run_monitoring
- Monitoring ポーリング間隔を 30 秒に変更
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper 検証レポート（例）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## 最後に（運用上の注意）

- 実取引を行う場合は API キー・認証情報・資金管理・レート制限・フェイルセーフやロギングを十分に確認し、バックテスト・Paper Trading を通じて充分な検証を行ってください。
- 本コードには各所でフェイルセーフやログ、再試行・マイグレーション処理が組み込まれていますが、実環境での動作確認（権限・ファイルパス・外部 API の挙動）を必ず行ってください。

---

README の内容や実行手順をプロジェクトの実際の運用ポリシーに合わせて調整してください。必要であれば `.env.example`、requirements.txt、デプロイ手順（systemd ユニット / コンテナ化）用の例も作成できます。必要ならそのテンプレートも作成します。