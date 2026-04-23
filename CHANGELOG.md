# Changelog

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」準拠です。

全般的なルール:
- 破壊的な変更は明確に記載します。
- 各項目は可能な限りどのモジュール/スクリプトに関係するかを明示します。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-23

初回公開リリース。日本株自動売買システム「KabuSys」のコアユーティリティ群と起動スクリプト、ポートフォリオ構築ロジック、各種ツールを含みます。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義（src/kabusys/__init__.py）。
- 起動スクリプト
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
    - 環境変数 KABUSYS_ENV に応じて本番 DB / ペーパートレード用 DB を切り替え（paper_trading 時は専用 DB に完全分離）。
    - BrokerClientFactory を利用したブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler を組み立てて ExecutionEngine を起動。
    - ストップフラグ（data/stop_requested.flag）検知による安全停止、実行 PID ファイル（data/execution.pid）サポート。
    - スレッドを用いたエンジン実行と 1 秒間隔での停止フラグ監視。
  - SystemMonitor 起動スクリプト（src/kabusys/run_monitoring.py）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を調整可能（デフォルト 60 秒）。不正な値は警告の上デフォルトにフォールバック。
    - 監視は環境にかかわらず本番の sqlite_path を使用して動作（監視データは環境で分離しない設計）。
    - 停止フラグ検出による監視ループの終了処理を実装。
- 設定管理
  - Settings クラス（src/kabusys/config.py）
    - .env の自動ロード（プロジェクトルート検出）・OS 環境変数保護（上書き制御）を実装。
    - 各種設定プロパティ（DB パス、API トークン、PID/kill flag パス、閾値など）を提供。
    - PAPER_FILL_MODE の検証、KABUSYS_ENV / LOG_LEVEL の妥当性チェックを実装。
  - 対話式 .env 作成ウィザード（src/kabusys/config_setup.py）
    - .env の初期作成・更新を補助する CLI（入力中断時の安全動作、秘密項目のマスク表示、確認後ファイル書き込み）。
- 設定検証ツール
  - validate_config CLI（src/kabusys/validate_config.py）
    - 必須環境変数・KABUSYS_ENV・LOG_LEVEL・DB パス・config/*.yaml の存在と YAML パース（PyYAML があれば）を検証。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定や kill flag の自動クリア設定への警告）。
    - --strict オプションで警告を FAIL 扱いにする機能。
- ロギング/プロセス管理ユーティリティ
  - 統一的ログセットアップ（src/kabusys/utils/logging_setup.py）
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を組み合わせた設定。
    - ログディレクトリ作成失敗時のフォールバック（コンソール出力のみ）。
    - デフォルトログディレクトリ `logs/`、日次ローテーションで30日保持。
  - プロセス優先度・CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）
    - Windows/Linux/macOS を吸収した set_process_priority と set_cpu_affinity を提供。
    - 権限不足や未対応 OS に対する安全なフォールバックとログ警告。
- ポートフォリオ構築ライブラリ（純粋関数群、DB非依存）
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates（スコア降順、同点タイブレーク）
    - calc_equal_weights / calc_score_weights（スコア全0フォールバックで等配分）
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（既存保有比率に基づく候補排除。unknown セクターは制限対象外）
    - calc_regime_multiplier（"bull"/"neutral"/"bear" に基づく乗数、未知のレジームはフォールバック）
  - 株数計算・リスク/丸めロジック（src/kabusys/portfolio/position_sizing.py）
    - risk_based / equal / score の割当方式に対応
    - 単元(lot_size)丸め、1銘柄上限・総投下上限（aggregate cap）に応じたスケーリングアルゴリズム
    - cost_buffer を用いた保守的コスト見積り、端数処理での再配分ロジックを実装
- 研究/分析用モジュール
  - factor_research（src/kabusys/research/factor_research.py）
    - DuckDB 接続を受けてモメンタム・MA200乖離等のファクターを計算する設計（prices_daily/raw_financials を参照）。（注：ファイル末尾に計算ロジックの続きあり）
- ペーパートレード検証ツール
  - paper_verification_report（src/kabusys/tools/paper_verification_report.py）
    - ペーパートレード用 SQLite（デフォルト data/paper_trading.db）から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計し、PASS/FAIL 基準で検証レポートを出力。
    - P95 計算ユーティリティ、日付フィルタ、SQL の存在しないテーブルに対する安全なフォールバックを提供。
- その他ユーティリティ
  - tools パッケージ初期化ファイル（src/kabusys/tools/__init__.py）
  - utils パッケージ初期化ファイル（src/kabusys/utils/__init__.py）

### Changed
- （初回リリースのため該当なし）

### Fixed
- .env パーサーの堅牢化（src/kabusys/config.py）
  - export プレフィックス対応、シングル/ダブルクォート内でのバックスラッシュエスケープ処理、インラインコメント処理等を実装して .env の多様な記法に対応。
  - .env 自動ロードでは OS 環境変数を保護しつつ .env.local を override で読み込む処理を実装。
- DB 初期化の冪等化
  - init_monitoring_db を使用して監視テーブルの存在を保証（監視・実行の両スクリプトで使用、存在確認は冪等）。

### Security
- .env ファイルについての注意書き
  - config_setup で生成される .env のヘッダに「.env は絶対に Git にコミットしないこと」と明記。

### Notes / Known limitations
- run_monitoring は監視用に常に本番 sqlite_path を使用する設計（環境に依らず）。運用上の意図的な設計のため、開発環境で別 DB を使いたい場合は設定やスクリプトを調整してください。
- factor_research のファイルは設計・一部実装が含まれていますが、利用には DuckDB のテーブル（prices_daily, raw_financials 等）が必要です。
- process_priority の設定は権限不足で失敗する場合があり、その場合は警告を出してスキップします。
- position_sizing の lot_size は現状全銘柄共通。将来的に銘柄別単元対応が想定されています（TODO コメントあり）。

---

（この CHANGELOG はリポジトリの現状のコードから推測して作成しています。詳細な変更履歴や過去のコミットメッセージが存在する場合は、それらに基づいてより正確な履歴を記載してください。）