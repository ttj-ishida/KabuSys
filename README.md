# KabuSys

KabuSys は日本株の自動売買・リサーチ・監視を目的としたミニマルなフレームワークです。本リポジトリは以下の主要機能を提供します。

- 注文発行・実行エンジン（ExecutionEngine）とリコンシリエーション
- リスク管理（ドローダウン・ポジション上限など）
- 監視（システム状態、注文滞留、約定異常）のポーリング
- Paper Trading 用の分離された DB & モックブローカー
- ファクター計算、特徴量探索、ファクター評価（Research）
- ニュースの LLM ベースセンチメント（OpenAI）によるスコアリング & レジーム判定
- 監視ダッシュボード（Streamlit）と検証レポート生成ツール

以下はコードベースに基づく README（セットアップ／使い方／構成）です。

---

## 機能一覧（概要）

- execution
  - 注文作成 → ブローカー送信 → 状態同期のワークフロー
  - Reconciler による起動時の自動復旧（OrderSent の突合・ポジション差分検出）
  - Paper Trading モードでは MockBroker を利用し、data/paper_trading.db に記録

- monitoring
  - SystemMonitor：CPU/メモリ/ディスク/プロセス状態・株価データ鮮度監視
  - TradeMonitor：滞留注文、約定価格の異常検出
  - RiskMonitor：ドローダウン・ポジション上限監視とダッシュボード更新
  - KillSwitch：条件に応じてフラグファイル (data/kill.flag) を書き、ExecutionEngine 停止を促す
  - AlertManager：LINE Messaging API へ通知（クールダウン管理）
  - Streamlit ダッシュボード（監視データの可視化）
  - monitoring DB（SQLite）用の永続化層とマイグレーション処理

- portfolio
  - 銘柄選定（スコア順ソートなど）
  - 重み計算（等金額、スコア加重）
  - セクターキャップ適用、レジーム乗数
  - 株数算出（リスクベース／等配分等）、単元切り上げ、aggregate cap 処理

- research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー

- ai
  - ニュース NLU（OpenAI）による銘柄別センチメントスコアの算出と ai_scores への書込み
  - マクロニュース + ETF MA200 を組み合わせた市場レジーム判定（bull/neutral/bear）

- tools
  - paper_verification_report：Paper Trading の検証レポート生成（各種指標と PASS/FAIL 判定）

- utils
  - process_priority：クロスプラットフォームでのプロセス優先度 / CPU affinity 設定ユーティリティ
  - 環境変数取り扱い（Settings クラス, .env 自動読み込み）

---

## セットアップ手順

前提
- Python 3.9+ を推奨（コード内での型ヒント・モジュールに準拠）
- system には DuckDB（Python パッケージ）、psutil、requests、openai、streamlit などが必要

推奨的な手順（仮想環境を使用）:

1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   以下は本プロジェクトで参照されている主なパッケージ例です。requirements.txt がない場合は手動でインストールしてください。
   - pip install duckdb psutil requests openai streamlit

   （必要に応じてその他の内部モジュール／DB ライブラリを追加してください）

3. 環境変数 / .env
   プロジェクトルートに `.env`（および `.env.local`）を配置できます。`kabusys.config` モジュールは自動的にプロジェクトルートを探索して `.env`/.env.local を読み込みます（ただし環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。

   主要な環境変数（例）:
   - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
   - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須の場合あり）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
   - OPENAI_API_KEY: OpenAI API キー（ai モジュールを使う場合必須）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知を使う場合
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（paper_trading 時の DB、デフォルト: data/paper_trading.db）
   - PID_FILE_PATH（デフォルト: data/execution.pid）
   - KILL_FLAG_PATH（デフォルト: data/kill.flag）
   - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）
   - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、run_monitoring で上書き可能）

   例 .env（最小）:
   ```
   KABUSYS_ENV=development
   KABU_API_PASSWORD=your_kabu_password
   OPENAI_API_KEY=sk-...
   LINE_CHANNEL_ACCESS_TOKEN=...
   LINE_USER_ID=...
   ```

4. データディレクトリ作成
   - mkdir -p data

※ SQLite / DuckDB の DB ファイルは自動生成・初期化を行う処理が含まれている箇所があります（例: init_monitoring_db）。ただし DuckDB 側は prices_daily などテーブルの準備が必要な場合があります（外部 ETL やデータ投入は別途必要）。

---

## 使い方（主要スクリプト）

プロジェクトはモジュールとして実行できます（パッケージのルートが PYTHONPATH にある想定）。

1. 監視ループの起動（SystemMonitor 単体）
   - python -m kabusys.run_monitoring
     - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
     - 監視は Settings に従って本番 sqlite_path を使用（KABUSYS_ENV にかかわらず monitoring DB は本番パスを参照）。

