CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
フォーマットは Keep a Changelog に準拠しています。

0.1.0 - 2026-04-17
------------------

Added
- 基本リリース: KabuSys 初期実装を追加。
- 環境設定/ロード周り
  - .env の自動読み込み機能を実装（プロジェクトルートに基づき .env / .env.local を順に読み込み）。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - 高度な .env パーサを実装（export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメント処理をサポート）。
  - protected キーを使用して OS 環境変数を上書きから保護する仕組みを導入。
- 設定ユーティリティ
  - Settings クラスを追加し、環境変数から各種設定（DB パス、API トークン、動作モード等）を取得する API を提供。KABUSYS_ENV の検証や PAPER_FILL_MODE の妥当性チェック等を実装。
  - config_setup CLI（対話式ウィザード）を実装し、.env の初期生成・更新を支援。機密項目はマスク表示、デフォルト値や選択肢サポートあり。
  - validate_config CLI を追加。必須環境変数、KABUSYS_ENV、LOG_LEVEL、DB パス、config/*.yaml の存在とパース（PyYAML が存在する場合）などを検証。--strict オプションで警告も失敗扱いにできる。
- 実行スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。起動時にプロセス優先度を上げ、環境に応じて paper_trading 用 DB を分離して使用（PAPER_TRADING_SQLITE_PATH）。BrokerClientFactory を利用して適切なブローカクライアントを生成。スレッドでエンジンを実行し、 data/stop_requested.flag による停止を監視。PID ファイル管理をサポート。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する点に注意。
- 監視 DB 初期化
  - init_monitoring_db により、起動時に監視用テーブルが存在することを保証する仕組みを追加（冪等）。
- ツール
  - tools/paper_verification_report: Paper Trading 用の検証レポート生成ツールを追加。期間指定可能（--from, --to, --db）。稼働率、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシなどを算出し PASS/FAIL を判定する閾値を定義。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア重み（calc_score_weights）を実装。スコアが全て 0 の場合は等金額へフォールバック。
  - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジームに基づく投下資金乗数（calc_regime_multiplier）を実装。未知レジーム時は警告とともに 1.0 でフォールバック。
  - portfolio.position_sizing: position sizing ロジックを実装。allocation_method に "risk_based" / "equal" / "score" をサポート。単元株（lot_size）で丸め、per-stock 上限および aggregate cap（available_cash）を考慮したスケールダウンと残余配分ロジックを実装。cost_buffer により手数料・スリッページ分を保守的に見積もり。
- リサーチ
  - research.factor_research: DuckDB 接続を受け取り、prices_daily / raw_financials テーブルから Momentum（1M/3M/6M、MA200乖離）および Volatility（ATR、平均売買代金、出来高比等）を計算する関数群を追加。営業日ベースのウィンドウを考慮した SQL を使用。
- ユーティリティ
  - utils.process_priority: クロスプラットフォーム（Windows / POSIX）でプロセス優先度（および CPU affinity）を設定するユーティリティを追加。psutil を使い、権限不足などは警告を出して安全にスキップする。

Changed
- パッケージ情報
  - パッケージ初期バージョンを __version__ = "0.1.0" に設定。

Fixed
- .env パースの堅牢化
  - クォート内のバックスラッシュエスケープや、クォート無し文字列でのコメント認識（直前が空白/タブの場合のみ）等、従来パターンでの誤解析を回避する実装に改良。

Security
- .env 取り扱い注意
  - config_setup にて .env の生成時に「.env は絶対に Git にコミットしないこと」を明示する説明を追加。

Notes / Breaking changes / Important
- 監視（run_monitoring）は「環境にかかわらず本番 sqlite_path を使用」します。監視 DB を分離したい場合は Settings の SQLITE_PATH を適切に設定してください。
- paper_trading（KABUSYS_ENV=paper_trading）では run_execution が paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番 DB と完全に分離されるようになっています。ペーパートレードと本番データの混在に注意してください。
- process_priority / set_cpu_affinity は権限やプラットフォームに依存するため、失敗時は警告を出して無害にスキップします。
- validate_config は PyYAML がインストールされていない環境でも実行可能ですが、その場合は YAML パースチェックをスキップして警告を出します。

今後の予定
- position_sizing における銘柄別 lot_size 対応（stocks マスタ参照）や価格フォールバックロジックの追加。
- factor_research の追加ファクター実装およびテストカバレッジ拡充。
- ExecutionEngine / SystemMonitor の追加統合テストと CLI の起動オプション拡張。