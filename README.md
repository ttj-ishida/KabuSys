README.md

KabuSys — 日本株自動売買システム
==============================

概要
----
KabuSys は日本株の自動売買・研究・監視を行うためのパッケージ群です。本リポジトリは以下の主要機能を持つモジュールで構成されています。

- 実行エンジン（ExecutionEngine）: ブローカーへの発注・注文状態管理・リスク管理を行う
- 監視モジュール（Monitoring）: システム状態や注文状況を定期的にチェックしてアラートや停止判定を行う
- ポートフォリオ構築ロジック（Portfolio）: 候補選定・重み付け・株数計算・セクター制約など
- 研究モジュール（Research）: ファクター計算・特徴量探索・IC 計測など
- AI/自然言語（AI）: ニュースを LLM でスコアリングし市場レジーム判定などに利用
- ツール: Paper Trading 検証レポート生成や Streamlit ダッシュボード

主な設計方針
- DuckDB / SQLite を用いたローカルデータベース中心の処理（外部 API 呼び出しは限定）
- Paper Trading 用 DB は本番 DB と完全分離
- LLM 呼び出しは冪等性・リトライ・フェイルセーフを考慮
- 時刻参照はルックアヘッドバイアスを避ける実装（date 引数等を受け取る）

機能一覧
--------
- 実行（run_execution.py）
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し data/paper_trading.db を利用
  - プロセス優先度設定・PID 管理・停止フラグ監視
  - OrderManager / RiskManager / Reconciler を組み合わせた ExecutionEngine 起動
- 監視（run_monitoring.py / monitoring package）
  - SystemMonitor: CPU/メモリ/ディスク、Execution プロセス PID、データ鮮度チェック
  - TradeMonitor: 滞留注文チェック、約定価格の異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード永続化
  - KillSwitch: 条件を満たしたら data/kill.flag を書き込み ExecutionEngine を停止させる
  - AlertManager: LINE push による通知（トークン未設定時はログのみ）
  - Streamlit ダッシュボード（ストリーミング表示）
- ポートフォリオ（portfolio package）
  - 候補選定、等金額/スコア加重配分、リスク調整（セクターキャップ・レジーム乗数）、株数算出（単元丸め・aggregate cap）
- 研究（research package）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン・IC（Spearman）・統計サマリー
- AI（ai package）
  - ニュースを LLM（OpenAI）でセンチメント評価して ai_scores テーブルへ書き込み
  - 市場レジーム判定（ma200 とマクロニュースの LLM スコアを合成）
- ツール
  - paper_verification_report: Paper Trading DB の検証レポート出力（稼働率/成功率/レイテンシ等）

セットアップ手順
----------------

前提
- Python 3.9+（コード上は最新の typing 機能等を利用）
- SQLite（標準ライブラリ）
- DuckDB（pip install duckdb）

推奨手順（例）
1. リポジトリをクローン、プロジェクトルートへ移動
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（お使いの環境に合わせて）
   - pip install duckdb psutil requests openai streamlit
   - もし依存ファイル（requirements.txt）がある場合は pip install -r requirements.txt
4. 環境変数設定
   - プロジェクトルートに .env または .env.local を配置すると自動的に読み込まれる（OS 環境変数が優先）
   - 自動ロードを無効化する場合: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 必須変数（例）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を利用する場合:
     - OPENAI_API_KEY を設定
   - その他の設定は Settings クラスのプロパティ（config.py）を参照（下記に主要設定を抜粋）

主要な環境変数（デフォルト値は Settings を参照）
- KABUSYS_ENV: development | paper_trading | live (default: development)
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- SQLITE_PATH: data/monitoring.db (監視用 DB)
- DUCKDB_PATH: data/kabusys.duckdb
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- PAPER_FILL_MODE: instant | partial | never | reject (paper_trading 時の約定挙動)
- PID_FILE_PATH: data/execution.pid
- KILL_FLAG_PATH: data/kill.flag
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用、デフォルト 60）

使い方
------

実行エンジン起動（本番 / Paper Trading）
- 本番（例）
  - KABUSYS_ENV=live を設定し、必要な API トークンなどを環境変数に設定してから:
    - python -m kabusys.run_execution
- Paper Trading（Mock ブローカー、DB 分離）
  - KABUSYS_ENV=paper_trading を設定:
    - python -m kabusys.run_execution
  - このモードでは settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用

監視モード起動
- run_monitoring は監視ループを開始して monitoring DB にログを蓄積します:
  - MONITOR_POLL_INTERVAL を環境変数で上書き可能（秒）
  - python -m kabusys.run_monitoring

