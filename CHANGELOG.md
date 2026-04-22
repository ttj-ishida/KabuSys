# Changelog

すべての重要な変更点をここに記録します。  
このファイルは「Keep a Changelog」規約に準拠しています。

フォーマット:
- 変更はセクション（Added, Changed, Fixed, Deprecated, Removed, Security）ごとに分類しています。
- 各バージョンにはリリース日を記載しています。

---

## [Unreleased]

開発中または次回リリースで取り込む予定の変更点をここに記載します。

- なし（初期リリースのため未登録）

---

## [0.1.0] - 2026-04-22

初回公開リリース。システム全体の基盤機能（実行エンジン、監視、設定管理、ポートフォリオ構築、ユーティリティ、ツール群）を実装しました。

### Added
- 実行/エンジン関連
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV による paper_trading モード判定を実装し、paper_trading 時は専用の SQLite（デフォルト: data/paper_trading.db）を使用することで本番 DB と完全分離を実現。
  - BrokerClientFactory によるブローカークライアントの組み立てを想定。
  - PID 管理（data/execution.pid）および停止フラグ（data/stop_requested.flag）サポート。

- 監視関連
  - run_monitoring.py: SystemMonitor 用ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）。監視は環境に関わらず本番用 sqlite_path を使用して監視データを記録。
  - monitoring_db 初期化ロジック呼び出し、duckdb と sqlite3 両方の接続を確立。

- 設定・環境
  - config.py: 環境変数/.env 管理モジュールを追加。自動 .env ロード（.env, .env.local）を行い、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化をサポート。
    - .env パースで export KEY=val 形式、クォート値（バックスラッシュエスケープ含む）、インラインコメントを正しく処理。
    - 各種設定プロパティ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス、Paper Trading 関連設定、監視閾値など）をプロパティとして提供。
    - KABUSYS_ENV / LOG_LEVEL 等のバリデーションを内蔵。
  - config_setup.py: 対話式 .env 作成ウィザードを追加（入力補助・デフォルト・シークレット表示など）。
  - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数、パス・ディレクトリ、config/*.yaml の存在とパース（PyYAML があればパース検証）等をチェック。--strict オプションで警告をエラー扱いに可能。

- ポートフォリオ構築（純粋関数）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルのスコア降順ソートと上位 N 選出。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分を実装（スコアが全て 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中の上限チェック（既存ポジションのセクター露出計算と候補除外）。
    - calc_regime_multiplier: マーケットレジームに応じた投下資金乗数（bull/neutral/bear をサポート、未知値は 1.0 にフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based/equal/score）に基づく発注株数算出。単元株（lot_size）、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap のスケーリングロジックを実装。

- ユーティリティ
  - utils/logging_setup.py: 統一ロギング設定ユーティリティを追加。stdout（StreamHandler）と日次ローテーション（TimedRotatingFileHandler）をルートロガーに設定、ログディレクトリ作成やフォールバック処理を備える。ログ保持は 30 日。
  - utils/process_priority.py: クロスプラットフォームのプロセス優先度設定（Windows の priority class、POSIX の nice 値）と CPU affinity 設定を追加。権限不足や未対応 OS の場合は警告でスキップ。

- ツール / レポート
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。システム稼働率、注文成功率、送信率、API レイテンシ（平均・最大・P95）などを集計して PASS/FAIL 判定を行う。デフォルトの閾値（稼働率 99%、成立率 90% 等）を設定し、--from/--to/--db オプションをサポート。

- パッケージ初期化
  - kabusys/__init__.py: パッケージメタ情報（__version__ = "0.1.0"）と公開 API の簡易宣言。

- 研究モジュール（骨組み）
  - research/factor_research.py: ファクター計算モジュールの骨格を追加（モメンタム・ボラティリティ等を設計）。DuckDB 接続を受け prices_daily / raw_financials を参照して計算する設計。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Deprecated
- なし

### Removed
- なし

### Security
- 環境変数の自動ロード時、OS 環境変数を保護する機能を実装（.env の値で OS 環境変数が誤って上書きされない）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化も提供。

---

## 既知の注意点 / TODO
- portfolio/risk_adjustment.apply_sector_cap: price_map に価格が欠損（0.0）の場合、エクスポージャーが過少見積りされる可能性がある旨の注記と将来的なフォールバック価格使用の TODO が残っています。
- position_sizing.calc_position_sizes:
  - 将来的には銘柄別の lot_size をサポートする予定（現在は全銘柄共通の lot_size を想定）。
- research/factor_research.py:
  - ファイル末尾が途中で切れている（calc_momentum の定義が途中）。研究モジュールの実装は継続中。
- run_monitoring.py:
  - 監視は「環境に関わらず本番 sqlite_path を使用する」仕様のため、運用時に意図しない DB を操作しないよう注意が必要（設計による挙動）。
- process_priority / cpu_affinity の設定は権限に依存するため、実行環境の権限設定によっては効果が得られない場合があります。失敗時は警告を出してスキップします。

---

脚注:
- 本 CHANGELOG は現行コードベースから推測して作成しています。実装の詳細や将来の変更にともない内容が更新されます。