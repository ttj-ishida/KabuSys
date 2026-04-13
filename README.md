# KabuSys

日本株向けの自動売買システム（ライブラリ＋起動スクリプト群）。  
このリポジトリは、注文実行エンジン、監視・アラート、ポートフォリオ構築、リサーチ、LLM を使ったニュース NLP / レジーム判定などの機能を含みます。

---

## 概要

KabuSys は以下のようなコンポーネントで構成されています。

- ExecutionEngine：ブローカークライアントを通じてシグナルに基づき発注を行うエンジン。実行時にリスク管理やリコンシリエーションを行う。
- Monitoring：システム状態・注文状態・リスクをポーリングしてログ保存・アラート・KillSwitch を管理する。
- Portfolio：銘柄選定、重み計算、ポジションサイズ決定・制限ロジックを提供する純粋関数群。
- Research：DuckDB 上の価格／財務テーブルを使ったファクター計算・特徴量解析。
- AI：OpenAI（gpt-4o-mini）を用いたニュースセンチメント（ai_scores）とマクロレジーム判定（market_regime）。
- Tools：Paper Trading の検証レポート生成や Streamlit ダッシュボードなどのユーティリティ。

---

## 機能一覧

- 発注フロー管理（OrderManager）：重複防止、送信・同期、拒否ハンドリング
- 起動時リコンシリエーション（Reconciler）：再起動後の注文/ポジション差分チェック
- リスク管理（RiskManager / RiskMonitor）：ドローダウンや保有銘柄数の監視とログ記録
- 監視（SystemMonitor / TradeMonitor）：CPU/メモリ/ディスク・プロセス死活・注文滞留・約定異常監視
- アラート（AlertManager）：LINE Push API による通知（クールダウン管理あり）
- Kill Switch：条件を満たすとファイルベースで ExecutionEngine 停止指示を出力
- DuckDB ベースのファクター計算（momentum / volatility / value）
- News NLP：記事群を LLM に送り銘柄ごとにセンチメントを算出して ai_scores テーブルへ保存（バッチ・リトライ実装）
- Regime Detector：ETF（1321）の MA200 とマクロニュースセンチメントを合成して日次レジーム判定
- Streamlit ダッシュボード：監視 DB の可視化
- Paper Trading 検証レポート出力ツール（成功率／稼働率／レイテンシ等の指標）

---

## 必要条件（概略）

- Python 3.10+ を推奨
- 主な Python パッケージ:
  - duckdb
  - psutil
  - requests
  - streamlit (ダッシュボード利用時)
  - openai (AI 機能利用時)
- SQLite3（標準ライブラリ）
- ネットワークアクセス（API 利用時）

requirements.txt は付属していませんが、上記パッケージを仮想環境にインストールしてください。

例:
pip install duckdb psutil requests streamlit openai

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動
2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb psutil requests streamlit openai
4. データディレクトリ作成（デフォルトの DB/ファイル置き場）
   - mkdir -p data
5. 環境変数の設定
   - project root に `.env`（または `.env.local`）を置くと自動で読み込まれます（OS 環境変数が優先）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須の環境変数（実行する機能により変わります）:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用
- KABU_API_PASSWORD — kabuステーション API 用
- OPENAI_API_KEY — AI 機能利用時に必須（score_news / score_regime）
任意/デフォルト値あり:
- KABUSYS_ENV — {development, paper_trading, live}（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（default: data/paper_trading.db）
- PAPER_FILL_MODE — paper_trading の MockBroker 挙動（instant|partial|never|reject。default: instant）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用（未設定なら送信はスキップ）
- PID_FILE_PATH / KILL_FLAG_PATH など監視関連のパス
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、default: 60）

---

## 使い方（主要スクリプト）

各スクリプトはパッケージモジュールとして起動できます。

