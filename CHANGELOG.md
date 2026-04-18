CHANGELOG
=========

すべての重大な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

Unreleased
----------

- 開発中の変更はここに記載します。

[0.1.0] - 2026-04-18
--------------------

Added
- 初回リリース。システム全体の主要コンポーネントを追加。
  - 実行エントリ
    - ExecutionEngine 起動スクリプトを追加（run_execution.py）。
      - KABUSYS_ENV=paper_trading の場合はペーパートレード用 DB / MockBroker を利用して本番 DB と分離（settings.is_paper / PAPER_TRADING_SQLITE_PATH）（src/kabusys/run_execution.py）。
      - エンジンはスレッドでデーモン実行され、data/stop_requested.flag による安全な停止処理を実装。
      - 実行中の PID を data/execution.pid に記録する設定をサポート（pid_file）。
      - RiskManager の既定設定（max_position_pct / max_utilization / rate_limit_per_sec 等）を追加。
    - SystemMonitor 起動スクリプトを追加（run_monitoring.py）。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視は環境にかかわらず本番用 sqlite_path を使用する設計（src/kabusys/run_monitoring.py）。
      - 停止フラグ（data/stop_requested.flag）の検出と例外ハンドリングを実装。
  - 設定管理
    - Settings クラスによる環境変数ラッパーを追加（src/kabusys/config.py）。
      - .env 自動ロード（プロジェクトルート自動検出: .git または pyproject.toml）を実装。
      - PAPER_FILL_MODE のバリデーション、PAPER_TRADING_SQLITE_PATH、DUCKDB_PATH など主要設定を提供。
      - KABUSYS_ENV / LOG_LEVEL の許容値チェック・ユーティリティを実装。
    - 対話式環境設定ウィザードを追加（config_setup.py）。
      - .env の初期作成・更新を対話形式で支援。シークレットはマスク表示、保存ファイルのテンプレート出力。
    - 設定検証 CLI を追加（validate_config.py）。
      - 必須環境変数・パスの存在チェック、config/*.yaml の存在と（PyYAML インストール時は内容）検証、KABUSYS_ENV=live 時の追加ガードを実装。
      - --strict オプションで警告を FAIL 扱いにできる。
  - ポートフォリオ構築（純関数群）
    - 候補選定・重み計算（portfolio_builder.py）
      - select_candidates（スコア降順、タイブレークロジック）
      - calc_equal_weights, calc_score_weights（スコア全0 の場合のフォールバックに WARNING ログ）
    - セクター制約・レジーム乗数（risk_adjustment.py）
      - apply_sector_cap（既存保有のセクターエクスポージャに基づく候補除外）
      - calc_regime_multiplier（bull/neutral/bear による乗数、未知レジームはフォールバックと警告）
    - 株数算出（position_sizing.py）
      - allocation_method= "risk_based" / "equal" / "score" をサポート
      - 単元株（lot_size）丸め、max_per_stock・aggregate cap のスケーリング、cost_buffer を考慮した安全な再配分アルゴリズムを実装
  - リサーチ / ファクター計算
    - factor_research.py を追加。DuckDB の prices_daily / raw_financials を用いてモメンタム・ボラティリティ等を計算するユーティリティを実装（P95・MA200・ATR など）。
  - ツール
    - Paper Trading 検証レポート生成スクリプトを追加（tools/paper_verification_report.py）。
      - 稼働率・注文成功率・送信率・レイテンシ（P95）などを算出し PASS/FAIL 判定を行う。期間指定オプション（--from / --to）と DB パス指定（--db）をサポート。
  - ユーティリティ
    - プロセス優先度・CPU affinity 設定ユーティリティを追加（utils/process_priority.py）。
      - Windows / POSIX（Linux / macOS / FreeBSD）差分を吸収。psutil を使って優先度・CPU 固定を設定。権限不足や未対応 OS では安全にスキップして警告を出力。

Changed
- データベース接続周りを整備
  - 起動スクリプトで sqlite3 / duckdb の接続を確実に close するよう finally ブロックを追加（run_execution.py, run_monitoring.py）。
  - monitoring 用 DB 初期化を冪等に行う init_monitoring_db の呼び出しを追加。
- ロギング
  - 起動時に INFO レベルで basicConfig を設定し、各所で適切な情報ログ・警告・例外ロギングを追加。
- .env パースの堅牢化
  - config モジュールの .env パーサーで export プレフィックス、クォート値、エスケープ、インラインコメント処理をサポートし、不正行を無視するよう改善。

Fixed
- ポートフォリオ算出でのエッジケース修正
  - calc_score_weights: 全銘柄のスコア合計が 0 の場合に 0 除算を回避して等金額配分にフォールバック。
  - position_sizing: price が欠損または 0 の場合のスキップ処理を強化し、負の値や不正入力に対する保護を追加。
- プロセス優先度設定での例外処理強化
  - psutil の未実装属性やアクセス拒否を適切に捕捉して WARNING を出し処理を継続するようにした。

Security
- .env を生成する際に「絶対に Git にコミットしないこと」を明記（config_setup.py）。シークレットは表示時にマスクして扱う。

Breaking Changes
- なし（初回リリース）

Notes / Known Issues
- 一部算出ロジックは将来的に拡張予定（例: position_sizing の銘柄別 lot_size サポート、price のフォールバック取得等）。
- config/*.yaml の内容検証は PyYAML が未インストールだとスキップされ、警告が出ます（validate_config.py）。
- apply_sector_cap は "unknown" セクターを上限適用対象外とする設計。必要に応じて運用ルールを見直してください。

Authors
- KabuSys 開発チーム（実装は各モジュールの docstring / コメントに準拠）

----------------------------------------------------------------
この CHANGELOG はコードベース（src/ 以下）から導出した変更点を要約しています。実際のコミット履歴ではなく、現状の機能追加・仕様を記述しています。