CHANGELOG
=========

すべての目立った変更点はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

注: 記載内容はコードベースから推測してまとめたもので、実装意図や将来の変更により差異が生じる可能性があります。

Unreleased
----------

- なし

[0.1.0] - 2026-04-19
--------------------

Added
- 初回リリース: KabuSys Python パッケージの基本機能を追加。
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。プロセス優先度設定、SQLite/DuckDB 接続、BrokerClient の生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、デーモンスレッドでのエンジン実行、停止フラグによるグレースフル終了処理を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する仕様。
- 設定・環境管理
  - config.py: .env の自動読み込み機能（.env / .env.local）、プロジェクトルート自動検出、.env パースロジック（export 形式／クォート／インラインコメントの取り扱い）を実装。Settings クラスで各種環境変数（DB パス、ログレベル、閾値、ペーパートレード設定等）をラップ。
  - config_setup.py: 対話式ウィザードで .env を作成・更新する CLI を追加。既存 .env の読み込み、シークレット扱い、デフォルト値や選択肢提示、保存確認をサポート。
  - validate_config.py: 起動前に .env と config/*.yaml の妥当性を検査する CLI を追加（--strict オプションあり）。必須環境変数やパス、YAML の存在・パース確認、KABUSYS_ENV に対する本番向けの注意喚起を行う。
- ログ・プロセスユーティリティ
  - utils/logging_setup.py: 標準化されたロギング設定ユーティリティを追加。コンソール(stdout) と日次ローテートファイル出力 (TimedRotatingFileHandler) を設定し、ログディレクトリ作成失敗時はファイル出力をスキップするフェイルセーフを実装。
  - utils/process_priority.py: プロセス優先度（Windows / POSIX に対応）と CPU affinity 設定機能を追加。権限不足や未対応 OS の場合は警告を出して安全にスキップする。
- ポートフォリオ構築モジュール（純粋関数）
  - portfolio/portfolio_builder.py: シグナルの上位選定、等金額配分、スコア加重配分を実装。スコア全ゼロ時は等配分にフォールバックして警告。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を実装。unknown セクター取り扱いやレジーム不明時のフォールバックを備える。
  - portfolio/position_sizing.py: allocation_method（risk_based / equal / score）に基づく株数算出、単元株（lot_size）丸め、個別上限・総投資上限（aggregate cap）を実装。コストバッファを考慮したスケーリングと残余配分ロジックを含む。
  - portfolio/__init__.py で主要 API をエクスポート。
- 解析 / ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシなどを算出・閾値判定して PASS/FAIL を出力。P95 算出、日付フィルタ、DB 存在チェックを実装。
  - research/factor_research.py: DuckDB を用いたファクター計算モジュール（モメンタム、MA200、ATR、出来高系など）を追加（実装は一部を含む）。
- パッケージメタ
  - __init__.py に __version__ = "0.1.0" を追加。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Security
- なし（初回リリース）

Notes / 実装上の重要な挙動（ドキュメント）
- Monitoring は KABUSYS_ENV に依存せず常に Settings.sqlite_path を使用して監視 DB を操作する（運用上の注意）。
- Execution は is_paper 判定により PAPER_TRADING_SQLITE_PATH（data/paper_trading.db デフォルト）を使用して本番 DB と分離する設計。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われ、プロジェクトルートが見つからない場合はスキップされる。
- process_priority / set_cpu_affinity は権限不足や未対応プラットフォームで安全にスキップし、起動失敗を引き起こさないようにしている。
- logging_setup はログディレクトリ作成に失敗した場合でもコンソールログのみで継続する。

今後の改善案（コード中に TODO が存在）
- position_sizing: 銘柄ごとの単元株（lot_size）を stocks マスタから取得して対応する（現在は全銘柄共通 lot_size を使用）。
- risk_adjustment: price 欠損時のフォールバック価格（前日終値や取得原価）を利用してエクスポージャー見積りを改善する。
- research/factor_research: 大量データ処理の最適化や追加ファクターの実装。

（以上）