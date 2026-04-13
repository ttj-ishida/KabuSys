README
======

概要
----
KabuSys は日本株の自動売買とモニタリングに関するユーティリティ群を集めた Python パッケージです。本リポジトリは以下の主要機能群を含みます。

- 注文実行エンジン（ExecutionEngine）の起動スクリプトと補助モジュール
- モニタリング（システム状態・注文監視・リスク監視）とダッシュボード
- ポートフォリオ構築アルゴリズム（候補選定・重み計算・ポジションサイズ計算など）
- 研究用モジュール（ファクター計算・特徴量探索）
- AI 連携モジュール（ニュースセンチメントによるスコアリング、レジーム判定）
- 付帯ツール（Paper Trading 検証レポート生成など）

主要な設計方針として、DB（SQLite / DuckDB）をデータ永続化に用い、外部 API 呼び出し（ブローカー・OpenAI 等）は抽象化して使えるようになっています。設定は環境変数 / .env ファイルで行います。

主な機能一覧
-------------
- run_execution.py: ExecutionEngine を起動して発注処理を行う（KABUSYS_ENV により paper_trading と本番を切替）
- run_monitoring.py: SystemMonitor をポーリングして system_status / risk_logs / trade_logs 等を蓄積
- monitoring:
  - SystemMonitor: CPU / メモリ / ディスク・プロセス生存・データ鮮度チェック
  - TradeMonitor: 注文滞留・約定異常価格の検出
  - RiskMonitor: ドローダウン・ポジション上限の監視とダッシュボード更新
  - AlertManager: LINE によるプッシュ通知（任意）
  - KillSwitch: 条件に応じて kill.flag を書いて ExecutionEngine 停止を指示
  - streamlit_dashboard.py: Streamlit を使った監視ダッシュボード
- portfolio:
  - 候補選定(select_candidates)、重み計算(calc_equal_weights、calc_score_weights)
  - リスク調整(apply_sector_cap、calc_regime_multiplier)
  - 発注株数決定(calc_position_sizes)
- research:
  - ファクター計算(calc_momentum / calc_volatility / calc_value)
  - 特徴量探索・IC・統計サマリー（calc_forward_returns / calc_ic / factor_summary 等）
- ai:
  - news_nlp.score_news: raw_news を OpenAI に送って銘柄ごとのセンチメントを ai_scores に書き込む
  - regime_detector.score_regime: ETF とマクロニュースを元に市場レジームを判定して保存
- tools:
  - paper_verification_report: Paper Trading の検証レポートを SQLite DB から生成

セットアップ手順
----------------
前提
- Python 3.10 以上（型注釈で | を使用しているため）
- SQLite は標準ライブラリで利用可能
- 推奨パッケージ（主要なもの）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボードを使用する場合）

例: 仮想環境の作成とパッケージインストール
- 仮想環境作成・有効化（例）
  - python -m venv .venv
  - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
- 必要パッケージをインストール
  - pip install duckdb psutil requests openai streamlit

設定 (.env)
- プロジェクトルートに .env または .env.local を置くと自動読み込みされます（OS 環境変数が優先、.env.local は上書き）。
- 自動読み込みを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主な環境変数（抜粋）
- KABUSYS_ENV: 起動環境（development / paper_trading / live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須な箇所あり）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須な箇所あり）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知を使う場合
- SQLITE_PATH: monitoring DB パス（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時の模擬約定モード（instant/partial/never/reject）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
- PID_FILE_PATH, KILL_FLAG_PATH 等（監視・停止機能に利用）

初期 DB 作成
- run_execution/run_monitoring は起動時に init_monitoring_db を呼び、必要なテーブルを冪等に作成します。したがって特別なマイグレーションは手動で行う必要は通常ありません。

使い方
------
1) 実行 (ExecutionEngine)
- Paper trading（モックブローカー）で実行（例）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - Paper trading の場合、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録され、本番 DB と分離されます。
- 本番想定実行:
  - KABUSYS_ENV=live python -m kabusys.run_execution
  - 実際のブローカークライアントが設定されていることを前提とします（環境変数等を設定）。

