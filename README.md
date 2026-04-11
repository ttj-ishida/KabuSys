# KabuSys

日本株向けの自動売買システムのサンプル実装です。  
本リポジトリは注文管理・リコンシリエーション、ポートフォリオ構築、リスク制御、監視・アラート、簡易的な研究用ファクター計算、LLM を用いたニュースセンチメント評価などの主要コンポーネントを含みます。

---

## プロジェクト概要

- 名前: KabuSys  
- 目的: 日本株の自動売買を想定した実験的なシステム（注文発行、約定同期、ポートフォリオ構築、監視、通知、研究用ツール等）を提供します。  
- 設計方針の一部:
  - DB（SQLite / DuckDB）を用いたデータ管理
  - 発注ロジックと永続化のクラッシュ安全性に配慮（例: OrderSent の二相永続化）
  - Paper trading 環境を分離して実口座のリスクを避ける
  - ニュース解析・市場レジーム判定には OpenAI（gpt-4o-mini）を利用（API キー必須）
  - 監視コンポーネントは LINE によるプッシュ通知と Streamlit ダッシュボードを提供

---

## 主な機能一覧

- ExecutionEngine: シグナルを受けて発注を行う（Gate チェック・リスク管理・push ドレイン等）
- Reconciler: 再起動後の注文状態同期・ポジション差分検出
- OrderManager / OrderRepository: 注文状態マシンと DB 永続化
- RiskManager: 発注前ゲート・レート制限・サーキットブレーカー等
- MonitoringEngine: System / Trade / Risk の定期チェック、kill flag による停止シグナル発行、LINE 通知
- Monitoring DB: system_status / trade_logs / positions / risk_logs / dashboard の永続化
- Portfolio construction: 候補選定、等金額／スコア加重、ポジションサイジング（単元株丸め）
- Research: ファクター計算（モメンタム / ボラティリティ / バリュー）、将来リターン、IC 計算、統計サマリー
- AI モジュール:
  - news_nlp.score_news: raw_news を集約して OpenAI で銘柄別センチメントを算出し ai_scores に記録
  - regime_detector.score_regime: MA200 とマクロニュースの LLM センチメントを組み合わせて market_regime を算出・保存
- Streamlit ダッシュボード: 監視 DB を読み取り可視化

---

## 動作環境 / 依存関係

- Python 3.10 以上（型注釈に `X | Y` を使用しているため）
- 必要なパッケージ（一例）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
- 標準ライブラリ: sqlite3, logging, datetime, pathlib など

仮想環境を作成してインストールする例:
- Unix/macOS:
  python -m venv .venv
  source .venv/bin/activate
  pip install duckdb psutil requests openai streamlit

※ requirements.txt がある場合は `pip install -r requirements.txt` を推奨します。

---

## 環境変数 / .env

このパッケージは起動時にプロジェクトルートの `.env` / `.env.local` を自動読み込みします（既存の OS 環境変数は保護）。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数（使用される箇所とデフォルト）:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能を使う場合に必須)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (監視アラート送信に必要)
- KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
  - `paper_trading` の場合は MockBroker を用い、SQLite DB は `PAPER_TRADING_SQLITE_PATH`（デフォルト data/paper_trading.db）に切り替える
- SQLITE_PATH (デフォルト: data/monitoring.db)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- PAPER_FILL_MODE (paper_trading の約定モード: instant|partial|never|reject)
- PID_FILE_PATH (デフォルト: data/execution.pid)
- KILL_FLAG_PATH (デフォルト: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (起動時に kill.flag を自動削除する場合は "1")
- MONITOR_POLL_INTERVAL (監視ポーリング間隔秒、デフォルト 60) — run_monitoring スクリプトで使用

例: .env スニペット
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
OPENAI_API_KEY=...
KABUSYS_ENV=development
SQLITE_PATH=data/monitoring.db
DUCKDB_PATH=data/kabusys.duckdb
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...

---

## セットアップ手順（簡易）

1. リポジトリをクローン
2. Python 仮想環境作成・有効化
3. 依存パッケージをインストール（上記参照）
4. プロジェクトルートに `.env` を用意して必須変数を設定
5. データディレクトリを作成（デフォルトでは data/ 内を使用）
   mkdir -p data
6. DuckDB/SQLite に必要なテーブルは実行時に自動作成されるコンポーネントが多いです（例: init_monitoring_db）。

---

## 使い方（起動 / 実行例）

※ パッケージをインストールせずソース直下で実行する場合は、リポジトリのルートを PYTHONPATH に含めてください（または該当スクリプトを直接実行）。

基本的な起動例:

- ExecutionEngine を起動（通常実行）
  - 方法 A: パッケージとして
    python -m kabusys.run_execution
  - 方法 B: スクリプトファイルを直接
    python src/kabusys/run_execution.py

  注意:
  - 環境変数 KABUSYS_ENV が `paper_trading` の場合は paper 用 DB に切替え、MockBrokerClient を使用します（本番 DB と分離）。
  - 起動時にプロセス優先度を High に設定しようとします（失敗しても継続）。

- MonitoringEngine を起動（周期的ポーリング）
  - python -m kabusys.run_monitoring
  - または: python src/kabusys/run_monitoring.py
  - ポーリング間隔を環境変数で上書き:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

  特記事項:
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用します（監視は本番DBを参照する想定）。
  - run_monitoring も process priority を High に設定します。

- Streamlit ダッシュボード（監視 UI）
  - コマンド:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは監視 DB を read-only で開きます。MonitoringEngine が先に起動していることを推奨します。

- AI 関連タスク（ニューススコア / レジーム判定）
  - OpenAI API キーを環境変数 `OPENAI_API_KEY` に設定してから利用してください。
  - Python から直接呼び出す例（REPL または短いスクリプト内で）:
    from kabusys.ai.news_nlp import score_news
    import duckdb, datetime
    conn = duckdb.connect('data/kabusys.duckdb')
    score_news(conn, datetime.date(2026,3,20), api_key=None)  # api_key省略なら環境変数を参照

    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, datetime.date(2026,3,20))

