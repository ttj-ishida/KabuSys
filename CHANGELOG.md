# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルでは、リポジトリ内の現在のコードベースから推測できる機能追加・変更点・既知の注意点をまとめています。

フォーマット:
- 変更は "Added", "Changed", "Fixed", "Deprecated", "Removed", "Security" のカテゴリに分けています。
- バージョン日付は本ファイル作成時（2026-04-12）を使用しています（推測に基づく初期リリース記述）。

## [Unreleased]

（今後の変更点をここに追記します）

---

## [0.1.0] - 2026-04-12

初回公開（コードベース解析に基づく推測）。以下の主要機能とコンポーネントを含みます。

### Added
- 全体
  - KabuSys パッケージの初期モジュール群を追加。バージョンは `__version__ = "0.1.0"`。
  - DuckDB / SQLite を組み合わせたデータ処理基盤を採用（prices_daily / raw_financials / ai_scores 等のテーブル想定）。
  - 環境変数管理機能（.env 自動読み込み）：プロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を読み込む機能。自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を用意。

- 設定（kabusys.config）
  - Settings クラスを導入し、各種環境変数のラップを提供。
  - 必須環境変数未設定時に分かりやすいエラーメッセージを投げる `_require` 実装（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
  - 環境分類 `KABUSYS_ENV`（development, paper_trading, live）とログレベル `LOG_LEVEL` の検証を追加。
  - Paper Trading 向けの設定:
    - `paper_fill_mode`（instant/partial/never/reject、無効値は例外）
    - `paper_sqlite_path`（デフォルト: data/paper_trading.db）
  - 監視・稼働関連設定（pid_file, kill_flag, 各種閾値: CPU/MEMORY/DISK）を提供。

- 実行スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。
    - 環境に応じて paper_trading 用の専用 SQLite DB を使用（本番 DB と完全分離）。
    - BrokerClientFactory によりブローカークライアントを生成。RiskManager / OrderManager / Reconciler を組み立て、ExecutionEngine.run_session() を実行。
    - duckdb 接続を受け取り研究・分析用のデータにアクセス。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）で上書き可能。無効値はデフォルトへフォールバックし警告を出力。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。

- 監視・プロセス管理ユーティリティ
  - utils/process_priority.py
    - Windows / POSIX を吸収するプロセス優先度設定 `set_process_priority(level)` を追加（high/normal/low）。
    - CPU affinity を設定する `set_cpu_affinity(cpu_count)` を追加。
    - 権限不足や未対応プラットフォーム時は警告を出して安全にスキップする挙動。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder.py
    - 銘柄選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を追加。
    - calc_score_weights は全スコアが 0 の場合に等金額にフォールバックし警告を出す。
  - risk_adjustment.py
    - apply_sector_cap: セクター集中度を評価し、過剰なセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返却（未知レジームは 1.0 にフォールバックし警告）。
    - セクター評価での既知の注意点（price が欠損だと露出が過小評価される）がコメントとして残されている。
  - position_sizing.py
    - 株数決定ロジック（risk_based / equal / score）を実装。
    - 単元（lot_size）単位で丸め、per-position と aggregate（available_cash）上限に基づくスケーリングを行う。
    - コストバッファ（cost_buffer）を考慮した保守的な見積りと、スケールダウン時の余剰配分アルゴリズムを持つ。

- 研究（kabusys.research）
  - factor_research.py
    - Momentum / Volatility / Value 等のファクター計算を DuckDB 上の SQL クエリで実装（ma200, mom_1m/3m/6m, atr20, avg_turnover, per, roe など）。
    - データ不足時は None を返す安全設計。
  - feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、rank、統計サマリー（factor_summary）を追加。
    - 外部依存を可能な限り使わずに純粋 Python と DuckDB で実装。