停止フラグ / Kill Switch
- 手動停止: プロジェクト内の data/stop_requested.flag を作成すると run_monitoring/run_execution は安全に終了します（実装上 stop flag を監視）
- 強制停止トリガー: KillSwitch が条件を満たすと data/kill.flag を書き込み、ExecutionEngine は起動中にこれを検知して停止します
- PID 管理: 実行時に data/execution.pid に PID を書く設計（Settings.pid_file_path）

Paper Trading 検証レポート
- data/paper_trading.db（または --db で指定）から集計・判定を行う CLI ツール:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- 出力: 稼働率・注文成功率・送信率・レイテンシ（P95）・最終判定 PASS/FAIL

Streamlit ダッシュボード
- 監視 DB を読み取り専用で表示する簡易ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

AI 関連
- OpenAI を使う機能（news_nlp.score_news, regime_detector.score_regime）は OPENAI_API_KEY が必要
- LLM 呼び出しはリトライやクリッピングなどの安全策が実装されていますが、API 料金・レート制限には注意してください

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py
- config.py                     — 環境変数/設定管理（.env 自動読込ロジック含む）
- run_execution.py              — ExecutionEngine 起動スクリプト
- run_monitoring.py             — SystemMonitor ポーリングループ起動スクリプト

kabusys/ai/
- news_nlp.py                   — ニュースを LLM でスコアリングして ai_scores に書き込む
- regime_detector.py            — 市場レジーム判定（ma200 + マクロセンチメント）

kabusys/monitoring/
- monitoring_db.py              — SQLite スキーマ初期化 + DB 操作ラッパー
- system_monitor.py             — CPU/メモリ/ディスク/プロセス/データ鮮度監視
- trade_monitor.py              — 注文滞留 / 約定価格異常監視
- risk_monitor.py               — ドローダウン・ポジション上限監視
- kill_switch.py                — kill.flag の作成/削除ロジック
- alert_manager.py              — LINE Push 通知ラッパー
- monitoring_engine.py          — 各モニタを束ねるエンジン
- streamlit_dashboard.py        — Streamlit ダッシュボード

kabusys/execution/
- reconciler.py                 — 起動時の注文・ポジション照合（自動復旧）
- order_manager.py              — 発注・状態遷移の上位 API
- その他（broker_factory, execution_engine, order_repository 等が存在）

kabusys/portfolio/
- portfolio_builder.py          — 候補選定・重み計算
- position_sizing.py            — 株数決定・丸め・aggregate cap
- risk_adjustment.py            — セクター上限・レジーム乗数

kabusys/research/
- factor_research.py            — ファクター計算（momentum, volatility, value）
- feature_exploration.py        — 将来リターン / IC / 統計サマリー

kabusys/tools/
- paper_verification_report.py  — Paper Trading 検証レポート CLI

kabusys/utils/
- process_priority.py           — プロセス優先度・CPU affinity 設定ユーティリティ

データ・フラグファイル（プロジェクトルート）
- data/monitoring.db            — 監視ログ SQLite（デフォルト）
- data/paper_trading.db         — Paper Trading 用 SQLite（paper_trading 時）
- data/kabusys.duckdb           — DuckDB データ
- data/execution.pid            — ExecutionEngine PID（デフォルトパス）
- data/kill.flag                — KillSwitch が書き込む停止フラグ
- data/stop_requested.flag      — run_* スクリプトの停止用フラグ（手動停止用）

実運用上の注意
--------------
- 本番環境（KABUSYS_ENV=live）では API キーやパスワード等の管理に注意してください（.env.local を利用し OS 環境変数を上書き可能）。
- OpenAI API 呼び出しには料金が発生します。エラー時はフェイルセーフ（0.0）で継続する実装ですが、利用方針を事前に決めてください。
- Paper Trading 用 DB は本番 DB と分離されていますが、誤った設定により混在しないよう .env を正しく整備してください。
- process priority / cpu affinity の設定は OS 権限の都合で失敗する場合があります（警告ログでスキップされます）。

追加情報 / 開発メモ
------------------
- Settings（config.py）はプロジェクトルートから .env/.env.local を自動読み込みします。OS 環境変数は保護されます。
- run_monitoring は MONITOR_POLL_INTERVAL によりポーリング間隔を変更可能（デフォルト 60 秒）。0 以下や不正な値はデフォルトにフォールバックします。
- monitoring_db.init_monitoring_db() は既存 DB に対する簡単なマイグレーション（カラム追加等）を行います。
- LLM 関連の内部呼び出し関数はテスト時にモック可能に設計されています（unittest.mock.patch など）。

ライセンス / 貢献
-----------------
- 本リポジトリのライセンス情報はルートの LICENSE を参照してください（存在する場合）。
- バグ報告・改善提案は Issue / PR にてどうぞ。

以上。README に追加してほしい実例（.env.example、実行ログ例、requirements.txt 想定内容など）があれば教えてください。