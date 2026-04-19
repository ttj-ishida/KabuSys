# Changelog

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣習に準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

全ての日付はコミット／リリース日を推測して記載しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-19
初回リリース（推定） — 基本的な自動売買フレームワークのコア機能を実装。

### Added
- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ（data/stop_requested.flag）検知でループを終了。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は専用のペーパートレード用 SQLite（data/paper_trading.db をデフォルト）を使用して本番 DB と分離。停止フラグと PID 管理に対応。
- 設定・環境管理
  - config.py: Settings クラスを追加し、環境変数経由の設定取得を提供。自動 .env ロード機能（プロジェクトルート検出: .git または pyproject.toml 基準）。多くの設定プロパティを提供（DB パス、ログレベル、閾値、PID/kill フラグパス、paper_trading 関連等）。PAPER_FILL_MODE の検証ロジックを実装。
  - config_setup.py: 対話式の .env 作成／更新ウィザードを追加。既存値の読み取り・シークレットマスク・選択肢などをサポートし、.env の安全な生成を支援。
  - validate_config.py: 起動前に .env および config/*.yaml の基本チェックを行う CLI を追加（--strict オプションで警告を Fail 扱いにできる）。
  - .env パーサ／ロード改良: export 形式の行、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント（クォート無しの場合はスペース直前の # をコメントと扱う）に対応。既存 OS 環境変数を保護する仕組み（protected set）あり。
- ロギング・プロセス制御
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。コンソール出力は stdout、日次ローテーション（TimedRotatingFileHandler）でログファイルを保存（既定 logs/、保管 30 日）。既存ハンドラをクリアして二重登録を防止。
  - utils/process_priority.py: プロセス優先度設定ユーティリティを追加（Windows / POSIX を吸収）。set_process_priority() と set_cpu_affinity() を提供。アクセス拒否等は警告ログでスキップ。
- モジュール群（ポートフォリオ構築・リスク調整・ポジションサイジング）
  - portfolio/portfolio_builder.py: select_candidates, calc_equal_weights, calc_score_weights を追加。スコアゼロ時のフォールバックの挙動を実装。
  - portfolio/risk_adjustment.py: apply_sector_cap（セクター集中制限）と calc_regime_multiplier（市場レジームに応じた乗数）を追加。unknown セクターの扱いや未知レジームでのフォールバックを明記。
  - portfolio/position_sizing.py: calc_position_sizes を追加。risk_based / equal / score の配分方式、lot_size（単元）丸め、aggregate cap（利用可能現金に合わせたスケーリング）、cost_buffer（手数料・スリッページの保守見積）や各種リスク上限の考慮を実装。
- 監視・計測・レポート
  - monitoring 初期化呼び出し（monitoring_db.init_monitoring_db を使用して監視テーブルの冪等初期化）。
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率、注文成功率（Filled / Created）、送信率、P95 レイテンシ等を計算・出力。期間指定（--from, --to）と DB 指定（--db）に対応。閾値による PASS/FAIL 判定を実装。
- 研究用ユーティリティ（ドラフト）
  - research/factor_research.py: DuckDB を用いたファクター計算基盤（モメンタム、MA、ATR 等）を追加。calc_momentum などの計算ロジックの実装開始（DuckDB を受け取って prices_daily 等を参照する設計）。

### Changed
- 起動時の安全対策
  - 監視プロセスは KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する旨を明記（監視データは環境に依存しない想定）。
  - 実行エンジンは paper_trading 环境では専用の paper_sqlite_path を用い、本番データと分離。
- ログ出力の挙動
  - ログはデフォルトで stdout に出力するように変更（cron 等で stdout/stderr を統合する運用を想定）。
  - ログハンドラの重複登録を防止するため、既存ハンドラを flush/close してから置き換える実装に変更。

### Fixed
- .env 自動読み込みの安全性向上
  - OS 環境変数を保護する protected set を導入し、.env.local で OS 環境変数が上書きされるのを防止。
- ポジション計算の安定化
  - calc_score_weights で全スコアが 0.0 の場合に等金額配分へフォールバックすることでゼロ除算や不正配分を防止。
  - calc_position_sizes における単元丸めや aggregate cap スケーリングで、端数処理（残余による lot_size 単位の追加配分）を明確化。

### Removed
- なし（初期リリースのため該当なし）

### Security
- .env ファイルは README/出力注釈で「絶対に Git にコミットしないこと」を強調するテンプレートを生成（config_setup.py の出力）。

### Notes / Known limitations / TODO
- research/factor_research.calc_momentum の実装は途中でファイルが切れている（コード断片が存在）。ファクター群の完全実装・テストは今後必要。
- apply_sector_cap: price_map に価格が欠損（0.0）した場合エクスポージャーが過少見積りされ、想定外の漏れが発生する旨の TODO コメントあり。前日終値等のフォールバック導入を検討。
- position_sizing: 将来的に銘柄別 lot_size をサポートする予定（現状は共通 lot_size）。
- process_priority / set_cpu_affinity は権限不足や環境差分で失敗する可能性があるため、失敗時は警告にとどめる設計。

---

開発者向け: 追加・変更点の詳細は各モジュールの docstring とコード内コメントを参照してください。必要であればこの CHANGELOG を基にセクションを分割してリリースノート化します。