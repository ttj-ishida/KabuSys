# Changelog

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」準拠です。  
主要バージョンは semantic versioning に従います。

※ 本ファイルはコードベースの内容から推測して作成しています。実際のコミット履歴と差異がある可能性があります。

## [Unreleased]

### Added
- 環境変数による監視ポーリング間隔上書き（MONITOR_POLL_INTERVAL）に対する追加バリデーションとログ（不正値時はデフォルト 60 秒にフォールバック）。
- AI ニュース NLP モジュール（news_nlp）におけるバッチ処理・リトライ・JSON バリデーション方針の文書化（API キー解決、スコアクリッピング、チャンクング）。
- DuckDB を用いたリサーチ／ファクター計算の設計方針の追記（性能上のスキャンバッファや NULL の扱いに関する注記）。
- position_sizing における cost_buffer を考慮した aggregate cap スケーリングのロジック説明。

### Changed
- .env 自動ロードの挙動を明確化（プロジェクトルートが特定できない場合は自動ロードをスキップ）。
- .env パーサーのふるまい（引用符付き値のエスケープ対応、インラインコメントの扱い）に関する説明を整理。

### Fixed
- psutil を用いた優先度／CPU affinity 設定でアクセス権限不足や未対応プラットフォームで例外が発生した場合に警告でスキップする挙動を明示。

---

## [0.1.0] - 2026-04-17

最初のリリース（コードベースから推測）。以下の機能群と実装が含まれます。

### Added
- 基本モジュール群の実装
  - kabusys パッケージの公開バージョン 0.1.0（src/kabusys/__init__.py）。
- 実行／監視用起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite DB（data/paper_trading.db 相当）を使用し、MockBroker を用いて本番 DB と分離して動作。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する設計。
- 設定／環境管理
  - config.Settings: 環境変数読み込みとバリデーションを行う設定クラスを実装（J-Quants / kabu API / LINE / DB / 監視閾値など）。
  - .env 自動読み込み機能（プロジェクトルートの検出: .git または pyproject.toml を基準）。優先順位は OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
  - .env パーサ実装: export プレフィックス対応、引用符付き値のエスケープ処理、コメント扱いのロジックなど。
  - Settings での入力検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等の有効値チェック）。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: スコア降順で候補選定（タイブレークは signal_rank）。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分。スコア全ゼロ時は等金額へフォールバック。
  - portfolio.position_sizing:
    - calc_position_sizes: risk_based / equal / score の allocation_method をサポート。単元株（lot_size）丸め、max_position_pct / max_utilization 制約、cost_buffer を考慮した aggregate スケーリングを実装。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限を超える場合の候補除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear 対応、未知はフォールバック）。
- リサーチ／ファクター計算（DuckDB ベース）
  - research.factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を計算（ウィンドウ不足時は None）。
    - calc_volatility: ATR20、ATR 比率、20日平均売買代金、出来高比率を計算（NULL の伝播制御に注意）。
    - calc_value: raw_financials と株価を組み合わせて PER / ROE を計算（target_date 以前の最新財務レコードを取得）。
  - research.feature_exploration:
    - calc_forward_returns: 指定ホライズンの将来リターン（LEAD を用いた一括取得）。
    - calc_ic: スピアマンランク相関（IC）計算（有効レコード 3 件未満は None）。
    - rank / factor_summary: ランク付け（同順位は平均ランク）・基本統計量集計。
  - research パッケージは zscore_normalize（kabusys.data.stats から）を再エクスポート。
- AI ニューススコアリング
  - ai.news_nlp:
    - raw_news を OpenAI（gpt-4o-mini）でセンチメントスコア化し、ai_scores テーブルへ書込む処理を設計。ターゲットウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）および UTC への変換ロジック実装。
    - バッチング（最大 20 銘柄／API 呼び出し）、1 銘柄あたりの文字数制限、スコアを ±1.0 にクリップ、429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフのリトライ方針を記載。
    - API キー解決（引数 > 環境変数 OPENAI_API_KEY）と未設定時の ValueError。
    - 出力 JSON の厳密なバリデーションと、部分失敗時の既存スコア保護（対象コードに限定して DELETE/INSERT）方針。
- ユーティリティ
  - utils.process_priority:
    - set_process_priority(level): プラットフォーム差分を吸収してプロセス優先度を設定（Windows / POSIX 対応）。未対応 OS やアクセス権限不足は警告を出してスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数に CPU affinity を設定。引数検証と例外ハンドリングを実装。
- 運用ツール
  - tools.paper_verification_report:
    - Paper Trading 用検証レポート生成 CLI（--from / --to / --db オプション）。稼働率・注文成功率・送信率・P95 レイテンシなどを集計し PASS/FAIL 判定を出力。
    - デフォルト閾値: 稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms。
- DB 関連
  - run_* スクリプトで sqlite3 と DuckDB の接続を使用。monitoring 用 DB 初期化を行う init_monitoring_db 呼び出しが組み込まれている（冪等な初期化を想定）。

### Changed
- 起動時のプロセス優先度をデフォルトで "high" に設定（run_monitoring/run_execution の最初に実行）。
- ExecutionEngine は停止フラグ（data/stop_requested.flag）を監視し、フラグ検出で安全に停止する制御を実装。
- run_execution は paper_trading 環境時に paper_sqlite_path を利用することで本番 DB との完全分離を実現。

### Fixed / Defensive
- .env ファイル読み込みに失敗した場合の警告出力を追加（IOError を警告として扱う）。
- .env の自動ロードで OS 環境変数を保護（protected set）し、.env.local の上書きや .env の既存値保持を正しく制御。
- DuckDB に対する executemany の事前パラメータチェック（空 params の問題に配慮する設計注記）。
- 各種関数がデータ不足時に None を返し安定動作するように設計（例: ファクター計算、latency 計算、レポート集計）。

### Documentation / Comments
- 各モジュールに詳細な docstring を追加し、設計上の注意点（ルックアヘッドバイアス回避、単元株の将来拡張、価格欠損時の TODO など）を明記。

### Removed
- なし（初期リリース）。

### Security
- 外部 API キー（OpenAI など）は引数または環境変数で解決し、未設定時は明示的エラーを発生させる実装。  
  （鍵の取り扱い方法については運用ドキュメントでの追加注意推奨）

---

参照:
- 各モジュールの実装や docstring に基づき機能・挙動を記述しています。実際のリリースノートにはコミット単位の変更点や影響範囲を追記してください。