- 実行エンジン（ExecutionEngine）
  - 用途: 発注セッションを実行する（本番/ペーパートレード切替あり）
  - 実行:
    - python -m kabusys.run_execution
  - 注意:
    - 環境 `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を使い DB は `data/paper_trading.db` に分離されます。
    - 起動直後にプロセス優先度が "high" にセットされます（権限によって失敗する場合あり）。

- 監視ループ（SystemMonitor を含む）
  - 用途: 定期的にシステムと注文の監視を実行し監視 DB に記録
  - 実行:
    - python -m kabusys.run_monitoring
  - オプション:
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 備考:
    - Monitoring 用の SQLite は実行環境にかかわらず production の `SQLITE_PATH` を使用します（監視データは本番 DB に記録される想定）。

- Paper Trading 検証レポート
  - 用途: Paper Trading DB を集計して稼働率・注文成功率・レイテンシ等のレポートを出力
  - 実行:
    - python -m kabusys.tools.paper_verification_report
    - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - デフォルト DB: data/paper_trading.db（環境変数 `PAPER_TRADING_SQLITE_PATH` で変更可）

- Streamlit ダッシュボード（監視）
  - 用途: 監視 DB（monitoring.db）の可視化
  - 実行:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 注意: 読み取り専用で開くため、MonitoringEngine を先に起動してデータを作成しておくこと。

- AI 機能（プログラム API）
  - ニューススコア算出:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続を受け取り、結果を DuckDB 内のテーブルに書き込みます。API キーは引数か `OPENAI_API_KEY` 環境変数から解決されます。API 呼び出し失敗時はフェイルセーフ（部分的に 0.0 でフォールバック）します。

---

## 設定の詳細（Settings モジュール）

設定は `kabusys.config.Settings` に集約されています。主なプロパティ：

- env: KABUSYS_ENV（development | paper_trading | live）
- duckdb_path: DUCKDB_PATH（default: data/kabusys.duckdb）
- sqlite_path: SQLITE_PATH（監視用、default: data/monitoring.db）
- paper_sqlite_path: PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
- paper_fill_mode: PAPER_FILL_MODE（instant|partial|never|reject）
- pid_file_path, kill_flag_path: 監視 / KillSwitch 用ファイルパス
- cpu_threshold_pct, memory_threshold_pct, disk_threshold_pct: 監視閾値
- log_level: LOG_LEVEL（INFO 等）

.env ファイルの自動読み込みについて:
- プロジェクトルート（.git または pyproject.toml を基準）で `.env` と `.env.local` を読み込みます。
- 優先順位: OS 環境変数 > .env.local > .env
- 自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

.env のパースはシェル形式（export やクォート、コメント）に配慮した実装になっています。

---

## ディレクトリ構成（主要ファイルの説明）

src/kabusys/
- __init__.py — パッケージ初期化、バージョン定義
- config.py — 環境変数 / 設定管理（.env 自動読み込み含む）
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト

subpackages:
- ai/
  - news_nlp.py — ニュースを LLM に送り銘柄ごとのセンチメントを算出・書き込み
  - regime_detector.py — マクロニュース + ETF ma200 で日次レジーム判定
- execution/
  - reconciler.py — 起動時リコンシリエーション
  - order_manager.py — 注文状態遷移と送信ロジック
  - (他に broker_factory, execution_engine, order_repository 等が存在する想定)
- monitoring/
  - monitoring_db.py — SQLite スキーマ定義と読み書きユーティリティ
  - system_monitor.py — CPU/メモリ/ディスク/プロセス/データ鮮度監視
  - trade_monitor.py — 注文滞留・約定異常監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — フラグファイル方式の停止シグナル
  - alert_manager.py — LINE Push API による通知
  - monitoring_engine.py — 各モニタを束ねる実行ループ
  - streamlit_dashboard.py — Streamlit ベースの監視 UI
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数計算・上限・丸めロジック
  - risk_adjustment.py — セクターキャップ、レジーム乗数
- research/
  - factor_research.py — momentum / volatility / value の計算
  - feature_exploration.py — 将来リターン、IC、統計サマリー等
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成ツール
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

データファイル（規約・デフォルトパス）
- data/kabusys.duckdb — DuckDB（prices_daily/raw_financials 等を格納）
- data/monitoring.db — 監視ログ（SQLite）
- data/paper_trading.db — Paper Trading 用 SQLite（KABUSYS_ENV=paper_trading 時使用）
- data/execution.pid — ExecutionEngine の PID（プロセス死活判定に使用）
- data/kill.flag — KillSwitch による停止フラグファイル

---

## 運用上の注意・設計上のポイント

- 監視は production の sqlite_path を使用します（run_monitoring は KABUSYS_ENV に依存しない）。
- Paper Trading モードは本番 DB から分離されるよう設計されています（`PAPER_TRADING_SQLITE_PATH` を使用）。
- OpenAI を使う処理はエラー耐性を考慮しています（429/タイムアウト/5xx でのリトライ、失敗時のフォールバック）。
- kill.flag を用いた停止は冪等（既存ファイルがあれば再書き込みしない）です。必要に応じて `kill_flag_clear_on_start` 設定で起動時にクリアできます。
- process priority / cpu affinity 設定は OS によって権限が必要になるため、権限不足時は警告を出してスキップします。

---

## よくある操作例

- 開発用に監視ループを起動:
  - export KABUSYS_ENV=development
  - python -m kabusys.run_monitoring

- Paper Trading で実行:
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10

- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

必要があれば、README に含める具体的な環境変数一覧やサンプル .env、起動スクリプトの systemd ユニット例、あるいはユニットテスト／CI に関する情報も追記します。どの情報が欲しいか教えてください。