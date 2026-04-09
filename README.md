KabuSys — README
=================

概要
----
KabuSys は日本株の自動売買／リサーチ／監視用ライブラリ群です。  
主に以下を目的として設計されています。

- DuckDB 上のマーケットデータを使ったファクター計算・リサーチ
- ポートフォリオ構築（銘柄選定、配分、ポジションサイズ決定、セクター制限）
- OpenAI を用いたニュースセンチメント・市場レジーム判定（AI 補助）
- ExecutionEngine を中心とした発注制御・再同期（リコンシリエーション）
- 監視（System / Trade / Risk）と LINE によるアラート送信、Streamlit ダッシュボード

小規模・モジュール化を重視し、DB 参照は明示的に行い、外部 API 呼び出しは該当機能のみで集中管理されています。

主な機能
--------
- 環境設定管理
  - .env / .env.local / OS 環境変数のロード（自動化、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - 必須設定のバリデーション（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）
- ポートフォリオ構築
  - 候補選定: スコア順で上位 N を選択（select_candidates）
  - 重み付け: 等配分 / スコア加重（calc_equal_weights, calc_score_weights）
  - リスク調整: セクターキャップ適用、レジーム乗数（apply_sector_cap, calc_regime_multiplier）
  - ポジションサイズ決定（リスクベース / 等分 / スコアベース）、単元丸め、集計キャップ（calc_position_sizes）
- リサーチ（DuckDB ベース）
  - モメンタム・ボラティリティ・バリュー算出（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算、IC（スピアマン）や統計サマリー（calc_forward_returns, calc_ic, factor_summary）
  - Z スコア正規化ユーティリティ（kabusys.data.stats 経由）
- AI（OpenAI）機能
  - ニュース記事の銘柄別センチメントスコアリング（news_nlp.score_news）
  - マクロニュース + ETF MA による市場レジーム判定（ai.regime_detector.score_regime）
  - バッチング、リトライ、レスポンス検証、フェイルセーフ設計済み
- Execution（発注）
  - OrderManager / OrderRepository / Reconciler / ExecutionEngine による注文生成・送信・同期
  - 再起動時のリコンシリエーション（OrderSent 状態の復旧・ポジション差分検出）
  - Gate ベースの多段リスク検査（シグナルレベル・エグゼキューションレベル・セッション中監視）
- 監視
  - MonitoringDB（SQLite）によるログ / テーブル管理（init_monitoring_db）
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager（LINE 送信）
  - Streamlit ダッシュボード（src/kabusys/monitoring/streamlit_dashboard.py）

セットアップ
----------
前提
- Python 3.10 以上（型注釈・パイプ形式 Union を使用）
- DuckDB、OpenAI SDK、psutil、requests、streamlit 等の外部ライブラリ

例: 仮想環境を作成して依存をインストールする
1. 仮想環境作成 / 有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージのインストール（プロジェクトに requirements.txt がない場合は主要パッケージを個別に）
   - pip install duckdb openai psutil requests streamlit

3. プロジェクトルートに .env を作成（自動読み込み機能によりプロジェクトルートから .env/.env.local を読みます）
   - .env のテンプレート例:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_api_password
     OPENAI_API_KEY=sk-...
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LINE_CHANNEL_ACCESS_TOKEN=                 # LINE 通知を使う場合
     LINE_USER_ID=
   - 注意: JQUANTS_REFRESH_TOKEN と KABU_API_PASSWORD は Settings クラスで必須となっています（取得に応じて設定してください）。

4. Monitoring DB の初期化（監視機能を使う場合）
   Python レベル例:
   import sqlite3
   from kabusys.monitoring.monitoring_db import init_monitoring_db
   conn = sqlite3.connect("data/monitoring.db")
   init_monitoring_db(conn)

使い方（主要な呼び出し例）
-------------------------

- 環境設定の取得
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  # 他のプロパティ: settings.kabu_api_password, settings.duckdb_path, settings.is_live など

- DuckDB を使ったリサーチ（例: モメンタム計算）
  import duckdb
  from datetime import date
  from kabusys.research import calc_momentum
  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, date(2026, 3, 20))

