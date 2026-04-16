# KabuSys

日本株自動売買システムのミニマル実装コレクション（参考実装）。  
このリポジトリはトレード実行エンジン、監視コンポーネント、リサーチ・ポートフォリオ構築・AI 支援モジュールなどを含みます。

---

## プロジェクト概要

KabuSys は以下を目的としたコンポーネント群を含むパッケージです。

- Execution：発注・注文状態管理・リコンサイル（再起動後の自動復旧）
- Monitoring：システム稼働状況、注文滞留、リスク（ドローダウン・ポジション上限）監視、アラート送信（LINE）
- Research / Portfolio：DuckDB を用いたファクター計算・特徴量解析、候補銘柄選定、配分・ポジションサイズ計算
- AI：ニュースセンチメント（OpenAI）を用いた銘柄スコアリング、マクロ・レジーム判定
- Tools：Paper Trading 向け検証レポート生成、Streamlit ダッシュボードなど
- Utils：プロセス優先度設定等のユーティリティ

設計上のポイント：
- DuckDB（価格・ファイナンスデータ）、SQLite（監視ログ・Paper Trading DB）をデータ層に利用
- 環境による挙動切替（`KABUSYS_ENV`）をサポート：`development` / `paper_trading` / `live`
- Paper Trading は本番 DB と分離し、MockBroker を用いる（`paper_trading` 環境）

---

## 主な機能一覧

- Execution
  - 発注フロー（OrderManager / OrderRepository）
  - 起動時の Reconciler による自動復旧
  - RiskManager（発注前の各種制約チェック）
- Monitoring
  - SystemMonitor：CPU・メモリ・ディスク・プロセス状態・データ鮮度監視
  - TradeMonitor：滞留注文・約定価格異常検出
  - RiskMonitor：ドローダウン・ポジション上限監視
  - KillSwitch：フラグファイルによるエンジン停止シグナル
  - AlertManager：LINE Push による通知（クールダウン管理）
  - Streamlit ダッシュボード（監視データ閲覧）
- Research / Portfolio
  - ファクター計算（モメンタム・ボラティリティ・バリュー）
  - 将来リターン計算、IC 計算、統計サマリ
  - 候補選定 / ウェイト計算 / セクター制約 / ポジションサイズ計算
- AI
  - ニュース記事を OpenAI でスコアリング → ai_scores 書き込み
  - マクロニュース + MA200 による市場レジーム判定（market_regime 書き込み）
- Tools
  - Paper Trading 検証レポート（期間指定可能）
  - Streamlit ダッシュボード

---

## 動作要件（主な依存パッケージ）

- Python 3.9+
- duckdb
- psutil
- requests
- openai
- streamlit（ダッシュボード利用時）
- sqlite3（標準モジュール）
- その他（logging 等標準ライブラリ）

（requirements.txt は含まれていないため、必要パッケージを手動でインストールしてください。）

例：
pip install duckdb psutil requests openai streamlit

---

## セットアップ手順（ローカル例）

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit

4. data ディレクトリ作成
   - mkdir -p data

5. 環境変数を設定（.env をルートに置くことを推奨）
   - 必須（実行内容による）
     - JQUANTS_REFRESH_TOKEN（J-Quants API を使う場合）
     - KABU_API_PASSWORD（kabuステーション API を使う場合）
   - OpenAI を使う機能を利用する場合
     - OPENAI_API_KEY
   - オプション
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - PID_FILE_PATH, KILL_FLAG_PATH, LOG_LEVEL, PAPER_FILL_MODE など

   .env 読み込みは自動で行われます（プロジェクトルートが .git または pyproject.toml を含む場合）。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

## よく使う環境変数（抜粋）

- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須の場合）
- KABU_API_PASSWORD: kabu API パスワード（実ブローカー利用時）
- OPENAI_API_KEY: OpenAI API キー（AI コンポーネント利用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading での約定モード（instant|partial|never|reject）

---

## 実行方法・使い方

各コンポーネントはパッケージモジュールとして起動します。ルートで実行してください（src 配下にパッケージがある想定）。

1. Execution Engine（トレード実行）
   - 本番/開発/紙の切替：
     - KABUSYS_ENV=paper_trading を設定すると MockBroker を使い data/paper_trading.db に記録します。
   - 実行：
     - python -m kabusys.run_execution
   - 停止方法：
     - data/stop_requested.flag を作成すると安全に停止します（または kill.flag により停止指示を出す管理フローあり）。

