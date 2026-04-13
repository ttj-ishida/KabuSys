# KabuSys

KabuSys は日本株の自動売買・研究・監視を目的とした Python コードベースです。本リポジトリは取引実行ロジック、ポートフォリオ構築、ファクター研究、監視・アラート、そして一部 AI（ニュースセンチメント・レジーム判定）を含むモジュール群で構成されています。

以下はコードベース向けの README（日本語）です。

---

## プロジェクト概要

KabuSys は以下の主要機能を持つコンポーネント群で構成されています。

- 実行エンジン（ExecutionEngine）: ブローカーと連携して注文を生成・送信・状態同期する。
- 監視エンジン（MonitoringEngine）: システム・注文・リスクをポーリングしてログ・アラート・Kill Switch を管理する。
- ポートフォリオ構築: 候補選定・重み計算・ポジションサイズ算出・セクター制約適用などの純粋関数群。
- リサーチ: DuckDB 上の時系列データを用いたファクター計算（Momentum / Volatility / Value）、特徴量探索ユーティリティ。
- AI モジュール: ニュースを LLM（OpenAI）で評価して銘柄別センチメントを算出、マクロニュースと MA 乖離から市場レジーム判定。
- ツール: Paper Trading 検証レポート生成、Streamlit 監視ダッシュボード など。
- 永続層: SQLite（監視ログ等）と DuckDB（価格データやファクタ処理用）を併用。

---

## 主な機能一覧

- Execution
  - 注文作成 / 送信 / 同期（OrderManager, OrderRepository）
  - 再起動時リコンシリエーション（Reconciler）
  - リスク管理（RiskManager）やオーダー管理（OrderManager）との連携

- Portfolio
  - 候補選定（select_candidates）
  - 等金額・スコア重み・リスクベースの配分（calc_equal_weights / calc_score_weights / calc_position_sizes）
  - セクター上限・レジーム乗数（apply_sector_cap / calc_regime_multiplier）

- Research
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン・IC・統計サマリ（calc_forward_returns, calc_ic, factor_summary）

- AI
  - ニュースセンチメント（news_nlp.score_news）
  - 市場レジーム判定（ai.regime_detector.score_regime）

- Monitoring
  - システム / 注文 / リスク監視（SystemMonitor, TradeMonitor, RiskMonitor）
  - 永続化（monitoring_db.MonitoringDB）
  - アラート（LINE via AlertManager）
  - Kill Switch（ファイルフラグによる ExecutionEngine 停止）
  - Streamlit ダッシュボード（src/kabusys/monitoring/streamlit_dashboard.py）

- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）
  - スクリプト起動用エントリ（run_monitoring.py, run_execution.py）

---

## 必要要件 / 推奨環境

- Python 3.9+
- 主要依存ライブラリ（一例）:
  - duckdb
  - psutil
  - requests
  - streamlit (ダッシュボード利用時)
  - openai (AI 機能利用時)
  - sqlite3（標準ライブラリ）

（プロジェクトの pyproject.toml / requirements.txt があればそれに従ってください）

---

## セットアップ手順

1. リポジトリをクローン / コピー
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb psutil requests
   - ダッシュボードを使う場合: pip install streamlit
   - AI 機能を使う場合: pip install openai
4. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（OS環境変数が優先）。
   - 自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
5. 必須環境変数（使用する機能に応じて）
   - JQUANTS_REFRESH_TOKEN（J-Quants API）
   - KABU_API_PASSWORD（kabuステーション API）
   - OPENAI_API_KEY（AI 機能利用時）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（LINE アラートを使う場合）

---

## 主要な環境変数とデフォルト

- KABUSYS_ENV: 起動環境（development / paper_trading / live）。デフォルト: development
- DUCKDB_PATH: DuckDB ファイルパス。デフォルト: data/kabusys.duckdb
- SQLITE_PATH: 監視用 SQLite パス。デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（paper_trading 時に使用）。デフォルト: data/paper_trading.db
- PAPER_FILL_MODE: Paper Trading の成行/部分充当挙動。デフォルト: instant（instant / partial / never / reject）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス。デフォルト: data/execution.pid
- KILL_FLAG_PATH: Kill Switch のフラグファイル。デフォルト: data/kill.flag
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒）。デフォルト: 60

注意:
- 監視（Monitoring）は KABUSYS_ENV にかかわらず本番の SQLITE_PATH を使用するよう設計されている箇所があります（run_monitoring.pyの挙動）。Paper Trading は run_execution.py で専用 DB に分離されます。

---

## 使い方（起動例）

プロジェクトルートで python モジュールとして実行できます。

- 監視ループ（MonitoringEngine を簡易起動して SystemMonitor を定期実行）
  - 環境変数でポーリング間隔を変更:
    - export MONITOR_POLL_INTERVAL=30
  - 実行:
    - python -m kabusys.run_monitoring