- kill flag（ExecutionEngine の停止）
  - 監視側が条件を満たすと `data/kill.flag` に理由を書き込んで ExecutionEngine 停止を誘導します。
  - 手動でクリアするにはファイルを削除するか、KillSwitch.clear() を使うか、起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定して自動クリアを有効化してください。

---

## 運用上の注意

- Paper trading を使うことで発注ロジックを実稼働 DB から切り離せます。テスト時は必ず `KABUSYS_ENV=paper_trading` を確認してください。
- OpenAI を用いる機能は API コスト・レスポンス変動があるため、失敗時フォールバック（スコア=0.0 など）が実装されていますが、運用前に API レートやコストを確認してください。
- Process priority / CPU affinity の設定は OS 権限に依存し失敗する場合があります（ログの警告を確認）。
- 監視は 1 ファイル（SQLite）の DB を永続化します。バックアップや DB ファイルの管理は運用でご検討ください。

---

## ディレクトリ構成（主要ファイルの説明）

- src/kabusys/
  - __init__.py: パッケージ定義、バージョン
  - config.py: 環境変数 / 設定管理（.env 自動読み込み含む）
  - run_execution.py: ExecutionEngine 起動スクリプト
  - run_monitoring.py: SystemMonitor ポーリングスクリプト
  - execution/
    - execution_engine.py: ExecutionEngine 本体（シグナル処理・push ドレイン）
    - order_manager.py: 発注ワークフロー（作成・送信・同期・キャンセル）
    - order_repository.py: （DBアクセス: orders）※詳細はリポジトリ内
    - reconciler.py: 起動時リコンシリエーション（注文・ポジション照合）
    - risk_manager.py: 発注ゲート等のリスク管理
    - broker_factory.py: ブローカークライアント生成（paper/live 切替）
    - broker_api.py: ブローカー API 抽象/エラー定義
  - monitoring/
    - monitoring_db.py: monitoring DB スキーマと永続化 API
    - system_monitor.py: システム / データ鮮度監視
    - trade_monitor.py: 注文滞留 / 約定異常監視
    - risk_monitor.py: ドローダウン / ポジション上限監視
    - kill_switch.py: kill.flag の作成・管理
    - alert_manager.py: LINE 通知送信
    - monitoring_engine.py: 各 Monitor を束ねるループ
    - streamlit_dashboard.py: Streamlit ダッシュボード
  - portfolio/
    - portfolio_builder.py: 候補選定・スコアソート
    - position_sizing.py: 株数計算・割当
    - risk_adjustment.py: セクターキャップ・レジーム乗数
  - research/
    - factor_research.py: モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py: 将来リターン / IC / 統計サマリー
  - ai/
    - news_nlp.py: ニュースから銘柄別センチメント算出（OpenAI 使用）
    - regime_detector.py: 市場レジーム判定（MA200 + LLM）
  - utils/
    - process_priority.py: プロセス優先度 / CPU affinity ユーティリティ

---

## 開発者向け補足

- DB スキーマはコード側で冪等に作成・マイグレーションが行われる箇所があります（例: init_monitoring_db は peak_value カラム追加の処理を含む）。
- テストや CI では `.env` の自動読み込みを無効化するため `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使用してください。
- OpenAI 呼び出し部分はユニットテストで差し替えやすいよう `_call_openai_api` 等が分離されているのでモックしやすい設計です。

---

この README はコードベースに含まれるドキュメント・コメントを基に要点を整理したものです。実行時の詳細な振る舞いや追加の設定は各モジュールの docstring を参照してください。必要であれば、インストール手順やサンプル .env のテンプレートを追記します。