- AI / NLP（kabusys.ai）
  - news_nlp.py
    - raw_news テーブルを OpenAI API（gpt-4o-mini）でセンチメントスコア化し、ai_scores テーブルへ書き込む処理を実装。
    - Batching（最大 20 銘柄）、トークン肥大化対策（最大記事数・最大文字数）、429/5xx/ネットワーク障害に対する指数バックオフリトライ、JSON レスポンスの厳格バリデーション、スコアの ±1.0 クリップなどを備える堅牢設計。
    - OpenAI API キーは引数または環境変数 `OPENAI_API_KEY` で指定。未設定時は ValueError を送出。
    - ニュース収集ウィンドウ（JST基準）を計算する calc_news_window を提供。
    - 部分失敗時に既存スコアを保護するため、対象コードのみを削除→挿入する戦略を採用（説明コメント）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading DB（デフォルト: data/paper_trading.db）から検証レポートを生成する CLI ツールを追加。
    - 指標: 稼働率(uptime)、注文成功率(fill rate)、送信率(send rate)、P95 レイテンシなどを算出し、閾値に基づいて PASS/FAIL を判定する。
    - 日付フィルタ（--from / --to）対応。DB 存在チェック・SQL エラー時のフォールバックを備える。
  - tools パッケージ初期化ファイルを追加。

- DB 初期化 / 互換性
  - monitoring.monitoring_db.init_monitoring_db を参照する箇所を多箇所で呼び出し、テーブル存在保証（冪等）を行う。

### Changed
- （初回公開のため履歴上の「変更」は該当なし。ただし各モジュールは現時点で設計上の挙動やバリデーションを多く備えており、将来のバージョンで細かい API 変更が想定される旨の注記を残す）

### Fixed
- （初回公開で明示的なバグ修正履歴はなし。コード中には入力検証・例外ハンドリングが追加されており、各所で安全化が図られている）

### Deprecated
- なし（初回公開）

### Removed
- なし（初回公開）

### Security
- OpenAI API キー・各種機密トークンは環境変数経由での管理を想定。Settings により未設定時にエラーを出すことで誤った運用を防ぐ設計。
- .env の自動読み込みは OS 環境変数を保護する実装（protected 引数）となっており、.env.local は上書き可能だが OS 環境変数は保持される。

---

## 既知の制約・注意事項（コードから推測）
- .env 自動読み込みはプロジェクトルートの検出に依存するため、配布後や CWD の違いにより想定通り動作しない可能性がある。必要に応じて `KABUSYS_DISABLE_AUTO_ENV_LOAD` を設定して手動管理すること。
- apply_sector_cap: price_map に欠損（0.0）があるとエクスポージャーが過小評価され、ブロックが外れる可能性がある（コメントで将来的なフォールバック実装が示唆されている）。
- position_sizing: 将来的に銘柄ごとの lot_size を持たせる設計への拡張が想定されている（現状はグローバル lot_size）。
- news_nlp: OpenAI API 呼び出し時のエラー耐性は用意されているが、API クォータやコストの観点から運用上の注意が必要。JSON Mode を前提としており、モデル応答のバリデーションが必須。
- run_monitoring は MONITOR_POLL_INTERVAL の不正値（0 や負値、非整数）を検出してデフォルトにフォールバックするが、監視対象の高頻度ポーリングが必要な場合は適切に調整すること。
- Paper Trading は本番 DB と完全に分離される設計（PAPER_TRADING_SQLITE_PATH を使う）。誤って本番 DB を操作しないよう環境変数の設定を確認すること。

---

## 開発者向けメモ（依存関係・実行に必要なもの）
- Python 標準ライブラリに加え以下の外部パッケージが必要（コードから推測）:
  - duckdb
  - psutil
  - openai
- DB:
  - SQLite（標準ライブラリ）
  - DuckDB（分析・ファクター計算用）
- 実行:
  - run_execution.py / run_monitoring.py / tools/paper_verification_report.py はそれぞれモジュールとして `python -m kabusys.run_execution` 等で実行可能。
  - News NLP 機能を使用する場合は OpenAI API キー（OPENAI_API_KEY）が必要。

---

メモ:
- 本 CHANGELOG は提供されたソースコードの解析に基づいて推測して作成した初期の変更履歴です。実際のコミット履歴やリリースノートが存在する場合は、そちらを優先して参照ください。