2) モニタリング起動
- ポーリングループを起動（デフォルト 60 秒間隔、MONITOR_POLL_INTERVAL で上書き）:
  - python -m kabusys.run_monitoring
- 監視は常に本番用の sqlite_path（Settings.sqlite_path）を用います（KABUSYS_ENV に依らず）。

3) Streamlit ダッシュボード（監視表示）
- 起動例（読み取り専用で DB を開く）:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- ブラウザでダッシュボードを表示します。

4) Paper Trading 検証レポート
- コマンドラインからレポートを生成:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db。--db オプションでパス上書き可能。

5) AI モジュールの利用（ライブラリ呼び出し）
- news_nlp.score_news(conn, target_date, api_key=...)
- regime_detector.score_regime(conn, target_date, api_key=...)
- どちらも OpenAI API キーが必要。API 呼び出しはリトライやフェイルセーフが組み込まれており、部分失敗時も安全に動作する設計です。

注意点
- .env の読み込み順: OS 環境変数 > .env.local > .env
- MONITORINGDB の初期化関数 init_monitoring_db は冪等です。既存スキーマにない列があれば追加マイグレーションを試みます。
- Process priority: 起動時にプロセス優先度を "high" に設定する処理が実行されます（set_process_priority）。権限不足の場合は警告が出るだけで続行します。
- kill.flag: KillSwitch はファイル（デフォルト data/kill.flag）に理由を書き込み、ExecutionEngine 停止を指示します。clear() で削除できます。

ディレクトリ構成
----------------
src/kabusys/
- __init__.py
- config.py
  - Settings クラス: 環境変数 / .env 読み込み・プロパティ管理
- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading 切替あり）
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト

src/kabusys/ai/
- news_nlp.py          — ニュースの LLM センチメント取得・ai_scores 書込
- regime_detector.py   — 市場レジーム判定（ETF MA + マクロセンチメント）

src/kabusys/monitoring/
- monitoring_db.py     — SQLite テーブル定義・読み書き API（MonitoringDB）
- system_monitor.py    — システム状態・データ鮮度チェック
- trade_monitor.py     — 注文滞留 / 約定異常チェック
- risk_monitor.py      — ドローダウン / ポジション上限監視
- kill_switch.py       — kill.flag 管理
- alert_manager.py     — LINE プッシュ通知
- monitoring_engine.py — 複数モニタの束ね・ポーリング制御
- streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード

src/kabusys/execution/
- order_manager.py
- reconciler.py
- order_repository.py, ...（発注・同期周りのモジュール群）※一部省略（コードベースに実装あり）

src/kabusys/portfolio/
- portfolio_builder.py  — 候補選定・重み計算
- position_sizing.py    — 株数計算・スケールダウンロジック
- risk_adjustment.py    — セクター上限・レジーム乗数

src/kabusys/research/
- factor_research.py    — ファクター計算（momentum/volatility/value）
- feature_exploration.py — 将来リターン / IC / 統計サマリー

src/kabusys/tools/
- paper_verification_report.py — Paper Trading 検証レポート生成

src/kabusys/utils/
- process_priority.py   — プロセス優先度 / CPU affinity ユーティリティ

補足（運用上のヒント）
--------------------
- Paper Trading 用 DB は settings.is_paper が True の場合に専用ファイル (PAPER_TRADING_SQLITE_PATH) を使用します。これにより実運用 DB と完全に分離できます。
- AI 関連処理は API 呼び出しでコスト・レート制限が発生するため、バッチサイズや文字数トリミングなどの保護機構が実装されています。
- 監視・アラートは発生頻度でクールダウンを設け、同一事象のスパム通知を抑制します（AlertManager）。

ライセンス / 貢献
-----------------
この README はコードベースに基づく簡易ドキュメントです。実際のライセンスや貢献ルールはプロジェクトのトップレベルの LICENSE / CONTRIBUTING ファイルに従ってください。

以上。追加で「使い方の具体的な例」や「環境変数の .env.example」などを作成したい場合は教えてください。