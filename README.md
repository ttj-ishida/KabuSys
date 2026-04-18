KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向け自動売買システム「KabuSys」のコアライブラリ群です。
実トレード（live）・ペーパートレード（paper_trading）・開発（development）それぞれに対応し、
発注エンジン、監視・キルスイッチ、ポートフォリオ構築、ファクター研究、LLM を使ったニュース解析などの機能を含みます。

主な特徴
-------

- ExecutionEngine：ブローカークライアント経由で注文管理・リスク管理を行う実行エンジン（run_execution.py で起動）
- Monitoring：システム稼働・注文ログ・リスク監視・Kill Switch を備えた監視基盤（run_monitoring.py、monitoring_engine）
- Portfolio construction：銘柄選定・重み付け・ポジションサイズ計算（kabusys.portfolio）
- Research：DuckDB 上の時系列データを用いたファクター計算、将来リターン・IC 等の解析（kabusys.research）
- AI モジュール：OpenAI を用いたニュースセンチメント評価（news_nlp）・市場レジーム判定（regime_detector）
- ユーティリティ：ログ設定、プロセス優先度設定、.env ウィザード、設定検証ツール 等
- 運用用ツール：Paper Trading の検証レポート生成スクリプト等（kabusys.tools.paper_verification_report）

セットアップ手順
---------------

前提
- Python 3.10 以上（型注釈で | を使用しているため）
- OS によっては psutil の追加権限が必要になる場合があります

1. リポジトリをクローンして作業ディレクトリへ
   - git clone ... && cd <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージのインストール（例）
   - pip install duckdb psutil openai
   - 任意（解析用）: pip install PyYAML

   ※ requirements.txt がない場合は上記を適宜追加してください。

4. .env の初期生成（対話式ウィザード）
   - python -m kabusys.config_setup
     - J-Quants / kabuステーション の資格情報や KABUSYS_ENV 等を設定します
     - .env は絶対に Git にコミットしないでください

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

デフォルトのデータパス（環境変数で上書き可能）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db (paper_trading 用)
- LOG_DIR: logs/ （ログは日次ローテーションで出力）

主な環境変数（抜粋）
- KABUSYS_ENV: 実行環境を指定（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、既定 60）
- PAPER_FILL_MODE: paper_trading 時のモック約定挙動（instant/partial/never/reject）

使い方
-----

起動スクリプト
- ExecutionEngine（発注エンジン）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使い、paper_trading 用 DB (PAPER_TRADING_SQLITE_PATH) に記録します
  - 起動時に data/stop_requested.flag が存在すると起動をスキップします
  - エンジンは別スレッドで実行され、stop flag の検出で停止します

- Monitoring（監視ループ）を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更できます（デフォルト 60 秒）
  - monitoring は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用して監視ログを記録します
  - 実行開始時にプロセス優先度を high に設定し、ログ出力は logs/に日次ローテーションで保存されます

ツール / スクリプト
- 環境設定ウィザード（.env 生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config [--strict]

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB は PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

プログラム的インターフェース（ライブラリ利用）
- ポートフォリオ関連関数（純粋関数）
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier

- 研究用関数
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
  - これらは DuckDB 接続を受け取り prices_daily / raw_financials 等のテーブルを参照します

- AI モジュール（ニューススコアリング）
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key=None) で ai_scores を DuckDB に書き込みます（OpenAI API キー必須）

監視 / キルスイッチの運用
- Kill Switch は条件を満たすと data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります
- 主要トリガー例:
  - ドローダウン閾値超過（RiskMonitor）
  - ポジション上限超過
  - 実行プロセスが停止していると監視で検出された場合
- 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると kill.flag を自動クリアします（本番環境では 0 推奨）

ディレクトリ構成（主要ファイル）
--------------------------------

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理、.env の自動読み込みロジック
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成
  - ai/
    - news_nlp.py             — ニュースの LLM センチメント評価（ai_scores 書込）
    - regime_detector.py      — ETF + マクロセンチメントで市場レジーム判定
  - monitoring/
    - monitoring_db.py        — SQLite による監視ログ永続化層
    - system_monitor.py       — システム状態・データ鮮度監視
    - trade_monitor.py        — 注文ログ監視（滞留・約定異常など）※実装ファイル参照
    - risk_monitor.py         — ドローダウン・ポジション数監視
    - kill_switch.py          — kill.flag の作成/消去
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - alert_manager.py        — アラート送信管理（LINE 等）※実装ファイル参照
  - execution/
    - execution_engine.py     — 実行エンジン本体（EngineConfig 等）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py       — ブローカークライアント生成（Mock / 実クライアント）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - monitoring/               — 監視関連（上記）
  - utils/
    - logging_setup.py        — 統一ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定ユーティリティ

（ここに挙げた以外にも多数の補助モジュールが含まれます。各モジュールの docstring を参照してください。）

運用上の注意
-----------

- .env ファイルは機密情報を含むため絶対にリポジトリにコミットしないでください。
- 本番（KABUSYS_ENV=live）では kill flag の自動クリアやログ・設定を慎重に扱ってください（validate_config が本番用の警告を出します）。
- OpenAI API を利用する機能は API キーが必要で、費用やレイテンシを考慮してください。API 呼び出しはリトライ・フェイルセーフ処理が組み込まれていますが、異常時の影響範囲を理解して運用してください。
- monitoring はデフォルトで本番用 sqlite_path を使います（run_monitoring は環境にかかわらず本番 sqlite_path を参照）。意図せず本番 DB に書き込むことがないよう .env の設定を確認してください。

問題・拡張
---------

- DuckDB / SQLite スキーマの変更はマイグレーション処理を追加してください（monitoring_db.py に簡易マイグレーションあり）。
- ブローカー実装、注文管理、リスクルール等はプロジェクト固有の業務ロジックに合わせて拡張してください。
- テストを書いて CI に組み込むことで安全な運用を助けます。

ライセンス・貢献
---------------

- 本ドキュメントではライセンス情報を明示していません。実運用・配布の前にライセンスを設定してください。
- 貢献は PR / Issue を通じて歓迎します。主要な変更（特に本番挙動や DB スキーマ）については後方互換性に注意してください。

以上。まずは .env を作成し、python -m kabusys.validate_config で設定を確認してから、
python -m kabusys.run_monitoring / python -m kabusys.run_execution を実行して運用を開始してください。