CHANGELOG
=========

すべての変更は「Keep a Changelog」形式に準拠して記載しています。  
日付はソースコードから推測できる最新の状態（2026-04-19）を使用しています。

[Unreleased]
------------

- ドキュメント・テストなどのマイナー作業（該当箇所が明示されていないため詳細は省略）。

[0.1.0] - 2026-04-19
-------------------

Added
- 初期リリース相当の機能群を追加。
  - 実行スクリプト
    - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。KABUSYS_ENV に応じて paper_trading 用 DB を分離して利用する（デフォルトで data/paper_trading.db）。停止用フラグファイル検知、PID ファイル書き込み・管理、バックグラウンドスレッドでのセッション実行制御を実装。
    - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は本番 sqlite_path を常に使用する設計。
  - 設定・環境管理
    - config.py: .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。環境変数のパース処理を強化し、クォートや export 形式、インラインコメント等に対応。設定値取得用 Settings クラスを提供（各種パス・閾値・フラグ・環境判定プロパティを実装）。
    - config_setup.py: 対話式ウィザードで .env を初期作成・更新する CLI を追加。デフォルト・選択肢・シークレット表示などの UX を実装し、.env の読み書きロジックを提供。
    - validate_config.py: 起動前に環境変数や config/*.yaml を検証する CLI を追加。必須/任意環境変数チェック、パス存在チェック、YAML パース（PyYAML があれば実施）、本番環境向けの追加警告を行う。--strict モードで警告を FAIL 扱いにできる。
  - ポートフォリオ構築（純関数群）
    - portfolio/portfolio_builder.py: シグナル選定（スコア降順）と等重・スコア重み計算を実装。
    - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。未知レジーム時のフォールバックやログ出力を含む。
    - portfolio/position_sizing.py: 株数決定ロジックを実装（risk_based / equal / score の各方式）。単元株丸め、ポジション上限、aggregate cap によるスケールダウン、コストバッファ考慮、残差配分ロジックを含む。
    - portfolio パッケージのエクスポートを追加（select_candidates 等）。
  - ユーティリティ
    - utils/logging_setup.py: ルートロガーの統一設定機能を追加。コンソール(stdout) と日次ローテーションファイル（TimedRotatingFileHandler）を設定。環境変数／引数によるログレベル・ログディレクトリ解決、ファイル出力失敗時のフォールバックを実装。
    - utils/process_priority.py: プロセス優先度（および CPU affinity）設定ユーティリティを追加。Windows と POSIX の差を吸収し、安全にフォールバックする実装。
  - 分析・レポート
    - tools/paper_verification_report.py: ペーパートレード専用 DB から稼働率・注文成功率・送信率・レイテンシ（P95）等を集計して検証レポートを生成する CLI を追加。閾値（稼働率 99% 等）に基づく PASS/FAIL 判定を実装。
  - 研究用モジュール
    - research/factor_research.py: DuckDB 接続を受け取り、Momentum/Value/Volatility/Liquidity 等のファクターを計算するための基盤実装を追加（モメンタム計算のための定数や関数の骨組みを含む）。DuckDB の prices_daily / raw_financials テーブルを参照する設計。
  - パッケージメタ
    - __init__.py に __version__ = "0.1.0" を設定。

Changed
- 監視 / 実行周りの設計調整
  - run_monitoring は KABUSYS_ENV にかかわらず監視用 DB に本番 sqlite_path を使用する仕様（監視データは一元化する意図）。
  - run_execution は paper_trading 時に専用 DB（paper_sqlite_path）を使うことで本番データと完全に分離する仕様を採用。

Fixed
- 環境変数パーサの堅牢化
  - config._parse_env_line にてクォート文字のエスケープや inline コメントの扱い、export 形式のサポートを実装。これにより .env の多様な記法に対して正しくパースできるようになった。
- ロギング設定の堅牢化
  - ログディレクトリ作成に失敗した場合でもコンソール出力のみで継続するようにし、ハンドラの二重登録を防止するため既存ハンドラをクリアしてから設定するようにした。
- プロセス優先度設定の安全化
  - 未対応 OS や権限不足時に例外を破壊的に投げないように捕捉して警告を出力するようにした。

Security
- 秘密情報の取り扱いに配慮
  - config_setup のウィザードではシークレット項目（トークン・パスワード）をマスク表示するなど、.env の取り扱いに注意を促す文言を追加。

Notes / Known issues
- TODO / 注意点（ソース内コメントより）
  - portfolio/risk_adjustment.apply_sector_cap:
    - price_map に price が欠損（0.0）の場合、エクスポージャーが過小評価される可能性がある。将来的に前日終値や取得原価などのフォールバック価格を使用する拡張を検討予定。
  - portfolio/position_sizing:
    - lot_size は現状グローバル固定（例: 100）を想定。将来的に銘柄別の lot_size を stocks マスタ等から取得する設計に拡張することが想定されている。
  - research/factor_research.py:
    - ファイル末尾で計算関数の実装が未完（抜粋のため一部未表示）。実装の継続・テストが必要。
- config の自動 .env 読み込みはプロジェクトルートが特定できない場合はスキップされる。テスト環境などで自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定する。

Migrating
- 既存の運用から移行する場合の注意
  - ペーパートレード DB（PAPER_TRADING_SQLITE_PATH）を利用することで本番 DB と分離できる。運用切替時は環境変数 KABUSYS_ENV を適切に設定し、.env の内容を validate_config で検証することを推奨。

Acknowledgments
- 初期実装をまとめたため大量のモジュール追加・設計決定が含まれます。今後はユニットテスト、ドキュメント整備、および research モジュールの完成を優先的に進めてください。