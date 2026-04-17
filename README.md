# KabuSys

日本株向け自動売買システム（ライブラリ/実行ユーティリティ群）

このリポジトリは、戦略・ポートフォリオ構築、発注エンジン、監視（モニタリング）、研究用ファクター計算、ニュース NLP（LLM を使ったセンチメント評価）などを含む自動売買システムのコードベースです。モジュール設計により、本番/ペーパートレードを切り替えられ、監視・リスク管理機能も備えています。

要求環境
- Python 3.10+
- 主な依存（代表例）:
  - duckdb
  - psutil
  - openai (LLM 機能を使う場合)
  - PyYAML（config ファイル検証を行う場合）
- インストール例:
  - pip install duckdb psutil openai pyyaml

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要コマンド例）
- ディレクトリ構成（主要ファイル説明）
- 運用メモ（停止方法・環境変数）

---

プロジェクト概要
- KabuSys は日本株自動売買システムの基盤ライブラリおよび実行スクリプト群です。
- 発注エンジン（ExecutionEngine）、監視システム（Monitoring）、リスク管理、ポートフォリオ構築、研究用ユーティリティ、LLM を使ったニュースセンチメント評価などを備えます。
- 本番（live）・ペーパートレード（paper_trading）・開発（development）を環境変数で切替可能。

---

