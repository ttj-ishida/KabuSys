# KabuSys

KabuSys は日本株自動売買システムのコアライブラリ群です。  
ポートフォリオ構築、発注・再構成（reconciliation）、監視（Monitoring）、研究用ファクター計算、ニュース NLP（LLM）連携などのコンポーネントを含みます。

概要、機能、セットアップ、使い方、ディレクトリ構成を以下にまとめます。

---

## プロジェクト概要

- 設計方針
  - 発注（Execution）と監視（Monitoring）を分離して実行可能。
  - DuckDB / SQLite を使ったオンプレミスでのデータ管理。
  - Paper trading 環境をサポート（本番 DB と分離）。
  - LLM（OpenAI）を用いたニュースセンチメント評価や市場レジーム判定機能を備える。
  - フェイルセーフ（APIエラーのリトライ、部分書き込みで既存データ保護等）を意識した実装。

- 主要技術
  - Python 3.10+
  - duckdb, sqlite3, psutil, requests, openai, streamlit など

---

## 主な機能一覧

- Execution（発注実行）
  - OrderManager / ExecutionEngine による発注ワークフロー
  - Broker クライアント抽象（本番・Mock を切替）
  - Reconciler による起動時の自動同期（OrderSent の突合、ポジション差分検出）
  - RiskManager によるリスク制限（例: ポジション上限・ドローダウン）

- Monitoring（監視）
  - SystemMonitor：CPU / メモリ / ディスク / プロセス存在確認、データ鮮度チェック
  - TradeMonitor：滞留注文（stale orders）や約定異常（価格乖離）検出
  - RiskMonitor：ドローダウン・ポジション上限の監視、ダッシュボード更新
  - KillSwitch：条件に応じてフラグファイルを書き、Execution を停止させる仕組み
  - AlertManager：LINE Messaging API を使ったアラート送信（クールダウン管理）
  - Streamlit ダッシュボード（監視データの可視化）

- Portfolio（銘柄選定・配分）
  - 候補選定（スコア順ソート）
  - 等金額 / スコア加重 / リスクベースのウェイト計算
  - セクター上限適用、レジーム乗数（bull/neutral/bear）
  - 発注株数（単元丸め、aggregate cap）計算

- Research（研究用）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー

- AI（LLM）統合
  - news_nlp: raw_news を集約し OpenAI に投げて銘柄別センチメントを ai_scores に格納
  - regime_detector: ETF ma200 乖離 + マクロニュースを LLM で評価して市場レジーム判定
  - 再試行や部分失敗時の保護ロジックあり

- ツール
  - paper_verification_report: Paper Trading DB から検証レポート（稼働率 / 注文成功率 / レイテンシ等）を生成
  - streamlit_dashboard: 監視 DB を可視化するダッシュボード

---

## セットアップ手順

前提：
- Python 3.10 以上を推奨

1. リポジトリをクローン / ソース配置
2. 必要パッケージをインストール（例）
   - pip install duckdb psutil requests openai streamlit
   - （開発用に）pip install -r requirements.txt があればそれを使用
3. 環境変数の設定
   - .env（または .env.local）をプロジェクトルートに置くと自動で読み込まれます（自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。
   - 主要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN —（必須）J-Quants API トークン
     - KABU_API_PASSWORD —（必須）kabuステーション API パスワード
     - OPENAI_API_KEY —（LLM 機能を使う場合必須）
     - KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト: development）
     - PAPER_FILL_MODE — paper_trading の約定動作（"instant"|"partial"|"never"|"reject"、デフォルト: "instant"）
     - SQLITE_PATH、DUCKDB_PATH、PAPER_TRADING_SQLITE_PATH 等（デフォルトは data/ 以下）
   - 環境変数に関する詳細は kabusys.config.Settings を参照してください。未設定の必須値は起動時に例外が出ます。
4. データディレクトリの作成
   - デフォルトで data/ 以下に DB や pid/flag ファイルが作成されます。書き込み権限を確認してください。

---

## 使い方（実行例）

