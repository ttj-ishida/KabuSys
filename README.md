KabuSys — 日本株自動売買システム
=============================

このリポジトリは、日本株の自動売買を想定した内部ライブラリ群および運用用ツール群を提供します。  
主に以下の機能を含みます。

- 注文作成 / 送信 / 状態管理（ExecutionEngine 周辺）
- 監視（System / Trade / Risk）とアラート送信（LINE）
- Paper Trading 用の分離した DB と検証レポート出力
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ算出）
- リサーチ用ファクター計算（DuckDB を用いた時系列計算）
- ニュース NLP による銘柄センチメント算出（OpenAI API 利用）
- 市場レジーム判定（ETF + マクロニュース + LLM）
- Streamlit を使った監視ダッシュボード

特徴
----

主な特徴を抜粋します。

- 単純関数ベースで分離されたポートフォリオ構築モジュール（テスト容易）
- DuckDB / SQLite を用いた高速なローカル分析・監視ストア
- Paper Trading モードは本番 DB と完全分離（data/paper_trading.db）
- LLM（OpenAI）を使ったニュースセンチメント機能を備え、結果は ai_scores に保存
- 監視用の Kill Switch（閾値超過で ExecutionEngine 停止指示を flag ファイルで送信）
- Streamlit ダッシュボードで手軽に監視状況を可視化

セットアップ
-----------

前提
- Python 3.10+（型注釈などを利用しているため推奨）
- SQLite（ファイルベースで同梱）
- 必要ライブラリ（少なくとも以下をインストールしてください）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit

例（仮想環境推奨）:
- 仮想環境作成・有効化
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- パッケージインストール（requirements.txt がある場合はそれを利用）
  - pip install duckdb psutil requests openai streamlit

プロジェクトルートの.env 自動読み込み
- このパッケージは起動時にプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を探し、
  .env → .env.local の順に自動ロードします（OS 環境変数は上書きされません）。
- 自動ロードを無効化する場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

重要な環境変数
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で必要）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（未設定なら通知はスキップ）
- KABUSYS_ENV: 起動環境（development / paper_trading / live）デフォルト: development
  - paper_trading の場合、Execution は MockBrokerClient を使い data/paper_trading.db を使用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant | partial | never | reject）（デフォルト instant）
- PID_FILE_PATH / KILL_FLAG_PATH: PID / kill flag のファイルパス（デフォルト data/execution.pid, data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag をクリアするなら "1"
- MONITOR_POLL_INTERVAL: run_monitoring 起動時のポーリング間隔（秒、デフォルト 60）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値（%）

簡単な .env 例
（機密情報は適切に管理してください）
- .env.example のように作成してください。例:
  - JQUANTS_REFRESH_TOKEN=xxxx
  - KABU_API_PASSWORD=yyyy
  - OPENAI_API_KEY=sk-...
  - KABUSYS_ENV=paper_trading
  - DUCKDB_PATH=data/kabusys.duckdb

使い方
----

起動スクリプト（エントリポイント）はモジュールとして実行できます。

1) 監視ループ（SystemMonitor の永続ポーリング）
- 目的: システム状態 / データ鮮度 / リスク指標を定期的に記録し、アラートや kill.flag を発行
- 実行:
  - python -m kabusys.run_monitoring
  - または直接: python src/kabusys/run_monitoring.py
- オプション:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き
- 備考:
  - Monitoring は KABUSYS_ENV に関係なく本番の sqlite_path を使用します（監視は本番 DB を参照）。

2) ExecutionEngine（実際の発注処理）
- 目的: ブローカーと連携して注文を発行・管理（リスク管理・リコンシリエーション含む）
- 実行:
  - python -m kabusys.run_execution
- 挙動:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し data/paper_trading.db を使用して本番 DB と分離
  - 起動時に pid ファイルを書き、KillSwitch が data/kill.flag を監視します

3) Streamlit ダッシュボード
- 監視データを可視化する軽量ダッシュボード
- 実行例:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

4) Paper Trading 検証レポート
- data/paper_trading.db を読み、稼働率・注文成功率・レイテンシなどを判定して標準出力にレポートを出力
- 実行例:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

5) AI（ニュース NLP / レジーム判定）
- news_nlp.score_news(conn, target_date, api_key=None)
  - raw_news, news_symbols を集約して OpenAI に送信。結果を ai_scores テーブルに書き込む。
  - OPENAI_API_KEY が必要
- regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF (1321) の MA200 乖離 + マクロニュースを LLM で評価し market_regime テーブルに書き込む。

運用上の注意
- Kill Switch:
  - RiskMonitor が Drawdown (デフォルト 10%) 超過や position limit 超過を検出すると、KillSwitch が data/kill.flag に理由を書き込みます。ExecutionEngine はこのフラグを検出して停止します。
- PID / kill flag のクリア:
  - Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 をセットすれば起動時に既存 kill.flag を削除できます。
- DB マイグレーション:
  - init_monitoring_db は冪等でテーブル・インデックスを作成し、既存 DB に対する軽微な ALTER（列追加）も実施します。

ディレクトリ構成（主なファイル）
-------------------------------

src/kabusys/
- __init__.py — パッケージ定義、__version__
- config.py — 環境変数 / 設定読み込みロジック（.env 自動読み込み、Settings クラス）
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト

モジュール別（抜粋）
- ai/
  - news_nlp.py — ニュースセンチメント（OpenAI）処理
  - regime_detector.py — 市場レジーム判定（ETF + LLM）
- monitoring/
  - monitoring_db.py — SQLite に対する永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py — CPU/メモリ/Disk / データ鮮度 / PID チェック
  - trade_monitor.py — 注文滞留 / 約定異常チェック
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — フラグファイルによる停止指示
  - alert_manager.py — LINE Push 通知（クールダウン管理）
  - monitoring_engine.py — 各 Monitor をまとめてポーリング
  - streamlit_dashboard.py — Streamlit ダッシュボード
- portfolio/
  - portfolio_builder.py — 候補選定・重み付け
  - position_sizing.py — 株数決定（ロット丸め・aggregate cap）
  - risk_adjustment.py — セクターキャップ / レジーム乗数
- research/
  - factor_research.py — Momentum / Value / Volatility ファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン計算 / IC / 統計サマリー
- execution/
  - reconciler.py — 起動時リコンシリエーション
  - order_manager.py — 注文状態遷移の外向き API（OrderManager）
  - （その他、broker_factory / order_repository 等が存在）

ユーティリティ
- utils/process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ

補足事項
- DuckDB／SQLite の接続はファイルパス（Settings）で管理されています。運用環境ではバックアップやファイルパーミッションに注意してください。
- OpenAI 連携部分は API エラー（429 / タイムアウト / 5xx）に対して指数バックオフでリトライする設計ですが、API キーの漏洩やコスト管理には注意してください。
- 本リポジトリはサンプル実装が主体であり、実運用に際しては更なる堅牢化（例: トランザクション設計、監査ログ、監視の冗長化、認証・権限管理）を推奨します。

問い合わせ / 開発
-----------------
- 開発時は Settings クラスを経由して環境変数へアクセスしてください（config.py）。
- 単体関数は副作用を極力排し、ユニットテストが容易な設計になっています。テスト実装時は外部 API 呼び出しをモックしてください（news_nlp._call_openai_api 等の差し替えポイントあり）。

以上がこのコードベースの概要と基本的な使い方です。必要があれば各モジュールの詳細ドキュメント（関数仕様・入力値・返却値・例外条件など）を別途作成します。どの部分を優先して詳細化するか指示ください。