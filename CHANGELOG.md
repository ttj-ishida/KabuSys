Keep a Changelog 準拠の形式で、提示されたコード内容から推測して生成した CHANGELOG.md を以下に示します。初回リリース相当（バージョン 0.1.0）として記載しています。日付は現時点の想定日付を使用していますが、必要に応じて変更してください。

Keep a Changelog
=================

すべての変更はセマンティックバージョニングに従って記載します。  
このファイルはコードベース（src/kabusys 以下）の内容から推測して作成しています。

Unreleased
----------

- （現時点では未リリースの変更はありません）

[0.1.0] - 2026-04-24
-------------------

Added
- 初期リリース: KabuSys 自動売買フレームワークのコアモジュールを追加
  - src/kabusys/__init__.py にバージョン 0.1.0 を定義
- 実行・監視用エントリポイント
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading SQLite（data/paper_trading.db）を使用して本番 DB と分離
    - BrokerClientFactory を経由したブローカークライアント生成、OrderManager / OrderRepository / RiskManager / Reconciler の組み立て、ExecutionEngine のバックグラウンド実行を実装
    - 停止用フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）を利用した起動・停止制御
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
    - 監視は環境に関係なく本番用 sqlite_path を使用する挙動を採用
    - stop flag 検知、例外発生時のログ出力とループ継続処理を実装
- 環境設定ユーティリティ / 検証 CLI / ウィザード
  - config.py: .env 自動読み込み機能、.env/.env.local の取り扱い、プロジェクトルート自動検出、環境変数の取得ラッパー（Settings クラス）を追加
    - .env の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能
    - _parse_env_line により export プレフィックスやクォート、インラインコメント等を考慮した .env パースを実装
    - Settings に多数のプロパティ追加（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, pid/kill flag 関連, 各種閾値, env/log_level 判定等）
    - PAPER_FILL_MODE の有効値チェック（instant/partial/never/reject）や KABUSYS_ENV / LOG_LEVEL のバリデーションを実装
  - config_setup.py: 対話式 .env 作成・更新ウィザードを追加
    - シークレット項目のマスク表示、選択肢・デフォルトの提示、キャンセル中断時の挙動、.env 書き出しテンプレートを提供
  - validate_config.py: 起動前の設定検証 CLI を追加
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パス親ディレクトリチェック、config/*.yaml の存在と（PyYAML があれば）パース検証を実施
    - --strict オプションで警告を失敗扱いにできる
- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加
    - stdout への StreamHandler（stdout を使用）と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log、30日保持）をルートロガーに設定
    - LOG_LEVEL, LOG_DIR, 引数によるオーバーライド対応。ログディレクトリ作成失敗時のフォールバック（コンソールのみ）
  - utils/process_priority.py: プラットフォーム差分を吸収するプロセス優先度設定と CPU affinity ユーティリティを追加
    - Windows / POSIX の差を吸収して set_process_priority(level) を提供（"high"/"normal"/"low"）
    - set_cpu_affinity(cpu_count) によるコア制限機能
    - psutil 権限エラーや未対応 OS の場合に警告を出して安全にスキップ
- ポートフォリオ構築ライブラリ（純関数群）
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等重み（calc_equal_weights）、スコア加重（calc_score_weights）を実装
  - portfolio/risk_adjustment.py: セクター集中制限の適用（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）を実装
  - portfolio/position_sizing.py: 発注株数算出ロジック（calc_position_sizes）を実装
    - allocation_method に応じた計算（risk_based / equal / score）
    - lot_size（単元）丸め、per-position 上限、aggregate cap によるスケールダウン、cost_buffer（手数料/スリッページ見積り）対応
    - 利用可能現金を超える場合のスケールダウンと残差に基づく追加配分ロジックを備える
  - portfolio/__init__.py で上記 API を公開
- 解析 / レポートツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標を集計して PASS/FAIL を判定
    - デフォルト DB パスは data/paper_trading.db、--from/--to/--db オプション対応
    - P95 算出、期間フィルタの組み立て、DB 存在チェック、欠損テーブルへの耐性を実装
- リサーチ / ファクター計算（草案）
  - research/factor_research.py: DuckDB を使ったモメンタム等のファクター計算モジュールを追加（設計方針、定数、関数雛形を実装）
    - prices_daily / raw_financials テーブル参照での計算を想定（完全化は継続作業）

Changed
- なし（初期リリース）

Fixed
- .env パース/読み込みに関する堅牢化
  - export プレフィックスのサポート、クォート内バックスラッシュエスケープ処理、インラインコメントの取り扱い、既存 OS 環境変数を保護する protected パラメータ導入
- ログ設定の堅牢化
  - ログディレクトリ作成失敗時のフォールバック（コンソールのみ）とハンドラ二重登録防止（既存ハンドラの flush/close→削除）
- 実行中の安定化ガード
  - run_monitoring のポーリングループで check_once() の例外を捕捉してログ出力しループ継続するようにした（監視の継続性確保）
  - run_execution/run_monitoring 起動時にプロセス優先度を最初に設定することで起動直後の重要処理を優先

Security
- 機密情報取り扱いについての注意
  - config_setup が生成する .env のヘッダに「.env は絶対に Git にコミットしないこと」を明記
  - config.py の _require() は未設定時に ValueError を投げ、起動前に必須トークンの不在を明示

Notes / その他
- Settings や validate_config による環境変数検証を導入したため、起動前に python -m kabusys.validate_config での確認を推奨
- run_execution は paper_trading と live を明確に分離（paper 用 DB を別に使用）して誤発注リスクを軽減
- 一部モジュール（research/factor_research.py）の実装は途中（ファイル末尾が断片的）であり、追加実装やユニットテスト整備が必要な箇所がある可能性あり

Authors
- コード内容からの推測に基づき本 CHANGELOG を作成

----------

補足: 本 CHANGELOG は提示されたコードスナップショットの内容から推測して起こした変更点一覧です。実際のコミット履歴やリリースノートと差異がある場合は、該当する Git コミットメッセージや開発履歴に基づいて調整してください。