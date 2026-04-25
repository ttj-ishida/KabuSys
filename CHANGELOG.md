# Changelog

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。

注意: 以下はコードベースの現状から推測して作成した変更履歴です。実際のコミット履歴とは異なる場合があります。

## [Unreleased]

（特になし）

## [0.1.0] - 2026-04-25

### Added
- 基本パッケージ構成を追加
  - パッケージ名: kabusys、バージョン 0.1.0（src/kabusys/__init__.py）。
- 起動スクリプト
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止はプロジェクト配下の data/stop_requested.flag で検出。監視用 DB 初期化（init_monitoring_db）と DuckDB 接続を行う。
  - run_execution: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（data/paper_trading.db を想定）を使用して本番 DB と分離。停止フラグ・PID ファイルによる制御を実装。
- 設定管理
  - Settings クラスを実装（src/kabusys/config.py）。.env 自動読み込み（.env → .env.local、OS 環境変数優先、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。多くの設定プロパティを提供（J-Quants / kabu API / DB パス / Paper Trading / 監視閾値 / 環境判定等）。
  - .env パーサー強化: クォート（シングル/ダブル）およびバックスラッシュエスケープ、行内コメントの扱い、export KEY=val 形式に対応。
- 設定ユーティリティ CLI
  - config_setup: 対話式 .env 作成ウィザードを追加（.env の作成・更新を支援）。既存値の取り込み・シークレットマスク・保存確認を実装。
  - validate_config: 起動前の設定検証 CLI を追加。必須環境変数や KABUSYS_ENV/LOG_LEVEL/DB パスのチェック、config/*.yaml の存在と YAML パース検証（PyYAML がない場合は警告）を行う。--strict オプションで警告を FAIL 扱いにできる。
- ロギング/プロセス制御ユーティリティ
  - logging_setup: ルートロガーを統一的に設定するユーティリティを追加。stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を持つファイルハンドラを設定。既存ハンドラの重複登録を避けるため一旦クリアする処理あり。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - process_priority: プロセス優先度 (high/normal/low) と CPU affinity 設定ユーティリティを追加。Windows / POSIX の差分を吸収し、権限や未サポート環境では安全にフォールバックする。
- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア全0時に等配分へフォールバック。
  - risk_adjustment: セクター集中制限の適用（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。未知レジーム時はフォールバック。
  - position_sizing: 発注株数算出（calc_position_sizes）を実装。allocation_method として "risk_based"/"equal"/"score" をサポートし、単元株（lot_size）で丸め、aggregate cap に対するスケーリング・端数配分ロジックを実装。手数料／スリッページ見積り用 cost_buffer を考慮。
- Paper Trading 検証ツール
  - tools/paper_verification_report: paper_trading 用 SQLite DB を解析して稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計し、閾値と比較して PASS/FAIL を判定するレポート生成スクリプトを追加。閾値はソース内定義（稼働率 99% 等）。
- リサーチ（ファクター計算）基盤
  - research/factor_research: DuckDB を使ったファクター計算モジュールの骨格を追加（モメンタム・MA200乖離・ATR 等を想定）。設計方針（DuckDB 接続を受ける、prices_daily/raw_financials のみ参照、結果は (date, code) ベースの dict リスト）を明記。
- DB 初期化
  - monitoring_db.init_monitoring_db を起動スクリプトから呼び出し、監視用テーブルが存在することを保証（冪等）。

### Changed
- .env 読み込みの優先順位と挙動を明確化
  - OS 環境変数 > .env.local (上書き) > .env（未設定時にのみセット）。既存の OS 環境変数は保護される。
- run_monitoring/run_execution が起動時にプロセス優先度を "high" に設定するよう変更（setup_logging の前に set_process_priority("high") を実行する構成に統一）。
- ロギング設定の挙動改善
  - 既にハンドラがある場合に二重登録を避けるためハンドラを flush/close のうえ削除して再設定するようにした。
  - コンソール出力は stdout を使用するように統一（cron/Task Scheduler での扱いを考慮）。

### Fixed
- MONITOR_POLL_INTERVAL の不正値（非整数や 0 以下）に対してデフォルトへフォールバックし、警告を出すバリデーションを追加（run_monitoring）。
- run_execution で paper_trading 環境時に本番 DB を誤って使用しないよう paper_sqlite_path を明示的に使用するように修正。
- ログディレクトリ作成失敗時にクラッシュしないよう例外を捕捉してファイルハンドラをスキップするフェイルセーフを追加。

### Security
- .env 関連: config_setup により .env をユーザー対話で生成する際、秘密値はマスクして表示するようにして誤公開リスクを軽減。

### Notes / Known limitations
- research/factor_research モジュールはファクター計算の骨格を追加しているが、実装の一部（calc_momentum の続きなど）が未完成・途中の可能性があります。実運用前に関数の完全実装とテストが必要です。
- BrokerClientFactory や ExecutionEngine の内部実装は本差分で参照されているが（起動スクリプトから利用）、これらの実装詳細・外部依存（ブローカークライアント等）は別途検証が必要です。
- process_priority や set_cpu_affinity は権限不足や未対応プラットフォームで失敗する可能性があるため、その場合は警告を出してスキップする挙動です。

---

今後のリリースでは、テストカバレッジの追加、research モジュールの完成、各コンポーネント（ExecutionEngine / BrokerClient / SystemMonitor 等）の詳細な変更履歴を追記することを推奨します。