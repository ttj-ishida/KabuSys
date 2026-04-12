# KabuSys

日本株向けの自動売買システム（プロトタイプ）。  
本リポジトリには売買実行エンジン、監視・アラート機構、ポートフォリオ構築ユーティリティ、リサーチ用ファクター計算、LLM を用いたニュース解析／レジーム判定などのコンポーネントが含まれます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な主要コンポーネントを分離して実装したシステムです。主要な設計方針は以下の通りです。

- 実行エンジン（ExecutionEngine）とブローカークライアントの抽象化
- 監視（MonitoringEngine）とアラート（LINE push）による運用安全性の確保
- ポートフォリオ構築・リスク調整・ポジションサイズ算出の純粋関数
- DuckDB を用いたリサーチ・ファクター計算（prices_daily / raw_financials を想定）
- OpenAI（gpt-4o-mini 等）を使ったニュースセンチメント解析・マクロレジーム判定（フェイルセーフ設計）
- Paper Trading（検証用 DB 分離）をサポート

---

## 主な機能一覧

- 実行（run_execution.py）
  - ブローカー抽象（本番／モック）を介した注文発行、リスク管理、リコンシリエーション
  - Paper Trading 用の専用 SQLite（data/paper_trading.db）サポート
- 監視（run_monitoring.py / monitoring パッケージ）
  - システム状態（CPU/メモリ/ディスク/プロセス監視）
  - 注文滞留・約定異常チェック
  - ドローダウン・ポジション上限の監視と kill.flag による停止シグナル
  - LINE による通知（AlertManager）
  - Streamlit ダッシュボード（監視用 UI）
- ポートフォリオ（portfolio パッケージ）
  - 候補選定、等金額／スコア加重配分、リスク調整（セクター上限、レジーム乗数）、ポジションサイズ計算
- リサーチ（research パッケージ）
  - Momentum / Volatility / Value ファクター計算
  - 将来リターン、IC（Information Coefficient）計算、統計サマリ
- AI（ai パッケージ）
  - ニュースを LLM でスコアリングして ai_scores に書き込み（score_news）
  - マクロニュース + ma200 で市場レジームを判定して market_regime に書き込み（score_regime）
- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
  - プロセス優先度・CPU affinity 設定ユーティリティ（kabusys.utils.process_priority）

---

## 前提 / 必要環境

- Python 3.9+
- ライブラリ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード利用時)
- SQLite が利用可能（標準ライブラリ）

（実際の依存関係はプロジェクトの pyproject.toml / requirements.txt を参照してください）

---

## セットアップ手順

1. リポジトリをチェックアウト / クローン
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Linux/macOS) または .venv\Scripts\activate (Windows)
3. 依存パッケージをインストール
   - pip install -r requirements.txt
     - ※ requirements.txt がない場合は、上記の主要パッケージを個別にインストールしてください
4. data ディレクトリを作成（必要に応じて）
   - mkdir -p data
5. 環境変数を用意する（.env ファイルをプロジェクトルートに置くことが可能）
   - 主要な環境変数（例）：
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - OPENAI_API_KEY (LLM を使う機能を使う場合)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (監視用デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB のパス、デフォルト: data/paper_trading.db)
     - PAPER_FILL_MODE (paper_trading の約定モード: instant|partial|never|reject、デフォルト: instant)
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（アラート有効化）
     - PID_FILE_PATH（デフォルト: data/execution.pid）
     - KILL_FLAG_PATH（デフォルト: data/kill.flag）
   - .env 自動ロード:
     - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます。
     - OS 環境変数が優先され、.env.local は .env を上書きします。
     - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

注意: Settings クラスは必須 env を _require() でチェックします（足りないと ValueError が発生します）。

---

## 使い方（例・コマンド）

- ExecutionEngine 起動（本番 / paper_trading を KABUSYS_ENV で制御）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - KABUSYS_ENV=live python -m kabusys.run_execution
  - 実行開始時にプロセス優先度を "high" に設定します。
  - Paper Trading の場合、専用の SQLite（PAPER_TRADING_SQLITE_PATH）に記録され、本番 DB と分離されます。

- Monitoring 起動（ポーリングループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト 60 秒）。
  - Monitoring は環境にかかわらず production sqlite_path（デフォルト data/monitoring.db）を使用します。

- Streamlit ダッシュボード（監視 UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは監視 DB を読み取り専用で開きます。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH または --db で指定可能）

- AI 関連（プログラム的に呼び出す）
  - ニューススコア付与（ai.news_nlp.score_news）: DuckDB 接続と target_date を与えて呼ぶ
  - レジーム判定（ai.regime_detector.score_regime）: DuckDB 接続と target_date を与えて呼ぶ
  - これらは OpenAI API キー（OPENAI_API_KEY）を必要とします。内部でリトライやフェイルセーフ（失敗時 0.0 フォールバック）が実装されています。

