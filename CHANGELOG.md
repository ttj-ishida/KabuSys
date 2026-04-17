# Changelog

すべての注目すべき変更をこのファイルに記録します。
このプロジェクトでは "Keep a Changelog" の慣習に従い、後方互換性のある変更は "Changed"、新機能は "Added"、バグ修正は "Fixed"、非推奨は "Deprecated"、削除は "Removed"、セキュリティ関連は "Security" のセクションに分類します。

※ 日付はリリース日を示します。

## [Unreleased]
（現在無し）

## [0.1.0] - 2026-04-17
初回リリース。自動売買システムのコア機能（設定管理・実行エンジン起動・監視・ポートフォリオ構築・リサーチ・ニュースNLP 等）を実装。

### Added
- 全体
  - パッケージ初期リリース (kabusys v0.1.0)。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するコマンドライン用スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は MockBroker を使用し、Paper Trading 用 SQLite DB（デフォルト: data/paper_trading.db）に完全分離して記録する挙動を実装。
    - 停止制御ファイル (data/stop_requested.flag) の検出による安全な終了処理を実装。
    - engine の PID を data/execution.pid に書き出す仕組みを想定（Settings 経由の pid_file パス対応）。
    - 起動時にプロセス優先度を "high" に設定する処理を追加。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト: 60秒）。不正値は警告してデフォルトにフォールバック。
    - 監視処理は実行環境にかかわらず本番用の sqlite_path を使用する設計（監視データは本番 DB に集約する想定）。
    - 停止フラグ (data/stop_requested.flag) によるループ中断、KeyboardInterrupt のハンドリングを実装。
    - 起動時にプロセス優先度を "high" に設定する処理を追加。

- 設定管理
  - config.py
    - Settings クラスを実装し、環境変数から各種設定を取得する API を提供。
    - .env/.env.local の自動ロード機能を実装（OS 環境変数優先、.env.local は上書き可能）。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - .env パーサはコメント、`export KEY=val` 形式、クォートとバックスラッシュエスケープに対応する堅牢な実装。
    - 各種設定プロパティ:
      - DB パス: `DUCKDB_PATH`, `SQLITE_PATH`（paper trading 用に `PAPER_TRADING_SQLITE_PATH` を別途サポート）
      - PID / Kill フラグ周り: `PID_FILE_PATH`, `KILL_FLAG_PATH`, `KILL_FLAG_CLEAR_ON_START`
      - 監視閾値: `CPU_THRESHOLD_PCT`, `MEMORY_THRESHOLD_PCT`, `DISK_THRESHOLD_PCT`
      - 環境種別 `KABUSYS_ENV` のバリデーション（`development`, `paper_trading`, `live`）
      - `PAPER_FILL_MODE` の検証（有効値: "instant" | "partial" | "never" | "reject"）

- Execution コンポーネント（骨格）
  - run_execution 内で利用する ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager 用の組み立てロジック（設定値と初期化手順）を追加（具体的な実装は別モジュールに分離されている想定）。
  - RiskManager のデフォルト RiskConfig 値を設定（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）。

- 監視
  - monitoring_db.init_monitoring_db の呼び出しで監視テーブルの存在を保証（冪等性）する処理を起動スクリプトに統合。

- ユーティリティ
  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でプロセス優先度を設定するユーティリティを追加。
    - Windows: psutil の HIGH_PRIORITY_CLASS 等を使用、POSIX (Linux/Mac/FreeBSD) では nice 値を設定。
    - CPU affinity を固定する set_cpu_affinity 関数を追加（指定が None のときは変更しない）。権限エラーは警告で回避。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py
    - シグナル選別（select_candidates）: スコア降順、同点は signal_rank 昇順でタイブレーク。
    - 重み計算: 等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights)。全スコアが 0 の場合は等金額にフォールバックして警告。

  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap を実装: 既存保有のセクター別エクスポージャーを計算し、特定セクターが max_sector_pct を超える場合はそのセクターの新規候補を除外（"unknown" セクターは除外しない）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull=1.0, neutral=0.7, bear=0.3、未知は 1.0 でフォールバックして警告）。

  - portfolio/position_sizing.py
    - 株数計算 calc_position_sizes を実装。allocation_method に応じて "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）丸め、per-position・aggregate（available_cash）上限、cost_buffer（手数料・スリッページ見積り）を考慮したスケールダウンロジックを実装。
    - リスクベース方式では stop_loss_pct を用いてポジションサイズを決定。価格欠損時のスキップやログを実装。
    - スケールダウン時に残余キャッシュを利用して端数の lot_size を再配分するロジックを実装。

