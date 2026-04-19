# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-04-19
最初のリリース。KabuSys のコアユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、検証ツール類を追加しました。

### Added
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV に応じて paper_trading 用 DB を分離（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。
    - BrokerClientFactory により本番/モックブローカーを切り替え。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）による安全停止機能。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視は環境に関わらず本番用 sqlite_path を使用する設計。
- 設定関連
  - config.py
    - .env の自動読み込み（.env, .env.local）と保護（OS 環境変数の上書き防止）。
    - .env パース機能（クォート、エスケープ、インラインコメント対応）。
    - Settings クラスを導入し、各種環境変数の getter（DB パス、ログレベル、しきい値等）を提供。
  - config_setup.py
    - .env を対話式に生成/更新するウィザードを追加（secret 項目のマスク表示、保存確認等）。
  - validate_config.py
    - 起動前の設定検証 CLI を追加（必須環境変数チェック、KABUSYS_ENV 検証、YAML ファイル存在・パースチェック、--strict オプション）。
- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - ルートロガーの統一設定関数を追加（コンソール stdout 出力 + 日次ローテーションのファイル出力、既存ハンドラのクリア）。
    - ログディレクトリ作成失敗時はファイル出力をスキップして処理継続するフォールバックを実装。
  - utils/process_priority.py
    - set_process_priority, set_cpu_affinity を追加。Windows / POSIX の差分を吸収し、安全に優先度/CPU affinity を設定。
    - 権限不足や未対応 OS の場合は警告ログを出してスキップする設計。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア全0時に等金額配分へフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中制限適用関数（apply_sector_cap）を実装。既存保有を考慮したセクター別エクスポージャー計算、"unknown" セクターの扱いについて明示。
    - 市場レジームに応じた乗数（calc_regime_multiplier）を追加（bull/neutral/bear とデフォルト挙動）。
  - portfolio/position_sizing.py
    - 発注株数計算（calc_position_sizes）を実装。risk_based / equal / score の配分方式、lot_size 単位への丸め、aggregate cap によるスケール調整、cost_buffer による保守的見積り等をサポート。
- 解析/検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から稼働率、注文成功率、送信率、レイテンシ（P95 等）を集計し、PASS/FAIL 判定レポートを出力する CLI を追加。
    - 指標のしきい値（稼働率 99%、成立率 90% 等）を定義して自動判定。
- 研究用モジュール（骨組み）
  - research/factor_research.py
    - DuckDB を用いたファクター計算モジュールの骨組みを追加（Momentum, Value, Volatility, Liquidity 等を想定）。関数インターフェースや定数を定義（計算ロジックの一部は実装中）。
- パッケージ管理
  - __init__.py にバージョン番号 __version__ = "0.1.0" を追加。
  - package の公開エクスポート（portfolio モジュールの __all__）を整備。

### Changed
- .env 処理
  - プロジェクトルート自動検出を実装（.git または pyproject.toml を基準）。これにより CWD に依存しない .env 自動読み込みを実現。
  - .env の読み込み優先順位を OS 環境変数 > .env.local > .env と明確化し、OS 環境変数を保護する protected パラメータを導入。
- ログ設定のデフォルトを統一
  - ログレベルの解決順およびログ出力先（logs/<app_name>.log）挙動を統一。
- 実行フローの安全策
  - 起動直後にプロセス優先度を High に設定する呼び出しを起動スクリプトに組み込み（set_process_priority）。
  - 起動時に監視用 DB テーブルの存在を保証するため init_monitoring_db を呼び出す処理を追加。

### Fixed
- .env パーサーの強化
  - シングル/ダブルクォート内のバックスラッシュエスケープ処理、クォート外のインラインコメント判定（直前が空白の場合のみ）など、実用上起こり得るケースに対応。
- ログハンドラの二重設定回避
  - setup_logging() で既存ハンドラを flush/close のうえ削除してから再設定するようにして、複数回呼び出し時の重複ログ出力を防止。
- DB/ファイルアクセスのフォールバック
  - ログディレクトリ作成失敗やファイルハンドラ作成失敗時に、コンソール出力のみで継続するよう安全にフォールバック。
- プロセス優先度/CPU affinity の例外ハンドリング
  - 権限不足や未実装 API 呼び出しでの例外を捕捉し、警告ログを出して処理継続するように修正。

### Documentation
- 各モジュールに詳細な docstring と使用例を追加（設定ウィザード、検証 CLI、起動スクリプト、各ポートフォリオ計算関数等）。
- tools/paper_verification_report の使い方と出力指標・しきい値を README 的に記述。

### Notes / Known issues
- research/factor_research.py は一部実装が途中で切れている（calc_momentum の実装開始のみを含む）。今後のリリースでファクター計算ロジックの完成とユニットテストを追加予定。
- apply_sector_cap のエクスポージャー計算は価格が欠損（0.0）な場合に過少見積りとなる旨を TODO として注記。将来的にフォールバック価格（前日終値等）を導入予定。

---

今後のリリース予定:
- factor_research の完成と DuckDB ベースのバッチ処理スクリプト追加
- ExecutionEngine / RiskManager まわりの拡張（より細かい設定の外部化、単体テスト追加）
- テストスイートと CI 設定の追加

（補足）この CHANGELOG は提供されたソースコードから推測して作成しています。実際のコミット履歴や意図と異なる場合があります。