- その他ユーティリティ
  - kabusys.utils.process_priority.set_process_priority でプロセス優先度設定（platform を吸収）

---

## 設定（主要な環境変数）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: ログレベル（デフォルト: INFO）
- JQUANTS_REFRESH_TOKEN: J-Quants API リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE Push 通知用（未設定だと通知はスキップされログのみ）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（デフォルト instant）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH: kill.flag パス（デフォルト data/kill.flag）

---

## 運用上の注意

- Monitoring の DB 初期化:
  - run_monitoring / run_execution 起動時に monitoring 用テーブル（system_status, trade_logs, positions, risk_logs, dashboard）を作成する init_monitoring_db が呼ばれます（冪等）。
- Monitoring は常に本番の sqlite_path を使用する設計です（環境に依らず監視ログは一元管理）。
- Paper Trading は実行側で専用 DB に分離されるため、本番 DB とデータ分離が保たれます。
- OpenAI（LLM）を使用する機能は API キー、リクエスト制限、通信エラーを考慮した設計になっていますが、料金やプライバシーには注意してください。
- kill.flag による停止は冪等で既存フラグは上書きしません。必要時は手動で削除可能（KillSwitch.clear）。

---

## ディレクトリ構成（主要ファイル）

src/
  kabusys/
    __init__.py                      — パッケージ定義（version）
    config.py                         — 環境変数読み込み / Settings
    run_execution.py                  — ExecutionEngine 起動スクリプト
    run_monitoring.py                 — SystemMonitor ポーリングループ起動スクリプト

    ai/
      __init__.py
      news_nlp.py                     — ニュース NLP スコアリング（OpenAI）
      regime_detector.py              — マクロレジーム判定（OpenAI + ma200）
    data/
      (外部テーブル / pipeline 等を想定: DuckDB 操作用モジュールが参照)
    execution/
      broker_api.py                    — ブローカー API 抽象（参照）
      broker_factory.py                — BrokerClientFactory（モック / 実装選択）
      execution_engine.py              — 実行エンジン本体（EngineConfig 等）
      order_manager.py                 — OrderManager（状態遷移・送信ロジック）
      order_repository.py              — Orders DB アクセス（SQLite）
      reconciler.py                    — 起動時のリコンシリエーション
      risk_manager.py                  — 注文発行前のリスクチェック
      order_record.py                  — OrderRecord, OrderState（ドメインモデル）
    monitoring/
      __init__.py
      monitoring_db.py                 — monitoring DB 層（テーブル作成 + CRUD）
      system_monitor.py                — システムヘルス・データ鮮度チェック
      trade_monitor.py                 — 注文滞留 / 約定異常検出
      risk_monitor.py                  — ドローダウン / ポジション上限監視
      kill_switch.py                   — kill.flag の書込み・評価
      alert_manager.py                 — LINE Push 通知ラッパー
      monitoring_engine.py             — 各 Monitor を束ねるループ
      streamlit_dashboard.py           — Streamlit ベースのダッシュボード
    portfolio/
      __init__.py
      portfolio_builder.py             — 候補選定・重み付け
      position_sizing.py               — 株数計算・スケーリング・単元丸め
      risk_adjustment.py               — セクターキャップ・レジーム乗数
    research/
      __init__.py
      factor_research.py               — Momentum / Volatility / Value 等
      feature_exploration.py           — 将来リターン / IC / 統計サマリ
    tools/
      __init__.py
      paper_verification_report.py     — Paper Trading の検証レポート生成
    utils/
      __init__.py
      process_priority.py              — プロセス優先度 / CPU affinity 設定ユーティリティ

データファイル（デフォルト）
- data/kabusys.duckdb       — DuckDB（prices_daily 等のリサーチ用テーブル）
- data/monitoring.db        — 監視ログ（system_status, trade_logs, positions, risk_logs, dashboard）
- data/paper_trading.db     — Paper Trading 用 SQLite（KABUSYS_ENV=paper_trading 時に使用）
- data/execution.pid        — ExecutionEngine 起動時の PID ファイル
- data/kill.flag            — KillSwitch の停止フラグ

---

## 開発・拡張のヒント

- .env のパースは config._load_env_file に独自実装があり、クォートやコメントに柔軟に対応します。CI やテストで自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を使用してください。
- DuckDB 接続は多くのリサーチ関数に引数で渡す設計のため、テスト時は in-memory またはテスト用 DB を渡して検証できます。
- OpenAI 呼び出し部分は _call_openai_api を介しているため、ユニットテストではパッチで差し替えることで外部 API をモックできます。
- monitoring_db.init_monitoring_db は冪等であり、テーブル追加やマイグレーション（列追加）処理が含まれています。既存データを扱う際は注意してください。

---

必要があれば、README に含める具体的な .env.example、サンプルコマンド（systemd ユニット例や docker-compose のテンプレート）なども作成します。どの内容を追加しましょうか？