- ExecutionEngine を起動（本番 or paper_trading を自動判定）
  - KABUSYS_ENV を設定して（例えば paper_trading）：
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
  - 挙動
    - 起動時にプロセス優先度を "high" に設定し、SQLite / DuckDB に接続
    - paper_trading の場合は MockBroker を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用

- Monitoring を起動（ポーリング）
  - python -m kabusys.run_monitoring
  - オプション: 環境変数でポーリング間隔を変更
    - export MONITOR_POLL_INTERVAL=30  # 秒（1 以上）
  - 注意: Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用します（監視は本番 DB を観測する想定）

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または DB パスを明示:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（プログラムから呼ぶ）
  - ニューススコア取得:
    - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key="...")  # conn は duckdb 接続オブジェクト
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key="...")

---

## 主要設定（抜粋）

- 自動 .env ロード
  - プロジェクトルート（.git / pyproject.toml を基準）にある `.env` / `.env.local` を自動で読み込みます。
  - OS 環境変数が優先され、.env.local は .env を上書きします。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

- KABUSYS_ENV 値
  - development / paper_trading / live のいずれか。無効値は例外。

- MONITOR_POLL_INTERVAL
  - run_monitoring でポーリング間隔を上書き可能（秒）。1 未満の値は無効扱いされデフォルト 60 秒にフォールバック。

- Paper Trading
  - KABUSYS_ENV=paper_trading の場合、実行時に MockBroker を使用し DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録され、本番 DB と分離されます。

- Kill switch
  - risk condition（ドローダウン超過等）により data/kill.flag が書き込まれ、Execution の停止を促します。flag の存在をチェックし、起動時に KILL_FLAG_CLEAR_ON_START を使ってクリア動作を制御できます（Settings.kill_flag_clear_on_start）。

---

## ディレクトリ構成（主要ファイル）

（リポジトリの src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / Settings 管理（.env 自動ロード含む）
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト

- src/kabusys/execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py, broker_api.py, ...（発注ロジックとブローカー抽象）
  
- src/kabusys/monitoring/
  - monitoring_db.py  — SQLite スキーマ & 永続化
  - system_monitor.py, trade_monitor.py, risk_monitor.py
  - monitoring_engine.py, kill_switch.py, alert_manager.py
  - streamlit_dashboard.py

- src/kabusys/portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py（ポートフォリオ構築ロジック）

- src/kabusys/research/
  - factor_research.py, feature_exploration.py（ファクター / リサーチ）

- src/kabusys/ai/
  - news_nlp.py, regime_detector.py（LLM を使ったニュース分析・レジーム判定）
  - __init__.py

- src/kabusys/tools/
  - paper_verification_report.py（Paper Trading レポート）

- src/kabusys/utils/
  - process_priority.py（プロセス優先度 / CPU affinity 設定ユーティリティ）

- data/
  - data/kabusys.duckdb（デフォルト DuckDB）
  - data/monitoring.db（SQLite 監視 DB）
  - data/paper_trading.db（Paper trading 用 SQLite）

---

## 運用上の注意・実装上のポイント

- Settings は必須 env 変数が未設定だと ValueError を送出します。起動前に .env を整備してください。
- Monitoring の DB スキーマは init_monitoring_db によって冪等に作成 / マイグレーションされます。
- LLM（OpenAI）を利用する機能は API キー必須。API 呼び出し部はリトライ・バックオフやレスポンス検証を行い、部分失敗時に既存データを保護する実装になっていますが、API利用料とレート制限に注意してください。
- Paper trading モードは本番 DB と完全に分離される設計なので、テスト運用に適しています。
- process priority / CPU affinity の設定はプラットフォームに依存するため、権限不足や未対応 OS の場合は警告を出してスキップします。

---

## 参考コマンドまとめ

- 実行（Execution）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - KABUSYS_ENV=live python -m kabusys.run_execution

- 監視（Monitoring）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

README に記載していない詳細（例: ExecutionEngine の内部設計、OrderRepository のスキーマ、Broker 実装等）はソースコードの docstring / コメントに豊富にあります。必要であれば、特定モジュールの詳細ドキュメント（API リファレンス、シーケンス図、運用手順書）を別途作成します。