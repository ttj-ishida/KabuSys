# KabuSys

KabuSys は日本株向けの自動売買／リサーチ／監視ユーティリティ群です。本リポジトリはトレード実行・監視・ポートフォリオ構築・リサーチ・AI を用いたニュース解析などの機能を提供します。

以下はこのコードベースの概要、主要機能、セットアップ／起動手順、およびディレクトリ構成の説明です。

注意: ここに記載の多くの機能は環境変数で設定します。自動で .env / .env.local を読み込む仕組みがあり（プロジェクトルートが特定できる場合）、テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化できます。

---

## プロジェクト概要

- 日本株自動売買システムのコアライブラリ群（実行エンジン・ブローカー連携・注文管理）
- 実行結果・監視ログの永続化（SQLite）
- データ分析 / ファクター計算（DuckDB を想定）
- Paper Trading（モックブローカー）対応（本番 DB と分離）
- モニタリング（システム状態・注文滞留・リスク監視）およびアラート（LINE）
- OpenAI を用いたニュース NLP と市場レジーム判定
- Streamlit による監視ダッシュボードと検証レポート生成ツール

---

## 主な機能一覧

- Execution
  - ExecutionEngine（起動・セッション管理）
  - ブローカーファクトリ（本番／モック切替）
  - OrderManager / OrderRepository / Reconciler（起動時の復旧・同期）
  - RiskManager：発注前リスクチェック（設定あり）

- Monitoring
  - SystemMonitor：CPU・メモリ・ディスク・データ鮮度・プロセス死活確認
  - TradeMonitor：滞留注文、約定異常（価格）検出
  - RiskMonitor：ドローダウン・ポジション上限などの監視
  - KillSwitch：条件により ExecutionEngine 停止フラグを書き込み（data/kill.flag）
  - AlertManager：LINE Push による通知（クールダウン管理）
  - streamlit_dashboard：監視ダッシュボード（Streamlit）

- Portfolio construction（純粋関数）
  - 銘柄選定（select_candidates）
  - 重み計算（等配分、スコア加重）
  - セクターキャップ適用、レジーム乗数
  - 株数計算（リスクベース・等配分など）、単元株丸め、集約上限調整

- Research
  - factor_research：モメンタム／ボラティリティ／バリュー等のファクター計算（DuckDB）
  - feature_exploration：将来リターン計算、IC（Spearman）などの統計解析

- AI
  - news_nlp.score_news：OpenAI（gpt-4o-mini）でニュースをスコアリングして ai_scores に保存
  - regime_detector.score_regime：ETF の MA200 とマクロニュースを LLM で集成して市場レジーム判定

- Tools
  - paper_verification_report：Paper Trading ログから検証レポート生成（成功率・稼働率・レイテンシ等）

---

## セットアップ手順

前提:
- Python 3.10+（typing 機能などを利用）
- 必要パッケージ（例: psutil, duckdb, requests, streamlit, openai）をインストールしてください。

例（pipenv/venv を利用する場合）:
- 仮想環境を作成して activate
- 必要パッケージをインストール（requirements.txt がある場合はそれを利用）

手動インストール例:
pip install psutil duckdb requests streamlit openai

環境変数:
- .env / .env.local をプロジェクトルートに置くと自動で読み込まれます（既存の OS 環境変数は保護）。
- 自動ロードを無効化する場合:
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

重要な環境変数（一部）:
- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — OpenAI API キー（AI 機能利用時に必須）
- KABUSYS_ENV — 起動環境（development | paper_trading | live）
  - paper_trading の場合は MockBrokerClient を使用し、別 DB（PAPER_TRADING_SQLITE_PATH）に書き込みます
- PAPER_FILL_MODE — Mock の約定挙動（instant | partial | never | reject）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH — 実行 PID / 停止フラグパス
- LOG_LEVEL — ログレベル（DEBUG|INFO|...）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE通知用

DB 初期化:
- run_monitoring.py / run_execution.py は起動時に監視用テーブルを自動作成します（init_monitoring_db を呼びます）。明示的なマイグレーションは不要です。

---

## 使い方（主要コマンド）

リポジトリのルートから以下を実行します（src を PYTHONPATH に含める、またはパッケージとしてインストールしている前提）。

1) 監視ループを起動（SystemMonitor のポーリング）
- デフォルトポーリング間隔: 60 秒
- 環境変数 MONITOR_POLL_INTERVAL で秒数を上書き可能（正の整数）

起動:
python -m kabusys.run_monitoring

例:
export MONITOR_POLL_INTERVAL=30
python -m kabusys.run_monitoring

停止:
- プロジェクトルートの data/stop_requested.flag を作成すると安全に停止します（run_monitoring はこのフラグを検知して終了します）。

