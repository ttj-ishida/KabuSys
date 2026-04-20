CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。
比較的最近のコードベースの状態から実装内容を推測してまとめたリリースノートです。

フォーマット:
- Unreleased: 今後の変更（現時点では未リリース）
- 各リリース: 日付とカテゴリ別（Added / Changed / Fixed / Removed / Security）

Unreleased
----------
（現状のコードベースに基づく初期リリース相当の状態のため、未リリース項目はありません。）

[0.1.0] - 2026-04-20
--------------------
初期公開リリース（推測）。システム全体のコア機能をまとめた最初の安定化版。

Added
- 実行用エントリスクリプト
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。プロセス優先度設定、SQLite / DuckDB 接続、Broker クライアント生成、OrderManager / RiskManager / Reconciler 組立、エンジンのデーモンスレッド実行・停止処理、停止フラグ（data/stop_requested.flag）検知を実装。
  - Paper Trading 環境（KABUSYS_ENV=paper_trading）の場合は専用 SQLite（data/paper_trading.db）を使用する仕組みを導入。MockBrokerClient を使った分離運用を想定。
- 監視用エントリスクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視用 DB 初期化・duckdb 接続・停止フラグ検知・例外ハンドリングを実装。
- 設定管理
  - config.py: 環境変数・.env 自動読み込みロジックを導入（プロジェクトルート自動検出: .git または pyproject.toml）。.env / .env.local の読み込み順と OS 環境変数を保護する仕組みを実装。設定値のプロパティ群（DB パス、API トークン、KABUSYS_ENV 判定、Paper Trading 設定など）を提供。
  - config_setup.py: .env 初期作成・更新のための対話式ウィザードを追加。既存 .env の読み込み、シークレット扱い、デフォルト／選択肢対応、書き込み機能を持つ。
  - validate_config.py: 起動前設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベル、DB パス存在性、config/*.yaml の存在・パース（PyYAML があれば検証）や本番環境向けガードを実装。--strict オプションで警告を FAIL 扱いにできる。
- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py: StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーへ一括設定するユーティリティを追加。ログディレクトリの自動作成と失敗時のフォールバック挙動を実装。ログレベル解決の優先度を定義。
  - utils/process_priority.py: Windows / POSIX の差分を吸収したプロセス優先度設定および CPU affinity 設定ユーティリティを追加。権限不足や未対応プラットフォームへの安全なフォールバックを用意。
- ポートフォリオ構築
  - portfolio/portfolio_builder.py: 候補銘柄の選定（スコア順）、等金額配分・スコア加重配分の純粋関数を実装。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。未知のセクター／レジームに対するフォールバック挙動を定義。
  - portfolio/position_sizing.py: position sizing（risk_based / equal / score）を実装。単元株（lot_size）丸め、1銘柄上限・aggregate cap、コストバッファを考慮したスケーリングロジック、端数処理ロジックなどを含む。
  - package エクスポート（portfolio/__init__.py）で主要関数を公開。
- ツール類
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。期間フィルタ、稼働率・注文成功率・送信率・P95 レイテンシなどを集計・判定（PASS/FAIL）する。欠損テーブルや OperationalError に対する耐性を持つ。各種閾値（稼働率99%、fill 90% 等）を定義。
- パッケージメタ
  - __init__.py にて __version__ = "0.1.0" を設定（パッケージバージョン）。

Changed
- 環境変数読み込みの堅牢化
  - .env パーサーが export プレフィクス、シングル／ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い、クォートなしでの # コメントの解釈（直前がスペースまたはタブの場合）に対応。
  - .env.local の上書き時に OS 環境変数を保護する protected パラメータを導入。
- ログ出力の標準化
  - 各起動スクリプトから共通の setup_logging を呼ぶことでログ出力形式・ローテーションを統一。
- DB パスの環境分離
  - 実行エンジンは paper_trading 環境時に専用 SQLite を使用（settings.paper_sqlite_path）。監視機能は環境にかかわらず本番 monitoring DB（settings.sqlite_path）を使う旨が明示されている（監視データの統一管理）。

Fixed
- 例外耐性の強化
  - run_monitoring.py の監視ループで check_once() が例外を投げてもループを継続し、スタックトレースはログに残すようにして運用の安定性を向上。
  - run_execution.py/run_monitoring.py の終了処理で SQLite / DuckDB 接続を finally で確実に close するように実装。
  - logging_setup でログディレクトリ作成失敗時にファイルハンドラをスキップする安全策を追加。

Security
- 機密情報の扱い
  - config_setup や .env 書き出しのドキュメントに「.env を絶対に Git にコミットしないこと」を明記。
  - config.Settings は必須機密値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）を取得するプロパティを提供し、未設定時は ValueError を送出して明示的に失敗させる。

Notes / Implementation details（補足）
- validate_config.py は PyYAML が未インストールでも動作し、YAML 検証は任意でスキップされる（警告出力）。config/*.yaml は scripts/generate_config.py で生成できる旨の注記がある。
- process_priority.set_process_priority() は OS に依存する実装差を吸収。権限不足等で設定できない場合は警告ログを出す設計。
- portfolio の関数群は純粋関数（副作用なし）として設計され、DB 参照を行わないため単体テストが容易。
- research/factor_research.py はファクタ計算モジュールの実装を開始しており（Momentum 等）、DuckDB の prices_daily / raw_financials を使う設計。ファイルは途中で切れているが設計方針や定数類が整備されている。

今後の提案（任意）
- validate_config の出力を CI チェックに組み込み、--strict モードを CI で使う。
- logging_setup のファイルハンドラ作成失敗時に、より詳細なフォールバック先（例: /var/log/kabusys/ など）を検討。
- portfolio の lot_size を銘柄別に拡張するための stocks マスタ導入（コメントに記載済み）。
- research/factor_research の続き実装と単体テスト追加。

--- 
（注）本 CHANGELOG は提示されたソースコードからの推測に基づいて作成しています。実際のコミット履歴・リリースノートがある場合はそちらを優先してください。