# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
日付はリリース日または変更時点を表します。

## [Unreleased]

（現在なし）

## [0.1.0] - 2026-04-17

Added
- 起動スクリプトを追加/整備
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ（data/stop_requested.flag）検知によるグレースフル終了に対応。
    - Monitoring は実行環境に関わらず本番用 sqlite_path を使用する旨を明記。
    - 起動時にプロセス優先度を high に設定。
  - src/kabusys/run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の MockBrokerClient を使用し、data/paper_trading.db（または PAPER_TRADING_SQLITE_PATH）に完全分離して記録。
    - 停止フラグ（data/stop_requested.flag）検知でエンジンを停止／起動中止。
    - ExecutionEngine を別スレッドで動作させ、PID ファイル管理・最大待機タイムアウトを考慮した停止処理を実装。
    - 起動時にプロセス優先度を high に設定。
- 設定管理・支援
  - src/kabusys/config.py
    - .env 自動読み込み機構を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - .env/.env.local の読み込み順序と OS 環境変数保護（protected keys）の仕組みを導入。
    - .env の行パーサを強化: export プレフィックス対応、クォートされた値のエスケープ処理、インラインコメントの取り扱い。
    - Settings クラスを実装し、各種設定値（DB パス、各 API トークン、監視閾値、環境判定フラグ等）をプロパティ経由で取得可能に。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）や paper_sqlite_path のプロパティを追加。
  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を追加。
    - 秘匿項目はマスク表示、既存 .env の読み込みと Enter による既存値再利用に対応。
    - 生成される .env テンプレートのフォーマットを定義。
  - src/kabusys/validate_config.py
    - 起動前に .env と config/*.yaml の健全性を検証する CLI を追加。
    - 必須環境変数のチェック、KABUSYS_ENV/LOG_LEVEL の妥当性検証、DB パスの親ディレクトリ存在確認、YAML の parse チェック（PyYAML が存在する場合）を実装。
    - --strict オプションで警告を FAIL 扱いにできる機能を追加。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定・KILL_FLAG_CLEAR_ON_START）を実装。
- ユーティリティ
  - src/kabusys/utils/process_priority.py
    - プロセス優先度（high/normal/low）をプラットフォーム差を吸収して設定する set_process_priority を実装（Windows の優先度クラス／POSIX の nice 値を扱う）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を追加。
    - 権限不足や未対応プラットフォーム時は警告を出してフォールバックする安全処理を実装。
- ポートフォリオ構築ロジック（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア全0時のフォールバック挙動を定義。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装。既存保有を基にセクター別エクスポージャーを計算し、上限超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear とフォールバック）。未知レジーム時はログ警告と 1.0 フォールバック。
  - src/kabusys/portfolio/position_sizing.py
    - allocation_method（risk_based / equal / score）に基づいて銘柄ごとの発注株数を計算する calc_position_sizes を実装。
    - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、総投下上限（available_cash/max_utilization）、コストバッファの考慮、スケールダウン時の残差配分ロジックを実装。
    - 価格欠損時のスキップや詳細なログを追加。
- リサーチ（ファクター計算）
  - src/kabusys/research/factor_research.py
    - DuckDB を利用した定量ファクター計算モジュールを追加。
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離（データ不足時は None）を実装。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率等を計算するクエリを実装（ウィンドウ集計を使用）。
    - DuckDB SQL を利用して効率的に集計する設計。
- ツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率・注文成功率・送信率・P95 レイテンシ等を算出し PASS/FAIL 判定を出力（デフォルトの閾値を定義）。
    - 日付フィルタ（--from / --to）、DB パス指定（--db / 環境変数）に対応。
    - P95 の算出、データなし耐性（テーブルがない場合は安全にハンドリング）を実装。

Changed
- パッケージメタ
  - src/kabusys/__init__.py にバージョン __version__ = "0.1.0" を設定。
- 設定の読み込みポリシー
  - .env 自動読み込みの優先順位を OS 環境変数 > .env.local > .env に明確化。
  - .env 読み込みで OS 環境変数は保護され、.env.local は上書き可能だが保護キーは変更されない。

Fixed
- 各種入力/パースの堅牢性向上
  - .env 行パースでクォート内エスケープや export プレフィックス、インラインコメント処理を適切に行うように改善。
  - process_priority の未対応プラットフォームや権限不足時の例外をキャッチして警告にフォールバックするよう修正。

Security
- .env 生成時に「.env は絶対に Git にコミットしないこと」を明示する注記を追加（config_setup が生成するテンプレートに記載）。

Notes / Implementation details
- Monitoring（run_monitoring.py）は運用上の安全策として、実行環境に関係なく本番向け sqlite_path を使用する設計になっています。運用時はデータパスの扱いに注意してください。
- run_execution.py は paper_trading モード時に本番 DB と完全分離することでテストと本番の衝突を避ける構成です（PAPER_TRADING_SQLITE_PATH を環境変数で上書き可能）。
- position_sizing のスケーリング/再配分アルゴリズムは、lot_size 単位での丸めと残差処理により再現性を保つ設計です。
- リサーチ系は DuckDB を前提としており、prices_daily / raw_financials のテーブル構造に依存します。

---

このリリースは初期の機能セット（起動スクリプト、設定管理、検証ツール、ポートフォリオ構築ロジック、運用モニタリング、Paper Trading 検証ツール、ユーティリティ）を含みます。今後はテストの追加、ドキュメント補強、各コンポーネント間の統合テストを進める予定です。