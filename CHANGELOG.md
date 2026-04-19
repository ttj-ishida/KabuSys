# Changelog

すべての重要な変更をこのファイルに記載します。  
フォーマットは「Keep a Changelog」（https://keepachangelog.com/ja/）に準拠します。

注: 本 CHANGELOG はリポジトリ内のソースコードから推測して生成したものであり、実際のコミット履歴ではありません。

## [Unreleased]

## [0.1.0] - 2026-04-19
初回公開リリース。以下の主要機能・ユーティリティを含みます。

### Added
- 実行エントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、Paper Trading 用 DB（data/paper_trading.db または環境変数で指定）を利用する。起動時にプロセス優先度を "high" に設定し、停止フラグ（data/stop_requested.flag）を検知して安全に停止できる仕組みを実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。Monitoringは環境に関わらず本番 sqlite_path を使用する設計。

- 設定管理
  - config.py: 環境変数管理クラス `Settings` を追加。.env 自動ロード（.env → .env.local、OS 環境変数優先）をサポート。多数の設定プロパティを提供（J-Quants / kabu API / DB パス / 監視閾値 / 環境判定等）。`KABUSYS_DISABLE_AUTO_ENV_LOAD` による自動読み込み無効化も実装。
  - config_setup.py: インタラクティブな .env 作成ウィザードを追加。既存値の再利用、シークレットマスク表示、保存処理（.env のテンプレート出力）をサポート。

- 設定検証 CLI
  - validate_config.py: .env と config/*.yaml の基本的な検証ツールを追加。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML パース（PyYAML がインストールされている場合）や本番環境向けの追加ガードを実行。`--strict` オプションで警告をエラー扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。コンソール（stdout）出力 + 日次ローテーションのファイル出力（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成に失敗した際はファイル出力をスキップしてコンソールのみで継続。既存ハンドラの重複防止のため一度クリアしてから設定する。ログローテーションは日次、バックアップ 30 日。
  - utils/process_priority.py: プラットフォーム差分を吸収したプロセス優先度設定と CPU affinity 設定を追加。Windows と POSIX（Linux/Mac/FreeBSD）でそれぞれ適切な優先度を設定し、権限不足時には警告を出してスキップする。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（スコア降順で上位 N）、等重配分、スコア加重配分（全スコア 0 の場合は等重フォールバック）を実装。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた資金乗数（calc_regime_multiplier）を実装。regime に対するデフォルトマッピング（bull/neutral/bear）と未知レジームのフォールバックを提供。
  - portfolio/position_sizing.py: 発注株数計算ロジックを実装。allocation_method として `risk_based`, `equal`, `score` をサポート。単元株（lot_size）丸め、1銘柄上限（max_position_pct）、合計投下上限（max_utilization）、コストバッファ（手数料・スリッページ想定）を考慮したスケーリングおよび残余処理を実装。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py: Paper Trading DB（デフォルト data/paper_trading.db）からレポートを生成するスクリプトを追加。期間フィルタ（--from/--to）、P95 レイテンシ計算、稼働率・注文成功率・送信率・リスク却下数などを集計して PASS/FAIL を判定する。閾値（稼働率 99%、成立率 90% 等）はコード内定義。

- リサーチ（ファクター計算）基盤
  - research/factor_research.py: DuckDB を用いたファクター計算モジュールの骨組みを追加（モメンタム等の定義と計算方針を明記）。（注: ファイルは途中実装の可能性あり）

- パッケージ初期化
  - __init__.py: パッケージバージョンを "0.1.0" として追加。

### Changed
- （初回リリースのため該当なし）

### Fixed
- コンフィグ読み込みの堅牢化
  - .env パーサはクォート・エスケープ・コメント処理に対応。`export KEY=val` 形式を許容。
  - .env 自動ロードの際、OS 環境変数は保護され上書きされない（protected set を導入）。

- ログ出力先の決定
  - コンソールハンドラは stdout を使用するよう明示。cron/Task Scheduler 等でのリダイレクトと利用しやすくするため。

### Deprecated
- （該当なし）

### Removed
- （該当なし）

### Security
- （該当なし）

---

既知の注意点 / TODO
- research/factor_research.py は設計方針と定数が定義されているが、末尾が途中で切れているなど実装が完了していない可能性があります。ファクター計算の完全実装は別コミットで追加予定。
- position_sizing の価格フォールバックは TODO コメントで言及されている（price が欠損した場合の扱い）。現状では価格欠損時にその銘柄はスキップされるため、完全な堅牢化が必要。
- Monitoring は環境にかかわらず本番 sqlite_path を使用するため、テスト用途においては明示的に DB パスを切り替える運用が必要。

参考（主な CLI / 実行方法）
- 実行監視ループ: python -m kabusys.run_monitoring
- 実行エンジン:     python -m kabusys.run_execution
- 設定ウィザード:   python -m kabusys.config_setup
- 設定検証:         python -m kabusys.validate_config [--strict]
- Paper レポート:   python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD --to YYYY-MM-DD --db PATH]