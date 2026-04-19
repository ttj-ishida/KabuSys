# CHANGELOG

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」準拠です。

次のバージョンでの変更点は、コードベースから推測して作成しています（初回リリース想定）。

## [Unreleased]

## [0.1.0] - 2026-04-19

### Added
- 基本アプリケーションとユーティリティを追加
  - パッケージ初期化情報を追加（src/kabusys/__init__.py, version = 0.1.0）。
- 実行系 / 監視系起動スクリプトを追加
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV に応じて Paper Trading 用 DB を分離し、BrokerClientFactory を通じて実行環境に適したブローカークライアントを生成。エンジンのデーモンスレッド実行と停止フラグ監視（data/stop_requested.flag）を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60秒）。監視用 DB は環境にかかわらず本番 sqlite_path を使用。
- 環境設定関連の CLI を追加
  - config_setup.py: 対話式 .env 作成/更新ウィザードを追加（複数の設定項目、シークレット入力、デフォルト値、.env への書き込みをサポート）。
  - validate_config.py: 起動前設定検証 CLI を追加（必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パス・config/*.yaml の存在確認、--strict オプションで警告を FAIL 扱いにできる）。
- 設定管理モジュールを追加
  - config.py: .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）、クォート/エスケープ/コメントを考慮した .env パーサ、Settings クラス（J-Quants / kabu / DB パス / PID/kill flag /閾値等のプロパティ）を実装。
- ロギング・プロセス制御ユーティリティを追加
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。stdout StreamHandler と日次ローテーションの TimedRotatingFileHandler をルートロガーに設定。既存ハンドラのクリア、ログディレクトリ自動作成、フォールバック動作を実装。
  - utils/process_priority.py: psutil を用いたプロセス優先度設定および CPU affinity 設定ユーティリティを追加。Windows と POSIX の差分を吸収し、安全に失敗をスキップする実装。
- ポートフォリオ構築（純粋関数群）を追加
  - portfolio/portfolio_builder.py: シグナルの候補選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）を実装。スコア全てが 0 の場合は等配分へフォールバックして警告を出す。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。unknown セクターは制限対象外。未知レジームではフォールバック動作。
  - portfolio/position_sizing.py: 様々な配分方式（risk_based, equal, score）に基づく発注株数計算を実装。単元株（lot_size）で丸め、1銘柄上限・合計キャッシュ上限に基づくスケーリング、cost_buffer を使った保守的な見積もり、残差配分ロジックを実装。
  - portfolio/__init__.py: 主要関数のエクスポートを整備。
- 研究用ファクター計算フレームワークを追加（基盤）
  - research/factor_research.py: DuckDB を想定したファクター計算モジュールの骨組み。モメンタム・MA・ATR・ボリューム等の計算方針と定数が定義され、calc_momentum 等の設計方針を記述（実装継続を想定）。
- Paper Trading 検証ツールを追加
  - tools/paper_verification_report.py: ペーパートレード DB から稼働率、注文成功率、送信率、レイテンシ（P95 等）を集計してレポート出力する CLI を追加。閾値による PASS/FAIL 判定を実装。PAPER_TRADING_SQLITE_PATH で DB パス指定可能。

### Changed
- ログ設定の初期化ロジックを統一
  - 各起動スクリプトから utils.logging_setup.setup_logging を呼ぶことでログ出力の挙動を統一。既存ハンドラをクリアして二重出力を防止。
- DB 周りの挙動を明確化
  - run_execution は paper_trading 環境時に専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と完全に分離。監視テーブルは init_monitoring_db で冪等に初期化。

### Fixed
- 環境変数・.env のパース精度向上
  - export プレフィックス、シングル／ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い、空行／コメント行の無視などに対応。
- ログディレクトリ作成失敗時のフェイルセーフ
  - logging_setup がディレクトリ作成に失敗した場合でもコンソール出力のみで継続するようにし、起動が妨げられないよう改善。
- プロセス優先度設定の安全化
  - 対応 OS 外や権限不足時に例外で落ちないよう警告ログを出してスキップするようにした。
- MONITOR_POLL_INTERVAL の妥当性チェック
  - 不正な値（数値変換失敗や 0/負値）を検出してデフォルト（60秒）へフォールバックするロジックを追加し、time.sleep に渡して ValueError を発生させないようにした。

### Documentation / UX
- config_setup.py により .env 作成／更新フローを対話式で改善。既存値の再利用、シークレットマスク表示、保存前の確認を実装。
- validate_config.py により起動前に設定不備（未設定・プレースホルダ・パス非存在・YAML パースエラー等）を検出できる CLI を提供。--strict オプションで警告をエラー扱いにできる。

### Internal / Notes
- 多くのモジュールは「DB 参照なしの純粋関数」として設計されており、ユニットテストが容易な構成になっている（portfolio/* 等）。
- DuckDB と SQLite の併用を前提にしている（analytics 用に DuckDB、監視/履歴用に SQLite）。
- 一部の機能（factor_research.calc_momentum の続き等）は骨子までで実装継続が必要。

### Security
- 本リリースでは機密情報（API トークン / パスワード）は .env に保存する想定。`.env` をリポジトリにコミットしない旨の注記を config_setup.py に追加。

---

今後の予定（推測）
- factor_research の完全実装（モメンタム・ATR 等の算出）
- ExecutionEngine / BrokerClient の詳細実装とテスト、リスク管理ロジックの強化
- 監視・アラート（LINE 等）連携の追加
- 単体テスト・CI・デプロイ手順の整備

もしリリースノートを特定の形式（例: GitHub リリース向けの短い要約や詳細な変更差分）の要件があれば、それに合わせて調整できます。どの形式で出力しますか？