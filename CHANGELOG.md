# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の慣例に従って記載しています。

注意: この CHANGELOG は提供されたソースコードから実装内容を推測して作成したものです。実際のコミット履歴ではなく機能観点のまとめです。

## [0.1.0] - 2026-04-19
初回リリース。KabuSys 自動売買システムのコア機能群を実装しました。

### Added
- 実行用エントリスクリプト
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。プロセス優先度を高く設定して実行。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用 SQLite（data/paper_trading.db）を使用し、本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のスレッド実行と停止フラグ監視を実装。
    - 起動時に停止フラグファイル（data/stop_requested.flag）を検出した場合は起動を中止。
- 監視用エントリスクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 常に本番用 sqlite_path を参照して監視テーブル初期化を行う。
    - 停止フラグファイルを検知してループを抜ける仕組みを実装。
- 設定・環境管理
  - config.py
    - Settings クラスを実装し、環境変数から各種設定（J-Quants / kabu API / DB パス / PID /閾値 / 実行環境 等）を取得するプロパティを提供。
    - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）。`.env` → `.env.local` の優先読み込みに対応。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化オプションあり。
    - PAPER_FILL_MODE 等の値検証、環境名（KABUSYS_ENV）・LOG_LEVEL の妥当性チェック、paper_trading の専用 sqlite パス等をサポート。
  - config_setup.py
    - 対話式 .env 作成ウィザードを実装。既存 .env の読み込み・編集、保存機能を提供。
  - validate_config.py
    - 起動前設定検証 CLI を実装。必須環境変数・KABUSYS_ENV・ログレベル・DB パス・config/*.yaml の存在と簡易パース検証、KABUSYS_ENV=live 時の追加注意喚起などを行う。`--strict` オプションで警告を失敗扱いに可能。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 一貫したログ設定ユーティリティを提供。Console(StreamHandler stdout) と TimedRotatingFileHandler（日次ローテーション）をルートロガーへ設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - プロセス優先度設定と CPU affinity 設定ユーティリティを実装（Windows/Linux/macOS を吸収）。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供し、アクセス権限不足等の例外は警告ログでスキップする実装。
- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py
    - 候補抽出（select_candidates）、等配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
  - portfolio/risk_adjustment.py
    - セクター上限適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
  - portfolio/position_sizing.py
    - position sizing ロジックを実装（allocation_method: "risk_based" / "equal" / "score" をサポート）。
    - 単元株（lot_size）での丸め、1銘柄上限、aggregate cap（利用現金に合わせたスケーリング）、手数料・スリッページ用 cost_buffer を考慮した保守的見積り、残差（fractional）処理による追加配分ロジックなどを提供。
  - portfolio/__init__.py で上記関数をまとめてエクスポート。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - paper_trading DB（デフォルト data/paper_trading.db）からシステム安定性、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）を集計して表示するレポートジェネレータを実装。
    - P95 計算ユーティリティ、各閾値（稼働率/成功率/送信率/P95 レイテンシ）を定義して PASS/FAIL 判定を行う CLI を提供。
- 研究用ファクター計算（骨組み）
  - research/factor_research.py
    - DuckDB 接続を受け prices_daily / raw_financials から各種ファクター（モメンタム、MA200乖離、ATR、流動性など）を計算する設計に基づくモジュールを追加（実装の冒頭〜一部関数が存在）。関数仕様・定数が定義済みで、DuckDB 経由での集計を想定。

### Changed
- ログ設定の改善
  - ログディレクトリ作成失敗時にプログラムが停止しないよう、ファイルハンドラ作成を保護してストリーム出力のみで継続する挙動に変更（logging_setup.py）。
- 環境変数ロードの堅牢化
  - .env パーサでクォート（シングル/ダブル）内のバックスラッシュエスケープに対応、`export KEY=val` 形式を扱えるようにした（config.py）。
  - .env の読み込み順と上書きルール（OS 環境変数保護）を明確化。

### Fixed
- 例外・障害回復の強化
  - run_monitoring のポーリング中に monitor.check_once() で例外が発生してもループを続行し、例外詳細をログに出すように変更。
  - process_priority / CPU affinity 設定でアクセス権限や未対応 OS の場合に例外で停止しないよう警告ログにフォールバックするよう対応。
  - logging_setup の既存ハンドラを安全にクローズしてから再設定するように修正（多重設定防止）。

### Documentation
- 各モジュールに docstring を充実させ、使い方・引数・戻り値・設計ノート（例: PortfolioConstruction.md への参照）を明記。
- config_setup と validate_config に CLI ヘルプと使用手順を追加。

### Known issues / Notes
- research/factor_research.py はモジュールの冒頭〜一部関数定義まで実装されていますが、ファイル末尾で途中（トランケーション）になっているため完全実装は未完です。今後のリリースで完成・テストを予定。
- portfolio.position_sizing の price 欠損時のフォールバック処理に TODO コメントあり（前日終値等のフォールバックを検討）。
- 実行・監視スクリプトはファイルベースの停止フラグ（data/stop_requested.flag）/PID ファイルに依存しているため、運用時のファイル管理ルールの周知が必要。

---

今後予定（推測）
- factor_research の完成、DuckDB を用いた各ファクター計算の実装完了。
- 単体テスト・統合テストの追加、CI 設定。
- ドキュメント（設計書 / 運用手順）の整備（PortfolioConstruction.md 等の参照先を正式化）。
- BrokerClient の Mock/実ブローカー差分の拡張とテストカバレッジ強化。