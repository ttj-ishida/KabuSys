# CHANGELOG

すべての重要な変更をこのファイルに記録します。本プロジェクトは「Keep a Changelog」の慣習に準拠します。  
日付は YYYY-MM-DD 形式を使用します。

## [Unreleased]

### Added
- 設定/起動用 CLI を追加
  - config_setup.py：対話式ウィザードで .env ファイルを作成 / 更新する機能を追加。機密項目はマスク表示し、保存前に確認を行う。
  - validate_config.py：.env および config/*.yaml の起動前検証 CLI を追加。--strict オプションで警告をエラー扱いに可能。
  - run_monitoring.py：SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番用 sqlite_path を使用する仕様。
  - run_execution.py：ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 用 DB に分離して記録。

- 環境/設定関連
  - config.py：.env ファイルの自動読み込み（プロジェクトルート検出）や、環境変数のパースロジック（クォート・エスケープ対応、コメント扱い）を実装。Settings クラスで各種設定値（DB パス、API トークン、各種閾値など）をプロパティとして提供。
  - .env 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。OS 環境変数は上書き保護。

- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py：標準化されたログ設定ユーティリティを導入。コンソール（stdout）と日次ローテーションによるファイル出力を設定。LOG_DIR/LOG_LEVEL の優先解決をサポートし、ファイルハンドラ作成失敗時はコンソール出力にフォールバック。
  - utils/process_priority.py：プラットフォーム差を吸収したプロセス優先度・CPU affinity 設定ユーティリティを追加。Windows/POSIX に対応し、失敗時は警告ログを出力してスキップ。

- 実行系 / 監視連携
  - run_execution と run_monitoring で監視テーブルの初期化（init_monitoring_db）を行い、duckdb との接続を統一的に確保。
  - 実行中の停止フラグ（data/stop_requested.flag や execution.pid の扱い）による安全停止の実装。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py：候補選別（select_candidates）、重み計算（等金額 calc_equal_weights、スコア加重 calc_score_weights）を実装。スコアが全て 0 の場合は等金額にフォールバックする警告を追加。
  - portfolio/risk_adjustment.py：セクター集中制限を適用する apply_sector_cap、マーケットレジームに応じた投下資金乗数 calc_regime_multiplier を実装（未知レジームはフォールバックと警告）。
  - portfolio/position_sizing.py：株数決定ロジックを実装。risk_based / equal / score の配分方式に対応。単元株丸め（lot_size）、最大ポジション上限、利用可能資金に基づく aggregate cap（スケーリングと端数処理）を実装。手数料・スリッページを見積もる cost_buffer 引数をサポート。

- 分析 / 検証ツール
  - tools/paper_verification_report.py：Paper Trading の検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・レイテンシ（P95）等を算出し、閾値（デフォルト）との比較で PASS/FAIL 判定を出力。P95 計算と日付フィルタ対応を実装。

- その他
  - パッケージバージョンを __version__ = "0.1.0" として定義。

### Changed
- 監視（run_monitoring）でプロセス優先度を起動直後に High に設定するように統一。run_execution も同様の挙動。
- logging_setup: デフォルトで stdout を使用する StreamHandler と、ファイル出力失敗時のフォールバック処理を明確化。

### Fixed
- .env パーサーでクォート内のバックスラッシュエスケープやインラインコメントを適切に処理するよう改善。

### Known / TODO
- research/factor_research.py はモメンタム等のファクター計算を実装中（calc_momentum が途中）。追加ファクターの実装・テストが必要。
- apply_sector_cap の価格欠損（price が 0 の場合）によるエクスポージャー過少見積りへのフォールバック対応は TODO コメントあり。
- position_sizing: 将来的に銘柄別 lot_size をサポートする拡張（lot_map）を予定。
- process_priority および CPU affinity の設定は権限やプラットフォームに依存するため、失敗時は無害にスキップする設計だが、運用時は権限確認が必要。
- ログディレクトリ作成やファイルハンドラ作成が失敗した場合はファイル出力が無効化される旨をドキュメント化済み。CI/運用環境でログ出力先の権限を確保することを推奨。

---

## [0.1.0] - 2026-04-19

初回リリース。

### Added
- 基本的な実行基盤とユーティリティ類を追加
  - 起動スクリプト: run_execution.py, run_monitoring.py
  - 設定管理: config.py（.env 自動ロード、Settings クラス）
  - 設定ウィザード / 検証: config_setup.py, validate_config.py
  - ロギングユーティリティ: utils/logging_setup.py
  - プロセス優先度ユーティリティ: utils/process_priority.py
  - ポートフォリオ構築モジュール: portfolio/（portfolio_builder, risk_adjustment, position_sizing）
  - Paper Trading 検証ツール: tools/paper_verification_report.py
  - パッケージメタ: __init__.py（バージョン設定）

### Changed
- （初回リリースにつき特記事項なし）

### Fixed
- （初回リリースにつき特記事項なし）

---

注意:
- この CHANGELOG はコードの実装内容・コメントから推測して作成しています。実際のコミット履歴やリリースノートと差異がある可能性があります。リリース時は Git コミットログ等に基づき適宜修正してください。