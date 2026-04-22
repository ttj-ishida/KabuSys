CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
日付はリリース日を表します。

Unreleased
----------

（現在未リリースの変更はありません）

[0.1.0] - 2026-04-22
-------------------

Added
- 初回公開: KabuSys 自動売買ライブラリおよび実行ユーティリティ群を追加。
- 実行スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV に応じて本番/ペーパートレードの DB を切り替え、スレッドでエンジンを起動・停止する仕組みを提供。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。
- 環境設定・検証
  - config_setup.py: .env を対話式に作成・更新するウィザード（CLI）を追加。
  - validate_config.py: .env と config/*.yaml の事前検証 CLI を追加（--strict オプションで警告をエラー扱いにできる）。
  - config.py: Settings クラスを導入し、環境変数の集中管理・検証（値チェック、既定値、Paper Trading 用オプション等）を追加。自動 .env ロード機構（.env, .env.local）を実装。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: シグナル選定 (select_candidates)、等加重・スコア加重（calc_equal_weights, calc_score_weights）を追加。
  - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を追加。
  - portfolio.position_sizing: 発注株数計算（calc_position_sizes）を追加。risk_based / equal / score の割当方式をサポートし、単元（lot_size）丸め、aggregate cap スケーリング、cost_buffer を考慮。
- 監視・検証ツール
  - monitoring.monitoring_db の初期化ユーティリティを利用する仕組みを導入（init_monitoring_db を起動時に呼び出し、冪等に監視テーブルを保証）。
  - tools.paper_verification_report: ペーパートレード検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・レイテンシ（P95）などの集計と PASS/FAIL 判定を出力。
- ユーティリティ
  - utils.logging_setup: 統一的なログ設定ユーティリティを追加。コンソール（stdout）と日次ローテートファイル（TimedRotatingFileHandler）を設定、ログディレクトリ作成の失敗はフォールバック。
  - utils.process_priority: クロスプラットフォームなプロセス優先度設定（高/通常/低）と CPU affinity 設定を追加（Windows/Linux/macOS 対応、権限エラーは警告で無視）。
- research.factor_research: DuckDB を用いたファクター計算（モメンタム等）を追加（prices_daily / raw_financials テーブル依存）。設計方針・定数・インターフェースを導入。
- パッケージメタ
  - __init__.py にバージョン __version__ = "0.1.0" を追加。

Changed
- 環境変数の読み込み/解析を堅牢化
  - config._parse_env_line: export 形式、単一/二重クォート、バックスラッシュエスケープ、行内コメントの扱い等に対応。
  - 自動 .env ロードは OS 環境変数を保護し、.env.local を .env の後に上書きで読み込む（既存 OS 環境変数は上書きされない）。
- 実行および監視の安全性改善
  - run_execution: Paper Trading（settings.is_paper）が有効な場合、paper_sqlite_path を使用して本番 DB と明確に分離。起動時に停止フラグが立っている場合は起動せず終了。
  - run_monitoring: 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様を明示。停止フラグ/KeyboardInterrupt によるクリーンなシャットダウン処理を実装。
  - init_monitoring_db を起動時に呼び出して監視テーブルの存在を保証（冪等）。
- ロギング
  - setup_logging: 既存ハンドラを安全に flush/close してクリアしてから再設定するように変更。ファイル書き出しに失敗した場合はコンソール出力にフォールバック。
- 取引ロジックの堅牢化
  - portfolio.calc_score_weights: 全てのスコアが 0 の場合、等金額配分にフォールバックして WARNING を出力。
  - risk_adjustment.apply_sector_cap: sector が不明な銘柄を "unknown" として扱い、セクター上限の適用対象外とする（既存保有の計算で除外可能）。
  - position_sizing.calc_position_sizes: lot_size による丸め、aggregate cap 超過時のスケールダウンと端数配分ロジック、cost_buffer による保守見積りを追加。
- CLI/レポート
  - paper_verification_report: date 範囲指定および DB パスオーバーライドオプションを追加。P95 計算・閾値チェックによる PASS/FAIL 判定を実装。

Fixed
- 環境変数値検証とフォールバック
  - _get_poll_interval (run_monitoring): MONITOR_POLL_INTERVAL が不正（非整数や 0 以下）の場合に警告を出しデフォルト（60 秒）へフォールバック。
  - Settings.paper_fill_mode: 無効な値指定時に ValueError を送出して早期検出。
  - set_process_priority / set_cpu_affinity: psutil の AccessDenied 等を捕捉し、失敗時は警告を出して処理を継続するように修正（起動失敗を避ける）。
- DB 周りの堅牢化
  - 各種クエリ関数（paper_verification_report 内）で sqlite3.OperationalError を捕捉し、テーブル未存在時に安全にデフォルト値を返すように対応。
- config_setup/_write_env: .env のテンプレート出力を追加し、生成される .env の内容とフォーマットを明確化。

Security
- .env ファイルの自動読み込みにおいて OS 環境変数を保護する仕組み（protected set）を導入。意図せず重要な OS 環境変数が .env によって上書きされることを防止。

Notes / Known limitations
- research.factor_research の実装はモジュール設計と一部関数のインターフェースを含むが、実装の続きはコードベース参照（ファイル末尾が未完の可能性あり）。
- 単元株（lot）や価格フォールバック（前日終値等）の扱いは現状簡易実装。将来的に stocks マスタの lot_size 等を受け取る拡張を想定。
- 一部外部ライブラリ（psutil, duckdb, PyYAML）が必須／任意で使用されるため、環境に応じてインストールが必要。validate_config は PyYAML 未導入時に YAML 検証をスキップする。

Copyright
- 初版リリース（0.1.0） — KabuSys チーム