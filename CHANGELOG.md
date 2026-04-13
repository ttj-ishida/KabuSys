CHANGELOG
=========
すべての注目すべき変更を記録します。本ファイルは Keep a Changelog の形式に準拠しています。

フォーマットの意味:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Deprecated / Removed / Security: 必要に応じて記載

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-13
### Added
- プロジェクト初期リリース。
- 基本設定管理モジュールを追加（kabusys.config.Settings）。
  - .env / .env.local の自動読み込み（プロジェクトルート検出: .git または pyproject.toml を起点）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化。
  - 必須環境変数取得ヘルパー（未設定時は ValueError を送出）。
  - 多数の設定プロパティを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - OPENAI 用環境変数参照（ai モジュール側）
    - DB パス: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
    - Paper Trading 関連: PAPER_FILL_MODE（instant/partial/never/reject のバリデーション）
    - 監視・プロセス関連: PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
    - 監視閾値: CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
    - 実行環境: KABUSYS_ENV（development/paper_trading/live のバリデーション）
    - LOG_LEVEL バリデーション

- 実行用スクリプト・エントリポイントを追加
  - run_execution.py
    - ExecutionEngine 起動用エントリポイント。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite DB を使用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成（テスト用の Mock を切替可）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
    - 実行開始前にプロセス優先度を "high" に設定。
    - DuckDB 接続（分析・時系列データ利用）を注入。
    - init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等）。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動用。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する点を明記（監視データは本番 DB で集約）。
    - 実行開始時にプロセス優先度を "high" に設定。
    - init_monitoring_db による監視テーブル初期化、DuckDB 接続の確立。

- 監視 DB 初期化ユーティリティを追加（kabusys.monitoring.monitoring_db への呼び出し箇所あり）。
  - run スクリプトから呼ばれ、監視用テーブルが存在することを保証。

- Portfolio 構築関連モジュールを追加（kabusys.portfolio）
  - portfolio_builder: select_candidates / calc_equal_weights / calc_score_weights
    - 候補選定（スコア降順、signal_rank によるタイブレーク）
    - スコア加重配分は全スコアが 0 の場合に等配分へフォールバック（警告ログ）
  - risk_adjustment: apply_sector_cap / calc_regime_multiplier
    - セクター集中上限チェック（売却予定コードの除外、"unknown" セクターは上限を適用しない）
    - レジームに応じた投下資金乗数（bull/neutral/bear のマッピングとフォールバック）
  - position_sizing: calc_position_sizes
    - allocation_method ("risk_based" / "equal" / "score") に対応した株数決定ロジック
    - 単元株（lot_size）丸め、per-stock 上限、aggregate cap（available_cash）によるスケーリング
    - cost_buffer を用いた約定コスト保守見積り、残差を lot 単位で割り振るアルゴリズム

- 研究（research）モジュールを追加（kabusys.research）
  - factor_research: calc_momentum / calc_volatility / calc_value
    - DuckDB の prices_daily / raw_financials を用いたファクター計算（モメンタム、ATR、流動性、PER/ROE 等）
    - MA200 の取り扱いやウィンドウ不十分時は None を返す堅牢設計
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
    - 将来リターン計算（可変ホライズン、入力検証）
    - スピアマン IC（ランク相関）計算（ties は平均ランクで処理）
    - 基本統計量サマリ（count/mean/std/min/max/median）
  - zscore_normalize を外部（kabusys.data.stats）から re-export

- AI ニュース NLP モジュールを追加（kabusys.ai.news_nlp）
  - OpenAI API（gpt-4o-mini）を用いたニュースセンチメント評価機能
  - 処理設計:
    - タイムウィンドウ計算（JST を基準に UTC に変換）
    - 銘柄ごとに記事を集約（最大記事数、最大文字数でトリム）
    - 最大 20 銘柄 / チャンクでバッチ送信
    - 429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフでのリトライ（上限あり）
    - レスポンス検証、スコアを ±1.0 にクリップ
    - 成功スコアのみ ai_scores テーブルへ書き込み（部分更新戦略）
  - API キー解決（引数 > 環境変数 OPENAI_API_KEY）、未設定時は ValueError

- ユーティリティを追加（kabusys.utils.process_priority）
  - set_process_priority(level) — Windows / POSIX を吸収して優先度を設定（"high"/"normal"/"low"）
    - 権限不足や未対応 OS の場合は警告ログでスキップ
  - set_cpu_affinity(cpu_count) — カレントプロセスを最初の N コアへピン留め（許容範囲チェック・権限不足時はスキップ）

- CLI ツールを追加（kabusys.tools.paper_verification_report）
  - Paper Trading 用検証レポート生成スクリプト
    - 引数: --from / --to / --db
    - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）
    - 指標:
      - 稼働率（uptime）閾値 99.0%
      - 注文成功率（fill rate）閾値 90.0%
      - 送信率（send rate）閾値 95.0%
      - P95 レイテンシ閾値 200 ms
    - DB の欠損やテーブル未存在時には N/A / 0 を扱いフェイルセーフに出力

- パッケージ基礎情報を追加（kabusys.__init__.__version__ = "0.1.0"）

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Notes / Implementation details
- 多くのモジュールは「メモリ内純粋関数」設計で副作用を最小化（特に portfolio / research モジュール）。
- DuckDB をデータ分析用途に利用（prices_daily / raw_financials 等のテーブル前提）。
- 監視用 DB 初期化は冪等であり、複数プロセスからの呼び出しを想定した安全設計。
- 実行スクリプトは起動直後にプロセス優先度を上げるため、実行環境の権限によっては警告が出る場合あり。
- OpenAI を利用する機能は API キー必須。API のレート制限やネットワーク障害を考慮したリトライロジックを導入。

### Security
- 外部 API キー等の機密情報は環境変数経由で管理する設計（.env 自動読み込みあり）。
- .env の読み込みは OS 環境変数を保護するため override の既定挙動を制御。

---

今後の更新候補（参考）
- position_sizing の lot_size を銘柄ごとに可変にするためのマスタ参照対応
- ai.news_nlp のレスポンス検証・エラー時の部分ロールバック処理の堅牢化
- run_monitoring/run_execution の systemd などサービス化向け改善（再起動・監視統合）
- テストカバレッジ拡充（特に数値アルゴリズム部分）

以上