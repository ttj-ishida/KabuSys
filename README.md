# KabuSys

日本株向け自動売買システムのコードベース（部分実装）。  
このリポジトリは戦略・ポジション構築、発注管理、監視・アラート、研究・ファクター計算、AI を使ったニュースセンチメント/レジーム判定などのコンポーネントを含みます。

---
## プロジェクト概要
KabuSys は日本株の自動売買を目的としたモジュール群です。主な設計方針は以下です。

- 戦略・ポートフォリオ構築は純粋関数（メモリ内計算）で実装。
- 発注・状態管理は OrderRepository（SQLite）と OrderManager を介して行う。
- 実運用モードと paper_trading（モックブローカー）モードを切り替え可能。
- 監視機構（MonitoringEngine）による定期チェック・アラート、kill.flag による外部停止シグナル機構を提供。
- DuckDB を用いた時系列データ処理（ファクター計算、リサーチ）と OpenAI を使ったニュース NLP／レジーム判定をサポート。
- Streamlit ダッシュボードで監視情報を可視化可能。

---
## 主な機能一覧
- Execution
  - 発注管理 (OrderManager)
  - リコンシリエーション（再起動時の同期）(Reconciler)
  - リスク管理（RiskManager の設定に基づく制限）
  - Broker クライアントの抽象化と paper_trading 用 MockBroker
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク/プロセス状態・データ鮮度の監視
  - TradeMonitor：滞留注文・約定異常価格の検出
  - RiskMonitor：ドローダウン・ポジション上限監視とログ/アラート記録
  - MonitoringDB：SQLite による監視ログ永続化、簡易 DB マイグレーション対応
  - AlertManager：LINE Push による通知（クールダウン管理）
  - Streamlit ダッシュボード（監視データの可視化）
  - KillSwitch：kill.flag による ExecutionEngine 停止シグナル
- Portfolio
  - 候補選定、等配分/スコア配分
  - セクター集中制限、レジーム乗数
  - ポジションサイズ計算（単元株丸め、aggregate cap）
- Research
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 特徴量探索（forward returns、IC、統計サマリ）
  - DuckDB を用いた SQL + Python 実装
- AI
  - ニュースのセンチメントスコアリング（OpenAI）
  - マーケットレジーム判定（ETF MA + マクロニュースセンチメント合成）
  - バッチ処理・リトライ・レスポンス検証を備えた堅牢な実装
- ツール
  - paper_verification_report：paper_trading データから検証レポート生成
  - プロセス優先度 / CPU affinity 設定ユーティリティ

---
## セットアップ手順（開発 / 実行用）
想定環境: Python 3.10+（typing | None union などを使用しているため近年の Python 推奨）

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # POSIX
   - .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール
   - pip install -U pip
   - 必要な主なパッケージ（プロジェクトに requirements.txt がない場合の参考）:
     - duckdb
     - psutil
     - openai
     - requests
     - streamlit
   例:
   - pip install duckdb psutil openai requests streamlit

4. 環境変数 / .env 準備
   - プロジェクトルートに .env または .env.local を置くと自動読み込みされます（自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 主要な環境変数（概要・デフォルト）:
     - JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用トークン
     - KABU_API_PASSWORD (必須) — kabuステーション API パスワード
     - OPENAI_API_KEY — OpenAI を使用する場合に必須（AI 機能）
     - KABUSYS_ENV — 起動環境: development | paper_trading | live （デフォルト: development）
     - PAPER_FILL_MODE — paper_trading の約定モード: instant | partial | never | reject（デフォルト: instant）
     - PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB（デフォルト: data/paper_trading.db）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
     - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - PID_FILE_PATH — ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
     - KILL_FLAG_PATH — kill.flag パス（デフォルト: data/kill.flag）
     - LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト INFO）
     - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
   - 最小構成 (.env 例):
     ```
     JQUANTS_REFRESH_TOKEN=your_jq_token
     KABU_API_PASSWORD=your_kabu_pwd
     OPENAI_API_KEY=sk-...
     KABUSYS_ENV=paper_trading
     ```

5. 初期データディレクトリ作成（必要に応じて）
   - mkdir -p data

---
## 使い方（主要コマンド）
以下はパッケージをソースツリー直下で実行する例です（PYTHONPATH が通っていることが前提）。

- 実行エンジン（ExecutionEngine）を起動
  - paper_trading モードで起動する例:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
  - live / development の場合は KABUSYS_ENV を適宜設定してください。
  - 挙動:
    - paper_trading の場合、MockBrokerClient を使用して PAPER_TRADING_SQLITE_PATH に記録します（本番 DB と分離）。

