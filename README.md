# KabuSys

日本株自動売買システムのコンポーネント群（ライブラリ＋実行スクリプト）。  
このリポジトリは戦略の研究・ファクター計算、ポートフォリオ構築、注文実行/リコンシリエーション、監視・アラート、AI を用いたニュースセンチメント評価などを含みます。

## 概要
- DuckDB / SQLite をデータ層に利用し、価格・財務データや監視ログを永続化します。
- ExecutionEngine（発注処理）と MonitoringEngine（監視・アラート）は独立して起動可能。
- Paper Trading（模擬売買）用に本番 DB と分離された設定が可能。
- OpenAI を利用したニュースセンチメント評価・市場レジーム判定モジュールを内包。
- Streamlit ベースの簡易ダッシュボードを提供。

## 主な機能一覧
- 環境管理（.env 自動読み込み / Settings）
- 実行エンジン起動スクリプト（run_execution.py）
  - 実ブローカー / モックブローカー（paper_trading）の切替
  - リスク管理（RiskManager）・オーダー管理・リコンシリエーション
- 監視用ポーリング（run_monitoring.py / MonitoringEngine）
  - システム監視（CPU/メモリ/ディスク、プロセス死活、データ鮮度）
  - 注文監視（滞留注文・約定価格異常）
  - リスク監視（ドローダウン・保有上限）
  - Kill Switch（フラグファイルで ExecutionEngine を安全停止）
  - LINE へのプッシュ通知（AlertManager）
- AI（OpenAI）連携
  - ニュースセンチメント評価（news_nlp.score_news）
  - 市場レジーム判定（regime_detector.score_regime）
- 研究系モジュール
  - ファクター計算（momentum / volatility / value）
  - 将来リターン・IC 計算、統計サマリー
- ポートフォリオ構築
  - 候補選定、重み付け、リスク調整（セクターキャップ・レジーム乗数）
  - ポジションサイズ計算（単元丸め・aggregate cap）
- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
- Streamlit 監視ダッシュボード

## 動作要件（概略）
- Python 3.10+
- 必要パッケージ（例）
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit（ダッシュボード利用時）
- 標準ライブラリ: sqlite3, logging など

例:
pip install duckdb psutil openai requests streamlit

（プロジェクト用の requirements.txt があればそちらを利用してください）

## セットアップ手順

1. リポジトリをクローン / ソースを配置
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb psutil openai requests streamlit
4. データディレクトリを作成
   - mkdir -p data
5. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動読み込みされます（OS 環境変数が優先）。
   - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 重要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN — （必須）
     - KABU_API_PASSWORD — （必須）
     - OPENAI_API_KEY — OpenAI を使用する場合
     - KABUSYS_ENV — 起動環境（development | paper_trading | live）、デフォルト: development
     - PAPER_FILL_MODE — paper_trading の約定挙動（instant|partial|never|reject）、デフォルト: instant
     - PAPER_TRADING_SQLITE_PATH — paper_trading 時の SQLite パス（デフォルト: data/paper_trading.db）
     - SQLITE_PATH — 監視ログ用 SQLite（デフォルト: data/monitoring.db）
     - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用

## 使い方（主要コマンド例）

- 実行（Execution Engine）
  - 本番モード（env を適宜設定）
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - Paper Trading（Mock Broker を使用）
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 実行時は Settings を参照して DB パスや PID ファイルを決定します。

- 監視（Monitoring）
  - デフォルトでは 60 秒ごとにポーリング。ポーリング間隔は環境変数で上書き可能:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は本番 sqlite_path を参照（KABUSYS_ENV に依らず production DB を使用する設計）。

- Streamlit ダッシュボード（ローカルで監視結果を可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプションで DB を明示: --db path/to/paper_trading.db
  - レポートは稼働率 / 注文成功率 / レイテンシ等を集計して PASS/FAIL を判定します。

- AI スコア付け（プログラムから利用）
  - 例（簡易）:
    - from datetime import date
      import duckdb
      from kabusys.ai import score_news
      conn = duckdb.connect("data/kabusys.duckdb")
      score_news(conn, date(2026, 4, 10), api_key="sk-...")

  - 同様に regime_detector.score_regime を使って market_regime テーブルへ書き込み可能。

## 主要設定と注意点
- Settings は起動時に .env/.env.local を自動ロード（ただし OS 環境変数優先）。
- KABUSYS_ENV の有効値: development, paper_trading, live
- PAPER_FILL_MODE の有効値: instant, partial, never, reject
- Monitoring は常に本番の sqlite_path を使用（監視ログは本番 DB に集約する設計）。
- run_execution は paper_trading の場合、paper 専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し本番 DB と分離します。
- MONITOR_POLL_INTERVAL の値は整数で 1 以上。無効値はデフォルト 60 秒にフォールバック。

## ディレクトリ構成（抜粋）
（src 配下を想定）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み / Settings クラス
  - run_execution.py
    - ExecutionEngine 起動スクリプト（KABUSYS_ENV による切替）
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - __init__.py
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py — SQLite テーブル初期化 / 永続化レイヤ
    - system_monitor.py — CPU/メモリ/ディスク / データ鮮度監視
    - trade_monitor.py — 注文滞留 / 約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書き込みロジック
    - alert_manager.py — LINE 通知
    - monitoring_engine.py — 各 Monitor を束ねるポーリング実行器
    - streamlit_dashboard.py — streamlit ベースの監視ダッシュボード
  - execution/
    - order_manager.py — 注文状態遷移の外向き API
    - reconciler.py — 起動時のリコンシリエーション（注文・ポジション突合）
    - （その他: broker_factory, execution_engine, order_repository 等 他ファイル）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数計算・aggregate cap
    - risk_adjustment.py — セクター上限・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py — momentum / volatility / value 計算
    - feature_exploration.py — 将来リターン / IC /統計サマリー
    - __init__.py
  - ai/
    - news_nlp.py — raw_news を OpenAI でスコアリングして ai_scores へ保存
    - regime_detector.py — ETF MA とマクロセンチメントを合成して market_regime に保存
    - __init__.py
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading の集計 / レポート

（上記は本 README に含まれる主要ファイルの抜粋です。詳細はソースを参照してください。）

## 開発／運用時のヒント
- SQLite / DuckDB ファイルは data/ 配下に配置されることが多いです。バックアップやローテーションの運用を検討してください。
- OpenAI API 呼び出しはレート制限やネットワークエラーに対してリトライ実装がありますが、API キーの保護やコスト管理に注意してください。
- Monitoring の kill.flag を使うことで ExecutionEngine の安全停止を行います。手動でフラグを消す場合は flag ファイルを削除してください（KillSwitch.clear）。
- ローカルでのデバッグ／テストでは KABUSYS_ENV=development を利用し、paper_trading であれば本番 DB を汚さないよう PAPER_TRADING_SQLITE_PATH を設定してください。

---
必要であれば README にサンプル .env.example、起動スクリプトの systemd / supervisor のサンプルユニット、あるいは各モジュールの API 使用例（コードスニペット）を追加します。どの情報を優先して追加しますか？