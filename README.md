README
=====

概要
----
KabuSys は日本株向けの自動売買 / リサーチ / 監視を行う内部ライブラリ群です。本コードベースは以下の主要機能を含みます。

- ExecutionEngine: シグナルに基づく発注ロジック、ブローカーとの同期・再結合（Reconciliation）、リスク管理
- Monitoring: システム稼働状況・注文状態・リスクの定期チェック、LINE 通知、kill フラグによる外部停止
- Research: DuckDB 上の市場データを使ったファクター計算・特徴量解析ユーティリティ
- AI: OpenAI を利用したニュースセンチメント / マクロセンチメント評価（スコアを DuckDB に書き込み）
- Portfolio: 銘柄選定、重み付け、ポジションサイズ計算、セクター制約の適用
- Utils: プロセス優先度・CPU affinity 設定、設定読み込み（.env 自動読み込み）など

機能一覧
--------
- シグナル受信 → Gate ベースのリスク検査 → 発注（市場・指値）フロー
- 発注状態の二相永続化（OrderSent 前後のクラッシュに対する安全設計）
- 起動時の Reconciler による未確定注文の復旧とポジション差分検出
- Execution 用 / Monitoring 用の SQLite（監視）・DuckDB（時系列データ）を分離
- monitoring engine（定期ポーリング）＋ Streamlit ダッシュボード（read-only）で可視化
- LINE 通知（AlertManager）・kill.flag を使った外部停止トリガー
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント（ai_scores）・レジーム判定（market_regime）
- 純粋関数ベースのポートフォリオ構築ロジック（候補選定・重み・株数算出）

セットアップ手順
---------------
前提: Python 3.10+（typing / match 等の言語機能に依存）を想定

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージインストール（最低限）
   - pip install duckdb psutil requests openai streamlit

   補足:
   - sqlite3 は標準ライブラリに含まれます。
   - 実運用では requirements.txt を作成して管理してください。

3. 環境変数 / .env
   - プロジェクトルート（.git / pyproject.toml のある階層）に .env または .env.local を置くと自動で読み込まれます。
   - 自動で読み込ませたくない場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   代表的な環境変数:
   - KABUSYS_ENV : development | paper_trading | live  （デフォルト: development）
     - paper_trading の場合、MockBrokerClient が使われ、paper 用 SQLite（data/paper_trading.db）に分離して記録されます。
   - JQUANTS_REFRESH_TOKEN : J-Quants API トークン（必須となる機能がある場合）
   - KABU_API_PASSWORD : kabu ステーション API のパスワード
   - KABU_API_BASE_URL : kabu API のベース URL（デフォルトは http://localhost:18080/kabusapi）
   - OPENAI_API_KEY : OpenAI API キー（AI 機能を使う場合）
   - DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH : 監視用 SQLite（デフォルト data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH : Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
   - PAPER_FILL_MODE : paper_trading の約定挙動（instant | partial | never | reject）
   - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
   - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID : アラート送信用

   例 (.env)
   ```
   KABUSYS_ENV=paper_trading
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   PAPER_FILL_MODE=instant
   LINE_CHANNEL_ACCESS_TOKEN=<your_token>
   LINE_USER_ID=<your_user_id>
   ```

4. データディレクトリ作成
   - mkdir -p data

5. DuckDB / SQLite の初期化
   - monitoring 用 DB（init_monitoring_db）が各起動スクリプト内で自動作成されます。明示的な初期化は不要です。

使い方
------
起動スクリプト（開発 / 運用例）

- Monitoring を起動（ポーリング型）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で変更できます（デフォルト 60 秒）。
  - 実行:
    - python src/kabusys/run_monitoring.py
    - あるいはモジュールとして: python -m kabusys.run_monitoring
  - 注意: Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用します。

- ExecutionEngine を起動（発注エンジン）
  - KABUSYS_ENV=paper_trading をセットすると MockBroker を使い、paper_trading 用 DB に記録されます。
  - 実行:
    - python src/kabusys/run_execution.py
    - あるいは: python -m kabusys.run_execution

- Streamlit ダッシュボード（監視データ閲覧）
  - 起動コマンド（例: 監視 DB を読み取り専用で開く）:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - コメント欄にあるように、実稼働時は monitoring プロセスがデータを書き込んでいることが前提です。

