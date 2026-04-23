# CHANGELOG

すべての重要な変更をこのファイルで記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

なお、本 CHANGELOG は提示されたソースコードから実装内容を推測して作成しています（コミット履歴そのものではありません）。

## [Unreleased]

### Added
- 実行用スクリプトを追加
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。プロセス優先度の設定、SQLite / DuckDB 接続、Broker クライアント生成、OrderManager / RiskManager / Reconciler の組み立て、Engine の起動・停止監視（data/stop_requested.flag を介した制御）を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は本番用 sqlite_path を使用（KABUSYS_ENV に依らない）。
- 設定管理と初期化ツール
  - config.py: 環境変数 / .env / .env.local の自動読み込み（プロジェクトルート検出による）、値取得ユーティリティ（Settings クラス）を実装。必須値のチェック（_require）や各種デフォルト値を定義。
  - config_setup.py: .env の対話式ウィザードを追加（.env の初期作成・更新を支援）。
  - validate_config.py: 起動前の設定検証 CLI を追加（--strict オプションで警告も失敗扱いにできる）。必須環境変数・パス・YAML ファイル等の検査を実施。
- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: ルートロガー設定ユーティリティを追加。StreamHandler（stdout）と日次ローテートの TimedRotatingFileHandler を設定。ログディレクトリ作成の失敗時はファイル出力をフォールバック。
  - utils/process_priority.py: クロスプラットフォームのプロセス優先度設定と CPU affinity 設定を追加。Windows / POSIX (Linux/macOS/FreeBSD) に対応し、権限不足等は警告でスキップ。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py: 候補選定（スコア降順・タイブレーク）、等配分・スコア加重配分（スコア全件 0 の場合は等配分にフォールバック）を実装。
  - portfolio/risk_adjustment.py: セクター集中上限を適用する apply_sector_cap、および市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（未知レジームは警告の上 1.0 でフォールバック）。
  - portfolio/position_sizing.py: 単元株丸めやリスクベース / 等分配 / スコア配分に基づく発注株数計算を実装。aggregate cap（利用可能現金超過時）のスケーリング、lot_size 単位での補正、cost_buffer による保守的なコスト見積りを実装。
  - portfolio/__init__.py で上記関数群を公開。
- Paper Trading ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。期間指定（--from / --to）や DB パス指定（--db / 環境変数）に対応。稼働率・注文成功率・送信率・レイテンシ（P95）などの指標を計算し PASS/FAIL を判定する閾値を定義。
- Research モジュール（基盤）
  - research/factor_research.py: ファクター計算の骨組みを追加（Momentum / Value / Volatility / Liquidity を想定）。DuckDB を受け取り prices_daily / raw_financials を参照する方針で実装開始（モジュールは引き続き実装中）。
- パッケージ・メタ
  - __init__.py にバージョン定義 __version__ = "0.1.0" を追加。

### Changed
- なし（本 CHANGELOG 作成時点での初期機能群として推定）

### Fixed
- なし（ソースに明示的なバグ修正履歴は含まれていないため記載なし）

### Security
- なし

## [0.1.0] - 2026-04-23

Initial release（推定）。上記「Added」に記載した主要機能を含む最初のリリース相当。

- 実行/監視の起動スクリプト（run_execution, run_monitoring）
- 環境設定 / 検証用 CLI（config_setup, validate_config）
- ログ設定・プロセス制御ユーティリティ
- ポートフォリオ構築・リスク制御・ポジションサイジングの純粋関数群
- Paper Trading 向け検証レポート生成ツール
- DuckDB を利用するリサーチ基盤（factor_research の骨子）
- パッケージバージョン設定

## 既知の制限・注意点（コードコメント等からの要約）
- run_monitoring は KABUSYS_ENV にかかわらず本番用 sqlite_path（SQLITE_PATH のデフォルト）を使用する実装になっている点に注意。paper_trading 環境で監視 DB を分離したい場合は注意が必要。
- run_execution は paper_trading 環境時に専用 DB（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）を使用して本番 DB と分離する設計。
- .env 自動読み込みはプロジェクトルートの検出に依存する（.git または pyproject.toml が見つからない場合は自動ロードをスキップ）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
- .env パーサは export プレフィックス、引用符内のエスケープやインラインコメント処理に対応しているが、極端に複雑な .env の全ケースを保証しているわけではない。
- portfolio.risk_adjustment.apply_sector_cap:
  - price_map に価格が欠損（0.0）だとセクターエクスポージャーが過小見積りされる警告コメントあり。将来的にフォールバック価格の導入を検討中。
- portfolio.position_sizing:
  - 現在は全銘柄共通の lot_size を想定（デフォルト 100）。将来的に銘柄別 lot_size を受け取る設計への拡張が TODO として記載されている。
  - aggregate スケーリングは lot_size 単位の丸めと残余配分ロジックにより再現性を確保しているが、端数処理の実装結果は運用で要確認。
- utils/process_priority: 権限不足や未サポート OS の場合は警告を出して設定をスキップする（失敗は致命的にならない）。
- research/factor_research.py は計算ロジックの実装途中（ファイル末尾の calc_momentum の実装が途中で切れている）であり、完全な動作には追加実装が必要。

## 将来の改善候補（ソースからの推奨・TODO）
- portfolio.position_sizing: 銘柄ごとの lot_size を導入し、stocks マスタ等から取得する設計に拡張する。
- apply_sector_cap: 価格欠損時のフォールバック価格（前日終値や取得原価）を導入してエクスポージャー見積りを改善する。
- research モジュール: Factor 計算の完全実装とユニットテスト追加。
- run_monitoring/run_execution: より柔軟な DB パス/環境分離ポリシーの見直し（監視用途での paper_trading 分離等）。
- ロギング: ファイル出力失敗時の詳細通知やリモート集約オプションの追加。

---

（注）本 CHANGELOG は提供されたソースコードの内容をもとに推測して作成しています。実際の変更履歴（コミットログ等）に基づく正確な履歴が必要な場合は、該当リポジトリの Git 履歴を参照のうえ調整してください。