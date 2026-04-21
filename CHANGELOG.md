# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。  
各リリースでは主な追加・変更・修正点を日本語で記載しています。

フォーマット:
- Added: 新機能や追加されたモジュール
- Changed: 既存挙動の変更や設計上の改善
- Fixed: バグ修正や回避策
- Notes: 運用上の注意等

## [Unreleased]

## [0.1.0] - 2026-04-21
最初の公開リリース。システムのコア機能、ユーティリティ、運用用 CLI/ツールを含む。

### Added
- コアパッケージ初期実装
  - src/kabusys/__init__.py にバージョン情報を追加（`__version__ = "0.1.0"`）。
- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ（data/stop_requested.flag）検知で安全に終了。監視は環境にかかわらず本番用 SQLite パスを使用。
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。`KABUSYS_ENV=paper_trading` 時はペーパートレード専用の DB（data/paper_trading.db）と MockBrokerClient を使用して本番 DB と分離。停止フラグ・PID ファイルの扱いに対応。
- 設定管理・ウィザード・検証
  - config.py: Settings クラスを実装。環境変数 / .env / .env.local の自動読み込み（プロジェクトルート検出ベース）。`KABUSYS_DISABLE_AUTO_ENV_LOAD` による自動読み込み無効化。各種設定値（DB パス、KABUSYS_ENV、PAPER_FILL_MODE など）をプロパティで提供し、妥当性チェックを行う。
  - config_setup.py: 対話式 .env 作成・更新ウィザードを追加（CLI）。シークレットマスク、選択肢、デフォルト値、保存確認機能あり。
  - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パスと config/*.yaml の存在・パース検証（PyYAML 未存在時はスキップ）、本番向けのガード項目を警告。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定を提供。stdout に StreamHandler を出力し、日次ローテート（TimedRotatingFileHandler）でファイル出力（デフォルト logs/、30 日保持）。既存ハンドラのクリア処理を実装。
  - utils/process_priority.py: プロセス優先度（high/normal/low）と CPU affinity 設定ユーティリティを追加。Windows と POSIX 系を吸収し、権限不足や未対応 OS では警告を出して安全にスキップ。
- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py: 候補選定、等金額配分、スコア加重配分を実装（select_candidates, calc_equal_weights, calc_score_weights）。スコアが全て 0 の場合は等金額にフォールバック。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）および市場レジームに基づく乗数（calc_regime_multiplier）を実装。unknown セクターの扱いや、既存保有・売却予定銘柄の除外ロジックを含む。
  - portfolio/position_sizing.py: 単元株丸め、リスクベース / 等配分 / スコア配分に基づく発注株数算出を実装（calc_position_sizes）。個別上限・aggregate cap・コストバッファ・lot サイズの考慮、スケールダウン時の端数処理を含む。
  - portfolio/__init__.py: 上記関数群をエクスポート。
- 監視・実行関連 DB 初期化
  - 辺りのコードから monitoring_db の初期化を起動時に行うように組み込み（init_monitoring_db を使用）。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレード DB から稼働率、注文成功率、送信率、レイテンシ等を集計してレポートを出力。P95 計算、閾値判定（稼働率 99% など）と PASS/FAIL 判定を提供。--from/--to/--db オプション対応。
- 研究用ファクター計算の骨組み
  - research/factor_research.py: モメンタム等のファクター計算方針・定数を定義。DuckDB 接続を受ける設計。注釈や設計方針を含む（実装途中と思われる箇所あり）。

### Changed
- 設定読み込みの優先順位明確化
  - OS 環境変数 > .env.local > .env の順でロード。既存 OS 環境変数は保護される（保護セット protected を使用）。
- .env パーサの拡張
  - export プレフィックス対応、シングル/ダブルクォート内でのバックスラッシュエスケープ対応、コメントの扱い（クォート外での '#' とスペース条件）などをサポートして頑健性を向上。
- ログ出力の振る舞い
  - stdout を使う方針を明記（cron 等で stdout/stderr を一本化するユースケースを考慮）。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
- プロセス優先度設定の振る舞い改善
  - 権限不足・未対応 OS 時に警告を出して処理をスキップするようにし、起動時に優先度を先に設定する運用を推奨（run_*.py で採用）。

### Fixed / Robustness
- 環境変数のバリデーションとフォールバック
  - MONITOR_POLL_INTERVAL の不正値に対して警告を出しデフォルトにフォールバック（run_monitoring.py）。
  - PAPER_FILL_MODE に対する許容値チェックを実装（config.py）し、不正値は ValueError を送出。
- DB 関連の安全性
  - 起動スクリプトでの DB 接続後に finally で確実にクローズするようにしてファイルハンドルリークを回避。
  - run_execution.py では paper_trading 環境で専用 SQLite を選択し、本番 DB と分離して誤発注リスクを低減。
- CLI とファイル IO の例外ハンドリングを追加
  - .env 読み込み時の OSError に対して警告を出して読み込みを継続（config.py）。
  - 設定ウィザードでの EOF/KeyboardInterrupt を適切にハンドリングして途中キャンセル時に安全に戻る。

### Notes
- 本リリースはアーキテクチャ・運用周り（設定管理、ログ、プロセス優先度、DB 分離、監視/停止フラグ、検証ツール）の整備に重点を置いており、戦略（シグナル生成）や ExecutionEngine の内部ロジックは別モジュールとして分離されています。
- research/factor_research.py の実装は途中（ファイル末尾で切れている箇所あり）。今後の追加実装でファクター計算を完成させる予定です。
- コンフィグ YAML（config/*.yaml）については雛形生成スクリプトやサンプルが別途存在することを想定しており、validate_config.py はファイルの存在とパース可能性をチェックします（PyYAML が未インストールの場合はパース検証をスキップして警告）。
- 本番運用時は KABUSYS_ENV=live 設定と LINE 通知設定を必ず確認してください。validate_config による事前チェックを推奨します。

---

将来的なリリースでは、研究モジュールの完成、Strategy/Execution の詳細実装、より細かなモニタリング指標の追加、ユニットテストと CI の整備を予定しています。