# Changelog

すべての注目に値する変更をこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-11

初回リリース。自動売買システム KabuSys のコア機能群を追加。

### Added
- パッケージ構成
  - kabusys パッケージ本体を追加。バージョンは `__version__ = "0.1.0"`。
  - エクスポート: portfolio、execution、monitoring、data 等のサブパッケージを想定。

- 設定関連
  - robust な .env 読み込み実装（kabusys.config）
    - プロジェクトルートを .git / pyproject.toml で探索して自動的に .env / .env.local を読み込む。
    - export 形式やクォート、インラインコメントを考慮したパーサを実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
    - Settings クラスを提供し、環境変数に対するプロパティ（DB パス、API トークン、環境判定フラグ等）を集約。
    - 環境値の検証（KABUSYS_ENV・LOG_LEVEL・PAPER_FILL_MODE 等）のバリデーションを実施。

  - 対話式環境設定ウィザード CLI（kabusys.config_setup）
    - `.env` の初期作成・更新を支援するウィザードを追加。
    - J-Quants / kabu API / DB パス / LINE 通知等の項目を対話式に設定・保存可能。
    - 既存 .env の読み込み、シークレットのマスク表示、保存確認を実装。

  - 設定検証 CLI（kabusys.validate_config）
    - 起動前に .env と config/*.yaml の整合性をチェックするコマンドを追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、DB パスの親ディレクトリ存在確認、YAML のパースチェック（PyYAML が存在する場合）等を実施。
    - --strict オプションで警告を失敗扱いにできる。

- 実行・監視ランナー
  - 実行エンジン起動スクリプト（kabusys.run_execution）
    - 起動時にプロセス優先度を高く設定。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用 SQLite（デフォルト `data/paper_trading.db`）を使用し、本番 DB と完全分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動（スレッド実行）。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル管理、優雅な停止処理をサポート。

  - 監視ループ起動スクリプト（kabusys.run_monitoring）
    - SystemMonitor を用いたポーリング監視ループを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視 DB は環境に関係なく本番 sqlite_path を使用する設計。
    - 停止フラグ検出でループを終了、例外発生時のログと次ポーリングへのフォールバック。

- ロギング・プロセス制御ユーティリティ
  - 統一ロギング設定ユーティリティ（kabusys.utils.logging_setup）
    - stdout へ StreamHandler、日次ローテートの TimedRotatingFileHandler（デフォルト logs/、30日保持）を設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続する安全処理を実装。
    - ログレベルや出力先の解決順（引数 > 環境変数 > デフォルト）を実装。

  - プロセス優先度 / CPU affinity 設定ユーティリティ（kabusys.utils.process_priority）
    - Windows / POSIX (Linux, macOS, BSD) に対応した set_process_priority と set_cpu_affinity を実装。
    - psutil を用い、権限不足や未対応環境では警告を出してフェールセーフに動作。

- ポートフォリオ構築
  - 候補選定・重み計算（kabusys.portfolio.portfolio_builder）
    - select_candidates: スコア降順 + tie-break による候補選定。
    - calc_equal_weights / calc_score_weights: 等重・スコア加重配分。スコア合計が 0 の場合は等重へフォールバック。

  - リスク調整（kabusys.portfolio.risk_adjustment）
    - apply_sector_cap: セクター集中を検出し、既存ポジション状況により新規候補を除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数（デフォルトマップを実装、未知レジームは警告して 1.0 へフォールバック）。

  - ポジションサイズ計算（kabusys.portfolio.position_sizing）
    - calc_position_sizes: risk_based / equal / score の割当方式をサポート。
    - 単元株（lot_size）への丸め、1 銘柄上限（max_position_pct）、aggregate cap（available_cash）に応じたスケーリング、手数料/スリッページ見積り（cost_buffer）を考慮した安全な配分ロジックを実装。
    - 利用可能現金を超える場合に残差処理で単元単位の追加配分を行うアルゴリズムを実装。

- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
    - Paper Trading 用 SQLite（デフォルト `data/paper_trading.db`）から集計を行い、稼働率・注文成功率・送信率・P95 レイテンシなどの指標を算出して PASS/FAIL を判定。
    - 日付フィルタ --from / --to と --db オプションをサポート。
    - 指標の閾値（稼働率 99%、成功率 90% など）を定義し、評価結果と詳細を標準出力で出力。

- リサーチ（部分実装）
  - ファクター計算モジュール（kabusys.research.factor_research）
    - StrategyModel に基づくモメンタム等のファクター計算の骨組みを追加。DuckDB 接続を前提とした設計。
    - calc_momentum の実装開始（関数ドキュメントと定数群を追加、実装の続きあり／部分的）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Implementation details
- 設計方針として、データベース接続（SQLite / DuckDB）やブローカー操作は起動スクリプト側で受け渡し、コア計算ロジック（ポートフォリオ構築、ポジション計算、リスク調整、ファクター計算）は副作用のない純関数として実装している。
- ログやプロセス優先度設定は起動直後に行い、運用環境での安定稼働を意識したフォールバック（権限不足や未対応環境での graceful degradation）を行う。
- Paper Trading と Live（本番）は DB を分離する設計（paper_trading 用の sqlite を使用）により、発注・検証データの混在を防止。

### Known issues / TODO
- factor_research.calc_momentum 等の一部リサーチ関数は実装が途中でファイル末尾が未完了（ドキュメントは整備済み）。今後の実装完了が必要。
- position_sizing 内の price 欠損時のフォールバック（前日終値や取得原価）について TODO コメントあり。将来的に拡張予定。
- 単元株サイズ（lot_size）が全銘柄共通になっているため、銘柄別の lot_map による拡張を検討中。

---

今後のリリースではリサーチモジュールの完了、ExecutionEngine 周りの詳細実装、より多くのテストとドキュメント整備を予定しています。