# Changelog

すべての注目すべき変更点をここに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

なお、本CHANGELOGはソースコードからの推測に基づいて作成しています（実際のコミット履歴ではありません）。

## [Unreleased]

## [0.1.0] - 2026-04-19

### Added
- 初回公開: KabuSys コードベースの主要コンポーネントを実装・追加。
  - コアパッケージ
    - kabusys パッケージ本体（__version__ = 0.1.0）。
  - 設定管理
    - Settings クラス（src/kabusys/config.py）
      - .env 自動読み込み（プロジェクトルートの検出: .git または pyproject.toml）。
      - 読み込み優先度: OS 環境変数 > .env.local > .env。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
      - 各種プロパティ（J-Quants、kabu API、DBパス、ログレベル、環境判定フラグ等）を提供。
      - PAPER_FILL_MODE の値検証（"instant" | "partial" | "never" | "reject"）。
      - paper_trading 用 DB パス（PAPER_TRADING_SQLITE_PATH）サポート。
    - .env パーサーの強化
      - export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
  - 起動スクリプト / CLI
    - run_monitoring（src/kabusys/run_monitoring.py）
      - SystemMonitor のポーリングループ起動スクリプト。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視は環境にかかわらず本番 sqlite_path を使用（監視 DB を分離しない設計）。
      - 停止フラグ（data/stop_requested.flag）検知による安全シャットダウン。
    - run_execution（src/kabusys/run_execution.py）
      - ExecutionEngine 起動スクリプト。
      - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB を使用して本番 DB と分離。
      - BrokerClientFactory を介したブローカークライアント生成。
      - ExecutionEngine を別スレッドで実行し、停止フラグで安全停止。
      - PID ファイル管理（data/execution.pid 等）。
    - config_setup（src/kabusys/config_setup.py）
      - 対話式ウィザードで .env の初期作成・更新を支援。
      - 入力補助、シークレットのマスク表示、保存確認付き。
    - validate_config（src/kabusys/validate_config.py）
      - .env と config/*.yaml の起動前チェック CLI。
      - --strict オプションで警告も FAIL 扱いにできる。
      - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パス・YAML ファイル存在チェック、live 環境向け追加ガードを実装。
    - tools.paper_verification_report（src/kabusys/tools/paper_verification_report.py）
      - ペーパートレード用の検証レポート生成スクリプト。
      - CLI オプション: --from, --to, --db（PAPER_TRADING_SQLITE_PATH 環境変数も使用可）。
      - 稼働率 / 注文成功率 / 送信率 / レイテンシ (avg/max/p95) 等を集計し PASS/FAIL 判定（閾値はソース内に定義）。
  - ポートフォリオ構築（純粋関数群）
    - portfolio_builder（選定・重み計算）
      - select_candidates（スコア降順選抜）
      - calc_equal_weights, calc_score_weights（重み計算。スコア全0時は等金額にフォールバック）
    - risk_adjustment（セクター上限・レジーム乗数）
      - apply_sector_cap：セクター集中制限ロジック（売却予定銘柄除外、"unknown" セクターは制限対象外）
      - calc_regime_multiplier：market regime に対する資金乗数（bull/neutral/bear）
    - position_sizing（株数決定・リスク制限）
      - calc_position_sizes：allocation_method に応じた株数算出（risk_based / equal / score）、lot_size に基づく丸め、aggregate cap のスケーリングと端数処理を実装。
      - cost_buffer による保守的見積り対応。
      - TODO: 将来的な銘柄別 lot_size 拡張の注記あり。
  - ユーティリティ
    - logging_setup（src/kabusys/utils/logging_setup.py）
      - stdout 出力用 StreamHandler と日次ローテーションの TimedRotatingFileHandler をルートロガーに設定。
      - ログディレクトリ自動作成（失敗時はファイル出力をスキップし stdout のみ）。
      - ログレベル解決（引数 > 環境変数 > デフォルト）。
    - process_priority（src/kabusys/utils/process_priority.py）
      - プロセス優先度（high/normal/low）と CPU affinity 設定ユーティリティ（Windows / POSIX を吸収）。
      - アクセス権限などで設定できない場合は警告を出してスキップ。
  - データベース接続
    - sqlite3 と DuckDB の組合せで、監視（SQLite）と分析（DuckDB）を分離する設計を採用。
  - 基本的なロギング・エラーハンドリングを各起動スクリプトに実装。

### Fixed
- 起動時の一部初期化上の安全策を追加。
  - init_monitoring_db の呼び出しにより監視テーブルの存在を保証（冪等）。
  - DB やファイルハンドルの確実なクローズ処理（finally ブロック）。
  - run_monitoring の MONITOR_POLL_INTERVAL が不正な値の場合はデフォルトにフォールバックし警告を出力。

### Changed
- （初回リリースのため該当なし）

### Breaking Changes
- Settings の env/log_level 等のプロパティは不正な値に対して ValueError を送出するため、以前のゆるい環境変数値に依存するコードからは例外処理が必要になります。
- .env 自動読み込みの挙動が導入されており、環境依存の設定が意図せず上書きされる可能性があるため、テスト等で自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

### Security
- 機密値（トークン・パスワード）は .env に保存する設計。config_setup は .env を生成するが、.env は絶対に Git にコミットしない旨をファイルヘッダに明記。

### Notes / Known issues
- research.factor_research モジュールは実装途中の記述（ファイル末尾で途中のコード断片あり）を含みます。完全なファクター計算ロジックは今後の実装が必要です。
- position_sizing における price が欠損（0.0）の場合の扱いに注意: 現状はスキップされるが、将来的には前日終値などのフォールバック価格を導入予定（TODO コメントあり）。
- run_monitoring は監視用 DB を環境にかかわらず sqlite_path（本番パス）で開く設計。必要に応じて監視専用 DB の分離を検討してください。
- ログディレクトリ作成やプロセス優先度設定は環境により失敗する可能性があり、その場合は警告を出して処理を継続する設計です。

---

以上。今後のリリースでは各機能の追加・テスト・ドキュメント整備・不具合修正を予定してください。