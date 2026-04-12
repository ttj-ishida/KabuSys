# KabuSys

日本株向けの自動売買システム（プロトタイプ）。  
シグナル生成やポートフォリオ構築、発注管理、監視、検証レポート、LLM を用いたニュースセンチメント評価など複数モジュールで構成されています。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の関心事を分離して実装したモジュール群から成る自動売買基盤です。

- 発注実行（ExecutionEngine）と注文管理（OrderManager / OrderRepository）
- 監視（MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor）
- ポートフォリオ構築（候補選定・重み計算・株数決定・リスク調整）
- リサーチ（ファクター計算、特徴量探索）
- AI モジュール（ニュースセンチメント、レジーム判定：OpenAI を使用）
- ツール（Paper Trading 検証レポート生成、Streamlit ダッシュボード）
- 設定管理（.env 自動ロード）とユーティリティ（プロセス優先度設定 等）

設計方針の例:
- ルックアヘッドバイアス回避（date.today 等を直接参照しない実装）
- フェイルセーフ（API 失敗時はフォールバック値で継続）
- DB 分離（paper_trading は本番 DB と分離）
- 冪等性を重視した DB 書き込み

---

## 主な機能一覧

- Execution
  - ExecutionEngine によるセッション実行
  - Broker クライアントの抽象化（本番 / Mock を切替）
  - 再起動時のリコンシリエーション（Reconciler）
- Monitoring
  - システム状態（CPU / Memory / Disk / プロセス）監視とログ永続化（SQLite）
  - 注文滞留・約定異常チェック
  - ドローダウン / ポジション数アラートと kill.flag による停止シグナル
  - LINE への通知（AlertManager、トークン未設定時は送信せずログのみ）
  - Streamlit ベースの監視ダッシュボード
- Portfolio
  - 候補選定（スコア順ソート）
  - 等重み・スコア重みの重み計算
  - 単元丸め・リスクベースのポジションサイズ計算
  - セクター上限・レジーム乗数適用
- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を利用）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー
- AI（OpenAI）
  - raw_news を結合して銘柄別センチメントを算出し ai_scores テーブルへ格納
  - マクロニュース + ETF ma200 乖離を合成した市場レジーム判定
- Tools
  - Paper Trading 検証レポート生成スクリプト（sqlite DB を集計）
  - Streamlit ダッシュボード（監視用）

---

## 動作要件（概略）

- Python 3.10+
- SQLite（標準ライブラリ sqlite3 を使用）
- 主要パッケージ（例）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード使用時）
- ネットワーク接続（OpenAI / LINE API を使う場合）

必要パッケージは環境に合わせて pip でインストールしてください：
pip install duckdb psutil requests openai streamlit

---

## セットアップ手順（ローカル開発）

1. リポジトリをクローン
   - 例: git clone <repo-url>

2. 仮想環境を作る（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt  （無ければ必要なパッケージを個別にインストール）

4. 環境変数（.env）を用意
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（デフォルトで自動ロードされます）。
   - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

5. 必須環境変数の例
   - JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン（必須）
   - KABU_API_PASSWORD — kabu API パスワード（必須）
   - OPENAI_API_KEY — OpenAI を利用する場合（AI 機能）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知を使う場合
   - KABUSYS_ENV — 環境 ('development' | 'paper_trading' | 'live'), デフォルト: development

6. データベース・ディレクトリ作成
   - デフォルトの SQLite / DuckDB パスは data/ 配下になります（必要に応じて作成）。
   - DuckDB（時系列価格や財務データ）と monitoring SQLite は別ファイルです。

---

## 主要な環境変数（抜粋とデフォルト）

- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- JQUANTS_REFRESH_TOKEN: （必須）
- KABU_API_PASSWORD: （必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知設定
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
- PID_FILE_PATH: data/execution.pid
- KILL_FLAG_PATH: data/kill.flag
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: モニタ閾値
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL

注意: Settings クラスで多くの環境変数は必須チェックや値検証を行います。

---

## 実行方法

パッケージをインストールせず直接実行する場合、プロジェクトルートから Python モジュールとして実行できます。

- ExecutionEngine（発注実行: 本番 または paper_trading 切替）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。

- Monitoring（システム監視ポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH より優先）
  - 例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit ダッシュボード（監視）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは monitoring DB を read-only モードで開きます。MonitoringEngine を先に動かしてデータを作ってください。

- AI 機能（ニューススコア / レジーム判定）
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime をプログラムから呼び出すか、スクリプトを作成して呼び出します。
  - OPENAI_API_KEY が必要です。API 呼び出しはリトライ・フォールバック実装済み。

---

## 監視と停止（kill.flag）

- KillSwitch は RiskMonitor の結果に基づき data/kill.flag を作成します。ExecutionEngine はこのファイルの存在を検知して安全に停止するよう想定されています。
- kill.flag は Settings.kill_flag_path で変更可能。Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時にファイルを消去できます。

---

## ロギングとプロセス優先度

- 起動スクリプトは最初に set_process_priority("high") を呼び出して優先度設定を試みます（Windows/Linux を抽象化）。
- logging.basicConfig(level=logging.INFO) を使用して INFO レベルでログ出力されます。LOG_LEVEL 環境変数で検証されます。

---

## DB 初期化

監視用 DB（SQLite）は run_execution/run_monitoring 内で `init_monitoring_db()` を呼ぶことでテーブル作成（冪等）・簡易マイグレーションが実行されます。手動で初期化する場合は以下のように呼び出してください（Python セッション内）:

- from kabusys.monitoring.monitoring_db import init_monitoring_db
- conn = sqlite3.connect("data/monitoring.db")
- init_monitoring_db(conn)

DuckDB 側は prices_daily / raw_financials 等のテーブルを準備しておく必要があります（リサーチ機能利用時）。

---

## ディレクトリ構成（抜粋）

プロジェクト内の主なファイル・モジュール構成:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor ポーリング起動
  - utils/
    - process_priority.py          — 優先度 / CPU affinity ユーティリティ
  - execution/
    - order_manager.py
    - reconciler.py
    - ...（broker_factory, execution_engine, order_repository 等）
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
    - streamlit_dashboard.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py

（上記はコードベースの主要部分を抜粋したものです）

---

## 注意点 / 運用メモ

- KABUSYS_ENV によって挙動が変化します。paper_trading は本番 DB と分離して動作するよう設計されています。
- OpenAI / LINE の API を使う機能はキーが未設定でもシステム全体は稼働しますが、該当機能は無効になります（フェイルセーフ）。
- データ鮮度チェックは DuckDB 上の prices_daily の最終日付を参照します。リサーチ用データセットの投入を忘れないでください。
- Paper Trading 用 DB（data/paper_trading.db）を検証用に保存・バックアップすることを推奨します。
- 本リポジトリは完全な運用プロダクトではなく、設計・アルゴリズムの構成を示すプロトタイプです。実運用前に内部ロジック（例: リスク制御、注文フロー、エラーハンドリング、テスト）を十分に検討してください。

---

## 参考・連絡

不明点や実装上の質問がある場合はリポジトリの issue に記載してください。README の改善提案も歓迎します。