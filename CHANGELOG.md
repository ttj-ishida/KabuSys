# Changelog

すべての注目すべき変更をこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-04-23

初版リリース。

### Added
- 実行スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ (data/stop_requested.flag) を検知して安全にループを終了。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨を明示。
    - start/stop ログと例外ハンドリングを実装。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は専用の MockBrokerClient を使用し、paper_trading 用 DB（data/paper_trading.db）に記録して本番 DB と分離。
    - 停止フラグと PID ファイル（data/execution.pid）によるセッション管理、デーモンスレッドでの実行制御を実装。

- 設定管理
  - config.py: 環境変数・設定管理モジュールを実装。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）により .env 自動読み込み（.env → .env.local、OS 環境変数を優先）。
    - .env パース強化: export プレフィックス、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理に対応。
    - 各種設定プロパティ（DB パス、Paper Trading の挙動、監視しきい値、KABUSYS_ENV/LOG_LEVEL の検証など）を提供。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを追加。

- 設定ユーティリティ / CLI
  - config_setup.py: 対話式 .env 作成ウィザードを実装（.env の初期作成・更新を支援）。
    - デフォルト値、マスク入力（secret）、選択肢などをサポート。
    - 保存前の確認プロンプトを実装。
  - validate_config.py: 起動前の設定検証 CLI を実装。
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリチェック、config/*.yaml 存在チェック（PyYAML が未インストール時はスキップ）を実施。
    - --strict オプションで警告を FAIL 扱いにできる。

- ログ / プロセスユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定ユーティリティを追加。
    - stdout 出力の StreamHandler と日次ローテーション（TimedRotatingFileHandler、30 日保持）をルートロガーへ設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
    - ログレベル解決順・ログディレクトリ解決順を明示。
  - utils/process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX（Linux, Darwin, FreeBSD）を吸収する実装。
    - set_process_priority(level) で "high"/"normal"/"low" を指定可能。失敗時は警告を出して安全にフォールバック。
    - set_cpu_affinity(cpu_count) による先頭 N コアへのピン留め（実行環境依存で安全に失敗処理）。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコア降順ソートと上位 N 選択を実装。
    - calc_equal_weights / calc_score_weights: 等金額配分／スコア加重配分の重み計算を実装（スコアが 0 の場合は等分配にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限（既存保有比率が閾値を超える場合、新規候補を除外）を実装。unknown セクターは適用対象外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返すユーティリティを実装。未知レジームはフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく株数決定ロジックを実装。単元株（lot_size）丸め、1 銘柄上限、aggregate cap に基づくスケールダウン、cost_buffer（手数料/スリッページ見積）を考慮した配分を行う。

- Paper Trading 検証用ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。
    - 指定期間の system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、平均/最大/P95 レイテンシなどを算出し PASS/FAIL 判定を行う。
    - デフォルトの閾値: 稼働率 99.0%、成立率 90.0%、送信率 95.0%、P95 レイテンシ 200 ms。

- research/factor_research.py（ファクター計算基盤）
  - DuckDB 接続を受けてモメンタム等のファクターを計算するための基盤と設計コメントを追加（モジュール実装の一部が含まれる）。

- パッケージメタ
  - src/kabusys/__init__.py に version = "0.1.0" を設定。

### Changed
- DB とモニタリングの扱いを明文化
  - run_monitoring は常に本番用 sqlite_path を参照（監視データは環境にかかわらず本番 DB を想定）。
  - run_execution は paper_trading モード時に paper_sqlite_path を使用して本番データと分離。

- .env 自動ロードの挙動
  - OS 環境変数 > .env.local > .env の優先順位で読み込む。
  - .env.local は .env の上書き用に使用され、OS 環境変数は保護される（既存の OS 環境変数は上書きされないよう protected 制御）。

### Fixed
- 環境変数のパースとロードに関する堅牢性向上
  - export プレフィックス、クォート内エスケープ、およびインラインコメントの取り扱い問題を解消。
  - .env の読み込みエラー時に警告を出して処理を継続するよう改善（テスト/CI 環境での扱いを配慮）。

- ロギング設定の二重登録防止
  - setup_logging() が既存ハンドラを一度クリアしてから再設定するようにし、複数回呼び出した場合の二重出力を防止。

### Documentation / UX
- 各 CLI スクリプト・ユーティリティに使用方法と注記を docstring とヘルプに追加。
- config_setup の出力フォーマット、保存前確認、ヒント表示（シークレット値マスク）を改善。

### Known issues / Notes
- research/factor_research.py の一部（calc_momentum 等）は実装途中（ソースの末尾で途中切れ）になっている箇所があります。今後のリリースで完成予定です。
- position_sizing の価格欠損（price が 0.0）時の扱いは現状ログ出力でスキップしており、将来的に前日終値等のフォールバックを検討するコメントを残しています。
- run_monitoring が本番 sqlite_path を常に使用する挙動は設計上の選択です。テスト環境で監視 DB を分離したい場合は実行方法（起動スクリプト / 環境変数）を調整してください。

---

今後のリリース予定:
- factor_research の完成、DuckDB ベースのファクター計算と正規化ワークフローの追加。
- テストカバレッジ拡充（特に資金配分・スケーリングロジック、.env パーサ）。
- ローカル開発時の監視 DB の分離オプション追加検討。