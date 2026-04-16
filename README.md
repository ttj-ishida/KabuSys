# KabuSys

日本株自動売買システムの実装（部分）。このリポジトリは以下の主要コンポーネントを含みます：取引実行エンジン、監視（Monitoring）、ポートフォリオ構築ロジック、リサーチ/ファクター計算、AI を使ったニュース NLP、ユーティリティ等。

## プロジェクト概要
KabuSys は日本株の自動売買に必要な以下の機能を提供します（実装の一部が含まれます）：
- ExecutionEngine：ブローカーとやり取りして注文を管理・発注するエンジン（本番・ペーパートレードに対応）
- Monitoring：CPU/メモリ/ディスク/プロセス状態や注文状態を定期的に記録・監視し、アラートやキルスイッチで安全停止を行う仕組み
- Portfolio construction：候補銘柄選定、重み計算、ポジションサイジング、セクター制限などの純粋関数群
- Research：DuckDB 上の価格・財務データを用いたファクター計算・特徴量解析
- AI（news_nlp / regime_detector）：OpenAI を利用したニュースのセンチメントや市場レジーム判定
- ツール類：Paper Trading 検証レポート生成、Streamlit ダッシュボードなど
- 設定管理：.env 自動読み込み・Settings クラスによる環境変数管理

## 主な機能一覧
- 実行（run_execution.py）
  - KABUSYS_ENV により paper_trading（MockBroker）／live（実ブローカー）を切替
  - paper_trading は data/paper_trading.db に記録して本番 DB と分離
  - 起動時に優先度設定や自動リコンシリエーションを実行
- 監視（run_monitoring.py / MonitoringEngine）
  - システム状態（CPU/メモリ/ディスク）、プロセス存在、データ鮮度を定期記録
  - 注文滞留・約定異常・ドローダウン／ポジション上限を監視
  - KillSwitch による flag ファイルで ExecutionEngine を停止可能
  - LINE へのプッシュ通知（AlertManager）対応
  - Streamlit ダッシュボード（streamlit_dashboard.py）
- ポートフォリオ
  - 候補選定（select_candidates）
  - 重み付け（等金額 / スコア加重）
  - セクター制限適用（apply_sector_cap）
  - ポジションサイズ計算（calc_position_sizes）
- リサーチ
  - モメンタム / ボラティリティ / バリュー等ファクター計算（DuckDB）
  - 将来リターン・IC 計算、統計サマリー
- AI（ニュース NLP / レジーム判定）
  - OpenAI（gpt-4o-mini）を用いニュースセンチメントを算出・ai_scores に格納
  - マクロニュースと ETF MA 乖離の合成で市場レジームを判定し market_regime に保存
- ツール
  - paper_verification_report：Paper Trading データから運用検証レポートを生成

## セットアップ手順（開発環境向け）
1. リポジトリをクローンし、プロジェクトルートに移動
2. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール
   - pip install -r requirements.txt
   ※ requirements.txt がない場合、少なくとも以下を入れてください：
     - duckdb
     - psutil
     - openai
     - requests
     - streamlit
4. 環境変数（.env）を用意
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）
   - 主要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
     - KABU_API_PASSWORD: kabuステーション用パスワード（必須）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - PAPER_FILL_MODE: paper_trading の約定モード（instant|partial|never|reject）
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 時の DB）
     - SQLITE_PATH: data/monitoring.db（監視用 SQLite、デフォルト）
     - DUCKDB_PATH: data/kabusys.duckdb（DuckDB ファイル）
     - PID_FILE_PATH, KILL_FLAG_PATH, LOG_LEVEL, MONITOR_POLL_INTERVAL, 各閾値（CPU/MEM/DISK）など
5. データディレクトリを作成
   - mkdir -p data

注意: 一部機能は外部 API キーや DuckDB 内のテーブル（prices_daily, raw_financials, raw_news など）を前提にしています。必要なデータの用意が必要です。

## 使い方（よく使うコマンド）
- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可。デフォルト 60 秒。
  - 監視は実行環境にかかわらず Settings.sqlite_path（本番 DB）を使用します。
  - 停止は data/stop_requested.flag を作成するか Ctrl+C（KeyboardInterrupt）。
- 実行エンジンを起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い data/paper_trading.db に書き込みます。
  - 起動前に data/stop_requested.flag が存在すると起動せずに終了します。
  - 実行中に停止させたい場合は data/stop_requested.flag を作成するとエンジンが停止します。
