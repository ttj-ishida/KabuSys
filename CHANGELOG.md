CHANGELOG
=========
すべての変更は「Keep a Changelog」規約に準拠して記載しています。
リリース日はソースコードの最終更新日（このドキュメント作成日）を使用しています。

Unreleased
----------
（なし）

0.1.0 - 2026-04-12
------------------
初期公開リリース。

Added
- 基本パッケージ初期実装
  - パッケージメタ情報を src/kabusys/__init__.py に追加（__version__ = "0.1.0"）。
- 実行 / 監視用エントリポイント
  - run_execution.py
    - ExecutionEngine を起動する CLI エントリポイント。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（data/paper_trading.db をデフォルト）を使用し、本番 DB と分離。
    - BrokerClientFactory でブローカークライアントを生成。オーダー管理、リスク管理、和解（reconciler）を組み合わせてセッションを実行。
    - 起動時にプロセス優先度を "high" に設定。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値（0 以下や非整数）はデフォルトにフォールバックして警告を出力。
    - 監視は環境に関わらず（paper/live など）本番 sqlite_path を使用する設計。
    - SQLite / DuckDB 接続を確立し、監視テーブルの初期化を行う。

- 設定管理
  - config.py
    - プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local の自動ロードを実装（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env パーサを強化（export 形式対応、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントルール）。
    - 環境変数の保護（OS 環境変数を protected として .env.local の上書きを制御）。
    - Settings クラスを導入し、各種設定プロパティ（パス、閾値、PID/kill フラグ、PAPER_FILL_MODE 等）とバリデーションを提供。

- ポートフォリオ構築関連（純関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（スコア降順）、等金額配分、スコア重み配分を実装。スコア全てが 0 の場合は等配分にフォールバック。
  - portfolio/risk_adjustment.py
    - セクター上限適用（apply_sector_cap）。既存保有を基にセクター別エクスポージャーを計算し、上限超過セクターの新規候補を除外。unknown セクターは上限の対象外。
    - レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear + フォールバック挙動）。
  - portfolio/position_sizing.py
    - position サイズ計算（risk_based / equal / score）。単元株（lot_size）丸め、max per-stock 上限、aggregate cap（利用可能現金に対するスケールダウン）を実装。
    - コストバッファ（cost_buffer）を加味した保守的見積り、スケールダウン時の残差配分ロジックを実装。

- 研究（research）モジュール
  - research/factor_research.py
    - Momentum / Volatility / Value ファクター計算を DuckDB SQL を用いて実装（prices_daily / raw_financials テーブル参照）。
    - 各関数は target_date ベースで動作し、データ不足時は None を返す設計。
  - research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算、基本統計サマリー（factor_summary）、ランク変換ユーティリティを実装。
    - 外部依存を持たず標準ライブラリのみで実装。
  - research/__init__.py で主要関数・ユーティリティをエクスポート。

- AI ニュース NLP（OpenAI 統合）
  - ai/news_nlp.py
    - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini 想定）でセンチメントスコアを算出し、ai_scores テーブルへ書き込む処理を実装。
    - 処理は銘柄ごとに記事をトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）し、最大 _BATCH_SIZE=20 銘柄ずつバッチ送信。
    - JSON Mode を前提にレスポンス検証、スコアを ±1.0 にクリップ。
    - 429 / ネットワークエラー / 5xx に対する指数バックオフリトライを実装。
    - OpenAI API キー未設定時は ValueError を送出。

- ユーティリティ
  - utils/process_priority.py
    - プロセス優先度設定（Windows: HIGH_PRIORITY_CLASS 等、POSIX: nice 値）を抽象化して提供。
    - CPU affinity 設定用 set_cpu_affinity を追加（先頭 N コアに固定）。
    - 権限不足や未対応プラットフォームでのフォールバック・警告出力を実装。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポートを生成する CLI。
    - システム稼働率、注文成功率、送信率、P95 レイテンシ等を計算して判定（PASS/FAIL）を出力。
    - DB が未整備（テーブル欠落）の場合は例外を捕捉して N/A を扱うフェイルセーフ実装。

- DB 初期化ヘルパ
  - monitoring.monitoring_db.init_monitoring_db 呼び出しで監視テーブルを冪等に初期化（各起動スクリプトで保証）。

Changed
- （初期リリースのため履歴なし）

Fixed / Robustness improvements
- .env パーサの堅牢化
  - export プレフィックス対応、クォート内部でのバックスラッシュエスケープ処理、インラインコメントの取り扱いルールを追加。
  - OS 環境変数（protected）を尊重して .env ファイルによる不意の上書きを防止。
- 起動フローの安全化
  - 起動直後にプロセス優先度を設定するように統一（run_execution/run_monitoring）。
  - MONITOR_POLL_INTERVAL の不正値（0/負数/非整数）を検出してデフォルトにフォールバックし、time.sleep の ValueError を予防。
- レポート / クエリの耐障害性
  - paper_verification_report は SQL 実行時の sqlite3.OperationalError を捕捉して、テーブル未作成時でも処理を継続・表示できるようにした。
- AI スコアリングのフェイルセーフ
  - OpenAI API の失敗時に部分的にスコアを書き換えないよう、対象コードを絞って DELETE→INSERT を行う戦略を採用（部分失敗時の既存データ保護）。
- position sizing のスケールダウン処理を慎重に実装
  - 小数スケールによる端数を lot_size 単位で再配分する際、raw_shares と _max_per_stock を超えないように安全弁を追加。

Notes
- 監視（run_monitoring）は設計上、本番用 sqlite_path を使用する挙動です。paper_trading 環境でも監視 DB が本番と同じになる点に注意してください（設計上の意図として明記）。
- PAPER_FILL_MODE の有効値は instant/partial/never/reject のいずれかで、無効値は ValueError を発生させます。
- OpenAI 連携機能は実行環境に OPENAI_API_KEY が必要です（score_news の api_key 引数でも指定可能）。
- DuckDB を使った分析・計算関数群は prices_daily/raw_financials 等のスキーマを前提としています。実行前にデータ整備が必要です。

ライセンス・貢献
- 初期リリース。バグ修正・機能追加は CHANGELOG に追記していきます。機能改善や問題報告は issue/PR を通じてお願いします。