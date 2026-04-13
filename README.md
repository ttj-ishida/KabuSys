KabuSys — README
=================

概要
----
KabuSys は日本株の自動売買／研究／監視を目的とした Python ベースのプロジェクトです。  
主要コンポーネントは以下の通りです。

- Execution: 注文作成・送信・リコンシリエーションを行う実行エンジン
- Monitoring: システム状態・注文状況・リスク監視とアラート（LINE 連携）
- Portfolio: 候補選定・重み付け・ポジションサイズ計算などのポートフォリオ構築ロジック
- Research: DuckDB を用いたファクター計算・特徴量解析ユーティリティ
- AI: ニュースの NLP スコアリング / 市場レジーム判定（OpenAI API 利用）
- Tools: 検証レポート生成などのユーティリティスクリプト

主な設計方針：
- DuckDB / SQLite を用いたオンメモリ＋永続化の分離
- 外部 API 呼び出しは明示的・フェイルセーフに実装（OpenAI, ブローカー API 等）
- .env ファイル自動読み込み（プロジェクトルートの .env / .env.local）

主な機能
--------
- 実行エンジン（ExecutionEngine）: ブローカーへの注文送信、リスク管理、再起動後のリコンシリエーション
- 監視（MonitoringEngine）: CPU/メモリ/ディスク、プロセス生存確認、データ鮮度、滞留注文/約定異常の検出
- Kill Switch: ドローダウンやポジション過多を検出した場合にフラグファイルを書き ExecutionEngine を停止可能
- LINE アラート送信（AlertManager）: クールダウン管理付きの一方向プッシュ
- Streamlit ダッシュボード: 監視データの可視化（read-only 接続）
- Paper Trading 検証レポート生成ツール
- ポートフォリオ構築ユーティリティ（候補選定、等重／スコア重み、ポジションサイズ計算、セクターキャップ）
- Research モジュール: モメンタム/ボラティリティ/バリュー等のファクター計算、IC 計算、統計サマリ
- AI モジュール: ニュース記事のセンチメントスコアリング（OpenAI）、市場レジーム判定（LLM + MA200）

セットアップ
-----------
前提
- Python 3.10 以上（typing の | 記法などを利用）
- SQLite（標準ライブラリ）、DuckDB、外部ライブラリ（下記）

推奨手順（例）
1. 仮想環境作成と有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   必要なパッケージ（例）:
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit
   pip install duckdb psutil requests openai streamlit

   （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

3. 環境変数の設定
   プロジェクトルート（.git や pyproject.toml があるディレクトリ）に .env または .env.local を置くと自動ロードされます（既存の OS 環境変数は保護されます）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

   主な環境変数（例）
   - KABUSYS_ENV: 起動環境（development / paper_trading / live）。デフォルト: development
   - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知設定
   - SQLITE_PATH: 監視用 SQLite のパス（デフォルト data/monitoring.db）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
   - PAPER_FILL_MODE: paper_trading の挙動（instant|partial|never|reject、デフォルト instant）
   - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
   - PID_FILE_PATH、KILL_FLAG_PATH など（デフォルト data/execution.pid, data/kill.flag）

   .env のパーサはコメント、export 形式、クォートやエスケープ等をサポートします。未設定の必須変数は Settings クラスで検出され例外になります。

使い方
------
起動可能な主要スクリプト（パッケージとして実行）

- 監視ループ（Monitoring）
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き可能（デフォルト 60）。
  - 監視用 DB（SQLite）は Settings.sqlite_path を使用し、KABUSYS_ENV に関わらず本番 sqlite_path を参照します。
  - 実行時はプロセス優先度を "high" に設定しようと試みます（psutil による、権限不足時は警告で継続）。

- 実行エンジン（ExecutionEngine）
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に分離して記録します。
  - ブローカークライアント生成 → 依存コンポーネント組立て → 実セッション実行の流れです。
  - 起動時に PID ファイルを書き、kill.flag のチェック等を行う設計になっています（Settings に各パス設定あり）。

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  オプション:
  --from, --to: YYYY-MM-DD 形式の日付範囲
  --db: SQLite DB ファイルパス（PAPER_TRADING_SQLITE_PATH を上書き可能）
  出力: 稼働率、注文成功率、送信率、P95 レイテンシ等のサマリと PASS/FAIL 判定

