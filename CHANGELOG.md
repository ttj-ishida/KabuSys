# CHANGELOG

すべての注目すべき変更をこのファイルに記載します。  
フォーマットは "Keep a Changelog" に準拠しています。

全ての変更は重要度に基づいて分類しています。リリース日やバージョン番号はコードベース内の __version__（0.1.0）に基づいています。

## [0.1.0] - 2026-04-11

### 追加 (Added)
- 実行スクリプトを追加
  - run_execution.py
    - ExecutionEngine 起動用のエントリポイントを提供。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し、発注データを paper_trading 用の SQLite DB に分離して記録（デフォルト: data/paper_trading.db）。
    - プロセス優先度を起動直後に "high" に設定する仕組みを導入。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）による起動／停止制御。
  - run_monitoring.py
    - SystemMonitor（監視ループ）を起動するエントリポイントを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番の sqlite_path を使用して監視テーブルを保持。
- 設定管理とセットアップ
  - config.py
    - Settings クラスを追加し、環境変数から各種設定値を取得する共通インタフェースを提供。
    - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / PID_FILE_PATH などのプロパティを実装。
    - PAPER_FILL_MODE の検証（"instant"|"partial"|"never"|"reject"）を実装。
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェックを実装。
    - 自動 .env 読み込み: プロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を読み込む機能を追加。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - config_setup.py
    - 対話式ウィザードで .env を生成・更新する CLI を追加。項目の補助説明、シークレットマスク、既存値の読み込み／デフォルト適用をサポート。
- 設定検証ツール
  - validate_config.py
    - .env と config/*.yaml の整合性チェック CLI を追加。必須環境変数の未設定検出、KABUSYS_ENV/LOG_LEVEL の妥当性確認、DB パスの親ディレクトリ存在チェック、YAML のパース確認（PyYAML が存在する場合）を行う。
    - --strict オプションを追加（警告を FAIL として扱う）。
- ロギング／プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ初期化関数 setup_logging を提供。stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler）を設定。
    - LOG_DIR 指定やディレクトリ作成失敗時のフォールバック（コンソールのみ）に対応。
  - utils/process_priority.py
    - プラットフォーム差分を吸収してプロセス優先度を設定する set_process_priority を実装（Windows / POSIX 対応）。
    - CPU Affinity を設定する set_cpu_affinity を追加。
    - psutil を利用し、権限不足や未実装プラットフォームでは警告を出して安全にスキップする。
- ポートフォリオ構築ライブラリ (portfolio)
  - portfolio/portfolio_builder.py, risk_adjustment.py, position_sizing.py を追加
    - 候補選定（select_candidates）、等金額／スコア重み（calc_equal_weights / calc_score_weights）
    - セクター上限チェック（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）
    - 株数決定ロジック（calc_position_sizes）：risk_based / equal / score の配分方式、単元株丸め、aggregate cap のスケーリングなどを実装
- 研究・解析関連
  - research/factor_research.py（ファクター計算の骨組みを追加）
    - モメンタム／ボラティリティ等の計算を行う設計方針と定数を定義。DuckDB（prices_daily / raw_financials）を利用する設計。
- ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite DB を解析して検証レポートを生成する CLI を追加。
    - 稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）等を集計し PASS/FAIL を判定する。
    - デフォルト DB パスは data/paper_trading.db（PAPER_TRADING_SQLITE_PATH 環境変数で上書き可）。
- パッケージメタ情報
  - kabusys/__init__.py にバージョン __version__ = "0.1.0" を追加。

### 変更 (Changed)
- .env 読み込みの挙動改善（config.py）
  - .env のパースが強化され、export KEY=val 形式、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
  - .env の読み込み優先順位を OS 環境変数 > .env.local > .env とし、既存 OS 環境変数を保護（protected）する実装とした。
- ログ出力先を stdout に統一（utils/logging_setup.py）
  - StreamHandler は stderr ではなく stdout を使用する方針に変更（cron やスケジューラでのリダイレクトを考慮）。
- run_monitoring: MONITOR_POLL_INTERVAL の検証を追加
  - 環境変数に 0 以下や非整数が指定された場合は警告を出しデフォルト（60 秒）にフォールバック。
- run_execution: paper_trading 時の DB 分離
  - paper_trading モードでは paper_sqlite_path を使用することで本番 DB と完全に分離する仕様に変更。
- init_monitoring_db の呼び出しを全起動パスで実行
  - 監視用テーブルが存在することを冪等的に保証するため、Execution 起動時にも監視テーブルの初期化を行うようにした（テーブルが存在しないと監視やレポートが動作しないため）。

### 修正 (Fixed)
- 環境変数パースの不具合に対処（config.py）
  - クォート付き文字列中のエスケープやコメント処理、export プレフィックスに対する誤動作を修正。
- ログハンドラの二重設定を防止（utils/logging_setup.py）
  - 既存のハンドラを flush/close した上でクリアしてから新規ハンドラを追加するようにして、複数回起動時の重複ログ出力を回避。
- process_priority の例外処理強化
  - 権限不足や未サポートプラットフォームでの例外を捕捉し、警告を出して処理を続行するようにした。
- paper_verification_report の統計計算耐障害性向上
  - テーブルやカラムが存在しない場合に sqlite3.OperationalError を捕捉して、空データ扱いでレポートを生成するようにした。

### 破壊的変更 (Breaking Changes)
- 監視 DB の利用ポリシー
  - run_monitoring は KABUSYS_ENV にかかわらず Settings.sqlite_path（監視用 sqlite）を使用するように明記。運用設定により想定外の DB を参照しないよう注意が必要です。
- デフォルトの .env 自動読み込み
  - プロジェクトルートが特定できる環境では起動時に自動的に .env / .env.local を読み込む挙動が追加されました。テスト環境等でこれを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

### セキュリティ (Security)
- 環境変数に関する注意喚起
  - config_setup にて .env を生成する際、生成された .env を絶対に Git へコミットしない旨の注記を追加。
  - validate_config にて本番環境（KABUSYS_ENV=live）利用時に LINE トークン未設定や KILL_FLAG_CLEAR_ON_START の危険設定を警告するガードを追加。

---

注: 本 CHANGELOG はリポジトリ内のソースコードから推測してまとめたものです。実際のリリース履歴や日付は開発・運用チームの正式な情報に基づいて更新してください。