- AI 関連バッチ（ニューススコア / レジーム判定）
  - プログラムから直接呼び出す:
    - from kabusys.ai.news_nlp import score_news
      - score_news(duckdb_conn, target_date, api_key=None)
    - from kabusys.ai.regime_detector import score_regime
      - score_regime(duckdb_conn, target_date, api_key=None)
  - OpenAI API キーが必要です（api_key 引数または OPENAI_API_KEY 環境変数）。

- ライブラリ的利用（インタラクティブ / スクリプト）
  - ポートフォリオ/リサーチ関数:
    - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
    - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
  - 設定参照:
    - from kabusys.config import settings

注意点 / 運用上のヒント
- ExecutionEngine と Monitoring はそれぞれ PID ファイル / kill.flag を使って相互に状態を検出・制御します。kill.flag を書くと ExecutionEngine は安全に停止する設計です。
- PAPER_FILL_MODE により paper_trading の挙動を制御できます（instant, partial, never, reject）。
- OpenAI 呼び出しはリトライ・バックオフやレスポンス検証を行いますが、API のコスト・レートリミットに注意してください。
- プロセス優先度は起動時に set_process_priority("high") で試みられます。権限がない環境では警告が出力されます。
- .env の自動読み込みはプロジェクトルートを .git または pyproject.toml から探索して行います。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を指定して無効化できます。

ディレクトリ構成（抜粋）
---------------------
src/kabusys/
- __init__.py
- config.py                 — 環境変数 / .env ロード & Settings クラス
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — SystemMonitor ポーリング起動スクリプト

サブパッケージ / 主要モジュール
- execution/
  - execution_engine.py     — ExecutionEngine（発注ループ・push ドレインなど）
  - order_manager.py        — OrderManager（Order state machine 外向き API）
  - order_repository.py     — SQLite ベースの注文永続化（not listed 全体実装あり）
  - reconciler.py           — 再起動時の復旧 / ポジション照合
  - risk_manager.py         — リスク検査（Gate）ロジック
  - broker_factory.py       — BrokerClientFactory（環境に応じて Mock/実ブローカー生成）

- monitoring/
  - monitoring_db.py        — SQLite スキーマ作成 + MonitoringDB 操作
  - system_monitor.py       — システム稼働・データ鮮度監視
  - trade_monitor.py        — 注文滞留・約定異常監視
  - risk_monitor.py         — ドローダウン / ポジション上限監視
  - kill_switch.py          — kill.flag 制御
  - alert_manager.py        — LINE 通知送信（クールダウン管理）
  - monitoring_engine.py    — 各 Monitor を束ねるポーリングエンジン
  - streamlit_dashboard.py  — Streamlit による監視ダッシュボード

- portfolio/
  - portfolio_builder.py    — 候補選定・重み計算
  - position_sizing.py      — 株数算出・スケールダウン・lot 調整
  - risk_adjustment.py      — セクター制約・レジーム乗数

- research/
  - factor_research.py      — Momentum / Volatility / Value の計算（DuckDB）
  - feature_exploration.py  — 将来リターン / IC / 統計サマリー等

- ai/
  - news_nlp.py             — ニュース記事をまとめて OpenAI に投げる処理（batch, retry, validation）
  - regime_detector.py      — ETF MA + マクロニュース LLM で市場レジーム判定
  - __init__.py

- utils/
  - process_priority.py     — プロセス優先度・CPU affinity ユーティリティ

ドキュメント / 参考
------------------
- 各モジュール内に詳細な docstring / コメントが含まれています。実装の仕様や設計意図（例: フェイルセーフ、ルックアヘッドバイアス対策、DuckDB の利用方法など）はコード内コメントを参照してください。
- Streamlit ダッシュボードの起動方法は monitoring/streamlit_dashboard.py の冒頭コメントを参照してください。

ライセンス・貢献
----------------
このリポジトリに付与されたライセンス情報がある場合はプロジェクトルートの LICENSE を参照してください。貢献する際は issue / PR を用いて設計意図やテストを添えてください。

お問い合わせ
------------
実行時のエラーや運用に関する質問は (社内の適切な連絡先や issue tracker) にて報告してください。README の不足や補足希望があればお知らせください。