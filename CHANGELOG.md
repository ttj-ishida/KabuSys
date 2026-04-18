# Changelog

すべての重要な変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog 準拠で維持されています。  

フォーマット:
- Unreleased: 将来のリリースで取り込まれる変更
- 各リリース: 変更内容をカテゴリ別に記載（Added / Changed / Fixed / Security / Notes）

## [Unreleased]

## [0.1.0] - 2026-04-18
初回リリース。以下の主要機能・ユーティリティ群を追加しました。

### Added
- 実行エントリ・監視
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（data/paper_trading.db 既定）を使用。
    - BrokerClientFactory を介したブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のセッション実行（スレッド起動）を実装。
    - 停止フラグ（data/stop_requested.flag）検知で安全に停止する仕組み。
    - 実行時 PID を data/execution.pid に記録。
  - run_monitoring.py: SystemMonitor 用ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出す。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する設計（監視データは統一 DB）。
    - 停止フラグでループを終了し、SQLite / DuckDB 接続を確実にクローズする取り回し。

- 設定管理
  - config.py: Settings クラスを追加。環境変数（.env 自動ロード含む）から各種設定を提供。
    - 自動 .env ロード: プロジェクトルート（.git もしくは pyproject.toml を基準）を探索して .env / .env.local を読み込み（OS 環境変数を保護）。
    - .env パース機能 (_parse_env_line) を実装（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理）。
    - 多数のプロパティを提供（J-Quants トークン、kabu API、DuckDB/SQLite パス、Paper Trading 設定、監視しきい値、環境種別判定等）。
    - PAPER_FILL_MODE の値検証（instant/partial/never/reject）。

  - config_setup.py: 対話式 .env 作成ウィザードを追加。
    - セット項目定義、既存 .env の読み込み・Enter で再利用、保存前の確認表示、.env ファイル生成（テンプレート付き）。

  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース（PyYAML があれば内容検証）。
    - --strict オプションで警告を失敗扱い（exit 1）にできる。

- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py:
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30世代）を設定する共通セットアップ関数 setup_logging を追加。
    - ログディレクトリ自動作成試行。失敗時はファイル出力をスキップしてコンソールのみで継続。
    - LOG_LEVEL と LOG_DIR の環境変数を考慮した解決ルール。
  - utils/process_priority.py:
    - クロスプラットフォームなプロセス優先度設定 set_process_priority を追加（Windows / POSIX(nice) を吸収）。
    - CPU 固定用 set_cpu_affinity を追加。権限不足や未対応 OS の場合は警告を出して安全にスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順で選定（同点は signal_rank でブレーク）。
    - calc_equal_weights / calc_score_weights: 重み計算。スコア合計が 0 の場合は警告して等分配へフォールバック。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限を実装。既存ポジションのセクター別時価計算に基づき、上限を超えるセクターの新規候補を除外。unknown セクターは除外対象にしない。
    - calc_regime_multiplier: 市場レジームに応じた投下乗数（bull/neutral/bear）を提供、未知のレジームは警告して 1.0 にフォールバック。
  - portfolio/position_sizing.py:
    - calc_position_sizes: 等配分 / スコア配分 / リスクベース配分に基づく株数計算を実装。
    - 単元株（lot_size）丸め、per-stock 上限、aggregate cap スケーリング（cost_buffer を考慮）、残差分配ロジックを実装。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 検証レポート生成スクリプトを追加。system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・レイテンシ等の指標を集計し PASS/FAIL 判定を出力。
    - P95 算出、期間フィルタ（--from/--to）、DB パス解決（オプション / 環境変数 / デフォルト）を実装。
    - 既定の判定基準（稼働率 99%, 成功率 90% 等）を定義。

- 研究用ファクター計算（着手）
  - research/factor_research.py: DuckDB を使ったファクター計算基盤を追加（モメンタム等の計算方針と定数定義、calc_momentum の骨組みを実装開始）。

- パッケージ情報
  - __init__.py にバージョン 0.1.0 を設定。

### Changed
- DB の取り扱い
  - run_monitoring は環境に依らず Settings.sqlite_path（本番 sqlite_path）を使用する仕様を明確化。監視データは環境分離せず統一 DB を想定。
  - run_execution は paper_trading 環境時に paper_sqlite_path を使用することで本番 DB と完全分離する挙動を実装。

- ログ出力
  - logging_setup により全起動スクリプト間でログ出力の方式（stdout + 日次ファイル）を統一。

- .env 自動ロード
  - プロジェクトルートの検出を .git / pyproject.toml を基準に行うため、CWD に依存しない自動読み込みを実現。
  - .env.local の上書き優先度（OS 環境変数は保護）を実装。

### Fixed
- 環境変数パースの堅牢化
  - .env パーサでクォート内のエスケープや inline コメントを正しく扱うように改善。
- MONITOR_POLL_INTERVAL の扱い
  - 不正（0/負数/非整数）な MONITOR_POLL_INTERVAL を与えられた場合に警告を出しデフォルトにフォールバックする処理を追加（time.sleep に渡して ValueError が出るのを防止）。

### Security
- .env ファイルの取り扱いに関する注意喚起を config_setup.py のテンプレートに記載（.env を絶対に Git にコミットしない旨）。
- Settings._require() は必須環境変数未設定時に ValueError を投げることで起動前に明確に失敗させるようにして意図しない起動を防止。

### Notes / Todo
- research/factor_research.py はモメンタム等の計算ロジックの実装が途中（calc_momentum の実装続行が必要）。
- portfolio.position_sizing の価格欠損時の扱い（price が 0.0 の場合のフォールバックロジック）については TODO コメントあり。前日終値や取得原価等のフォールバックを検討する必要あり。
- process_priority と set_cpu_affinity は権限不足や環境差分でスキップする安全設計だが、運用環境での確認推奨。
- config/*.yaml の検証は PyYAML に依存。パッケージに PyYAML がない場合は内容検証がスキップされる（警告）。

---

このリリースはコードベースから推測して作成した CHANGELOG です。実際のコミット履歴やリリース方針に合わせて加筆・修正を行ってください。