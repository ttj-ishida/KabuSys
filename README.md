# KabuSys — README (日本語)

このドキュメントはリポジトリの主要コンポーネント、セットアップ手順、使い方、およびディレクトリ構成をまとめたものです。KabuSys は日本株向けの自動売買・リサーチ・監視を目的としたコードベースです。本 README は提供されたソースコードをもとに作成しています。

重要: 実際に稼働させる前に必ずローカル環境・法規制・ブローカー契約等を確認してください。コードは教育的なサンプル実装の要素を含みます。

概要
- KabuSys は日本株の自動売買システムに関する複数モジュール群（実行エンジン、監視、リスク管理、ポートフォリオ構築、リサーチ、ニュースNLP 等）を含む Python パッケージです。
- DuckDB を用いた市場データ処理、SQLite による監視/注文ログ永続化、OpenAI を用いたニュースセンチメント評価などを組み合わせています。
- 実行モードは開発 / paper_trading / live を想定し、paper_trading モードではブローカー呼び出しをモックして本番 DB と分離して動作します。

主な機能一覧
- ExecutionEngine（run_execution.py）
  - ブローカークライアントの生成（本番/モック切替）
  - 注文管理（OrderManager, OrderRepository）
  - リスク管理（RiskManager）
  - 起動時のリコンシリエーション（Reconciler）
  - PID ファイル管理、プロセス優先度設定