2) 実行エンジン（ExecutionEngine）を起動
- KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）に書き込みます。

起動:
python -m kabusys.run_execution

例（Paper Trading）:
export KABUSYS_ENV=paper_trading
export PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
python -m kabusys.run_execution

停止:
- data/stop_requested.flag を作成するとエンジン停止処理が開始されます。
- エンジンは data/execution.pid を作成して自身の PID を管理します。stale PID の検出と自動削除を SystemMonitor が行います。

3) Paper Trading 検証レポート生成
- Paper Trading の SQLite ログから検証用レポートを標準出力に出します。

実行例:
python -m kabusys.tools.paper_verification_report
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

4) Streamlit ダッシュボード
- 監視 DB を read-only モードで表示するダッシュボードです。

実行例:
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

5) AI 機能（ニューススコアリング / レジーム判定）
- OpenAI API キーが必要です（OPENAI_API_KEY）。
- プログラム的に利用する場合:
  - kabusys.ai.score_news(conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

注意:
- OpenAI 呼出しはレート制限・タイムアウト等に対してリトライ実装がありますが、API キー・料金に注意してください。

---

## 実行時の挙動と運用メモ

- プロセス優先度:
  - run_* スクリプトは最初に set_process_priority("high") を呼びます（psutil 経由）。権限がないと警告のみ出てスキップされます。

- 停止フラグ:
  - data/stop_requested.flag を監視して安全にループから抜けます（run_monitoring/run_execution）。

- Kill Switch:
  - RiskMonitor 等の判定により、KillSwitch が data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります。kill.flag は冪等に書き込まれ、必要なら KillSwitch.clear() で削除します。

- DB 分離:
  - paper_trading（模擬環境）では paper_sqlite_path を使用し、本番の monitoring.db と完全分離します。

- 環境変数の自動ロード:
  - プロジェクトルート（.git or pyproject.toml がある場所）を自動検出して .env と .env.local を読み込みます。
  - .env.local は .env の上書きに使用可能（ただし OS 環境変数は保護される）。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下を想定）

- src/kabusys/__init__.py
  - パッケージ定義・バージョン

- src/kabusys/config.py
  - 環境変数の読み込み・Settings クラス（アプリ設定）

- src/kabusys/run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
  - 環境変数: MONITOR_POLL_INTERVAL（秒）

- src/kabusys/run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading モード対応）

- src/kabusys/monitoring/
  - monitoring_db.py — SQLite スキーマ初期化 / MonitoringDB ラッパー
  - system_monitor.py — システム状態・データ鮮度監視
  - trade_monitor.py — 注文滞留・約定異常検出
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag 管理
  - alert_manager.py — LINE push 送信（クールダウン）
  - monitoring_engine.py — Monitor を束ねるループ
  - streamlit_dashboard.py — Streamlit ダッシュボード

- src/kabusys/execution/
  - order_manager.py — 注文作成／状態遷移管理
  - reconciler.py — 起動時の注文・ポジション照合（自動復旧）
  - その他: broker_factory, execution_engine, order_repository など（ブローカー抽象化）

- src/kabusys/portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数計算・リスク調整
  - risk_adjustment.py — セクター上限・レジーム乗数

- src/kabusys/research/
  - factor_research.py — モメンタム・ボラティリティ・バリュー計算（DuckDB）
  - feature_exploration.py — 将来リターン・IC・統計サマリー

- src/kabusys/ai/
  - news_nlp.py — ニュースを LLM でスコアリングして ai_scores に保存
  - regime_detector.py — MA200 とマクロニュースで市場レジーム判定

- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading 検証レポート出力

- src/kabusys/utils/
  - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

---

## 追加の運用上の注意

- DuckDB / SQLite のパスは Settings で指定可能（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）。
- Monitoring の DB スキーマは init_monitoring_db() により自動作成・必要に応じたマイグレーション（列追加）を行います。
- AI 呼び出しでのレスポンスバリデーションやリトライは実装済みですが、LLM 出力の変動に対しては注意が必要です（スコアは ±1.0 にクリップ）。
- LINE 通知は channel token / user id が未設定の場合スキップされます。実運用ではトークン管理に注意してください。
- run_* スクリプトはログを標準出力に出します。systemd 等でサービス化する場合は stdout/stderr の扱いを整えてください。

---

この README はコードベース全体の導入ガイドです。実際のデプロイや運用向けに、.env.example を作成して環境変数の整理、また systemd の unit ファイルやログローテーション、監視体制（外部監視/アラート）を整備することを推奨します。必要ならサンプル .env.example や systemd ユニットのテンプレートも作成しますので、教えてください。