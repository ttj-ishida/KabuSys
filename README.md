KabuSys — 日本株自動売買システム (README)
=======================================

概要
----
KabuSys は日本株向けの自動売買および研究支援を目的とした軽量なフレームワークです。
主な機能はシグナル処理→発注の ExecutionEngine、監視 (Monitoring) 系機能、因子計算・特徴量解析、LLM を用いたニュースセンチメント評価などを含みます。設計方針として、以下を重視しています。

- 本番／検証（paper trading）を分離した DB 設計
- ルックアヘッドバイアス防止（target_date ベースの計算）
- フェイルセーフ（API 失敗時に継続、部分成功の保護）
- モジュール化された純粋関数群（ポートフォリオ構築・サイズ決定等）
- DuckDB / SQLite を用いたローカル分析・監視データ永続化

主な機能
---------
- ExecutionEngine
  - シグナル読み込み → Gate によるリスクチェック → 発注（kabu ステーション等のブローカー実装を利用）
  - 再起動時の Reconciliation（未確定注文照合）で状態回復
  - レート制限・サーキットブレーカー等のリスク管理組み込み
  - paper_trading モード（MockBroker を用いて専用 SQLite DB に記録）

- Monitoring
  - SystemMonitor：CPU / メモリ / ディスク / データ鮮度 / 実行プロセス監視
  - TradeMonitor：滞留注文（stale order）や約定価格異常の検出
  - RiskMonitor：ドローダウン・ポジション上限監視、ダッシュボード永続化
  - KillSwitch：条件により ExecutionEngine 停止のためのフラグファイル（data/kill.flag）を書き込む
  - AlertManager：LINE Messaging API を使ったプッシュ通知（クールダウン管理あり）
  - Streamlit ダッシュボード（読み取り専用で監視 DB を可視化）

- Portfolio construction
  - 候補選定、等金額／スコア加重配分、リスクベースの株数決定、セクター帽子（sector cap）適用、レジーム乗数

- Research
  - DuckDB を用いたファクター計算（Momentum / Volatility / Value 等）、将来リターン計算、IC や統計サマリ

- AI（OpenAI）連携
  - ニュース記事をまとめて LLM（gpt-4o-mini）へ投げ、銘柄ごとのセンチメントを ai_scores テーブルへ書き込む
  - マクロニュース + ETF MA200 による市場レジーム判定（regime_detector）

セットアップ手順
----------------

前提
- Python 3.10 以上（型ヒントの | 演算子等を使用）
- システムに duckdb, psutil, requests, streamlit, openai 等をインストールできること

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - requirements.txt が用意されている場合:
     - pip install -r requirements.txt
   - ない場合は最低限次を個別インストール:
     - pip install duckdb psutil requests streamlit openai

4. 環境変数の設定
   - プロジェクトルートに .env / .env.local を置くと自動読み込みされます（既存 OS 環境変数優先）。
   - 自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
   - 主要な環境変数（例）:
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - JQUANTS_REFRESH_TOKEN（必須: ファクター等で使用）
     - KABU_API_PASSWORD（必須: kabuステーション接続）
     - OPENAI_API_KEY（AI 機能を使う場合必須）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート送信に使用、未設定なら送信はスキップ）
     - SQLITE_PATH（監視 DB：data/monitoring.db がデフォルト）
     - DUCKDB_PATH（分析 DB：data/kabusys.duckdb がデフォルト）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB。デフォルト data/paper_trading.db）
     - PAPER_FILL_MODE（paper_trading の挙動: instant | partial | never | reject。デフォルト instant）
     - PID_FILE_PATH（デフォルト data/execution.pid）
     - KILL_FLAG_PATH（デフォルト data/kill.flag）
     - MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒。デフォルト 60）

   - .env のサンプル（.env.example を参照して作成してください）:
     - KABUSYS_ENV=paper_trading
     - OPENAI_API_KEY=sk-...
     - KABU_API_PASSWORD=...
     - SQLITE_PATH=data/monitoring.db

5. データディレクトリ作成
   - mkdir -p data

起動・使い方
------------

実行エンジン（発注）
- paper_trading（本番 DB と分離して検証）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- 本番（live）:
  - KABUSYS_ENV=live python -m kabusys.run_execution
- 補足:
  - ExecutionEngine は起動時に PID ファイル（デフォルト data/execution.pid）を利用して実行プロセスの存在を管理します。
  - kill.flag（デフォルト data/kill.flag）が存在すると起動処理や発注ループで検出され、終了動作に入ります。
  - KILL_FLAG_CLEAR_ON_START を環境変数に 1 を設定すると、起動時に kill.flag をクリアする用途で参照できます（実装側で利用される設定）。

