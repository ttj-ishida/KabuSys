# Changelog

すべての変更は「Keep a Changelog」の形式に従っています。  
このファイルはリポジトリの現在のコードベース（バージョン __0.1.0__）から推測して作成した変更履歴です。

注: 自動で読み込まれる .env の挙動や動作ディレクトリなどは環境に依存します。必要に応じて各 CLI（config_setup / validate_config）や Settings クラスのドキュメントを参照してください。

## [Unreleased]

- （現時点では未リリースの変更はありません）

## [0.1.0] - 2026-04-20

### Added
- 初回公開（0.1.0）。
- 実行 / 監視用エントリポイントを追加
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプト。
    - KABUSYS_ENV が `paper_trading` の場合は Paper Trading 用の専用 SQLite DB（data/paper_trading.db、環境変数で上書き可能）を使用し、本番 DB と完全分離。
    - ブローカクライアントを BrokerClientFactory で生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine をスレッドで実行する。
    - data/stop_requested.flag による停止フラグ検知、実行中の停止制御、PID ファイル出力をサポート。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority を使用）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。
    - 監視用 DB は環境に関わらず本番 sqlite_path を使用して監視テーブルを初期化。
    - data/stop_requested.flag による停止検知、例外発生時のログ出力とループ継続を実装。
- 設定管理 / ウィザード / 検証
  - config.py
    - Settings クラスを実装。環境変数の抽象化とバリデーションを提供（KABUSYS_ENV / LOG_LEVEL 等）。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）に基づく .env 自動読み込み（.env, .env.local）。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - .env のパースは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理等に対応する堅牢な実装。
    - PAPER_FILL_MODE 等の特定環境変数に対する値チェック（有効値のバリデーション）を実装。
  - config_setup.py
    - 対話式の .env 作成 / 更新ウィザードを実装。必須項目・オプション項目のプロンプト、シークレットのマスク表示、.env の書き出しを提供。
    - デフォルト値や説明付きで初期設定生成が可能。
  - validate_config.py
    - 起動前の設定検証 CLI を実装（必須環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の妥当性確認、DB パスの親ディレクトリ確認、config/*.yaml の存在確認とパース（PyYAML 未インストール時は警告））。
    - `--strict` オプションで警告を FAIL 扱い（exit(1)）。
    - 本番（live）環境に対する追加ガード（LINE トークン未設定や Kill Flag の自動クリア設定等の警告）。
- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順で BUY 候補を選択（signal_rank によるタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分（スコア合計 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（既存保有を考慮して当日新規候補をフィルタ）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームは警告の上 1.0 フォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算、単元株丸め、1銘柄上限・aggregate cap（available_cash）処理、cost_buffer（スリッページ・手数料見積り）考慮、余り分の lot 単位での再配分アルゴリズムを実装。
    - risk_based モードでは損切り・許容リスクに基づく株数算出。
- ユーティリティ類
  - utils/logging_setup.py
    - setup_logging を提供。ルートロガーに stdout StreamHandler と 日次ローテーション（TimedRotatingFileHandler、30 日保管）を設定する。
    - ログディレクトリの自動作成、失敗時はファイル出力をスキップしてコンソール出力のみで継続。
    - stdout を使用する理由（ジョブスケジューラ連携）を反映。
  - utils/process_priority.py
    - set_process_priority(level)（high/normal/low）と set_cpu_affinity(cpu_count) を実装。Windows/Linux(Mac含む) の差分を吸収し、権限不足等は警告して安全にフォールバック。
- 分析 DB 統合
  - DuckDB を分析用に採用。Execution / Monitoring スクリプトから duckdb.connect を利用して分析・集計用 DB を扱う設計を導入（Settings.duckdb_path）。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite DB（デフォルト: data/paper_trading.db）から検証レポートを生成する CLI。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標取得と基準（閾値）による PASS/FAIL 判定を実装。
    - 日付フィルタ（--from / --to）や DB パス指定（--db）に対応。
- 研究用モジュール（作業中）
  - research/factor_research.py
    - DuckDB 上の prices_daily / raw_financials を使うファクター計算の骨子を追加（モメンタム / MA200 / ATR / ボラティリティ / 流動性等の計算を想定）。（実装は一部未完の状態）

### Changed
- ロギングのデフォルトを統一
  - 全スクリプトは setup_logging(app_name=...) を呼び出すことで一貫したログ出力先／フォーマットを利用。
- 環境変数の読み込みロジック
  - OS 環境変数を保護して .env.local の上書きを行う仕組みを実装（既存の OS 環境変数は上書きされない）。
  - 自動ロードを無効化するための `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。

### Fixed
- .env パーサーの堅牢性向上
  - export プレフィックス、クォート内のエスケープ、インラインコメントの扱い等に対応し、従来の単純な split/strip による誤解釈を回避。
- 実行中の例外ハンドリング
  - run_monitoring のポーリングループで check_once() 内の例外をキャッチしてログ出力し、次のポーリングまで継続するように改善。
- DB 初期化の冪等性
  - run_execution / run_monitoring の起動時に監視テーブルを init_monitoring_db() で必ず存在するようにして、初回起動や DB 作成漏れに対処。

### Deprecated
- なし

### Removed
- なし

### Security
- .env の生成ファイルに関する注意を明記（config_setup にて .env を生成する際に「絶対に Git にコミットしないこと」を強調）。
- J-Quants / kabu API の認証情報は .env に保存する設計のため、config_setup の出力/表示時にはシークレットをマスク表示。

### Known issues / TODO（コード内コメントより）
- portfolio/risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合、エクスポージャーが過少見積りされる問題がある。将来的には前日終値や取得原価でのフォールバックを検討。
- position_sizing:
  - 将来的には銘柄ごとの lot_size を stocks マスタで持たせる拡張が想定されている。
- research/factor_research:
  - 実装途中（calc_momentum の実装が途中で終わっている）。DuckDB ベースのファクター計算はまだ作業中。
- 一部外部ライブラリ（PyYAML, psutil など）に依存。未インストール時の挙動は警告やスキップでフォールバックする実装になっているが、機能制限が発生する場合がある。

---

▲ 補足: 上記はソースコードから推測して作成した CHANGELOG です。リリースやバージョニング運用の方針があれば日付やセクション名を調整してください。