2. Monitoring（監視ループ）
   - 説明：
     - 実行プロセスの稼働・リソース・データ鮮度・注文状況を定期的に記録し、risk_events や kill flag を管理します。
     - monitoring は KABUSYS_ENV にかかわらず本番の sqlite_path を使用する設計（run_monitoring.py の仕様）。
   - 実行：
     - python -m kabusys.run_monitoring
   - ポーリング間隔変更：
     - 環境変数 MONITOR_POLL_INTERVAL=<秒>（デフォルト 60）
   - 停止方法：
     - data/stop_requested.flag を作成すると監視ループが終了します。

3. Streamlit ダッシュボード（監視可視化）
   - 起動：
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
     - または --db オプションで DB パスを指定
   - DB を読み取り専用で開きます（存在しない場合はエラーメッセージが出ます）。

4. Paper Trading 検証レポート
   - 使い方：
     - python -m kabusys.tools.paper_verification_report
     - 期間指定例：
       - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - DB パス指定：
       - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH
   - 出力内容：
     - システム稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）、リスク却下数、PASS/FAIL 判定など

5. AI 関連（ニューススコアリング / レジーム判定）
   - OpenAI API キーが必要（OPENAI_API_KEY）
   - メソッドを直接呼び出して使用：
     - kabusys.ai.score_news(conn, target_date, api_key=None)
     - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
   - 実行は DuckDB 接続（prices_daily / raw_news 等が事前にロード済み）を渡す想定。

---

## 制御フラグ・ファイル

- data/stop_requested.flag
  - 実行スクリプト（run_execution.py, run_monitoring.py）がこのファイルの存在をチェックし、存在すれば安全に終了します。

- data/kill.flag
  - KillSwitch が書き込むファイル。ExecutionEngine に止めるべき重大事象が発生した際に作成される。存在している場合、Execution の起動を拒否したり停止操作をトリガーします。

- PID ファイル
  - data/execution.pid（デフォルト）に ExecutionEngine のプロセス PID を書き、SystemMonitor が存在確認を行います。stale PID の検出・削除ロジックあり。

---

## 開発者向けメモ

- 設計は「DB を直接編集・参照する」より「明確な API を通して操作する」方針を採用しています（MonitoringDB / OrderRepository 等）。
- DuckDB を用いるリサーチ系は SQL と Python を組み合わせており、外部 ML ライブラリに依存していません。
- OpenAI の呼び出しはリトライ・バックオフを備えており、失敗時はフォールバック（0.0）や部分的スキップを行ってシステムの継続性を維持します。
- process priority / cpu affinity 等は psutil によってプラットフォーム差分を吸収するユーティリティを提供しています（権限不足時は警告ログでスキップ）。

---

## ディレクトリ構成

（src/kabusys 配下を中心に抜粋）

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数/.env のロードと Settings クラス
  - run_execution.py                  — ExecutionEngine 起動スクリプト
  - run_monitoring.py                 — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py    — Paper Trading 検証レポート CLI
  - execution/
    - order_manager.py
    - order_repository.py
    - execution_engine.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
    - order_record.py
    - order_repository.py
    - ... (その他発注関連)
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
    - streamlit_dashboard.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - utils/
    - process_priority.py
    - __init__.py
  - data/  (実行時に使用する DB / フラグファイルなど)
    - monitoring.db (default SQLITE_PATH)
    - kabusys.duckdb (default DUCKDB_PATH)
    - paper_trading.db (paper trading 用)
    - kill.flag / stop_requested.flag / execution.pid

---

## よくある運用フロー（例）

1. DuckDB に価格データや raw_news をロード（外部スクリプトや ETL を想定）。
2. KABUSYS_ENV=paper_trading で run_execution を起動しアルゴリズムの動作確認（MockBroker で注文を記録）。
3. run_monitoring を別プロセスで起動してシステム稼働・注文ログ・リスクを監視。
4. Streamlit で監視ダッシュボードを確認。
5. Paper Trading の結果を tools.paper_verification_report で解析し PASS/FAIL 判定。

---

## ライセンス / 注意事項

- 本リポジトリは教育・研究用の参考実装です。実運用する場合は法規制・ブローカー仕様・安全対策（例: 資金管理、失敗時のフェイルセーフ、テスト）を十分に検討してください。
- 実運用での利用は自己責任です。実ブローカー接続（kabu API 等）を行う際はテスト環境での検証を必ず実施してください。

---

不明点や README に追記してほしい項目があれば教えてください。必要に応じて実行例や .env.example の雛形も作成します。