- 実行エンジン（ExecutionEngine）
  - Paper Trading（KABUSYS_ENV=paper_trading をセット）では MockBrokerClient を使用し `data/paper_trading.db` に記録され、本番用 DB と分離されます。
  - 実行:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - 本番（live）: KABUSYS_ENV=live python -m kabusys.run_execution

- Streamlit ダッシュボード（監視情報を可視化）
  - 起動例:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート
  - 実行例:
    - python -m kabusys.tools.paper_verification_report
    - 期間指定:
      - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - DB を指定する場合:
      - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI モジュール（コード内 API）
  - news_nlp.score_news(conn, target_date, api_key=None) — DuckDB 接続を渡して実行。api_key が None の場合は環境変数 OPENAI_API_KEY を参照します。
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## 実行時の挙動メモ / 注意点

- process priority: run_monitoring.py / run_execution.py は起動直後にプロセス優先度を "high" に設定しようとします（kabusys.utils.process_priority.set_process_priority）。
- Kill Switch:
  - KillSwitch はファイル（KILL_FLAG_PATH）を作成することで ExecutionEngine に停止シグナルを送ります。
  - ExecutionEngine 側はこのフラグの存在をチェックして安全停止する想定です。
- Paper Trading:
  - KABUSYS_ENV=paper_trading 時、run_execution は paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番データと分離します。
  - PAPER_FILL_MODE により MockBrokerClient の約定挙動を変更できます。
- .env 自動読み込み:
  - プロジェクトルート（.git または pyproject.toml の存在するディレクトリ）を基準に `.env` と `.env.local` が自動読み込みされます。
  - OS 環境変数が優先され、`.env.local` は上書き可能（ただし OS 環境を保護）。
  - 自動ロードを止めるには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- モニタリング DB マイグレーション:
  - init_monitoring_db は存在しないテーブル／カラムを追加する簡易マイグレーションを行います（例: dashboard.peak_value, trade_logs.latency_ms）。

---

## ディレクトリ構成（主要ファイルと役割）

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数 / Settings 管理（.env 自動ロード含む）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト（paper_trading 用分離対応）
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite ベースの監視ログ永続化層（init / MonitoringDB）
    - system_monitor.py — CPU / メモリ / データ鮮度 / PID チェック
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - monitoring_engine.py — 各 Monitor を束ねてポーリングするエンジン
    - kill_switch.py — kill.flag 管理
    - alert_manager.py — LINE Push 通知ラッパ
    - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
  - execution/
    - order_manager.py — 注文ライフサイクル管理（作成・送信・同期）
    - reconciler.py — 起動時の再同期・ポジション突合
    - （その他: broker_factory 等、ブローカークライアント関連）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数計算・丸め・投下資金調整
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py — ニュースセンチメント計算（OpenAI 呼び出し・バッチ処理・検証）
    - regime_detector.py — マクロ + MA200 乖離で日次レジーム判定（OpenAI 呼び出し）
  - tools/
    - paper_verification_report.py — Paper Trading 結果の検証レポート生成

---

## 開発 / 拡張のポイント

- DuckDB を用いたデータ処理は SQL と Python の混成で記述されています。prices_daily / raw_financials / raw_news 等のスキーマが前提です。
- AI 部分は OpenAI API を使用します。API 呼び出しはリトライ・バリデーション・レスポンス検査を行う実装ですが、コストとレイテンシに注意してください。
- 監視・運用面は Kill Switch / LINE 通知 / Streamlit ダッシュボードで一通りカバーしています。実運用では PID / 権限やファイルパス（data/ 以下）のパーミッションに注意してください。
- 設定は Settings クラス（kabusys.config.Settings）経由で取得する設計です。環境変数名やデフォルトは config.py を参照してください。

---

## よくある質問 / トラブルシュート

- .env が読み込まれない
  - プロジェクトルートが .git または pyproject.toml によって特定されます。配布後やパスが変わった場合は手動で環境変数を設定するか `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使って自前ロードに切り替えてください。
- AI 関連で API エラーが出る
  - OPENAI_API_KEY が正しく設定されているか確認。429/5xx は実装側でリトライしますが、継続的に失敗する場合は API Key や利用制限、ネットワークを確認してください。
- Paper Trading のデータを誤って本番 DB に書き込みたくない
  - run_execution.py は KABUSYS_ENV=paper_trading の場合に PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用して分離します。必ず環境変数を設定してから起動してください。

---

必要があれば、README に実行例の詳しいコマンド（systemd / docker-compose の unit / コンテナ化方法）、DB スキーマやサンプル .env.example の追加、あるいは各モジュールの API 使用例（簡単なコードスニペット）を追記します。どの点を詳しく補足しますか？