# KabuSys

日本株向け自動売買システム（Lightweight / モジュール設計）

このリポジトリは、取引実行エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ、ニュース NLP（OpenAI）等のコンポーネントを含む自動売買プラットフォームのコードベースです。設計方針は堅牢性（クラッシュ耐性・冪等性）、フェイルセーフ、ルックアヘッドバイアス排除、外部 API 呼び出しの隔離です。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（起動コマンド・ツール）
- 環境変数一覧（主要）
- ディレクトリ構成

---

プロジェクト概要
- Execution：発注・注文状態管理・リコンシリエーション（Reconciler）を提供する実行エンジン。
- Monitoring：システム稼働状態、注文滞留、約定異常、ドローダウンなどを監視し、ログ／アラート／kill フラグを書き込む。
- Portfolio：銘柄選定、重み計算、ポジションサイズ算出、セクターキャップ等の純粋関数群。
- Research：DuckDB を用いたファクター計算・特徴量解析ユーティリティ。
- AI：ニュースのセンチメント解析（OpenAI）、市場レジーム判定（LLM + 指標の合成）。
- Tools：Paper Trading 検証レポート生成、Streamlit ダッシュボード等のユーティリティスクリプト。
- 設定管理：.env 自動読み込み（プロジェクトルートに .env / .env.local があれば読み込む。無効化可）。

---

主な機能一覧
- 実行エンジン（ExecutionEngine）
  - ブローカー（実口座 or モック）を切替可能（KABUSYS_ENV に依存）
  - OrderManager / OrderRepository による堅牢な注文ワークフロー
  - 起動時の自動リコンシリエーション（未確定注文の同期・ポジション差分検出）
  - リスク管理（RiskManager）: ポジション上限・利用率・回路遮断など

- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/ディスク/プロセス状態・データ鮮度監視
  - TradeMonitor: 注文滞留（stale orders）・約定異常価格検出
  - RiskMonitor: ドローダウン検知・ポジション数監視・ダッシュボード更新
  - KillSwitch: 条件に応じて flag ファイルを書き、Execution を停止できる
  - AlertManager: LINE Push による通知（クールダウン管理付き）
  - Streamlit ベースの監視ダッシュボード

- ポートフォリオ構築
  - 候補選定、等金額/スコア加重、スコア加重が 0 の場合のフォールバック
  - セクター集中制限、レジームによる投下資金乗数
  - ポジションサイズ計算（単元株丸め、aggregate cap のスケーリング）

- リサーチ
  - Momentum / Volatility / Value 等のファクター計算（DuckDB + SQL）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリ

- AI
  - ニュースをまとめて OpenAI へ投げ、銘柄別センチメントを ai_scores テーブルへ書き込む
  - マクロニュース + ETF MA200 乖離を用いて市場レジームを判定

- ツール
  - paper_verification_report: Paper Trading の検証レポート生成
  - streamlit_dashboard: 監視情報を可視化するダッシュボード

---

セットアップ手順（ローカル開発／簡易）
1. Python 環境を用意
   - 推奨: Python 3.9+
   - 仮想環境を作成・有効化
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 必要な主なパッケージ（例）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - 例:
     - pip install duckdb psutil requests openai streamlit

   （プロジェクトに requirements.txt があれば pip install -r requirements.txt を使用してください）

3. 環境変数の設定
   - プロダクション用の必須項目:
     - JQUANTS_REFRESH_TOKEN（J‑Quants API）
     - KABU_API_PASSWORD（kabu API）
   - OpenAI 機能を使用する場合:
     - OPENAI_API_KEY
   - 設定は .env / .env.local に記述するか、OS 環境変数として設定してください。
   - 自動ロード:
     - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）が見つかると .env/.env.local が自動で読み込まれます。無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

4. データディレクトリ作成
   - デフォルトでは data/ に DB 等を作成します。必要に応じてディレクトリ作成:
     - mkdir -p data

5. Paper Trading（分離 DB）
   - KABUSYS_ENV=paper_trading を設定すると、paper_trading 用の SQLite を使い、本番 DB と完全に分離されます（デフォルト: data/paper_trading.db）。

