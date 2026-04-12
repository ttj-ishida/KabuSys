KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買システムのコードベースです。本リポジトリは以下の主要機能を含みます。

- 実売買を行う ExecutionEngine（本番 / paper_trading 切替対応）
- システム稼働・注文監視を行う MonitoringEngine（SQLite にログ永続化）
- Paper Trading 向け検証レポート生成ツール
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- リサーチ用ファクター計算・特徴量解析
- ニュース NLP を用いた銘柄センチメント評価（OpenAI 経由）
- 市場レジーム判定（MA + マクロセンチメントの合成）
- Streamlit ベースの監視ダッシュボード
- LINE Push によるアラート送信、Kill Switch、再同期（Reconciler）等の運用機能

設計方針は「テスト可能性」「ルックアヘッドバイアス回避」「フェイルセーフ」を重視しており、DB 操作は明確に分離されています。

主な機能一覧
-------------
- Execution
  - ExecutionEngine（実際のブローカー/API 経由で注文）
  - BrokerClientFactory により paper_trading 環境では MockBroker を使用、paper DB（data/paper_trading.db）へ記録
  - Reconciler による起動時の注文・ポジション同期

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス稼働確認、データ鮮度チェック
  - TradeMonitor: 滞留注文・約定異常価格検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - MonitoringEngine: 各 Monitor を束ねてポーリング、KillSwitch 評価、AlertManager と連携
  - MonitoringDB: SQLite での監視ログ永続化（テーブル自動作成・マイグレーション対応）
  - Streamlit ダッシュボード（src/kabusys/monitoring/streamlit_dashboard.py）

- Tools
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）
  - 各種 research / portfolio / ai モジュール（DuckDB を用いて履歴データを解析）

- AI
  - news_nlp.score_news: OpenAI（gpt-4o-mini）でニュースを銘柄ごとにセンチメント評価し ai_scores テーブルへ書き込み
  - regime_detector.score_regime: ETF MA とマクロニュースの LLM 評価を合成して市場レジーム判定

セットアップ手順
----------------
前提
- Python 3.10+ を推奨（型注釈の union 演算子などを使用）
- Git, pip

推奨手順（UNIX 系）
1. リポジトリをクローン
   - git clone <repository-url>
2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate
3. 必要パッケージをインストール
   - 必須（コード参照）: duckdb, psutil, requests, openai, streamlit
   - 例:
     - pip install duckdb psutil requests openai streamlit
   - （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）
4. data ディレクトリ作成（任意だが推奨）
   - mkdir -p data
   - デフォルトで生成される DB: data/monitoring.db（SQLite）、data/kabusys.duckdb（DuckDB）
5. 環境変数を設定（.env ファイルをプロジェクトルートに置くと自動ロードされます）
   - 主要な環境変数（抜粋）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: （必須: J-Quants API 用）
     - KABU_API_PASSWORD: （必須: kabuステーション API 用）
     - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector）
     - PAPER_FILL_MODE: paper_trading 時の約定挙動（instant|partial|never|reject、デフォルト: instant）
     - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: monitoring DB（デフォルト: data/monitoring.db）
     - PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
     - KILL_FLAG_PATH: kill flag（デフォルト: data/kill.flag）
     - MONITOR_POLL_INTERVAL: 監視ループの秒間隔（run_monitoring 用、デフォルト: 60）
     - LOG_LEVEL: DEBUG|INFO|...（デフォルト: INFO）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE Push 用（任意）
   - .env の書式はシェル形式（コメント、クォート等に対応）

初期化
- Monitoring / Execution のスクリプトは起動時に必要なテーブルを自動作成（init_monitoring_db）します。特別な初期化手順は不要です。

使い方
------
実行可能スクリプト（モジュール実行）
- 監視ループ起動（MonitoringEngine を単体で使う簡易起動）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でループ間隔（秒）を上書き可能（例: export MONITOR_POLL_INTERVAL=30）
  - 実行時にプロセス優先度を "high" に設定し、SQLite / DuckDB へ接続します

- ExecutionEngine（取引エンジン）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ記録されます
  - 起動時にプロセス優先度を "high" に設定します