- ニュースセンチメントのスコア付け（OpenAI API 必須）
  from kabusys.ai.news_nlp import score_news
  import duckdb
  from datetime import date
  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, date(2026, 3, 20), api_key="sk-...")

- 市場レジーム判定（OpenAI API 必須）
  from kabusys.ai.regime_detector import score_regime
  import duckdb
  from datetime import date
  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, date(2026, 3, 20), api_key="sk-...")

- MonitoringEngine / Streamlit ダッシュボード
  - 監視エンジンは MonitoringDB（SQLite）、SystemMonitor（psutil + DuckDB）、TradeMonitor（order repo）等と組み合わせて使用します。テスト用に run_once() が用意されています。
  - Streamlit ダッシュボード起動:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- ExecutionEngine（本番セッション実行）
  ExecutionEngine は BrokerAPIProtocol 実装（ブローカークライアント）、OrderRepository（SQLite 実装）、RiskManager 等を渡して利用します。詳細は ExecutionEngine クラス docstring を参照してください。

自動 .env ロードの挙動
--------------------
- プロジェクトルートは .git または pyproject.toml を基準に __file__ から探索します（CWD に依存しません）。
- ロード順序: OS 環境変数 > .env.local (override=True) > .env (override=False)
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途など）。

主要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- OPENAI_API_KEY (AI 機能を使う場合必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_FILL_MODE (paper trading 向け: instant/partial/never/reject)
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（AlertManager 用）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START（ExecutionEngine / KillSwitch）

ディレクトリ構成（主なファイル）
------------------------------
src/kabusys/
- __init__.py                  — パッケージ定義、バージョン
- config.py                    — 環境変数 / 設定管理（.env 自動読み込み）
- portfolio/
  - __init__.py
  - portfolio_builder.py       — 候補選定・配分重み
  - position_sizing.py         — 株数決定・集計キャップ・単元丸め
  - risk_adjustment.py         — セクター上限・レジーム乗数
- research/
  - __init__.py
  - factor_research.py         — momentum / volatility / value の計算
  - feature_exploration.py     — 将来リターン・IC・統計サマリー
- ai/
  - __init__.py
  - news_nlp.py                — ニュースセンチメント（OpenAI 経由）
  - regime_detector.py         — マクロ + MA によるレジーム判定（OpenAI 経由）
- monitoring/
  - __init__.py
  - monitoring_db.py           — SQLite テーブル定義・MonitoringDB（CRUD）
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - alert_manager.py           — LINE push
  - kill_switch.py
  - monitoring_engine.py
  - streamlit_dashboard.py
- execution/
  - broker_api.py              — Broker API のデータモデル・Protocol・例外
  - order_manager.py
  - order_repository.py        — (存在を想定) Orders DB 操作
  - reconciler.py
  - execution_engine.py
  - ...                        — その他 execution 関連
- monitoring/                   — 監視関連（上記）
- research/, portfolio/ etc.    — 他のユーティリティ群

設計上の注意点 / 運用上のポイント
--------------------------------
- DuckDB / SQLite を用いる設計のため、データファイルのバックアップ・整合性に注意してください。
- OpenAI を利用する機能は API 呼び出し失敗時にフェイルセーフで処理を継続する設計ですが、API キーや料金に注意してください。
- ExecutionEngine は実際のブローカー API と組み合わせる想定です。ローカルまたは paper_trading 環境で十分にテストしてから production 環境へ移行してください。
- kill.flag / PID 管理により単一プロセス制御を行います。運用時は PID ファイルの配置先や権限を確認してください。
- thread / DB commit の順序やクラッシュ耐性を考慮した永続化戦略（OrderSent の早期永続化など）が各所に実装されています。内部実装を変更する場合はリコンシリエーションロジックとの整合性を確認してください。

さらに詳しく
-------------
各モジュールの docstring / 関数コメントに詳細設計や期待される振る舞いが記載されています。実装の理解や拡張を行う際はそれらを参照してください。

ライセンス / 貢献
-----------------
（ライセンス表記や貢献ガイドラインがあればここに追記してください）

---

ご要望があれば以下のドキュメントを追加作成できます：
- デプロイ / systemd 起動例
- オペレーション手順（日次運用チェックリスト）
- テスト用モック（BrokerAPI のスタブ）とユニットテストのサンプルコード