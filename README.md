# KabuSys — README（日本語）

このリポジトリは日本株自動売買システム「KabuSys」のコードベースです。  
実行エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI（ニュースセンチメント／レジーム判定）などの主要コンポーネントを含みます。

---

## プロジェクト概要
KabuSys は日本株向けの自動売買システムの実験実装です。主な目的は以下です。

- シグナルから注文を作成してブローカーへ発注（実口座 / ペーパートレードを切替可能）
- 実行状況・システム状態の継続的監視（監視ログは SQLite に永続化）
- リスク管理（ドローダウン監視、ポジション上限等）と自動停止（Kill Switch）
- ポートフォリオ構築（候補選定・重み算出・株数決定）
- リサーチ用ファクター計算（DuckDB 経由でファクターや将来リターンを算出）
- ニュースを用いた LLM（OpenAI）ベースのセンチメント評価とレジーム判定
- 検証ツール（paper trading 検証レポート）、Streamlit ダッシュボード

---

## 機能一覧
- Execution
  - 実取引 / ペーパートレード切替（KABUSYS_ENV）
  - リコンシリエーション（再起動後の自動同期）
  - リスク管理（RiskManager）
- Monitoring
  - SystemMonitor（CPU/メモリ/ディスク/データ鮮度/プロセス監視）
  - TradeMonitor（滞留注文・約定異常監視）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（閾値超過時に停止フラグ書き込み）
  - AlertManager（LINE Push による通知）
  - Streamlit ダッシュボード（監視データ閲覧）
- Portfolio
  - 候補選定（score / rank ベース）
  - 重み付け（等分 / スコア加重）
  - ポジションサイズ計算（リスクベース、利用可能現金考慮、単元丸め）
  - セクター上限・レジーム乗数適用
- Research
  - ファクター計算（momentum, volatility, value 等）
  - 将来リターン / IC / 統計サマリ
- AI
  - news_nlp: raw_news を LLM（OpenAI）でセンチメント化 → ai_scores へ書込
  - regime_detector: ma200 + マクロニュースで市場レジーム判定
- Tools
  - paper_verification_report: Paper Trading 用検証レポート生成
  - streamlit_dashboard: 監視ダッシュボード起動スクリプト

---

## セットアップ手順（開発環境）
前提
- Python 3.10 以上（型ヒントや union 型記法に依存）
- SQLite（標準ライブラリ）
- DuckDB（pip インストール）
- OpenAI SDK（AI 機能を使用する場合）
- psutil, requests, streamlit（オプション：監視や UI）

