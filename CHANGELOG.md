# CHANGELOG

すべての注目すべき変更をこのファイルで管理します。  
フォーマットは「Keep a Changelog」に準拠します。

最新の変更
----------

### [0.1.0] - 2026-04-21

Added
- 初期公開リリース。
- 起動スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は専用のペーパートレード用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全に分離して動作する。実行中の停止フラグ（data/stop_requested.flag）検出や PID ファイル管理を実装。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。Monitoring は環境に関係なく本番 sqlite_path を使用して監視データを記録。
- 設定関連
  - config.Settings: 環境変数をラップする Settings クラスを提供。多数のプロパティ（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_TRADING_SQLITE_PATH、PID ファイルパス、閾値設定など）を定義し、妥当性チェックを行う。
  - 自動 .env ロード: プロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を自動的に読み込み（OS 環境変数優先、.env.local は上書き）、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化オプションをサポート。
  - 高度な .env パーサ: export プレフィックス、クォート値（エスケープ対応）、インラインコメントの扱いなどに対応する堅牢な .env パーサを実装。
- 設定運用支援 CLI
  - config_setup: 対話式ウィザードで .env の初期作成・更新を支援。入力のマスク、選択肢、デフォルト値をサポートし .env を書き出す。
  - validate_config: .env と config/*.yaml（存在する場合）の整合性を検証する CLI を追加。必須環境変数チェック、KABUSYS_ENV と LOG_LEVEL の妥当性、DB パスの親ディレクトリチェック、YAML パースチェック（PyYAML が存在する場合）や本番環境向けの追加ガードを実装。--strict オプションで警告を FAIL 扱いにできる。
- ロギング・プロセス管理ユーティリティ
  - utils.logging_setup: stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を組み合わせた統一ログセットアップを提供。LOG_DIR 指定・自動作成、LOG_LEVEL 解決ルール、既存ハンドラのクリア機能等を実装。ログディレクトリ作成失敗時はファイル出力をスキップして console のみで継続。
  - utils.process_priority: Windows と POSIX（Linux/macOS 等）で動作するプロセス優先度設定および CPU affinity 設定ユーティリティを追加。権限不足や非対応プラットフォームでは警告ログを出してフォールバックする。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順・同点タイブレークの選定ロジックを実装。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分を実装。スコア合計が 0 の場合は等配分にフォールバックして警告。
  - portfolio.risk_adjustment
    - apply_sector_cap: 既存保有のセクター別エクスポージャーを計算し、セクター集中が閾値を超える場合に当該セクターの新規候補を除外するロジックを実装（unknown セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数を提供。未知のレジームは 1.0 でフォールバックし警告。
  - portfolio.position_sizing
    - calc_position_sizes: risk_based / equal / score の各配分方法に対応した株数決定ロジックを実装。単元（lot_size）丸め・1 銘柄上限・全体投下上限（aggregate cap）・cost_buffer を考慮したスケーリングと残差分配ロジックを備える。価格欠損時はスキップする安全策あり。
- Paper Trading 検証ツール
  - tools.paper_verification_report: ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）からシステム安定性、注文成功率、送信率、レイテンシなどを集計してレポートを出力。P95 計算、閾値判定（稼働率、成立率、送信率、P95 レイテンシ）に基づく PASS/FAIL 判定を行う。コマンドライン引数 --from / --to / --db をサポート。
- research.factor_research（骨組み）
  - ファクター計算モジュールの骨組みを追加（Momentum / Value / Volatility / Liquidity の設計方針、定数、関数インターフェース）。DuckDB 接続を受け取り prices_daily / raw_financials を用いた計算を行う想定。

Changed
- 初期リリースのため変更履歴の過去版なし。

Fixed
- ログディレクトリ作成やファイルハンドラ作成に失敗した場合に、フォールバックしてコンソール出力のみで動作を継続する堅牢性を確保。
- 環境変数の自動ロードロジックが OS 環境変数を上書きしないよう保護キーセットを導入。

Security
- config_setup で生成される .env ファイルについて「絶対に Git にコミットしないこと」を明記（ウィザード内および出力ヘッダに警告）。

Known issues / Notes / TODO
- research.factor_research.calc_momentum の実装が未完（ソースが途中で切れている）。ファクター計算は現状で未完成の部分があるため、本格運用前に実装完了・検証が必要。
- portfolio.risk_adjustment.apply_sector_cap 内の price 欠損時の取り扱いについて注記あり（将来的に前日終値や取得原価でのフォールバックを検討）。
- position_sizing: 将来的に銘柄別の lot_size をサポートするための TODO が存在（現状は統一 lot_size）。
- run_monitoring は Monitoring 用 DB として settings.sqlite_path（本番パス）を常に使用するため、開発・テスト運用時は注意が必要。
- run_execution は paper_trading 時に MockBrokerClient を使い DB を分離する設計になっているが、BrokerClientFactory の具体的な実装やモックの動作は別モジュールに依存するため、環境設定に応じた確認が必要。

未分類
- パッケージ初期バージョンは __version__ = "0.1.0" として定義。

今後の予定（例）
- research モジュールのファクター計算を完成させる。
- 銘柄別 lot_size サポート、価格フォールバックロジックの強化。
- モニタリング・実行エンジンのさらに詳細な統合テストと運用ドキュメント整備。

-----------------------------------------------------------------------------
過去のリリース
- なし（初期リリース）