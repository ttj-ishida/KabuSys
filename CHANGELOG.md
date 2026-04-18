CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" 規約に準拠しています。主にコードベースから推測される変更点・追加機能を日本語でまとめています。

フォーマット
-----------
- 参考バージョン: 0.1.0（パッケージ内の __version__ より）
- 日付: 2026-04-18（このログ作成日）

[Unreleased]
------------
（現時点では未リリースの変更はありません）

0.1.0 - 2026-04-18
-----------------

Added
- 基本アプリケーション骨格を実装
  - パッケージメタ情報（kabusys.__version__ = "0.1.0"）。
- 起動用スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを実装。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル（data/stop_requested.flag）を検知して安全にループを終了。
    - 起動時にプロセス優先度を "high" に設定。
    - 監視用 DB は環境に依らず production の sqlite_path を使用する設計。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを実装。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite DB（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成（環境に応じて Mock を切替）。
    - Engine をスレッドで起動し、停止フラグで Graceful stop（停止フラグ: data/stop_requested.flag）。
    - 起動時にプロセス優先度を "high" に設定、PID ファイルの扱いをサポート。
- 環境設定・検証ツール
  - config.py
    - .env 自動読み込み機能（プロジェクトルートの探索：.git または pyproject.toml 基準）。
    - 複雑な .env パーサ実装（export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメント処理）。
    - Settings クラスでアプリケーション設定（DB パス、各種閾値、KABUSYS_ENV 等）をプロパティ経由で安全に提供。値検証（許容値チェック）を実装。
  - config_setup.py
    - 対話式ウィザードで .env を生成/更新する CLI を実装。
    - 入力プロンプト、既存 .env の読み込み、シークレットマスク表示、ファイル書き出しをサポート。
  - validate_config.py
    - 起動前に .env と config/*.yaml の整合性を検証する CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、DB パス／ディレクトリ存在確認、YAML のパース検証（PyYAML がある場合）など。
    - --strict オプションで警告を失敗扱いにする機能。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30 日保持）を統一設定するユーティリティを実装。
    - ログレベル/ログディレクトリの解決順を明示（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - utils/process_priority.py
    - Windows と POSIX（Linux/Mac 等）でプロセス優先度の違いを吸収する set_process_priority 実装。
    - CPU affinity を指定する set_cpu_affinity 実装（指定が None の場合は変更しない）。
    - 権限不足や未対応 OS では警告を出して安全にスキップ。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコアが全て 0 の場合は等金額へフォールバック（警告ログ）。
  - portfolio/risk_adjustment.py
    - セクター上限（apply_sector_cap）: 既存保有比率に基づいて新規候補の除外ロジックを実装。unknown セクターは上限の対象外。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装（bull/neutral/bear をマップ、未知レジームはフォールバック 1.0）。
  - portfolio/position_sizing.py
    - 複数の配分方式（risk_based / equal / score）に対応した株数算出ロジックを実装。
    - lot_size（単元）丸め、単銘柄上限・集計上限（available_cash）チェック、コストバッファ考慮、スケーリング・端数配分ロジックを実装。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成 CLI を実装。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどを計算し PASS/FAIL を判定するしきい値を設置。
    - 日付フィルタ（--from / --to）と DB パス指定（--db / 環境変数）をサポート。
- リサーチ
  - research/factor_research.py（初期実装）
    - モメンタム等のファクター計算関数群の骨組みを実装（DuckDB 接続を受け prices_daily / raw_financials を参照する設計）。
    - 設計と定数定義（期間・ウィンドウ等）を含むが、一部関数実装が途中（ファイル末尾で切れている）。

Changed
- なし（初回リリース想定のため）

Fixed
- なし（初回リリース想定のため）

Deprecated / Removed / Security
- なし

Notes / 想定設計上の注意点（コードから推測）
- .env 自動読み込みはプロジェクトルートが検出できない場合はスキップされる。テストや特殊用途で無効化するために KABUSYS_DISABLE_AUTO_ENV_LOAD を用意。
- run_monitoring は監視用 DB を環境に依らず production sqlite_path を使用する設計（監視は常に本番データを参照する想定）。
- run_execution は paper_trading 環境時に完全に別 DB に記録し、本番 DB と分離することで安全にペーパートレードを行える設計。
- process_priority や CPU affinity の設定は権限・プラットフォームに依存するため失敗時は警告ログを出して処理を継続する（安全第一）。
- portfolio や position sizing の実装は純粋関数で DB 参照なし、テスタビリティと再現性を重視（randomness なし）。
- research/factor_research.py は価格データに基づく各種ファクター計算を行う設計だが、実装が途中のため追加実装・単体テストが必要。

今後の作業提案（推奨）
- research/factor_research の未完部分の実装完了とユニットテスト追加。
- 各 CLI（config_setup, validate_config, run_execution, run_monitoring, paper_verification_report）に対する統合テストの整備。
- ロギング周りのファイルパーミッションやログローテーション動作の実運用確認。
- position_sizing の lot_size を銘柄別に拡張する（TODO コメントあり）。
- Paper Trading レポートの閾値や判定ロジックを運用実績に合わせて調整。

--- 
（この CHANGELOG は、提供されたソースコードの内容から機能・設計意図を推測して作成しています。実際のコミット履歴や開発ノートがある場合はそれらに基づいて補完・修正してください。）