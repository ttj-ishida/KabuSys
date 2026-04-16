README
=====

概要
---
KabuSys は日本株向けの自動売買・リサーチ・監視を目的とした Python パッケージ群です。  
このリポジトリは以下の主要機能を含みます。

- 発注実行エンジン（ExecutionEngine）および起動スクリプト
- 監視コンポーネント（System / Trade / Risk）と監視ループ起動スクリプト
- Paper Trading 用の分離された DB とモックブローカー動作
- ニュースの NLP による銘柄センチメント算出（OpenAI 使用）
- 市場レジーム判定（MA + マクロセンチメントを合成）
- ポートフォリオ構築・ポジションサイズ計算の純粋関数群
- Paper Trading 検証レポート生成ツール
- Streamlit ベースの監視ダッシュボード

主な設計方針
- 本番／Paper Trading を環境変数で切替（KABUSYS_ENV）
- DB は DuckDB（時系列・ファクター計算）と SQLite（監視ログ / 発注ログ）を併用
- LLM（OpenAI）呼び出しはリトライ・バリデーション・部分失敗のフェイルセーフ設計
- 多くのコンポーネントは純粋関数または DB 読み書きに限定（テスト容易性を重視）

機能一覧
---
- run_execution.py
  - ExecutionEngine を起動。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録。
  - 停止フラグ（data/stop_requested.flag）で安全停止。
- run_monitoring.py
  - SystemMonitor をポーリングして system_status / risk_logs / trade_logs / dashboard を更新。
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可（デフォルト 60 秒）。
- monitoring パッケージ
  - SystemMonitor, TradeMonitor, RiskMonitor, MonitoringEngine, AlertManager（LINE プッシュ）等を提供。
  - kill_switch: ドローダウンやポジション上限で data/kill.flag を出力して ExecutionEngine 停止をトリガー。
  - streamlit_dashboard: 監視 DB を可視化する簡易ダッシュボード（streamlit 実行）。
- ai パッケージ
  - news_nlp.score_news: raw_news を集約して OpenAI に投げ、ai_scores テーブルに書込み。
  - regime_detector.score_regime: ETF MA とマクロニュースの LLM 評価を合成して market_regime に書込み。
- research パッケージ
  - factor_research: momentum / volatility / value 等のファクターを DuckDB 上で計算。
  - feature_exploration: 将来リターン計算や IC（Information Coefficient）等。
- portfolio パッケージ
  - 候補選定、等重・スコア重み、リスク調整、ポジションサイズ計算等の純粋関数群。
- tools
  - paper_verification_report: Paper Trading DB を参照して運用検証レポートを標準出力に生成。

セットアップ手順
---
前提:
- Python 3.9+（パッケージで明確な最低バージョンを指定していればそれに従ってください）
- Git リポジトリをクローンして src を PYTHONPATH に含める、または pip install -e . 相当の手順

必須ライブラリ（一例）:
- duckdb
- psutil
- requests
- openai
- streamlit（ダッシュボード使用時）

インストール例（venv 推奨）:
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存インストール（例）
   - pip install duckdb psutil requests openai streamlit

環境変数 / .env
- 自動でプロジェクトルートの .env または .env.local を読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
- 主要な環境変数:
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
  - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
  - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
  - OPENAI_API_KEY: OpenAI API キー（ai モジュール使用時に必須）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE 通知）用
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - PAPER_FILL_MODE: Paper Trading の約定モード（instant|partial|never|reject、デフォルト instant）
  - PID_FILE_PATH: ExecutionEngine の pid ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH: kill.flag ファイルパス（デフォルト: data/kill.flag）
  - KABUSYS_ENV: 起動環境（development | paper_trading | live、デフォルト development）
  - LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
  - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

例 (.env)
  KABUSYS_ENV=development
  JQUANTS_REFRESH_TOKEN=xxxx
  KABU_API_PASSWORD=xxxx
  OPENAI_API_KEY=sk-xxxx
  DUCKDB_PATH=data/kabusys.duckdb
  SQLITE_PATH=data/monitoring.db
  PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
  LINE_CHANNEL_ACCESS_TOKEN=
  LINE_USER_ID=

使い方
---
起動スクリプト（パッケージとして実行可能）:

- 監視ループを起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL によってポーリング間隔を上書き可（例: MONITOR_POLL_INTERVAL=30）。

- 実行エンジンを起動（Execution）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用して PAPER_TRADING_SQLITE_PATH に記録する（本番 DB と分離）。

- Streamlit ダッシュボード表示
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 引数 --db で監視 DB を指定できます。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パス上書き可（環境変数 PAPER_TRADING_SQLITE_PATH より優先されます）。