監視プロセス（Monitoring）
- ポーリング監視ループを起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - デフォルトは 60 秒。MONITOR_POLL_INTERVAL を整数秒で上書き可能（1 以上）。
- 監視は常に本番用 sqlite_path（Settings.sqlite_path）を使用します（monitoring は環境に依存しません）。
- 監視は system_status / trade_logs / positions / risk_logs / dashboard のテーブルを管理します。

Streamlit ダッシュボード（ローカル閲覧）
- 監視 DB を読み取り専用で表示する UI:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- ダッシュボードは監視 DB に依存するため、Monitoring を先に起動してデータを流してください。

AI 機能（ニュースセンチメント / レジーム判定）
- OpenAI API キーが必要です（OPENAI_API_KEY）。
- ニュースのスコアリング例（スクリプト呼び出し用 API を提供していますが、直接呼び出す場合は次の関数を使います）:
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- これらは DuckDB 接続を受け取って ai_scores / market_regime へ書き込みます。失敗時はフォールバック動作を行います（例: API がダウンなら 0.0 を使う等）。

主な環境変数の補足
- PAPER_FILL_MODE: paper_trading での約定挙動（instant / partial / never / reject）。不正な値はエラーになります。
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）。0 以下や非整数は無視され、デフォルト 60 秒を使います。

ディレクトリ構成（主要ファイル）
--------------------------------
以下は src/kabusys 以下の主要モジュールと役割の抜粋です。

- src/kabusys/__init__.py
  - パッケージ定義とバージョン

- src/kabusys/config.py
  - 環境変数 / .env ロードと Settings クラス（全設定の集中管理）

- src/kabusys/run_execution.py
  - ExecutionEngine 起動スクリプト（KABUSYS_ENV による paper_trading 分離）

- src/kabusys/run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL に対応）

- src/kabusys/execution/
  - execution_engine.py : ExecutionEngine 本体（シグナル処理・push ドレイン）
  - order_manager.py   : 発注ワークフロー（DB 永続化と broker 呼び出しの保険）
  - order_repository.py, order_record.py, reconciler.py, risk_manager.py, broker_factory.py, broker_api.py など

- src/kabusys/monitoring/
  - monitoring_db.py   : SQLite のスキーマ初期化とアクセスラッパー
  - system_monitor.py   : システム状態・データ鮮度監視
  - trade_monitor.py    : 注文滞留・約定異常検出
  - risk_monitor.py     : ドローダウン・ポジション上限監視
  - kill_switch.py      : フラグファイル方式のシャットダウントリガ
  - alert_manager.py    : LINE への通知
  - monitoring_engine.py: 監視コンポーネントの統合ループ
  - streamlit_dashboard.py : Streamlit ベースの監視ダッシュボード

- src/kabusys/portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
  - ポートフォリオ構築・配分・リスク調整ロジック（純粋関数群）

- src/kabusys/research/
  - factor_research.py, feature_exploration.py
  - DuckDB を使ったファクター計算・将来リターン・IC 計算など

- src/kabusys/ai/
  - news_nlp.py: ニュースを LLM で評価し ai_scores に書き込む
  - regime_detector.py: マクロセンチメント + MA200 で市場レジーム判定

- src/kabusys/utils/
  - process_priority.py: プロセス優先度・CPU affinity 設定（psutil）

注意事項 / 運用上のヒント
------------------------
- DB の分離
  - paper_trading を使うと sqlite のパスが paper_trading 用に切り替わり、本番 sqlite を汚しません。DuckDB（分析データ）は共通パスを使う設計になっています（設定で変更可能）。
- 再起動耐性
  - OrderManager は発注手順を複数段階で永続化することで、クラッシュ後に Reconciler が復元可能な状態を作っています。
- LLM 呼び出し
  - OpenAI の呼び出しはリトライやバックオフを実装していますが、API キーや使用量には注意してください。レスポンスのバリデーションは厳しめになっており、想定外の出力はスキップされます。
- 権限
  - set_process_priority 等は OS により権限が必要な場合があります。設定に失敗しても警告が出てスキップされます。
- kill.flag の管理
  - KillSwitch によって data/kill.flag が作成されると ExecutionEngine は安全に停止する設計です。手動でフラグを置いて停止させる運用も可能です。不要な場合は起動前に削除してください。

付録：よく使うコマンドまとめ
----------------------------
- ExecutionEngine（paper trading）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Monitoring（ポーリング）
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring

- Streamlit Dashboard
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- 依存インストール（最低限）
  - pip install duckdb psutil requests streamlit openai

問い合わせ・拡張
----------------
- コードはモジュール化されているため、ブローカー実装（kabu ステーション API）の交換、戦略ロジックの差し替え、さらなる分析機能の追加が容易です。具体的な拡張やデプロイに関する質問があれば、使用目的や実行環境（OS / Python バージョン / データ量）を添えて問い合わせください。

以上。README の内容に追加してほしい項目（例: サンプル .env、依存関係の固定バージョン、デプロイ手順など）があれば教えてください。