- Monitoring（run_monitoring.py / monitoring/*）
  - SystemMonitor: CPU/メモリ/ディスク/プロセス状態・データ鮮度監視
  - TradeMonitor: 注文滞留・約定価格異常の検出
  - RiskMonitor: ドローダウン・ポジション上限監視とダッシュボード更新
  - KillSwitch: 条件に応じて停止フラグ（data/kill.flag）を書き込み
  - AlertManager: LINE Push 通知（オプション）
  - Streamlit ベースの監視ダッシュボード（monitoring/streamlit_dashboard.py）
- Portfolio construction（portfolio/*）
  - 候補選択、重み付け、セクター制限、ポジションサイズ計算（等金額・スコア加重・リスクベース）
- Research（research/*）
  - ファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 特徴量探索、将来リターン、IC 計算、統計サマリ
- AI（ai/*）
  - news_nlp: raw_news を集約して OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを評価し ai_scores に書き込み
  - regime_detector: ETF（1321）MA200 乖離とマクロニュースの LLM センチメントを合成して市場レジーム判定を行い market_regime に記録
- Tools
  - paper_verification_report: Paper Trading DB を解析して稼働率・注文成功率・API レイテンシなどの検証レポートを生成

セットアップ手順（ローカル開発向け）
1. Python の用意
   - Python 3.10 以上を推奨（型注釈に | 演算子が使われています）。
2. 仮想環境作成
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）
3. 依存ライブラリのインストール
   - 使用されている主な外部ライブラリ:
     - duckdb
     - psutil
     - requests
     - streamlit
     - openai
   - 例:
     - pip install duckdb psutil requests streamlit openai
   - （プロジェクトに requirements.txt がある場合はそれを使用してください）
4. .env の準備
   - プロジェクトルートに .env（もしくは .env.local）を置くと自動読み込みされます。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - KABUSYS_ENV=development  # development | paper_trading | live
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PAPER_FILL_MODE=instant  # instant|partial|never|reject
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - LOG_LEVEL=INFO
     - LINE_CHANNEL_ACCESS_TOKEN=... (任意)
     - LINE_USER_ID=... (任意)
   - サンプル（.env.example があれば参照してください）
5. データディレクトリ作成
   - mkdir -p data

簡単な動作確認（ローカル）
- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト 60）
  - 監視は Settings の sqlite_path（デフォルト data/monitoring.db）を使用して DB を初期化します
- 実行エンジン起動（注文処理）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にするとモックブローカーを使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録して本番 DB と分離します
- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - read-only モードで SQLite を開きます（監視プロセスが DB を更新していることが前提）
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを明示できます（環境変数 PAPER_TRADING_SQLITE_PATH と優先順位は --db > 環境変数 > デフォルト）
- OpenAI を使う処理
  - ai.news_nlp.score_news(conn, target_date, api_key=None) など関数呼び出しで利用します。API キーは api_key 引数か OPENAI_API_KEY 環境変数で指定してください。
  - ai.regime_detector.score_regime(conn, target_date, api_key=None) も同様です。

運用上の注意
- KABUSYS_ENV による DB 分離:
  - paper_trading モードでは paper_sqlite_path を使用して、本番の monitoring DB と分離して動作します。
  - 監視機能（run_monitoring）は本コードでは常に Settings.sqlite_path（本番パス）を使う設計になっています。環境に応じた運用設定に注意してください。
- PID / Kill flag:
  - ExecutionEngine は起動時に PID ファイル（デフォルト data/execution.pid）を書きます。SystemMonitor はこの PID を見てプロセスが生存しているか評価します。
  - KillSwitch は data/kill.flag を書き込んで ExecutionEngine に停止信号を送ります。ExecutionEngine 側でこのフラグを検知して停止する実装がある想定です。
- OpenAI API:
  - API 呼び出しはエラー耐性（リトライ・フォールバック）を備えていますが、API キーとクォータ、コストに注意してください。
- LINE 通知:
  - LINE のトークン／ユーザID が未設定の場合、AlertManager は送信をスキップします。設定済みでもクールダウン（既定 30 分）があります。

主要なコマンド例まとめ
- 監視を開始（デフォルト間隔 60s）
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
- 実行エンジン開始（paper_trading モードの例）
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution
- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / Settings 管理（.env 読み込み含む）
  - run_monitoring.py             — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py         — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py            — SQLite 永続化レイヤ（init, MonitoringDB クラス）
    - system_monitor.py           — システム状態 / データ鮮度監視
    - trade_monitor.py            — 注文滞留 / 約定異常監視
    - risk_monitor.py             — ドローダウン / ポジション上限監視
    - kill_switch.py              — kill.flag 制御
    - alert_manager.py            — LINE 通知
    - monitoring_engine.py        — 監視コンポーネント束ね実行ロジック
    - streamlit_dashboard.py      — Streamlit ダッシュボード
  - execution/
    - order_manager.py            — 注文状態マシン用の外向き API
    - order_repository.py         — (参照あり) SQLite 注文保存（コード抜けあり）
    - order_record.py             — OrderRecord, OrderState など（参照あり）
    - reconciler.py               — 起動時リコンシリエーション
    - broker_factory.py           — ブローカークライアント生成（参照あり）
    - execution_engine.py         — ExecutionEngine（参照あり）
    - risk_manager.py             — リスク管理（参照あり）
    - …（その他 execution 関連）
  - portfolio/
    - __init__.py
    - portfolio_builder.py        — 候補選択、重み付け
    - position_sizing.py          — 株数算出・丸め・利用キャップ
    - risk_adjustment.py          — セクターキャップ・レジーム乗数
  - research/
    - __init__.py
    - factor_research.py          — ファクター計算（momentum, volatility, value）
    - feature_exploration.py      — 将来リターン, IC, 統計サマリ
  - ai/
    - __init__.py
    - news_nlp.py                 — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py          — 市場レジーム判定（MA + マクロ NLP）
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
  - data/ (想定: データファイル格納ディレクトリ)
    - monitoring.db (SQLite)
    - paper_trading.db (SQLite)
    - kabusys.duckdb (DuckDB)

補足（実装上の注意点）
- DB マイグレーション: monitoring_db.init_monitoring_db は冪等でテーブルを作成し、既存カラムの追加（ALTER TABLE）を行う処理を含みます。
- セキュリティ: .env にパスワードや API キーを平文で置く場合はアクセス管理に注意してください。
- テスト: OpenAI 呼び出し等はテスト時にモック化する設計（内部の _call_openai_api をパッチ）になっています。

問い合わせ / 変更履歴
- この README は与えられたソースコードのコメント・実装に基づいて作成されています。実運用時は実際の requirements.txt、運用手順書、.env.example を整備してください。

以上。