# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。  
リリース日付はコードベースから推測して付与しています。

なお本ファイルはコードの内容（ソースコメント・実装）から機能・動作を推測して作成しています。

## [Unreleased]

- なし（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-21

### Added

- 基本的なアプリケーションフレームワークを追加
  - パッケージメタ情報: kabusys (バージョン 0.1.0)
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加
    - KABUSYS_ENV=paper_trading 時は paper 用の SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離して動作
    - エンジンはスレッドで実行され、 data/stop_requested.flag による外部停止をサポート
    - PID ファイル（data/execution.pid）をサポート
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）
    - 監視側は KABUSYS_ENV に関わらず本番 sqlite_path を使用する（監視データは一元管理）
    - 外部停止は data/stop_requested.flag により検知
- 設定管理とユーティリティ
  - config.py: 環境変数 / .env 自動読み込み機能を追加
    - プロジェクトルート（.git または pyproject.toml を基準）を自動検出して .env を読み込む
    - .env と .env.local の読み込み順序・上書きルールを実装（OS 環境変数を保護）
    - クォートやエスケープ、コメントを考慮した .env パーサを実装
    - 各種設定プロパティ（DB パス、PID/キルフラグ、しきい値、環境判定フラグ等）を提供
  - config_setup.py: 対話式 .env 作成ウィザードを追加
    - 必須/任意項目、シークレット入力、デフォルト値、保存確認を実装
  - validate_config.py: 起動前の設定検証 CLI を追加
    - 必須環境変数のチェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認
    - config/*.yaml の存在確認と PyYAML によるパースチェック（PyYAML 未インストール時は警告）
    - --strict モードで警告を FAIL 扱いにできる
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加
    - stdout への StreamHandler と、日次ローテート（30 日保持）のファイルハンドラをルートロガーに設定
    - LOG_DIR/LOG_LEVEL による上書き、ディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続
  - utils/process_priority.py: プロセス優先度（および CPU affinity）設定ユーティリティを追加
    - Windows / POSIX を吸収する実装（psutil ベース）、設定できない場合は警告でスキップ
    - set_process_priority("high" | "normal" | "low")、set_cpu_affinity(n) を提供
- ポートフォリオ構築ライブラリ（純粋関数群、DB 非依存）
  - portfolio/portfolio_builder.py
    - select_candidates: スコアに基づく候補選出
    - calc_equal_weights / calc_score_weights: 重み計算（スコアが全て 0 の場合は等金額にフォールバック）
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（売却予定銘柄はエクスポージャー計算から除外）
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた株数算出
    - 単元株（lot_size）丸め、1 銘柄上限・全体投下上限、コストバッファを考慮した aggregate スケーリング実装
- 分析・検証ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL を判定するレポートを出力
    - デフォルト DB パスは PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db
    - P95 計算、各種閾値（稼働率 99%、注文成功率 90% など）を定義
- リサーチ基盤（初期実装）
  - research/factor_research.py: DuckDB を使ったファクター計算のスケルトンを追加
    - Momentum / MA200 / ATR / Liquidity 等を想定した定数と関数スケルトン（prices_daily / raw_financials を参照）

### Changed

- なし（初回リリースのため変更履歴無し）

### Fixed

- なし（初回リリース）

### Deprecated

- なし

### Removed

- なし

### Security

- なし

## 既知の注意点・設計意図（コードから推測したもの）

- run_monitoring は「監視データは本番 DB に記録する」という設計意図に基づき、KABUSYS_ENV の値に関係なく Settings.sqlite_path（本番用パス）を使って接続します。運用時は意図的に分離する必要がある場合は注意してください。
- run_execution は paper_trading 環境時に paper 用 SQLite を使用して本番 DB と明確に分離します。
- .env 自動読み込みはプロジェクトルートが検出できない場合はスキップされます。テスト環境等で自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- process_priority / cpu_affinity の設定は権限やプラットフォームに依存するため、失敗した場合は警告を出してスキップします（安全側で設計）。
- logging_setup はログディレクトリの作成に失敗した場合にファイル出力を無効化して標準出力のみで動作します。cron 等で起動する運用を想定して stdout を使う点に留意してください。
- ポートフォリオ関連関数は純粋関数（メモリ内計算）として設計され、本番 API へのアクセスや DB 参照を行いません。単体テストが容易な構造になっています。
- paper_verification_report はデータ欠損やテーブル未存在時に例外を吸収して N/A 表示や FAIL 判定の原因表記を行う設計です。

---

この CHANGELOG はソースコードのコメント・実装から推測して作成しています。実際のリリースノートはリリース時のコミット履歴や変更要求に基づいて更新してください。