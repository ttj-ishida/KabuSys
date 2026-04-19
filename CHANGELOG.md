CHANGELOG
=========

すべての重要な変更はこのファイルに記載します。
フォーマットは「Keep a Changelog」仕様に準拠します。
タグ付けやリリースノート生成はここを参照してください。

Unreleased
----------

- 開発中の変更点はここに記載します。

0.1.0 - 2026-04-19
-----------------

Added
- 初回リリース: KabuSys 自動売買ライブラリ / 実行ユーティリティ群を追加。
- 環境設定・管理
  - Settings クラス（kabusys.config）を追加し、環境変数および .env ファイルから設定を取得できるようにしました。
  - .env 自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - .env ファイルの対話的作成・更新ウィザードを実装（kabusys.config_setup）。
    - シークレット項目はマスク表示。書き込み用テンプレート生成機能あり。
- 設定検証 CLI
  - validate_config モジュールを追加。必須環境変数や config/*.yaml の検査、KABUSYS_ENV や LOG_LEVEL の値チェック、起動前ガードなどを実行。
  - --strict オプションにより警告を失敗扱いにできる。
- ログ／プロセス管理ユーティリティ
  - 統一ログ設定ユーティリティ setup_logging（kabusys.utils.logging_setup）を追加。コンソール（stdout）と日次ローテートファイル出力をルートロガーに設定。
  - プロセス優先度と CPU affinity 設定ユーティリティを追加（kabusys.utils.process_priority）。
    - Windows/Linux/macOS の差分を吸収する実装。
- 実行／監視エントリポイント
  - run_execution: ExecutionEngine を起動するスクリプトを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB に分離して動作（MockBrokerClient 想定）。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能。停止フラグファイルによる安全停止対応。
- データベース連携
  - DuckDB と SQLite を併用する設計を採用。デフォルトパスは data/kabusys.duckdb / data/monitoring.db（環境変数で上書き可）。
  - 監視用 DB 初期化ユーティリティ（init_monitoring_db）呼び出しを各起動時に実行（冪等）。
- ポートフォリオ生成ロジック（純関数群）
  - portfolio_builder: 候補選定（select_candidates）・等重配分（calc_equal_weights）・スコア加重配分（calc_score_weights）を実装。calc_score_weights は全スコアが 0 の場合に等重配分へフォールバックして警告を出す。
  - risk_adjustment: セクター集中の上限適用（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。unknown セクターは上限対象外。
  - position_sizing: 発注株数決定ロジック（calc_position_sizes）を実装。risk_based / equal / score の配分方式に対応し、単元株（lot_size）丸め・aggregate キャップ（利用可能現金に合わせたスケールダウン）・cost_buffer を考慮した調整を行う。
    - スケールダウン時の端数処理は fractional remainder を用いて lot 単位で追加配分するアルゴリズムを実装。
- Paper Trading 検証ツール
  - tools/paper_verification_report: ペーパートレード用 SQLite から稼働率・注文成功率・レイテンシ等を集計し、PASS/FAIL 判定を行うレポート生成スクリプトを追加（期間指定オプションあり）。
- 研究用ファクター計算（下地）
  - research/factor_research: DuckDB を使ったモメンタム等のファクター計算モジュールを追加（設計方針、定数、calc_momentum 等の下地）。（実装は続く）

Changed
- ログ出力の標準化: すべての起動スクリプトで setup_logging を呼ぶことでログ設定を統一。
- run_execution / run_monitoring は起動直後にプロセス優先度を "high" にセットするように変更（set_process_priority を使用）。

Fixed
- 環境変数パースの堅牢化（kabusys.config）
  - .env の行パーサーを改善：export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント判定の扱いを明確化。
  - _load_env_file はファイルアクセス失敗時に警告を出してスキップするように安全化。
- run_monitoring のポーリング間隔設定で不正値（0 または負値、非整数）が設定された場合にデフォルト値へフォールバックし、警告を出すように修正。
- logging_setup: ログディレクトリ作成に失敗した場合はファイルハンドラをスキップしてコンソール出力のみで継続するように改善（起動失敗を防止）。
- process_priority / set_cpu_affinity: 権限不足や未対応プラットフォームでの例外を捕捉して警告にとどめるように変更し、起動停止しないようにした。
- validate_config:
  - PyYAML 未インストール時に YAML 検証をスキップして警告を出すようにした。
  - config/*.yaml の存在チェックとパース時のエラーメッセージを改善。
- position_sizing:
  - 価格未取得（<=0）の銘柄はスキップしてログにデバッグ情報を出すようにして安全化。
  - aggregate cap のスケーリングと端数配分ロジックを実装して、利用可能現金を超えないように調整。
- apply_sector_cap:
  - 当日売却予定銘柄（sell_codes）を既存エクスポージャー計算から除外できるようにした。
  - "unknown" セクターはセクター上限の対象外として扱う仕様を明示。

Security
- .env テンプレート生成時に「.env を絶対に Git にコミットしないこと」を明示。シークレット値は対話表示時にマスク。

Deprecated
- なし

Removed
- なし

Known issues / TODO
- apply_sector_cap: price_map に価格が欠損（0.0）の場合、エクスポージャーが過少見積もられてしまいブロックが外れる可能性あり。将来的に前日終値や取得原価でのフォールバックを導入予定。
- position_sizing: 現状は全銘柄共通の lot_size（単元株）を使用。将来的に銘柄別 lot_size を stocks マスタで管理する拡張を検討（コード内に TODO）。
- research/factor_research はモジュールの実装が一部で切れている（継続実装が必要）。

脚注
- 本 CHANGELOG はソースコードの内容から推測して作成したものであり、実際の変更履歴（コミットログ）とは異なる場合があります。必要に応じて正確なコミット履歴に基づく更新を行ってください。