- AI / リサーチ関数の利用
  - ai.score_news や ai.regime_detector.score_regime 等はライブラリ関数として呼び出します。OpenAI API キーが必要です。

停止 / フラグ
- run_execution / run_monitoring はプロセス優先度を high に設定し起動します（権限不足時は警告）。
- 停止フラグ:
  - data/stop_requested.flag: run_execution/run_monitoring で存在を監視し、あれば安全に停止します。
  - Kill Switch は監視コンポーネントから data/kill.flag を書き込んで ExecutionEngine の停止を要求します（kill.flag のパスは Settings.kill_flag_path による）。
- ExecutionEngine は pid ファイル（デフォルト data/execution.pid）を管理します。stale PID 検出時は PID ファイルを削除して警告ログを出します。

DB 初期化
- run_execution と run_monitoring の起動時に init_monitoring_db() を呼び出し、監視用のテーブルが存在することを保証します（冪等）。
- DuckDB 側のスキーマ（prices_daily / raw_financials / raw_news 等）は別処理でロードする想定です（データパイプライン経由）。

設定検証（よくあるエラー）
- OpenAI を使う処理で API キー未設定だと ValueError を送出します。
- PAPER_FILL_MODE は instant|partial|never|reject のいずれかでないと ValueError。
- KABUSYS_ENV は development|paper_trading|live のいずれかでないと ValueError。
- psutil による優先度/affinity 設定は権限不足で警告になり得ます（機能はスキップされます）。

ディレクトリ構成（主要ファイル）
---
src/kabusys/
- __init__.py
- config.py                       — 環境変数 / .env ロード & Settings
- run_monitoring.py               — SystemMonitor ポーリング起動スクリプト
- run_execution.py                — ExecutionEngine 起動スクリプト

packages / サブモジュール:
- ai/
  - news_nlp.py                    — ニュースの LLM センチメント集約・書込み
  - regime_detector.py             — 市場レジーム判定（MA + マクロ LLM）
- monitoring/
  - monitoring_db.py               — SQLite 監視テーブル初期化 + MonitoringDB クラス
  - system_monitor.py              — システム・データ鮮度監視
  - trade_monitor.py               — 注文滞留・約定異常監視
  - risk_monitor.py                — ドローダウン・ポジション上限監視
  - kill_switch.py                 — kill.flag 書込みロジック
  - alert_manager.py               — LINE プッシュ通知
  - monitoring_engine.py           — 複数モニタを束ねるランナー
  - streamlit_dashboard.py         — streamlit ベースの監視ダッシュボード
- execution/
  - reconciler.py                  — 起動時リコンシリエーション
  - order_manager.py               — 発注状態遷移 API
  - (その他、broker_factory 等は存在)
- portfolio/
  - portfolio_builder.py           — 候補選定・重み計算
  - position_sizing.py             — 発注株数計算・集計キャップ
  - risk_adjustment.py             — セクターキャップ・レジーム乗数
- research/
  - factor_research.py             — Momentum/Volatility/Value 計算（DuckDB）
  - feature_exploration.py         — 将来リターン / IC / 統計サマリ
- tools/
  - paper_verification_report.py   — Paper Trading 検証レポート生成 CLI
- utils/
  - process_priority.py            — プロセス優先度 / CPU affinity ユーティリティ

注意事項 / ベストプラクティス
---
- Paper Trading モード（KABUSYS_ENV=paper_trading）は本番 DB とは別の SQLite を使用するため、実運用の検証やテストに便利です。
- LLM 呼び出し（OpenAI）はコストとレイテンシを考慮しバッチ・トリミング・リトライ等の制御が実装されています。API キーは厳重に管理してください。
- streamlit ダッシュボードは監視 DB を読み取り専用で開きます（起動時に DB が存在しないとエラーを表示します）。
- 自動 .env の読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。CI やテストで自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

トラブルシューティング（簡易）
- モジュール ImportError が出る場合:
  - src を PYTHONPATH に含めるか、パッケージを適切にインストールしてください（pip install -e . など）。
- psutil 関連の警告:
  - プロセス優先度や CPU affinity は権限依存のため、権限不足で設定できない旨の警告が出ることがあります（動作自体は継続します）。
- OpenAI 呼び出しで 429 / タイムアウト が頻発する:
  - レート制限のためリトライが行われますが、頻発する場合はバッチサイズや呼び出し頻度を制御してください。

ライセンス・貢献
---
本 README にはライセンス情報は含まれていません。リポジトリのトップレベルに LICENSE などがあればそれに従ってください。バグ報告や機能追加は Pull Request / Issue で受け付けてください。

補足
---
この README はリポジトリ内の主要コード（config, monitoring, execution, ai, research, portfolio, tools, utils 等）を参照して作成しています。実際の導入時は各モジュールのドキュメントや docstring を併せて参照してください。