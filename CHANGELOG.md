CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマットは「Keep a Changelog」に準拠します。  

0.1.0 — 2026-04-24
------------------

Added
- 初期リリース: KabuSys 自動売買フレームワークの基本コンポーネントを追加。
- 起動スクリプト:
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB を使用し MockBroker を利用可能。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（不正値はログ警告の後にデフォルト 60 秒にフォールバック）。停止フラグ（data/stop_requested.flag）検知で安全にループ終了。
- 設定管理:
  - config.py: .env 自動読み込み（.env → .env.local、OS 環境変数を保護）と堅牢な .env パーサを実装。Settings クラスで各種環境変数を型付きで取得・検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。
  - config_setup.py: 対話式 .env 作成/更新ウィザードを追加（既存 .env 読み込み、シークレット入力、ファイル出力）。
  - validate_config.py: 起動前の設定検証 CLI を追加（必須環境変数チェック、パス存在チェック、config/*.yaml の簡易検証、--strict オプション）。
- 監視周り:
  - monitoring 側で監視用テーブルが存在することを保証する init_monitoring_db 呼び出しを追加（冪等）。
  - 監視は環境に関わらず本番 sqlite_path を参照する動作を明確化。
- ロギング／プロセスユーティリティ:
  - utils/logging_setup.py: stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler を組み合わせた統一ログ設定ユーティリティを追加。ログディレクトリ自動作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: Windows / POSIX 両対応でプロセス優先度設定と CPU affinity 設定を提供。権限不足等の失敗を警告で処理。
- ポートフォリオ構築:
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）および等ウェイト／スコア重み（calc_equal_weights, calc_score_weights）を追加。スコア全てが 0 の場合に等分配にフォールバックして警告。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を追加。未知のレジームはフォールバックで 1.0 を返す。
  - portfolio/position_sizing.py: allocation_method（risk_based / equal / score）に基づく株数算出ロジックを実装。単元株丸め、per-position 上限、aggregate cap（available_cash を超える場合のスケールダウン）、cost_buffer を考慮した安全な配分ロジックを実装。端数配分アルゴリズムを導入し再現性を確保。
- 分析 / ツール:
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・レイテンシ（P95）等を計算して PASS/FAIL 判定を出力。P95 算出、期間フィルタ、および DB 存在チェックを実装。
  - research/factor_research.py: ファクター計算モジュール（モメンタム、Value、Volatility、Liquidity）開始。一連の定数と calc_momentum の実装を開始（モジュールは DuckDB を利用して prices_daily / raw_financials を参照する設計）。
- パッケージ情報:
  - __init__.py にてバージョンを "0.1.0" に設定し、主要サブパッケージをエクスポート。

Changed
- なし（初期リリース）。

Fixed
- MONITOR_POLL_INTERVAL の不正値に対して例外を回避し、警告ログとともにデフォルト値へフォールバックする処理を追加（run_monitoring.py）。
- ログ設定で既存ハンドラを安全にフラッシュ／クローズしてから差し替える実装により、二重ハンドラ設定を防止。
- process_priority のプラットフォーム差分を吸収し、未対応 OS の場合は警告ログでスキップするようにした（例外で落ちないように設計）。

Deprecated
- なし。

Removed
- なし。

Security
- なし。

Notes / Known issues / TODO
- portfolio/risk_adjustment.apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーの過少見積りが発生する旨の注記あり。将来的に前日終値や取得原価によるフォールバックが必要。
- position_sizing: 現状は全銘柄共通の lot_size（デフォルト 100）を想定。将来的に銘柄別単元情報を持たせる拡張を検討中（TODO コメントあり）。
- research/factor_research.calc_momentum: ファイル末尾で未完の記述（start_da で途切れている）あり。ファクター群の実装は継続作業が必要。
- validate_config: PyYAML が未インストールの場合に YAML 内容検証をスキップする。厳格に検証するには PyYAML のインストールを推奨。

Migration notes
- .env は絶対に Git にコミットしないでください（config_setup.py の出力にも警告あり）。
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START をデフォルト 0 にしておくことを推奨（validate_config が注意喚起）。
- PAPER_TRADING_SQLITE_PATH を設定すると paper_trading 実行時に専用 DB を使用して本番 DB と分離できます。

今後の予定（非網羅）
- research モジュールのファクター実装完了。
- 銘柄別の lot_size サポート／stocks マスタとの連携。
- 監視・実行のより詳細なメトリクス収集とアラート強化（LINE 通知の実装拡張）。