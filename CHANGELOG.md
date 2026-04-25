# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
本ファイルは「Keep a Changelog」形式に従っています。  

- フォーマット: https://keepachangelog.com/ja/1.0.0/
- バージョニング: SemVer 準拠（推定）

## [Unreleased]

### Added
- なし（現状のコードベースは初期リリース相当の実装を含むため、未リリース変更はありません）。

---

## [0.1.0] - 2026-04-25

初回リリース（推定）。以下はコードベースから推測した追加機能・実装内容の要約です。

### Added
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。  
    - KABUSYS_ENV による paper_trading モードの切替をサポート。paper_trading 時は専用の SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。  
    - プロセス優先度を起動時に "high" に設定。停止フラグ（data/stop_requested.flag）を検知して安全に停止。
    - 実行時の PID ファイル管理（data/execution.pid）をサポート。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。  
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化する。停止フラグでループ終了。

- 設定・環境管理
  - config.py: 環境変数・設定取得用の Settings クラスを導入。  
    - .env 自動ロード機能（プロジェクトルート検出による .env/.env.local 読み込み、OS 環境変数を保護）。  
    - 各種プロパティ（DB パス、KABUSYS_ENV、LOG_LEVEL、paper_trading 用設定、しきい値等）を提供。  
    - PAPER_FILL_MODE の妥当性チェックや KABUSYS_ENV のバリデーションを実装。
  - config_setup.py: 対話式の .env 作成・更新ウィザードを追加。  
    - 一連の設定項目を対話的に入力・保存する機能。既存 .env の読み込み/デフォルト利用、シークレット値のマスク表示、保存確認を実装。
  - validate_config.py: 起動前検証用 CLI を追加。  
    - 必須環境変数の存在確認、KABUSYS_ENV／LOG_LEVEL の妥当性チェック、DB パスや config/*.yaml の存在・パース検証（PyYAML 未インストール時は警告）を実施。  
    - --strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）と重み算出（等金額 calc_equal_weights、スコア加重 calc_score_weights）を実装。  
    - スコア 0 の場合は等配分へフォールバック（警告ログ）。
  - portfolio/risk_adjustment.py: セクター集中上限の適用（apply_sector_cap）、マーケットレジームに基づく投下資金乗数（calc_regime_multiplier）を実装。  
    - 未知レジームはフォールバック（1.0）し、警告ログを出力。
  - portfolio/position_sizing.py: 発注株数算定ロジック（risk_based / equal / score）を実装。  
    - 単元（lot_size）、手数料・スリッページのバッファ（cost_buffer）、ポジション上限（max_position_pct）、投下上限（max_utilization）を考慮したスケールダウン処理を実装。  
    - aggregate cap 超過時のスケール＆再配分アルゴリズムを導入（端数処理により lot_size 単位で調整）。

- 監視・モニタリング補助
  - monitoring.monitoring_db の初期化呼び出し（init_monitoring_db）を run_* スクリプトに統合して監視テーブルの存在を保証。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。  
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app>.log、30 日保持）を設定。既存ハンドラを一旦クリアしてから設定する。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: クロスプラットフォームでのプロセス優先度設定（Windows / POSIX）と CPU affinity 設定ユーティリティを追加。  
    - アクセス権限や未サポート環境では警告を出して安全にスキップ。

- Execution 系の骨組み
  - run_execution.py から利用するコンポーネント群（BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager 等）を統合するコードを配置（実行フローの組立て、スレッド起動、停止ハンドリング）。
  - RiskManager に対するデフォルト RiskConfig を run_execution.py 内で提供（max_position_pct=0.20 など）。初期ポートフォリオ値はブローカーの get_available_cash() を使用。

- ペーパートレード検証ツール
  - tools/paper_verification_report.py: ペーパートレード DB（SQLite）から検証レポートを生成する CLI を追加。  
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、API レイテンシ（avg/max/P95）などを算出。  
    - 基準値（しきい値）を定義して PASS/FAIL 判定を行う（デフォルト: 稼働率 >= 99%、fill >= 90% 等）。  
    - 日付フィルタ（--from / --to）および DB パス指定（--db / 環境変数）をサポート。DB 欠如やテーブル欠如時のフォールバック処理を実装。

- リサーチ（ファクター）モジュール（骨組み）
  - research/factor_research.py: DuckDB 接続を受け取りファクター（Momentum、Value、Volatility、Liquidity 等）を計算するための骨組みを追加。  
    - モメンタム計算関数 calc_momentum の導入（コードは途中まで実装・設計方針記載）。DuckDB の prices_daily / raw_financials テーブルを参照する設計。

- パッケージ情報
  - kabusys/__init__.py に初期バージョンを追加（__version__ = "0.1.0"）。

### Changed
- （初版のため該当なし。実装は新規追加が中心）

### Fixed
- （初版のため該当なし）

### Security
- 環境設定ウィザード・.env 書き込み時に注意喚起を出す（.env を絶対にコミットしない旨のコメントを .env ヘッダに追加）。

### Notes / Implementation details（ドキュメント的追記）
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml を探索）に依存しており、見つからない場合は自動ロードをスキップする。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
- .env パーサは引用符付き値のエスケープ処理やインラインコメント処理を考慮した堅牢な実装が施されている。
- run_monitoring は明示的に本番 sqlite_path を使用して監視データを一元管理する設計（環境に依存しない監視 DB の確保）。
- process_priority の実行は可能であっても権限不足などにより失敗する可能性があるため、失敗時は警告でスキップする安全策が組み込まれている。
- position_sizing の aggregate cap 処理は lot_size 単位での丸めと、残差に基づく追加配分ロジックを実装しており、投資合計が利用可能現金を超えた場合にスケールダウンする。

---

今後の改善案（推奨）
- research/factor_research.py の未完実装部分（モメンタム等の完全実装）を完了し、ユニットテストを追加。
- ExecutionEngine / BrokerClient のインターフェースに対する単体テストの拡充（paper_trading の挙動確認含む）。
- logging_setup のファイルハンドラ作成失敗時の通知をメール/通知に統合する検討。
- portfolio モジュールに対する包括的なテストケース（edge case、価格欠損時のフォールバック等）。

(注) 上記はコード内容から推測して作成しています。実際のリリース日やリリースノートはプロジェクトの公式記録に従ってください。