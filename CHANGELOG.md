Keep a Changelog
=================

すべての変更は慣例に従い分類しています。  
このファイルは日本語で記載しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
---------

- （なし）

0.1.0 - 2026-04-23
-----------------

Added
- 初回公開: KabuSys パッケージ v0.1.0 を追加。
  - パッケージ概要: 日本株自動売買システムの基盤モジュール群（config / execution / monitoring / portfolio / utils / research / tools 等）。
  - バージョン定義: src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

- 起動スクリプト / CLI:
  - run_monitoring (src/kabusys/run_monitoring.py)
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 停止用フラグファイル data/stop_requested.flag を監視してグレースフルに停止。
    - 起動時にプロセス優先度を "high" に設定。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様。
  - run_execution (src/kabusys/run_execution.py)
    - ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を介して本番ブローカー / MockBrokerClient を切り替え可能（設定に応じて）。
    - エンジンの PID ファイル (data/execution.pid) の取り扱い、停止フラグの検出でエンジン停止。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理 / ユーティリティ:
  - config (src/kabusys/config.py)
    - .env 自動ロード機能（デフォルトで有効）。プロジェクトルート検出（.git または pyproject.toml を基準）。
    - .env/.env.local の安全な読み込み（OS 環境変数を保護する protected 機構）。
    - .env の行パーサを実装: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
    - Settings クラスを導入し、アプリケーション設定（各種パス、閾値、API トークン等）をプロパティで取得可能に。
    - PAPER_FILL_MODE のバリデーション、KABUSYS_ENV / LOG_LEVEL の検証、paper_sqlite_path/prod sqlite/duckdb パス等。
  - config_setup (src/kabusys/config_setup.py)
    - インタラクティブな .env 作成ウィザードを追加。既存 .env の読み込み、シークレット値のマスク表示、選択肢サポート、.env テンプレート出力機能を提供。
  - validate_config (src/kabusys/validate_config.py)
    - 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース確認（PyYAML がない場合はスキップして警告）。
    - --strict オプションで警告を FAIL 扱いにするモードを提供。
  - ツール: paper_verification_report (src/kabusys/tools/paper_verification_report.py)
    - ペーパートレード用検証レポート生成スクリプトを追加。
    - 指標: システム稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、リスク却下数、レイテンシ（avg, max, P95）を算出。
    - P95 計算、期間指定 (--from / --to)、DB 指定 (--db / 環境変数 PAPER_TRADING_SQLITE_PATH) に対応。
    - デフォルト評価基準を定義（稼働率 >=99%、注文成功率 >=90%、送信率 >=95%、P95 <=200ms）。

- ポートフォリオ構築（純関数群、DB 非依存）:
  - portfolio_builder (src/kabusys/portfolio/portfolio_builder.py)
    - 候補選定 (select_candidates)、等分配 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。スコアが全て 0 の際は等分配にフォールバックして警告を出す。
  - risk_adjustment (src/kabusys/portfolio/risk_adjustment.py)
    - セクター集中制限 apply_sector_cap、レジーム乗数 calc_regime_multiplier を追加。未知のレジームはフォールバックで警告を出す。
  - position_sizing (src/kabusys/portfolio/position_sizing.py)
    - position size 計算を実装。allocation_method として "risk_based" / "equal" / "score" をサポート。
    - lot_size（単元）丸め、per-stock 上限、aggregate cap（available_cash を超えた際のスケーリング）、cost_buffer による保守的コスト見積り、残余キャッシュを用いた端数配分ロジックを実装。

- 汎用ユーティリティ:
  - logging_setup (src/kabusys/utils/logging_setup.py)
    - 統一ロギング設定ユーティリティを追加。StreamHandler を stdout に設定し、TimedRotatingFileHandler による日次ローテーション（30日保持）をサポート。
    - 既存ハンドラのクリーンアップ（重複設定防止）、環境変数 LOG_LEVEL / LOG_DIR による上書き、ログディレクトリ作成失敗時のフォールバック。
  - process_priority (src/kabusys/utils/process_priority.py)
    - set_process_priority / set_cpu_affinity を追加。Windows / POSIX の差分を吸収、psutil を用いた安全な実装（権限不足等は警告でスキップ）。

- research/factor_research (src/kabusys/research/factor_research.py)
  - ファクター計算モジュールを追加（モメンタム / MA200 / ATR / ボリューム等の計算方針を実装予定）。DuckDB を受け取り prices_daily / raw_financials を参照する設計。モジュールは計算関数の骨格（calc_momentum 等）を含む。

Changed
- ログ出力の標準エラーではなく標準出力（stdout）に統一する方針を採用（logging_setup）。
- .env の自動ロード時に OS 環境変数を保護（既存の OS 環境変数を .env で上書きされないようにする）。

Fixed
- .env パーサを強化:
  - export プレフィックスの処理、クォート中のバックスラッシュエスケープ、インラインコメントの扱いを改善。
  - 空行やコメント行を無視する挙動を明確化。

Notes / Implementation details
- Monitoring と Execution の起動時にプロセス優先度を "high" に設定するため、実行環境によっては権限不足で警告が出る場合があります（実行は継続されます）。
- validate_config は PyYAML がインストールされていない場合に YAML 内容の検証をスキップして警告を出します。
- Paper Trading は本番 DB と完全分離する設計（PAPER_TRADING_SQLITE_PATH / settings.is_paper を利用）。
- research/factor_research の calc_momentum 等は実装の骨格を含みますが、全ファクターの実装・テストは今後の拡張予定です。

Acknowledgements
- 初版リリース。今後の改善点（テスト追加、エラーケースの更なる扱い、パフォーマンス最適化、ドキュメント整備など）は次回リリースで順次反映します。