- Streamlit ダッシュボード（監視）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（デフォルトは data/paper_trading.db または PAPER_TRADING_SQLITE_PATH 環境変数）
- AI 機能（プログラム的呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - いずれも api_key を直接渡すか環境変数 OPENAI_API_KEY を設定してください。

運用上の注意
- kill.flag（Settings.kill_flag_path）:
  - KillSwitch は特定条件（ドローダウンやポジション上限）で flag を書き、ExecutionEngine 停止を促します。
  - clear は KillSwitch.clear() または flag ファイルを手動削除してください（起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動クリアする挙動に対応する設定があります）。
- pid ファイル:
  - ExecutionEngine は pid ファイルを管理します。stale PID 検出時に監視が PID ファイル除去・リスクログ記録を行います。
- Paper Trading と本番 DB は分離されています（PAPER_TRADING_SQLITE_PATH）。

## 主要な環境変数（抜粋）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- OPENAI_API_KEY（AI 機能を使う場合は必須）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 用）
- PID_FILE_PATH（デフォルト: data/execution.pid）
- KILL_FLAG_PATH（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 1 にすると起動時に kill.flag をクリア
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
- MONITOR_POLL_INTERVAL: 監視のポーリング間隔（秒）

## ディレクトリ構成
（src 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / Settings 管理（.env 自動ロード）
  - run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - portfolio/
    - portfolio_builder.py     — 候補選定・重み計算
    - position_sizing.py       — 発注株数計算・リスク制限・単元丸め
    - risk_adjustment.py       — セクター制限・レジーム乗数
  - research/
    - factor_research.py       — モメンタム・ボラティリティ・バリュー等の計算（DuckDB）
    - feature_exploration.py   — 将来リターン / IC / 統計サマリー
  - ai/
    - news_nlp.py              — ニュースを OpenAI でスコアリングして ai_scores に書込み
    - regime_detector.py       — マクロセンチメント＋ETF MA でレジーム判定
  - monitoring/
    - monitoring_db.py         — SQLite の監視ログ永続化層（テーブル作成・CRUD）
    - system_monitor.py        — システム状態・データ鮮度監視
    - trade_monitor.py         — 注文滞留・約定異常監視
    - risk_monitor.py          — ドローダウン・ポジション上限監視
    - kill_switch.py           — フラグファイルによる停止制御ユーティリティ
    - alert_manager.py         — LINE Push でのアラート送信
    - monitoring_engine.py     — 各 Monitor を束ねるポーリングエンジン
    - streamlit_dashboard.py   — Streamlit ベースの監視ダッシュボード
  - execution/
    - reconciler.py            — 再起動時のリコンシリエーション（注文・ポジション同期）
    - order_manager.py         — 注文の作成・同期・状態遷移管理
    - order_repository.py      — Orders DB 操作（該当ファイルはリポジトリ内にあるはずです）
    - ...                      — ブローカ抽象・実装等
  - utils/
    - process_priority.py      — プロセス優先度 / CPU affinity 設定ユーティリティ
  - data/                      — (運用環境) data/*.db, pid/flag 等が置かれる想定

プロジェクトルート（README 等）
- .env.example                 — 環境変数サンプル（ある場合）
- data/                        — 実行時に使用する SQLite/DuckDB やフラグファイル置き場

## 開発・運用時の補足
- DB マイグレーションは簡易的に monitoring_db.init_monitoring_db が表構造と追加カラムのチェックを行います。
- 実行プロセスは set_process_priority により可能な限り優先度を上げますが、権限不足などで失敗することがあります（ログに警告が残る）。
- AI 関連は OpenAI の料金・レート制限に注意してください。429 等は内部で再試行ロジックを持ちますが、運用ルールを設けてください。
- Paper Trading（検証）は本番 DB と分離されるよう設計されています。テスト・検証を行う場合は KABUSYS_ENV=paper_trading を推奨します。

---

この README はコードベース（src ディレクトリ）の現状実装に基づいて作成しています。追加の操作手順や設計ドキュメント（PortfolioConstruction.md / StrategyModel.md 等）があれば、該当箇所に沿って補完してください。必要であれば、README に具体的な .env.example、requirements.txt、運用 runbook を追加するテンプレートを作成します。どの情報を優先して追加しますか？