機能一覧
- 設定管理
  - .env 自動読み込み（プロジェクトルートの .env / .env.local、OS 環境優先）
  - 設定ウィザード（対話式で .env を生成 / 更新）
  - 検証 CLI（.env と config/*.yaml の整合性チェック）
- 実行コンポーネント
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV に応じて本番/モックブローカーを切替）
  - run_monitoring.py: SystemMonitor のポーリングループを起動
- 監視 / リスク管理
  - SystemMonitor: プロセス生存、CPU/メモリ/ディスク、データ鮮度をチェック
  - TradeMonitor: 滞留注文、約定価格異常をチェック
  - RiskMonitor: ドローダウン・ポジション上限を監視、ダッシュボード更新、リスクログ記録
  - KillSwitch: 条件に応じて停止フラグを書き込み ExecutionEngine を止める
  - MonitoringDB: 監視ログ / トレードログ / ダッシュボード等を SQLite に永続化
  - MonitoringEngine: 各 Monitor を束ねてポーリング、アラート通知連携（AlertManager）
- ポートフォリオ構築
  - 候補選定、等金額 / スコア加重の重み計算、リスク調整（セクターキャップ、レジーム乗数）、株数決定（単元丸め、aggregate cap）
- 研究用（Research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー 等）
  - 将来リターン計算、IC（Information Coefficient）計算、特徴量サマリ
- AI（LLM）連携
  - news_nlp: raw_news を集約して OpenAI に送信、銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書込
  - regime_detector: マクロニュース + ETF MA200 乖離を用いた市場レジーム判定（bull/neutral/bear）
- 運用ツール
  - paper_verification_report: ペーパートレード DB を読み取り検証レポートを生成

---

セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   - git clone ... && cd <repo>

2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存ライブラリをインストール
   - pip install duckdb psutil openai pyyaml
   - （開発用）pytest 等を追加

4. .env の作成（推奨: ウィザードを利用）
   - python -m kabusys.config_setup
     - 対話式で .env を生成します（.env は絶対に Git にコミットしないでください）
   - もしくは .env.example を参考に手動作成

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）になります

6. データディレクトリ作成（必要に応じて）
   - デフォルト: data/ 以下にファイルを作成します（duckdb, sqlite, pid/flag 等）

環境変数（主なもの）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境:
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DB パス:
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- OpenAI:
  - OPENAI_API_KEY（news_nlp / regime_detector 使用時）
- ログ:
  - LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）
- その他:
  - PAPER_FILL_MODE（paper_trading のモック約定モード: instant|partial|never|reject、デフォルト instant）
  - MONITOR_POLL_INTERVAL（monitor のポーリング間隔（秒）、run_monitoring で参照、デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START（本番で Kill Flag 自動クリアするか: 1=クリア、0=クリアしない。安全上 0 推奨）

---

使い方（主要コマンド例）

設定ウィザード（.env を対話式で生成）
- python -m kabusys.config_setup

設定検証
- python -m kabusys.validate_config
- Strict モード（警告を失敗扱い）:
  - python -m kabusys.validate_config --strict

ExecutionEngine を起動（発注エンジン）
- 通常（モジュールとして実行）:
  - python -m kabusys.run_execution
- 補足:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）に記録されます（本番 DB と分離）。
  - 起動時に data/execution.pid を作成します（PID ファイル）。run_execution は data/stop_requested.flag が存在すると起動を中止／停止します。

SystemMonitor を起動（監視ループ）
- python -m kabusys.run_monitoring
- オプション:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き（例: MONITOR_POLL_INTERVAL=30）
- 補足:
  - 監視は常に production（本番）用 sqlite_path を使用して監視ログを書き込みます（環境に関係なく sqlite_path を参照）。
  - run_monitoring はプロセス優先度を "high" に設定し、定期的に SystemMonitor.check_once() を呼びます。
  - data/stop_requested.flag が作成されるとループを抜けて終了します。

Paper Trading 検証レポート生成
- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB 指定:
  - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

AI（LLM）機能（ライブラリ呼び出し）
- news_nlp.score_news(conn, target_date, api_key=None)
  - DuckDB 接続を渡して日次でニューススコアを生成し ai_scores テーブルへ書き込み
- regime_detector.score_regime(conn, target_date, api_key=None)
  - マクロニュースと ETF MA200 乖離を組み合わせて market_regime に書込み
- 実行には OPENAI_API_KEY の設定が必要（引数で渡すことも可）。

停止方法（運用）
- ExecutionEngine / Monitoring を安全に停止する方法:
  - run_execution / run_monitoring はプロジェクトルート data/stop_requested.flag を監視します。停止したい場合はこのファイルを作成してください（中断・シャットダウンのシグナル）。
  - KillSwitch（監視側）が条件を満たした場合、Settings.kill_flag_path（デフォルト data/kill.flag）に理由を書き込みます。ExecutionEngine は起動時に kill_flag_clear_on_start に基づき kill.flag を削除する動作が設定可能。
  - PID ファイル: data/execution.pid（存在しない / stale PID の検出は SystemMonitor によりログ化 / 削除されます）

---

ディレクトリ構成（主要ファイル／モジュール説明）
- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数 / .env 自動読み込み、Settings クラス（設定取得ユーティリティ）
  - config_setup.py
    - .env 対話式ウィザード（python -m kabusys.config_setup）
  - validate_config.py
    - 起動前チェック CLI（必須環境変数や config/*.yaml の存在確認）
  - run_execution.py
    - ExecutionEngine 起動スクリプト（本番/ペーパートレード切替、PID/stop フラグ管理）
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔指定可）
  - utils/
    - process_priority.py
      - psutil を使ったプロセス優先度設定 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py
      - SQLite による監視ログ永続化（テーブル作成、マイグレーション、CRUD ユーティリティ）
    - system_monitor.py
      - システム状態チェック（CPU/メモリ/ディスク、プロセス、データ鮮度）
    - trade_monitor.py
      - 発注滞留・約定異常監視
    - risk_monitor.py
      - ドローダウン / ポジション上限監視、ダッシュボード更新、リスクログ
    - kill_switch.py
      - Kill Switch（停止フラグ書込）ユーティリティ
    - monitoring_engine.py
      - 各 Monitor を束ねるエンジン（run / run_once）
    - alert_manager.py
      - （未表示の詳細部分あり）アラート通知管理
  - execution/
    - （発注エンジン関連: EngineConfig, ExecutionEngine, broker_factory, order_manager, order_repository, reconciler, risk_manager 等 — run_execution から組立て）
  - portfolio/
    - portfolio_builder.py
      - 候補選定 / 等金額・スコア配分
    - position_sizing.py
      - 発注株数計算、単元丸め、aggregate cap
    - risk_adjustment.py
      - セクターキャップ、レジーム乗数
  - research/
    - factor_research.py
      - モメンタム / ボラティリティ / バリュー ファクター計算（DuckDB 経由）
    - feature_exploration.py
      - 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py
      - raw_news を LLM でスコアリングし ai_scores に書込むロジック（OpenAI SDK 使用）
    - regime_detector.py
      - マクロニュース + ETF MA200 による市場レジーム判定
  - tools/
    - paper_verification_report.py
      - ペーパートレード DB から検証レポート生成

補足設計ノート（運用上の重要点）
- .env は OS 環境変数より優先度が低く、自動読み込みはプロジェクトルートが検出できる場合のみ行われます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- run_execution と run_monitoring はプロセス優先度を可能な限り高く設定しようとします（psutil の権限や OS に依存）。
- Paper Trading は本番 DB と完全分離（PAPER_TRADING_SQLITE_PATH）。
- AI（OpenAI）呼び出しは堅牢性を意識してリトライやレスポンス検証を備えていますが、API キーや課金に注意してください。
- 監視 DB（SQLite）はモジュール monitoring_db によってマイグレーション（カラム追加）を安全に行います。

---

よくある運用フロー（例）
1. .env を作成（python -m kabusys.config_setup）
2. 設定検証（python -m kabusys.validate_config）
3. データ取得 / DuckDB を準備（prices_daily / raw_financials / raw_news 等）
4. ペーパートレードで動作確認:
   - export KABUSYS_ENV=paper_trading
   - python -m kabusys.run_execution
   - python -m kabusys.run_monitoring
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
5. 十分な検証後、本番切替:
   - export KABUSYS_ENV=live
   - （注意: 本番では LINE 等の通知設定、KILL_FLAG_CLEAR_ON_START 等を慎重に設定）

---

お問い合わせ / 貢献
- README の改善やドキュメント追記、バグ修正は PR を歓迎します。
- 機能追加や設計に関する説明が必要であれば、該当モジュール名を指定して質問してください。

以上。