- Streamlit 監視ダッシュボード
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用で監視用 SQLite に接続してダッシュボードを表示します。

- AI 機能（ニュース NLP / レジーム判定）
  - kabusys.ai.score_news (news_nlp.score_news): DuckDB の raw_news / news_symbols を参照して ai_scores に書き込み。OPENAI_API_KEY 必須。
  - kabusys.ai.regime_detector.score_regime: ETF 1321 の MA200 乖離とマクロニュースの LLM センチメントから market_regime を作成。OPENAI_API_KEY 必須。
  - 両者は OpenAI API へバッチ送信やリトライロジックを備えています。API キーが未設定の場合は ValueError。

設定のポイント / 注意事項
- KABUSYS_ENV の有効値: development / paper_trading / live。Settings.env で検証されます。
- Paper Trading: paper_trading 環境ではブローカー呼び出しがモックされ、DB も paper_trading 専用となります（本番 DB と完全分離）。
- 監視 DB 初期化: init_monitoring_db() により必要テーブルと簡易マイグレーションを行います（冪等）。
- kill.flag: KillSwitch はデータベースの RiskMonitor 等の結果からフラグファイルを書いて ExecutionEngine に停止シグナルを送ります。既存ファイルは上書きしません。
- プロセス優先度: set_process_priority("high") を呼びますが、OS/権限により成功しない場合があります（警告ログ）。
- .env 自動ロード: プロジェクトルートを .git または pyproject.toml で検出して .env/.env.local を読み込みます。OS 環境変数は保護されます。

ディレクトリ構成（抜粋）
-------------------
src/kabusys/
- __init__.py                — パッケージ定義、__version__
- config.py                  — Settings: 環境変数/.env 読み込みと検証
- run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py           — ExecutionEngine 起動スクリプト

- ai/
  - __init__.py
  - news_nlp.py              — ニュース NLP（OpenAI）で ai_scores 書き込み
  - regime_detector.py       — 市場レジーム判定（MA200 + LLM）

- monitoring/
  - __init__.py
  - monitoring_db.py         — SQLite テーブル定義・アクセスラッパー
  - system_monitor.py        — CPU/MEM/DISK、プロセス確認、データ鮮度チェック
  - trade_monitor.py         — 滞留注文 / 約定異常チェック
  - risk_monitor.py          — ドローダウン/ポジション上限監視
  - kill_switch.py           — kill.flag 書き込みユーティリティ
  - alert_manager.py         — LINE プッシュ通知
  - monitoring_engine.py     — 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py   — Streamlit ベースの監視ダッシュボード

- execution/
  - order_manager.py         — 注文フロー（作成・送信・同期）
  - reconciler.py            — 起動時リコンシリエーション（注文・ポジション突合）
  - (その他: broker 接続・order_repository 等がある想定)

- portfolio/
  - __init__.py
  - portfolio_builder.py     — 候補選定・等重/スコア重み
  - risk_adjustment.py       — セクターキャップ・レジーム乗数
  - position_sizing.py       — 株数計算・単元丸め・集計キャップ

- research/
  - __init__.py
  - factor_research.py       — momentum/volatility/value ファクター計算（DuckDB）
  - feature_exploration.py   — 将来リターン・IC・統計サマリ

- tools/
  - __init__.py
  - paper_verification_report.py — Paper Trading の検証レポート生成スクリプト

- utils/
  - __init__.py
  - process_priority.py      — プロセス優先度 / CPU affinity ユーティリティ

運用上のヒント
--------------
- 監視ループ(run_monitoring) は MONITOR_POLL_INTERVAL（秒）で稼働。テスト時に短めに設定すると便利です。
- Paper Trading は実行時に本番 DB に影響を与えないよう専用 DB を使用するため、安全に検証できます。
- OpenAI を使う機能は API 呼び出し数が課金対象になります。batch サイズやトークン上限に注意してください。
- Streamlit は監視 DB を読み取り専用で開きます。MonitoringEngine を止めずに可視化できます。
- .env の取り扱いは慎重に：シークレット（API キー等）は .env をソース管理しないこと。

ライセンス / 貢献
-----------------
この README はコードベースから生成されたドキュメント例です。ライセンス表記・コントリビュート方法はプロジェクトルートに追加してください。

以上。運用やデプロイ、README に追記したい項目（例: systemd ユニット例、Dockerfile、CI 設定等）があれば教えてください。