- リサーチ機能
  - research/factor_research.py
    - モメンタム、ボラティリティ、バリュー系のファクター計算関数を実装:
      - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を duckdb の prices_daily テーブルから計算（ウィンドウ・欠損管理あり）。
      - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比を計算（true_range の NULL 伝播を正しく扱う）。
      - calc_value: raw_financials テーブルから最新財務データを取得し PER / ROE を計算（EPS が 0 または欠損なら None）。
    - DuckDB を使用した SQL+Python 混合実装でパフォーマンスを意識。

  - research/feature_exploration.py
    - 将来リターン calc_forward_returns（任意ホライズン、入力検証あり）、IC 計算 calc_ic（Spearman のランク相関）、列ごとの統計量 factor_summary、ランク変換 rank を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装（pandas 非依存）。

  - research/__init__.py で上記機能を公開。

- AI / ニュース NLP
  - ai/news_nlp.py
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI API (gpt-4o-mini) を用いて銘柄ごとのセンチメント（-1.0〜1.0）を算出して ai_scores テーブルへ書き込む仕組みを実装（主な設計）。
    - バッチ処理（1 回に最大 20 銘柄）、トークン対策（1 銘柄あたり最大記事数/文字数制限）、429/ネットワーク/5xx 系のリトライ（指数バックオフ）を実装。
    - レスポンス検証（JSON の構造・型チェック）、スコアの ±1.0 クリップ、部分失敗時の既存スコア保護（対象コードに限定して DELETE→INSERT）といった安全策を設計。
    - ニュース収集ウィンドウは JST ベースで設計（前日 15:00 JST 〜 当日 08:30 JST を UTC に変換して利用）。calc_news_window を提供。
    - API キーは引数または環境変数 OPENAI_API_KEY を使用。未設定時は ValueError。

- CLI ツール
  - tools/paper_verification_report.py
    - Paper Trading 検証レポート生成スクリプトを追加。
    - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH または --db で上書き可）。
    - 集計指標:
      - 稼働率（system_status）
      - 注文成功率/送信率（trade_logs）
      - リスク却下数（risk_logs）
      - レイテンシ（avg / max / P95）
    - PASS/FAIL 判定基準（デフォルト閾値）を定義:
      - 稼働率 >= 99.0%
      - 成立率 (fill_rate) >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - 日付フィルタ (--from / --to) と出力フォーマットを提供。

### Changed
- パッケージ構成を整理して機能別モジュールを分離（portfolio, research, ai, tools, utils, monitoring, execution 等）。
- データ永続化は sqlite + duckdb の組み合わせで想定。監視用テーブルは sqlite 側で管理。

### Fixed
- （本リリースは初版のため該当なし）

### Deprecated
- （本リリースは初版のため該当なし）

### Removed
- （本リリースは初版のため該当なし）

### Security
- OpenAI API キーや各種秘密情報は Settings 経由で環境変数から取得する設計。自動 .env ロード機能は OS 環境変数を上書きしない保護を実装。

---

注意事項 / 運用メモ
- run_monitoring は監視 DB（settings.sqlite_path）を本番用として扱う設計のため、開発環境で監視データを分離したい場合は sqlite_path を明示的に変更してください。
- run_execution は paper_trading 環境で Paper Trading 用 DB に書き込むことで本番データと分離します（settings.is_paper を参照）。
- .env の自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト環境向け）。
- process priority / CPU affinity の設定は権限やプラットフォームに依存します。権限不足時はログに警告が出てスキップされます。
- ai/news_nlp の実行は OpenAI API の利用料金・利用制限に注意してください。API のレート制限時は実装済みのリトライロジックが働きますが、運用では適切なキーと利用制限設定を行ってください。

もし詳細な変更点（ファイル毎の差分や実装上の注意点）を CHANGELOG にさらに追加したい場合は、どのモジュールに重点を置くか指示してください。