例（仮想環境作成 + 必要パッケージインストール）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb psutil openai requests streamlit
```

※プロジェクトに requirements.txt がある場合は `pip install -r requirements.txt` を推奨します。

データディレクトリ作成:
```bash
mkdir -p data
```

環境変数（最低限必要なもの）
- JQUANTS_REFRESH_TOKEN — J-Quants API（使用する場合）
- KABU_API_PASSWORD — kabuステーション API パスワード（実トレード時必須）
- OPENAI_API_KEY — OpenAI を使う機能（news_nlp / regime_detector）を使う場合
- KABUSYS_ENV — 起動環境: development | paper_trading | live （デフォルト: development）
- その他（任意）
  - LOG_LEVEL (DEBUG|INFO|...)
  - PAPER_FILL_MODE (instant|partial|never|reject)
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB パス）
  - DUCKDB_PATH / SQLITE_PATH（デフォルト: data/kabusys.duckdb / data/monitoring.db）

.env について
- リポジトリルートに .env / .env.local を置くと自動読み込みされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
- 自動読み込みは .git または pyproject.toml を基準にプロジェクトルートを探索します。

例（.env）:
```
KABUSYS_ENV=paper_trading
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_password
JQUANTS_REFRESH_TOKEN=...
PAPER_FILL_MODE=instant
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
```

---

## 実行方法（代表的なコマンド）
- 監視ループ起動（Monitoring）
```bash
python -m kabusys.run_monitoring
# ポーリング間隔を変更する場合:
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```
- 実行エンジン起動（ExecutionEngine）
```bash
python -m kabusys.run_execution
# KABUSYS_ENV=paper_trading の場合、paper_trading 用 DB に分離して動作します
KABUSYS_ENV=paper_trading python -m kabusys.run_execution
```
- Streamlit ダッシュボード（監視 DB を読み取り専用で表示）
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
- Paper Trading 検証レポート
```bash
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB を指定する場合:
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```

停止方法 / フラグ
- 手動停止（run_monitoring/run_execution ループ）:
  - データディレクトリに stop_requested.flag を作成するとループが検知して終了します（スクリプト内で参照）。
- Kill Switch による停止:
  - KillSwitch が条件を満たすと data/kill.flag を書き込み、ExecutionEngine に停止信号を送る設計です。
  - Settings.kill_flag_clear_on_start が有効だと起動時にフラグをクリアできます。

ログ / PID
- ExecutionEngine は PID ファイル（デフォルト data/execution.pid）を出します。SystemMonitor はこの PID を見てプロセス存否を監視します。

注意事項
- run_monitoring は「監視用 DB（SQLITE_PATH）」を環境に関係なく使用します（常に本番 sqlite_path を参照する設計）。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_trading 用 SQLite を使用して本番 DB と分離します。
- OpenAI を利用する機能は API キー必須。失敗時はフォールバックやスキップの実装が多いですが運用時は注意。

---

## 主要モジュールと使い方（短い説明）
- kabusys.config
  - Settings クラスで環境変数をラップ。自動 .env ロード機能あり。
- kabusys.run_monitoring
  - SystemMonitor のポーリングループ起動スクリプト。
  - MONITOR_POLL_INTERVAL で周期変更可（秒）。
- kabusys.run_execution
  - ExecutionEngine の起動スクリプト。paper_trading モードで MockBroker を使用し DB を分離。
- kabusys.monitoring
  - monitoring_db: SQLite スキーマ初期化と CRUD ラッパー（MonitoringDB）
  - system_monitor / trade_monitor / risk_monitor: 監視ロジック
  - kill_switch / alert_manager / monitoring_engine / streamlit_dashboard
- kabusys.execution
  - order_manager, reconciler, execution_engine（主な発注・状態管理ロジック）
- kabusys.portfolio
  - portfolio_builder / position_sizing / risk_adjustment（候補選定〜株数算出）
- kabusys.research
  - factor_research, feature_exploration（DuckDB を使ったファクター計算・統計）
- kabusys.ai
  - news_nlp.score_news(target_date, conn, api_key) — raw_news を LLM で評価して ai_scores に書込
  - regime_detector.score_regime(target_date, conn, api_key) — ma200 + マクロニュースでレジームを判定
- kabusys.tools.paper_verification_report
  - Paper Trading の検証レポート出力（標準出力）

---

## ディレクトリ構成（主要ファイル）
（src/kabusys 以下を抜粋）
- __init__.py — パッケージ定義、バージョン
- config.py — 環境変数 / 設定管理
- run_monitoring.py — 監視ループ起動スクリプト
- run_execution.py — 実行エンジン起動スクリプト

- ai/
  - news_nlp.py — ニュースセンチメント取得（OpenAI）
  - regime_detector.py — 市場レジーム判定（ma200 + マクロニュース + OpenAI）

- monitoring/
  - monitoring_db.py — SQLite スキーマ・MonitoringDB
  - system_monitor.py, trade_monitor.py, risk_monitor.py — 各種監視ロジック
  - kill_switch.py — 停止フラグ管理
  - alert_manager.py — LINE push API 連携
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py — Streamlit ベースの UI
- execution/
  - order_manager.py, reconciler.py, ... — 発注・同期・再起動復旧ロジック
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py — ポートフォリオ構築ロジック
- research/
  - factor_research.py, feature_exploration.py — ファクター計算・分析
- tools/
  - paper_verification_report.py — Paper Trading 用レポート

---

## 運用上のヒント / 注意
- 本番運用時は KABUSYS_ENV=live を設定し、適切な KABU_API_PASSWORD をセットしてください。
- Paper Trading モードは本番 DB と明示的に分離します（PAPER_TRADING_SQLITE_PATH）。
- OpenAI API 呼び出しはコストとレイテンシが発生します。API キーとレート制限に注意してください。
- ファイルロックや PID 管理、データベースのバックアップ・保全は運用時に必須です。
- 監視周りは冪等性を意識した作りになっていますが、本番移行前にローカルで動作確認（monitoring + streamlit）を行ってください。

---

この README はコードベースから主な設計・使い方をまとめたものです。必要があれば具体的なコマンド例や .env.example のテンプレート、requirements.txt の作成を追記できます。どの情報を詳細化したいか教えてください。