2. ExecutionEngine（注文実行）の起動
   - python -m kabusys.run_execution
     - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と分離）。
     - 実行前に Settings（環境変数）が正しく設定されていることを確認してください。

3. Paper Trading 検証レポート生成（ツール）
   - python -m kabusys.tools.paper_verification_report
   - オプション:
     - --from YYYY-MM-DD
     - --to YYYY-MM-DD
     - --db PATH （PAPER_TRADING_SQLITE_PATH を上書き）
   - 例:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

4. Streamlit 監視ダッシュボード
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
     - 監視用 SQLite を read-only モードで開く（デフォルト: data/monitoring.db）。
     - MonitoringEngine を先に起動してデータを投入しておく必要があります。

5. AI 系処理
   - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime はプログラムから呼び出して利用します。
   - OpenAI API キー（OPENAI_API_KEY）を設定してください。
   - Paper/Production 共に API 利用時は費用とレートに注意してください（リトライ・バックオフ実装あり）。

---

## 実行時の挙動・注意事項

- Settings（kabusys.config）
  - .env, .env.local をプロジェクトルートから自動読み込み（OS 環境変数が優先）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
  - KABUSYS_ENV は "development", "paper_trading", "live" のいずれか。有効でない値はエラー。

- Paper Trading
  - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path（デフォルト data/paper_trading.db）を使い、本番 DB と完全分離されます。
  - PAPER_FILL_MODE（instant|partial|never|reject）で MockBroker の約定振る舞いを制御できます。

- 監視（monitoring）
  - init_monitoring_db により monitoring DB のテーブル作成・簡易マイグレーションを自動実行します。
  - KillSwitch は監視結果からフラグファイル data/kill.flag を書き込むことで ExecutionEngine に停止を促します。ExecutionEngine 側ではこのフラグを監視して処理を停止する実装が想定されています。

- プロセス優先度
  - 実行スクリプトは起動時に set_process_priority("high") を呼びます（psutil によるプラットフォーム依存設定）。権限不足や未サポート OS の場合は警告が出ますが継続します。

- OpenAI API
  - 呼び出しは堅牢化（429/接続断/タイムアウト/5xx のリトライ、JSON バリデーション、スコアクリップ）されています。
  - API キー未設定時の挙動：一部関数は ValueError を投げます（API キー必須）。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主要ファイル/モジュールの概要です。

- kabusys/
  - __init__.py — パッケージ定義（__version__ 等）
  - config.py — 環境変数 / Settings クラス、.env 読み込みロジック
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - execution/
    - order_manager.py — 注文管理（状態遷移、送信、重複チェック）
    - reconciler.py — 起動時の注文・ポジション突合
    - (その他: broker_factory, execution_engine, order_repository 等が存在)
  - monitoring/
    - monitoring_db.py — SQLite ベースの永続化層（テーブル作成 / CRUD）
    - system_monitor.py — CPU/メモリ/ディスク・プロセス・データ鮮度監視
    - trade_monitor.py — 注文滞留 / 約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — フラグファイルによる停止シグナル
    - alert_manager.py — LINE Push 通知
    - monitoring_engine.py — 各 Monitor を束ねるポーリング実行器
    - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
  - portfolio/
    - portfolio_builder.py — 候補選定・スコアソート
    - position_sizing.py — 株数決定（単元丸め・aggregate cap）
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — Momentum/Volatility/Value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / summary
  - ai/
    - news_nlp.py — 記事集約 → OpenAI による銘柄センチメント算出 → ai_scores へ書込
    - regime_detector.py — マクロニュース + ETF MA200 によるレジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート出力
  - run_monitoring.py — SystemMonitor のシンプルなポーリングループ起点
  - run_execution.py — ExecutionEngine 起動スクリプト

（上に挙げたファイル群は抜粋です。その他に execution/broker_*、data パイプライン関連のモジュールが想定されます。）

---

## 参考コマンドまとめ

- 監視ループ（デフォルト 60 秒）:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- ExecutionEngine 起動:
  - KABUSYS_ENV=development python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Streamlit Dashboard:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

---

## 開発時の注意・拡張ポイント

- DuckDB の prices_daily / raw_financials / raw_news 等のテーブルは本リポジトリに含まれていません。データ投入パイプライン（ETL）は別途必要です。
- ExecutionEngine や Broker クライアントは外部 API（kabuステーション等）に依存するため、実稼働前にテスト＆モックを用いた検証を強く推奨します。
- Paper Trading は本番データベースと厳密に分離される設計ですが、設定ミスで環境が混在しないよう .env の管理に注意してください。
- OpenAI 利用はコストとレート制限に留意。モデルやバッチサイズは定数で管理されています（news_nlp.py 内）。

---

この README はソースコード内のドキュメント文字列（docstring）や実装に基づき作成しています。実運用する際は、環境変数や依存パッケージのバージョン、DB スキーマや ETL フロー等をプロジェクト固有の要件に合わせて整備してください。