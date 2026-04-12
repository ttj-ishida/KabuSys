# KabuSys — README

これは日本株自動売買システム KabuSys のコードベース向け README です。ここではプロジェクトの概要、主な機能、セットアップ手順、実行方法、ディレクトリ構成をまとめています。

注意: 本 README はソース内の docstring / 設計注釈に基づいて作成しています。実運用前に各種設定（APIキー・環境変数・DBパス等）を十分に確認してください。

---

## プロジェクト概要

KabuSys は日本株の自動売買・リサーチ・監視を行うためのモジュール群です。  
主な目的は以下のとおりです。

- リサーチ: ファクター計算・特徴量解析（DuckDB 上の時系列データを利用）
- ポートフォリオ構築: 候補選定、重み付け、ポジションサイズ算出、セクター制限・レジーム調整
- 実行エンジン: ブローカー連携（本番 / ペーパートレーディングの切替）、注文管理、リコンシリエーション
- 監視: システム稼働・注文状態・リスク監視、Kill Switch による安全停止、LINE へのアラート
- AI 支援: ニュースのセンチメントスコアリング（OpenAI）や市場レジーム判定
- 運用ツール: ペーパートレードの検証レポート生成、Streamlit ダッシュボード 等

---

## 主な機能一覧

- 環境・設定管理（kabusys.config）
  - .env 自動読み込み（プロジェクトルートを自動検出）
  - 必須/任意設定のラッパー（Settings クラス）
- 実行スクリプト
  - run_execution.py — ExecutionEngine 起動（KABUSYS_ENV により paper/live を切替）
  - run_monitoring.py — SystemMonitor のポーリングループ起動
- 監視（kabusys.monitoring）
  - SystemMonitor: CPU/メモリ/Disk/プロセス/データ鮮度監視
  - TradeMonitor: 注文滞留・約定異常の検出
  - RiskMonitor: ドローダウン・ポジション上限監視と dashboard 更新
  - KillSwitch: フラグファイルによる ExecutionEngine の停止指示
  - AlertManager: LINE Messaging API による通知（クールダウン管理あり）
  - MonitoringDB: SQLite を用いた監視ログ永続化。マイグレーションを内包（列追加）
  - Streamlit ダッシュボード（read-only で監視 DB を表示）
- 実行ロジック（kabusys.execution）
  - OrderManager / OrderRepository / Reconciler 等の注文管理／復旧機能
  - BrokerClientFactory による本番 / モックブローカー切替（paper_trading 環境）
- ポートフォリオ（kabusys.portfolio）
  - 候補選定（スコア降順）、等配分/スコア重み、リスク調整（セクター上限、レジーム乗数）
  - ポジションサイズ計算（単元株丸め、aggregate cap、リスクベース等）
- リサーチ（kabusys.research）
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化の統合
- AI（kabusys.ai）
  - news_nlp: raw_news を OpenAI に投げて銘柄ごとのセンチメントスコアを ai_scores に書込
  - regime_detector: ETF（1321）MA とマクロニュースの LLM 評価を合成して market_regime に書込
  - OpenAI 呼び出しはリトライ・バックオフやレスポンス検証を含む
- 運用ツール（kabusys.tools）
  - paper_verification_report: Paper Trading DB を分析して PASS/FAIL レポートを生成

---

## 必要条件（開発環境の目安）

- Python >= 3.10 （型注釈に PEP 604 の | を利用）
- 依存パッケージ（代表例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード利用時）
- SQLite（標準ライブラリ sqlite3 を利用）
- ネットワーク接続（LINE / OpenAI / ブローカー API を使う場合）

requirements.txt が無い場合は上記パッケージを pip でインストールしてください。

例:
pip install duckdb psutil requests openai streamlit

---

## セットアップ手順

1. リポジトリをクローン／配置
2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
4. 環境変数を設定（推奨はプロジェクトルートに .env を置く）
   - 自動読み込み: kabusys.config はプロジェクトルート（.git または pyproject.toml を探索）にある .env / .env.local を自動で読み込みます。
   - 自動読み込みを無効にする場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
5. データディレクトリの作成
   - デフォルトの DB/ファイルは data/ 配下に書き込まれるため、書き込み権限を確認してください。

---

## 主要な環境変数（Settings / デフォルトなど）

- KABUSYS_ENV: 起動環境（development / paper_trading / live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: （必須）J-Quants API トークン
- KABU_API_PASSWORD: （必須）kabuステーション API パスワード
- KABU_API_BASE_URL: kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時に必要）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（未設定時は通知はスキップ）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 専用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch 用フラグ（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag をクリアするか（"1" で true）
- PAPER_FILL_MODE: Paper Trading の約定モード（instant|partial|never|reject。デフォルト: instant）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）。1未満/不正値はデフォルトにフォールバック。
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- CPU/MEM/DISK 閾値: CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT（%）

