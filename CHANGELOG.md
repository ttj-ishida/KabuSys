# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
このプロジェクトはセマンティックバージョニングに従います。

今リリース: 0.1.0 - 2026-04-13

## [0.1.0] - 2026-04-13

### Added
- 基本アプリケーションパッケージを追加
  - kabusys パッケージの初期実装を追加。バージョンは `__version__ = "0.1.0"`。
- 実行・監視エントリポイント
  - run_execution.py: ExecutionEngine を起動する CLI エントリポイントを追加。  
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用 SQLite（デフォルト: `data/paper_trading.db`）を使用して本番 DB と分離。
    - broker クライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler 組み立て、ExecutionEngine のセッション開始処理を実装。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。  
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番の `sqlite_path` を使用する仕様（監視データは production DB を参照）。
    - プロセス優先度を起動時に High に設定する処理を実行。
- 設定管理
  - kabusys.config.Settings 実装を追加。環境変数から各種設定を取得するプロパティを提供（DB パス、PID ファイルパス、閾値、環境判定など）。
  - `.env` 自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。  
    - 読み込み順: OS 環境 > .env.local > .env。  
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動読み込みを無効化可能。
  - .env 解析機能を強化：
    - `export KEY=val` 形式対応、クォート文字列のバックスラッシュエスケープ対応、インラインコメント処理、保護された OS 環境変数（上書き禁止）など。
  - PAPER 関連設定：
    - `paper_fill_mode`（`instant|partial|never|reject`）のバリデーション。
    - `PAPER_TRADING_SQLITE_PATH` で paper_trading 専用 DB パス指定可能。
- 監視 DB 初期化ユーティリティ
  - `init_monitoring_db` 呼び出しにより監視用テーブルの存在を冪等的に保証。
- ユーティリティ: プロセス優先度 / CPU affinity
  - `kabusys.utils.process_priority.set_process_priority` を追加。Windows / POSIX（Linux, Darwin, FreeBSD）に対応し、呼び出し元は OS を意識せずに優先度を設定可能。
  - `set_cpu_affinity` を追加し、プロセスを先頭 N コアにピン留めする機能を提供（利用不可時は安全にスキップ）。
  - 権限不足や未実装 API の場合は警告ログを出してスキップする実装。
- ポートフォリオ構築モジュール
  - `kabusys.portfolio` 以下の純粋関数群を追加:
    - portfolio_builder: `select_candidates`, `calc_equal_weights`, `calc_score_weights`（スコア全 0 の場合は等配分にフォールバックして警告）。
    - risk_adjustment: `apply_sector_cap`（セクター集中上限のフィルタリング）、`calc_regime_multiplier`（レジームに応じた投下資金乗数。`bull|neutral|bear` 対応、未知は 1.0 にフォールバック）。
    - position_sizing: `calc_position_sizes`（allocation_method=`risk_based|equal|score` をサポート、単元株丸め、aggregate cap によるスケールダウンと端数配分ロジックを実装）。
- リサーチ／ファクター計算
  - `kabusys.research.factor_research` を追加:
    - `calc_momentum`, `calc_volatility`, `calc_value` — DuckDB 上の `prices_daily` / `raw_financials` を参照してファクター群を計算。
    - 各関数はデータ不足時に None を返す挙動や、必要なウィンドウ長・計算方針を明示。
  - `kabusys.research.feature_exploration` を追加:
    - `calc_forward_returns`, `calc_ic`, `factor_summary`, `rank` — 将来リターン計算、IC（Spearman のランク相関）計算、統計サマリ等を実装。外部ライブラリに依存せず純粋 Python 実装。
- AI ニュース NLP スコアリング
  - `kabusys.ai.news_nlp` を追加:
    - raw_news と news_symbols を集約し OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメント（-1.0〜1.0）を算出、`ai_scores` テーブルに書き込むワークフローを実装。
    - バッチサイズ（20銘柄）、記事・文字数のトリム（1銘柄あたり最大 10 記事、3,000 文字）、スコアの ±1.0 クリップ、最大リトライ回数、指数バックオフなどのフェイルセーフを備える。
    - OpenAI API キー解決（引数または環境変数 `OPENAI_API_KEY`）。未設定時は ValueError を送出。
    - 結果の JSON 検証、部分失敗時に既存スコアを保護する書き込み戦略（該当コードのみ DELETE → INSERT）。
- ツール
  - `kabusys.tools.paper_verification_report` を追加:
    - Paper Trading 用検証レポート生成スクリプト（CLI）。`python -m kabusys.tools.paper_verification_report` で実行可能。
    - オプション: `--from`, `--to`, `--db`（DB パスは環境変数 `PAPER_TRADING_SQLITE_PATH` またはデフォルト `data/paper_trading.db`）。
    - 指標: 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（avg/max/P95）など。閾値に基づく PASS/FAIL 判定を出力。
    - P95 計算、日付フィルタ生成、Query の失敗（テーブル欠如など）を安全にハンドリング。
- パッケージエクスポート
  - 各モジュールを __all__ で整理し、研究 API（calc_momentum 等）や portfolio API を上位からインポートできるようにした。

### Changed
- DB 接続方針の明文化
  - 監視（run_monitoring）は KABUSYS_ENV にかかわらず本番の `sqlite_path` を使用する仕様を明確化（監視データの一元化のため）。
  - 実行（run_execution）は paper_trading 環境時に専用の `paper_sqlite_path` を使用して本番 DB と分離。
- .env 読み込みの保護強化
  - OS の環境変数はデフォルトで保護され、`.env.local` の override 時も OS 環境で定義されたキーは上書きされないようにした。
- ロギング初期化
  - CLI スクリプトで basicConfig(level=INFO) を採用（簡易起動時に INFO レベルで動作するように統一）。

### Fixed
- 環境変数パースの堅牢化
  - クォートやバックスラッシュエスケープ、インラインコメント処理を改善し、より実際の .env ファイルに耐性を持たせた。
- ポートフォリオ重み計算のフォールバック
  - スコア合計が 0 の場合に等金額配分へ明示的にフォールバックして警告を出すようにした（calc_score_weights）。

### Documentation / Notes
- 環境変数の主な利用方法
  - KABUSYS_ENV: development | paper_trading | live（無効な値は ValueError）
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒） — 正の整数のみ有効、0 以下や無効値はデフォルト 60 秒 にフォールバックし警告を出力
  - PAPER_FILL_MODE: paper trading の約定シミュレーション方式（instant|partial|never|reject）
  - PAPER_TRADING_SQLITE_PATH: paper trading 用 SQLite DB（デフォルト: data/paper_trading.db）
  - OPENAI_API_KEY: news_nlp の API キー（score_news 呼び出し時に引数で指定することも可能）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env 読み込みを無効化（テスト等で利用）
- AI ニュース機能の運用注意
  - OpenAI の呼び出しは外部 API 利用になるため、API 利用料・レート制限を考慮してください。
  - レスポンスの堅牢性のため JSON バリデーションとリトライを実装していますが、完全な耐障害性は保証されません。部分失敗時は取得済み銘柄のみ書き込みを行います。

### Breaking Changes
- （初版のため特になし）

---

将来的な改善候補（未実装だが TODO としてコード内に記載）
- position_sizing の銘柄別 lot_size 対応（現状は全銘柄共通の単元を想定）。
- apply_sector_cap の価格欠損時のフォールバック（前日終値や取得原価を使う検討）。
- news_nlp のより厳密なレート制御・非同期化やバッチ失敗時の部分再試行ロジックの強化。