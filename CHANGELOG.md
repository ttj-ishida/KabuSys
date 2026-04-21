# Changelog

すべての注目すべき変更点を記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

全般的な注意
- 本リポジトリはバージョン 0.1.0 として初期公開されています（src/kabusys/__init__.py の __version__ に基づく）。
- 日付は本ファイル作成日（2026-04-21）を使用しています。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-21

### Added
- 基本アプリケーション実装を追加。
  - src/kabusys パッケージの初期モジュール群を追加。
  - バージョン定義: __version__ = "0.1.0"。

- 設定管理（env / Settings）
  - src/kabusys/config.py:
    - .env ファイル自動読込機能を追加（プロジェクトルート検出: .git または pyproject.toml）。
    - .env の行パーサ（クォート、エスケープ、コメント、`export` プレフィックス対応）を実装。
    - 環境変数の保護（既存 OS 環境変数は上書きしない/必要に応じて上書き）を実装。
    - Settings クラスを実装（J-Quants / kabu / LINE / DB / 監視閾値 / システム設定などのプロパティを提供）。
    - env 値のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を実装。

- 環境設定ウィザード CLI
  - src/kabusys/config_setup.py:
    - 対話式ウィザードで .env を初期作成・更新する機能を実装。
    - シークレット入力・デフォルト提示・選択肢サポート・確認後保存を実装。
    - .env の読み書き処理を提供。

- 設定検証ツール CLI
  - src/kabusys/validate_config.py:
    - 起動前に .env および config/*.yaml の基本的な妥当性をチェックする CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、YAML パース（PyYAML があれば）などを行う。
    - --strict モードで警告も失敗扱いにできる。

- 実行/監視エントリポイント
  - src/kabusys/run_execution.py:
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db デフォルト）を使用し、本番 DB と分離。
    - BrokerClientFactory を使ったブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、エンジン起動と停止フラグ処理を実装。
    - 起動時にプロセス優先度を "high" に設定（set_process_priority）。
  - src/kabusys/run_monitoring.py:
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。
    - 監視（monitoring）では環境にかかわらず本番 sqlite_path を使用する設計（監視は本番 DB の状態を確認するため）。

- 監視 DB 初期化ユーティリティ呼び出し
  - run_execution/run_monitoring で init_monitoring_db を呼び出し、監視テーブルが存在することを冪等に保証。

- ロギングユーティリティ
  - src/kabusys/utils/logging_setup.py:
    - 全起動スクリプト共通のログ設定関数 setup_logging を実装。
    - stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の解決順を実装。ログディレクトリ作成失敗時はファイル出力を安全にスキップ。

- プロセス優先度 / CPU affinity ユーティリティ
  - src/kabusys/utils/process_priority.py:
    - Windows / POSIX の差を吸収する set_process_priority を実装（high/normal/low）。
    - set_cpu_affinity を実装（最初の N コアに固定）。
    - 権限不足や未対応環境でも安全にスキップして警告出力する設計。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - src/kabusys/portfolio:
    - portfolio_builder.py:
      - シグナル選択 select_candidates、等配分 calc_equal_weights、スコア加重 calc_score_weights を実装。
    - risk_adjustment.py:
      - セクター集中制限 apply_sector_cap、レジーム乗数 calc_regime_multiplier を実装。
    - position_sizing.py:
      - position サイズ計算 calc_position_sizes を実装（risk_based / equal / score の allocation_method、lot_size 単位処理、aggregate cap スケーリング、cost_buffer を考慮）。
    - すべてメモリ内計算の純粋関数として実装（DB 参照なし）。

- Paper Trading 検証レポート生成ツール
  - src/kabusys/tools/paper_verification_report.py:
    - SQLite の paper_trading DB（PAPER_TRADING_SQLITE_PATH）を読み、システム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（avg/max/P95）を集計してテキストレポートを出力。
    - P95 計算、期間フィルタ、閾値（稼働率/成功率/送信率/P95 レイテンシ）判定ロジックを実装。
    - テーブル欠如やデータ不足に対する耐性を実装（OperationalError を捕捉して N/A を扱う）。

- 研究用ファクター計算（骨組み）
  - src/kabusys/research/factor_research.py:
    - Momentum / Value / Volatility / Liquidity 計算の方針と定数を定義。
    - calc_momentum のドキュメントと設計を含む（prices_daily / raw_financials を用いることを明記）。
    - （ファイル末尾が途中までのため、実装は部分的に含まれる）

### Changed
- なし（初期リリース）

### Fixed
- なし（初期リリース）

### Deprecated
- なし（初期リリース）

### Removed
- なし（初期リリース）

### Security
- なし（初期リリース）

Notes / 備考
- run_monitoring は監視 DB として settings.sqlite_path（監視用のパス）を使用するため、環境に依存せず監視対象 DB を明確に分離している点に注意してください。
- run_execution は paper_trading モード時に paper_sqlite_path を使用し、本番 DB と完全に分離する設計です（ペーパートレードのログ/検証は data/paper_trading.db へ）。
- .env 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。テスト環境等で便利です。
- 設定値のバリデーションは厳密に行われます（無効な KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等は ValueError を送出するため、起動前に validate_config を実行して確認することを推奨します）。
- research/factor_research.py の実装は未完了の可能性があるため、研究用機能を利用する際は注意してください。

以上。