注意: Settings._require により必須キーが未設定だと起動時に ValueError を投げます。

---

## 実行方法（代表的なコマンド）

- 実行エンジン（注文処理）
  - 本番またはペーパーを Settings.KABUSYS_ENV で切替
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH に記録されます（本番 DB と分離）。
    - 起動時にプロセス優先度を High に設定しようとします（権限がないと警告）。

- 監視ループ
  - python -m kabusys.run_monitoring
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可（デフォルト 60 秒）。
    - 監視は設定にかかわらず本番の sqlite_path（Settings.sqlite_path）を使用してログを残します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション: --db PATH で SQLite ファイルを明示指定。環境変数 PAPER_TRADING_SQLITE_PATH でも指定可能。

- Streamlit ダッシュボード（監視 DB の可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用で DB を開く（URI に ?mode=ro が付与されます）。

---

## AI 機能について

- kabusys.ai.score_news (news_nlp.score_news)
  - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini を想定）に投げ、ai_scores テーブルに書き込みます。
  - OPENAI_API_KEY が必要。未設定だと ValueError。
  - バッチサイズ、リトライ制御、レスポンス検証、スコアのクリップ（±1.0）を行います。

- kabusys.ai.regime_detector.score_regime
  - ETF 1321 の MA200 乖離とマクロニュースの LLM 評価を合成して market_regime に書き込みます。
  - OPENAI_API_KEY が必要（未設定時はエラー）。
  - LLM 呼び出し失敗時はマクロスコアを 0.0 にフォールバックするなどのフェイルセーフ実装あり。

---

## ディレクトリ構成（主なファイルと役割）

- src/kabusys/
  - __init__.py — パッケージ定義（__version__ 等）
  - config.py — 環境変数 / .env の自動読み込みと Settings クラス
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - monitoring/
    - monitoring_db.py — SQLite テーブル作成・MonitoringDB クラス（ログ保存）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag を書く/削除するユーティリティ
    - alert_manager.py — LINE Push 通知
    - monitoring_engine.py — 各 Monitor を束ねるポーリングフレームワーク
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py — 注文作成 / 送信 / 同期のロジック
    - reconciler.py — 起動時リコンシリエーション
    - （その他 broker_factory / order_repository 等は本リポジトリに含まれる想定）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数算出（単元丸め・aggregate cap 等）
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン計算・IC・統計サマリー
  - ai/
    - news_nlp.py — ニュースセンチメントスコア取得ロジック（OpenAI）
    - regime_detector.py — 市場レジーム判定（OpenAI）
  - data/  （実運用では data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db 等）
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

（上記は本リポジトリに含まれる主要ファイルの抜粋です。その他、execution の broker 実装やデータパイプライン等のモジュールが存在する想定です。）

---

## 運用上の注意点

- .env 自動読み込み:
  - プロジェクトルート（.git もしくは pyproject.toml がある場所）を探索して .env / .env.local を読み込みます。
  - OS 環境変数が優先されます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DB のマイグレーション:
  - monitoring_db.init_monitoring_db() は必要テーブルを作成し、既存 DB に対して列追加（peak_value, latency_ms）を行う処理を持ちます（冪等）。
- プロセス優先度:
  - run_* スクリプトは起動時に set_process_priority("high") を呼びます。権限がない場合は警告が出ます。
- Paper Trading:
  - KABUSYS_ENV=paper_trading の場合、run_execution は Paper 専用の SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB とデータを分離します。
  - PAPER_FILL_MODE により MockBroker の約定挙動を制御できます（instant|partial|never|reject）。
- Kill Switch:
  - kill.flag を書くことで ExecutionEngine に停止シグナルを送ります。flag の書き込みは冪等（既存なら書かない）です。
  - Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時にフラグを削除できます。
- OpenAI 利用:
  - スコアリングやレジーム判定は外部 API を利用するため、API 利用制限や課金に注意してください。API 呼び出しはリトライと検証を実装していますが、失敗時はフェイルセーフ動作（スコア0やスキップ）になります。

---

## よく使うコマンドまとめ

- 実行（注文処理）
  - KABUSYS_ENV=live python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- 監視（デーモン）
  - python -m kabusys.run_monitoring
- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper 検証レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD --db path/to/paper_trading.db

---

以上がこのコードベースの README（日本語）になります。追加で例示の .env.example、requirements.txt、起動用 systemd ユニットや Dockerfile などの運用資料が必要であれば作成支援できます。必要な出力形式（Markdown/他）や追記したい情報があれば教えてください。