- 監視ループ（SystemMonitor を含む）を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き（例: MONITOR_POLL_INTERVAL=120）。

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開き、ポートフォリオ / 注文 / システム状態を表示します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで SQLite パスを指定可能（PAPER_TRADING_SQLITE_PATH 環境変数でも可）。

- AI モジュール（プログラム内 API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - raw_news を集約して ai_scores テーブルへ書き込み（OpenAI 必須）。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF MA とマクロニュースでレジーム判定し market_regime に書き込み。

注意点:
- OpenAI を使う機能は API キーとネットワークが必要です。API 呼び出しはリトライ処理を含みますが、レート制限やコストにご注意ください。
- Monitoring は settings.env にかかわらず本番 sqlite_path を使用する実装箇所があります（監視ログは本番 DB に記録する挙動の考慮あり）。

---
## よく使う環境変数（まとめ）
- 必須（起動時にチェックされる）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 任意（機能に応じて）
  - OPENAI_API_KEY
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID
  - KABUSYS_ENV (development | paper_trading | live) — default: development
  - PAPER_FILL_MODE (instant | partial | never | reject) — default: instant
  - PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
  - SQLITE_PATH — default: data/monitoring.db
  - DUCKDB_PATH — default: data/kabusys.duckdb
  - PID_FILE_PATH — default: data/execution.pid
  - KILL_FLAG_PATH — default: data/kill.flag
  - MONITOR_POLL_INTERVAL — default: 60 (秒)
  - LOG_LEVEL — default: INFO

---
## ディレクトリ構成
（この README は現状ソースのサンプルに基づいています）

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / 設定読み込みロジック
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py  — Paper Trading 検証レポートツール
    - ai/
      - __init__.py
      - news_nlp.py            — ニュースの OpenAI を使ったスコアリング
      - regime_detector.py     — マーケットレジーム判定
    - monitoring/
      - __init__.py
      - monitoring_db.py       — SQLite スキーマと永続化ロジック
      - monitoring_engine.py   — 各 Monitor を束ねるエンジン
      - system_monitor.py      — システム状態・データ鮮度監視
      - trade_monitor.py       — 注文滞留・約定異常監視
      - risk_monitor.py        — ドローダウン・ポジション上限チェック
      - kill_switch.py         — kill.flag 書き込みロジック
      - alert_manager.py       — LINE 通知ユーティリティ
      - streamlit_dashboard.py — Streamlit ダッシュボード
    - execution/
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - broker_factory.py
      - execution_engine.py
      - ... (その他発注周り)
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - utils/
      - __init__.py
      - process_priority.py     — プロセス優先度 / CPU affinity 設定ユーティリティ
    - data/ (生成される・運用上の DB / ファイル置き場)
      - kabusys.duckdb (default DUCKDB_PATH)
      - monitoring.db (default SQLITE_PATH)
      - paper_trading.db (default PAPER_TRADING_SQLITE_PATH)
      - execution.pid
      - kill.flag

---
## 実運用上の注意 / ヒント
- paper_trading モードは本番 DB と隔離されるよう設計されています。開発・検証時は必ず環境変数を確認してください。
- OpenAI など外部 API の失敗時は多くの処理がフェイルセーフ（例: スコア 0.0、処理スキップ、ログ記録）になっていますが、結果の解釈と運用には注意してください。
- process priority / cpu affinity の設定はプラットフォーム依存のため、権限不足の場合は警告を出してスキップします。
- kill.flag は冪等に書き込み（既存なら上書きしない）されます。ExecutionEngine は起動時にこのフラグを消去するオプション（設定）を持っています。

---
## 開発・拡張のポイント
- DuckDB を中心にデータ処理を行う設計なので、prices_daily / raw_financials / raw_news といったテーブルを投入すれば各ファクターや研究モジュールが機能します。
- AI 部分（news_nlp, regime_detector）は OpenAI SDK の呼び出しをラップしており、テスト時は _call_openai_api をモックすることが想定されています。
- ポートフォリオ構築ロジックは純粋関数群のためユニットテストが容易です。

---
もし README に追加してほしい内容（例: 具体的な SQL スキーマの説明、サンプル .env.example、CI / テスト手順、デプロイ手順など）があれば教えてください。必要に応じてサンプル .env や起動スクリプトの具体例を追加します。