# CHANGELOG

すべての注記は Keep a Changelog の慣例に準拠します。日付はリリース日です。

## [Unreleased]
- 次回リリース用の変更点はありません（現時点のコードベースを 0.1.0 として初回公開）。

## [0.1.0] - 2026-04-19

### Added
- 基本アプリケーション構成を実装（初回リリース）。
  - パッケージ情報
    - kabusys.__version = "0.1.0"
  - 設定管理
    - 環境変数 / .env 自動ロード機構を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env ファイルのパース機能を独自実装（シングル/ダブルクォート、エスケープ、インラインコメント等に対応）。
    - 環境変数取得ユーティリティ（必須チェック _require、Settings クラス）を提供。
    - 設定項目（J-Quants、kabu API、LINE、DB パス、監視閾値等）をまとめた Settings クラスを追加。
    - 環境自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD に対応。

  - 起動 / 制御スクリプト
    - 実行エンジン起動スクリプト run_execution.py を実装。
      - KABUSYS_ENV に応じて paper_trading 用の専用 SQLite を利用（settings.paper_sqlite_path）。
      - BrokerClientFactory によるブローカークライアント生成（paper_trading 時は Mock を想定）。
      - ExecutionEngine の起動/停止ロジック（PID ファイル、stop flag による外部停止）。
      - RiskManager / OrderManager / Reconciler の組み立てと初期設定（RiskConfig のデフォルト値を明示）。
    - 監視ループ起動スクリプト run_monitoring.py を実装。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視は環境に関わらず本番用 sqlite_path を使用する旨の仕様。
      - 停止フラグ（data/stop_requested.flag）検知による安全終了処理を実装。
    - 複数スクリプトで共通してプロセス優先度を High にする呼び出しを導入（set_process_priority）。

  - ユーティリティ
    - ロギング設定ユーティリティ utils.logging_setup.setup_logging を実装。
      - stdout StreamHandler と 日次ローテートされる TimedRotatingFileHandler（デフォルト logs/、30日保持）をルートロガーにセットアップ。
      - LOG_LEVEL / LOG_DIR の解決順をサポートし、ディレクトリ作成失敗時はファイル出力をスキップしてフォールバック。
    - プロセス優先度・CPU affinity 設定ユーティリティ utils.process_priority を実装。
      - Windows / POSIX を吸収する実装。set_process_priority(level) / set_cpu_affinity(cpu_count) を提供。
      - 権限不足などで設定できない場合は警告を出して安全にスキップ。

  - 設定操作用 CLI
    - config_setup.py: 対話式 .env 作成ウィザードを実装。
      - J-Quants、kabu API、DB パス、ログレベル、Kill Switch 設定などの項目を網羅。
      - 既存 .env 読み込み、シークレットのマスク表示、保存前確認を提供。
    - validate_config.py: 起動前設定検証 CLI を実装。
      - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在および PyYAML があればパース検証、KABUSYS_ENV=live 時の追加ガード。
      - --strict オプションで警告も失敗扱いにできる。

  - ポートフォリオ構築ライブラリ
    - portfolio.portfolio_builder: 候補選定と配分重み計算（select_candidates, calc_equal_weights, calc_score_weights）。
    - portfolio.risk_adjustment: セクター集中制限の適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。
      - unknown セクターはセクター上限の適用対象外とする挙動を明記。
      - 未知のレジームは 1.0 でフォールバックし警告を出す。
    - portfolio.position_sizing: 株数決定ロジック（calc_position_sizes）。
      - allocation_method として "risk_based" / "equal" / "score" に対応。
      - lot_size（単元株）対応、max_position_pct、max_utilization、cost_buffer による保守的なコスト見積り、aggregate cap に基づくスケーリングと端数処理（lot 単位での再配分）を実装。

  - 分析 / 検証ツール
    - tools.paper_verification_report: Paper Trading 用検証レポート生成スクリプトを実装。
      - PAPER_TRADING_SQLITE_PATH 環境変数または --db で DB 指定可能。
      - システム安定性（稼働率）、注文成功率・送信率、リスク却下数、レイテンシ（平均・最大・P95）を集計して PASS/FAIL 判定（デフォルト閾値をコード内に定義）を出力。
      - P95 計算、日付フィルタリング、データ欠損時の graceful handling を実装。

  - research/factor_research（骨格）
    - DuckDB を用いたファクター計算モジュールの骨格を追加（モメンタム等の仕様コメント、定数定義）。一部実装が未完（ファイル末尾で切れている）。

  - データベース周り
    - sqlite3 および duckdb 接続を利用する一貫した設計（monitoring DB と分析用 DuckDB の併用）。
    - 監視テーブルの初期化用 init_monitoring_db の呼び出しを各起動スクリプトで実施（冪等に保証）。

### Changed
- N/A（初回リリースのため既存機能変更はなし）。

### Fixed
- N/A

### Removed
- N/A

### Security
- N/A

---

注記・設計上の重要事項（ドキュメント的補足）
- paper_trading モードではデータベースが本番と分離される（settings.paper_sqlite_path が既定: data/paper_trading.db）。これによりペーパートレードの記録と本番監視データが混在しない設計。
- run_monitoring はモニタリング用の sqlite を環境に関係なく使用する仕様（監視は常に本番 DB に記録するという想定）。
- process_priority の設定は権限や OS に依存するため、失敗時は警告を出して処理を継続する設計。cron 等での運用を想定して stdout にログを出す構成になっている。
- .env ファイルはセキュリティ上 Git にコミットしない旨を config_setup の出力に明記している。

もし特定の変更点やリリースノートを詳細化（例えば各モジュール別の API 履歴や既知の TODO/制限事項の追加）したい場合は、その旨を指示してください。