---

使い方（主なコマンド例）

- 実行エンジン起動（Execution）
  - デフォルト（環境に応じて実口座またはモックブローカーが選択されます）:
    - python -m kabusys.run_execution
  - Paper trading（モック）で起動:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution

- 監視ループ起動（Monitoring）
  - デフォルトポーリング間隔 60 秒。ENV で上書き可:
    - export MONITOR_POLL_INTERVAL=30
    - python -m kabusys.run_monitoring
  - メモ: Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path（monitoring DB）を使用します。

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（ニューススコア・レジーム判定）
  - OPENAI_API_KEY を環境変数で設定してから、対応する関数を呼び出す（via スクリプト / バッチ処理 / scheduler）。
  - 例（Python から）:
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key=None)  # api_key=None → 環境変数を参照

---

主要な環境変数（抜粋）
- 必須 / 重要
  - JQUANTS_REFRESH_TOKEN — J‑Quants API 用トークン（必須）
  - KABU_API_PASSWORD — kabu API 用パスワード（必須）
- 動作モード
  - KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
- データベースパス
  - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- AI
  - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector 用）
- 監視関連
  - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
  - PID_FILE_PATH — ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — kill フラグファイル（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag をクリアするか（"1" でクリア）
- LINE 通知
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID

（詳細は src/kabusys/config.py を参照してください）

---

監視 / 停止の仕組み（簡単な説明）
- ExecutionEngine は pid ファイル（デフォルト data/execution.pid）を作成します。SystemMonitor はこの pid ファイルを見てプロセス生存を判定します。
- RiskMonitor がドローダウンやポジション上限を検出すると、KillSwitch が data/kill.flag を書き込みます。ExecutionEngine はこのフラグを検出して安全に停止する設計です。
- KILL_FLAG_CLEAR_ON_START を "1" にすると起動時に既存の kill.flag を自動でクリアします（テスト用途など）。

---

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI で銘柄別センチメント）
    - regime_detector.py     — 市場レジーム判定（MA + マクロセンチメント）
    - __init__.py
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py      — システム監視（CPU/MEM/DISK/プロセス/データ鮮度）
    - trade_monitor.py       — 注文滞留・約定異常監視
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 書き込みユーティリティ
    - alert_manager.py       — LINE 通知クライアント
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py — Streamlit 監視ダッシュボード
    - __init__.py
  - portfolio/
    - portfolio_builder.py   — 候補選定・均等/スコア配分
    - position_sizing.py     — 株数決定・単元丸め・aggregate cap
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py     — Momentum / Volatility / Value のファクター計算
    - feature_exploration.py — 将来リターン・IC・統計サマリ等
    - __init__.py
  - execution/
    - order_manager.py
    - reconciler.py
    - order_repository.py
    - order_record.py
    - broker_factory.py
    - execution_engine.py
    - ...（他、broker 抽象 / 実装）
  - utils/
    - process_priority.py    — プロセス優先度 / CPU affinity 設定ユーティリティ
    - __init__.py

（上記はコードベースの主要モジュールの一覧です。詳細は各ファイル内ドキュメントを参照してください）

---

注意事項 / ベストプラクティス
- .env ファイルの取り扱い: .env.example を参考に .env を作成してください（config._require が未設定時に ValueError を送出します）。
- OpenAI を利用する機能は API コストが発生します。運用時は使用頻度・バッチサイズやリトライ方針を理解した上で運用してください。
- Paper Trading は本番 DB と分離されるように実装されています。KABUSYS_ENV=paper_trading を使って動作確認を行ってください。
- プロセス優先度や CPU affinity の設定はプラットフォーム依存で権限が必要な場合があります（psutil に依存）。失敗しても警告ログを出してスキップします。

---

さらに詳しいドキュメントや運用手順、API キーの扱い、DB マイグレーション、CI/CD、テストは別途ドキュメント化することを推奨します。

不明点や追加したい README セクションがあれば教えてください。