- Streamlit ダッシュボード起動
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用で SQLite DB を開き、Overview / Positions / Orders / System タブを表示します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH より優先）
  - レポートは標準出力に表示され、稼働率・注文成功率・レイテンシ等の判定を PASS/FAIL 形式で出力します

- AI / リサーチ機能（プログラム呼び出し）
  - モジュール関数をインポートして利用します（例）:
    - from kabusys.ai.news_nlp import score_news
      - score_news(conn, target_date, api_key=None) -> int（書き込み銘柄数）
    - from kabusys.ai.regime_detector import score_regime
      - score_regime(conn, target_date, api_key=None) -> int
    - リサーチ:
      - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary

運用上の注意
- Monitoring は常に本番用の sqlite_path を使用します（KABUSYS_ENV に依存せず監視ログは本番 DB を想定）
- Execution は paper_trading 環境時に DB を分離（PAPER_TRADING_SQLITE_PATH）
- PID ファイル（デフォルト data/execution.pid）により ExecutionEngine の稼働判定を行います。stale PID 検出・削除の仕組みあり
- Kill Switch：RiskMonitor の判定により data/kill.flag を書き込み、Execution を停止させる運用が可能
- OpenAI 呼び出しは外部 API のため、API キーやレート制限・エラーに応じたリトライ・フォールバックが組み込まれています

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                     — 環境変数 / 設定管理（.env 自動ロード等）
- run_monitoring.py             — SystemMonitor ポーリング起動スクリプト
- run_execution.py              — ExecutionEngine 起動スクリプト

サブパッケージ（抜粋）
- kabusys/monitoring/
  - monitoring_db.py             — SQLite テーブル定義・読み書きラッパ
  - system_monitor.py            — CPU/メモリ/ディスク/プロセス/データ鮮度監視
  - trade_monitor.py             — 注文滞留・約定異常検出
  - risk_monitor.py              — ドローダウン / ポジション上限監視
  - monitoring_engine.py         — モニタ群を束ねるポーリングエンジン
  - alert_manager.py             — LINE push 通知ユーティリティ
  - kill_switch.py               — kill.flag 書き込みロジック
  - streamlit_dashboard.py       — Streamlit ダッシュボード

- kabusys/execution/
  - order_manager.py
  - reconciler.py
  - order_repository.py (参照)
  - execution_engine.py (参照)
  - broker_factory.py

- kabusys/portfolio/
  - portfolio_builder.py         — 候補選定・重み計算
  - position_sizing.py           — 発注株数計算
  - risk_adjustment.py           — セクター制限・レジーム乗数

- kabusys/research/
  - factor_research.py           — Momentum / Volatility / Value ファクター計算
  - feature_exploration.py       — 将来リターン計算・IC・統計サマリー

- kabusys/ai/
  - news_nlp.py                  — ニュースを OpenAI でスコアリングし ai_scores に書き込み
  - regime_detector.py           — 市場レジーム判定（MA + マクロセンチメント合成）

- kabusys/tools/
  - paper_verification_report.py — Paper Trading 検証レポート出力（CLI）

ユーティリティ
- kabusys/utils/process_priority.py — プロセス優先度 / CPU affinity 設定（Windows/Linux 対応）

追加情報・運用ヒント
--------------------
- .env の自動ロード: プロジェクトルート（.git または pyproject.toml を含む親ディレクトリ）から .env/.env.local を自動読み込みします。テスト時に自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DB マイグレーション: init_monitoring_db() は既存 DB を検査し、必要に応じて列を追加する簡易マイグレーションを実施します。
- Paper Trading と本番 DB は完全に分離する設計になっています。テスト時は必ず KABUSYS_ENV=paper_trading に切り替えてください。
- OpenAI API のレート制限や一時的な失敗は内部でエクスポネンシャルバックオフでリトライしますが、API キーの適切な管理と課金ポリシーの理解をお願いします。

ライセンス / 貢献
----------------
- 本 README はコードベースの説明を目的としたドキュメントです。実際のライセンスやコントリビューション方針はリポジトリの LICENSE や CONTRIBUTING.md を参照してください。

質問や追加のドキュメント（例えば API 仕様、運用手順、デプロイ手順など）が必要であれば教えてください。README に追記します。