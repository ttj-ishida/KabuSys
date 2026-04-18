# Changelog

すべての注目すべき変更をここに記録します。フォーマットは「Keep a Changelog」に準拠します。  
リリースの日付はコードベースの作成日時に基づき推測しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-18
初回リリース。KabuSys 自動売買フレームワークのコア機能、運用ユーティリティ、CLI ツール群を実装。

### Added
- 全体
  - パッケージ初期バージョンを追加（kabusys.__version__ = "0.1.0"）。
  - DuckDB / SQLite によるデータ管理をサポート (duckdb, sqlite3 を利用)。
  - ログ設定ユーティリティを追加（kabusys.utils.logging_setup.setup_logging）。
    - stdout 出力と日次ローテーション（TimedRotatingFileHandler）によるファイル出力を統一的に設定。
    - LOG_DIR 環境変数／引数でログ出力先を指定可能。失敗時はコンソール出力にフォールバック。
  - プロセス優先度・CPU affinity ユーティリティを追加（kabusys.utils.process_priority）。
    - Windows / POSIX（Linux/macOS等）間の差分を吸収して優先度設定を試行。
    - CPU 固定（set_cpu_affinity）機能を提供。
  - 設定管理モジュールを追加（kabusys.config）。
    - .env の自動読み込み（プロジェクトルート検出）と堅牢な .env パーサを実装。
    - 必須 / 任意の設定をプロパティ経由で取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH 等）。
    - KABUSYS_ENV（development / paper_trading / live）や PAPER_FILL_MODE の検証。
  - 対話式設定ウィザード CLI を追加（kabusys.config_setup）。
    - .env の作成・更新を支援。シークレットマスク表示、選択肢・デフォルト対応。
  - 設定検証 CLI を追加（kabusys.validate_config）。
    - 必須環境変数や config/*.yaml の存在・パース（PyYAML があれば検証）をチェック。
    - --strict フラグで警告を FAIL 扱いにできる。
  - 実行エンジン・監視の起動スクリプトを追加
    - run_execution.py
      - ExecutionEngine の起動スクリプト。KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用して本番 DB と分離。
      - BrokerClientFactory による Broker クライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler 組み立て、ExecutionEngine の起動監視（スレッド）を実装。
      - data/execution.pid、data/stop_requested.flag を用いた起動/停止制御。
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）。
      - 監視は常に本番用 sqlite_path を参照する（環境に依存しない設計）。
      - 停止フラグ検知、例外時の安全なループ継続、KeyboardInterrupt による終了処理を実装。
  - Paper Trading 向け検証ツールを追加（kabusys.tools.paper_verification_report）
    - ペーパートレード DB を集計して稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）等を出力する CLI。
    - P95 算出、閾値判定（稼働率 / 成立率 / 送信率 / P95 レイテンシ）による PASS/FAIL 判定を実装。
  - ポートフォリオ構築モジュールを追加（kabusys.portfolio）
    - portfolio_builder: 候補選定（select_candidates）、等金額・スコア加重の重み計算（calc_equal_weights, calc_score_weights）。同点時のタイブレークやスコア全ゼロ時のフォールバックを実装。
    - risk_adjustment: セクター上限適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。未知レジーム時のフォールバックとデバッグログを実装。
    - position_sizing: 株数算出（calc_position_sizes）
      - risk_based / equal / score の配分方式をサポート。
      - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金に合わせたスケーリング）、コストバッファ考慮、スケールダウン後の残差処理（端数を大きい順に割当）を実装。
  - 研究用ファクター計算モジュール（kabusys.research.factor_research）を追加（モメンタム等の計算枠組みを実装、DuckDB 経由で prices_daily/raw_financials を参照する設計）。

### Changed
- n/a（初回リリースのため既存との差分はなし）

### Fixed
- n/a（初回リリースのためバグ修正履歴はなし）

### Notes / Implementation details
- .env 自動読み込みはプロジェクトルート検出に依存し、CWD に依存しない設計（__file__ を基準に探索）。
- .env パーサは引用符付き値のバックスラッシュエスケープ、インラインコメント処理、export プレフィックス対応などをサポートして堅牢化。
- logging_setup はログディレクトリ作成に失敗した場合にファイルハンドラをスキップし、コンソール出力のみで継続するフォールバックを持つ。
- process_priority の優先度設定はアクセス権限やプラットフォーム非対応時に警告ログでスキップされ安全に扱われる。
- run_execution は paper_trading モードでは paper_sqlite_path を使用して本番 DB と分離するため、ペーパートレードでの検証が本番データに影響しない。
- run_monitoring は MONITOR_POLL_INTERVAL の値検証を行い、不正な値（0以下や非整数）はデフォルトにフォールバックして安全に稼働する。
- validate_config は PyYAML が無い場合は YAML 検証をスキップし、インストール状況に依存して柔軟に動作する。

### Removed
- n/a

### Security
- 機密値（J-Quants トークン、kabu API パスワード等）は .env によって管理する想定。本リリースでは .env を Git に commit しないことを明示（config_setup のコメント）。
- ログ出力では秘密値をマスクする実装（config_setup の表示時）など配慮あり。

### Known issues / TODO
- risk_adjustment.apply_sector_cap
  - price が欠損（0.0）の場合にエクスポージャーが過小見積りされブロックが外れる可能性あり。将来は前日終値や取得原価等のフォールバックを検討する旨を TODO コメントで明示。
- position_sizing
  - 将来的には銘柄ごとの単元（lot_size）をマスタで持たせる拡張を想定しており現状は全銘柄共通の lot_size を想定している旨がコメントで残されている。
- factor_research モジュールは SQL/計算ロジックの続き（ファイル末尾で未完）を実装することが想定されている（コード末尾で calc_momentum の実装が途中で終わっているように見える）。
- 本リリースはコードベースのスナップショットに基づくため、実運用での追加バグ修正や動作検証（特に BrokerClient 実装・ExecutionEngine の細部）は今後のイテレーションで必要。

---

README やデプロイ手順、テストケース等は別途整備を推奨します。必要であれば各モジュールごとの変更点をさらに詳細に分解して記載できます。