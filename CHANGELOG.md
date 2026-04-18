CHANGELOG
=========

すべての注目すべき変更点を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。

フォーマット:
- 変更はセマンティックバージョニングに従います（例: 0.1.0）。
- 各リリースは Added / Changed / Fixed / Removed のカテゴリで整理しています。

Unreleased
----------

（現時点の作業中の変更はここに記載します）

[0.1.0] - 2026-04-18
-------------------

初回リリース。日本株自動売買システム「KabuSys」の基本コンポーネントを実装しました。

### Added
- 基本パッケージ構成を追加
  - パッケージエントリポイント、バージョン情報を追加（src/kabusys/__init__.py）。
- 実行用スクリプト
  - 監視プロセス起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止制御はプロジェクトルート/data/stop_requested.flag を検出して行う。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用して起動。
    - 例外発生時は例外ログを出力して次のポーリングへフォールバック。
  - 実行（エンジン）起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - 停止フラグの検出で Engine を安全に停止する仕組み（スレッドを用いた実行と engine.stop()）。
    - 起動時に process priority を "high" に設定。
- 設定管理
  - 環境変数 / .env ローダー（自動読み込み）を追加（src/kabusys/config.py）。
    - .env/.env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込み。
    - export KEY=val 形式、クォート（'"/）とバックスラッシュエスケープ、インラインコメント処理に対応。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - 設定値はプロパティとして提供（KABUSYS_ENV / LOG_LEVEL / DUCKDB_PATH / SQLITE_PATH / PAPER_FILL_MODE 等）。
    - 値検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を実装し、不正値は ValueError を発生させる。
- 設定支援ツール
  - 対話式 .env 作成ウィザードを追加（src/kabusys/config_setup.py）。
    - 主要な環境変数を対話的に入力/確認して .env を生成。
    - 既存 .env の読み込み／Enter で既存値再利用、シークレット表示はマスク化。
- 設定検証ツール
  - 起動前チェック CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数の未設定検出、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、config/*.yaml の存在確認（PyYAML がある場合はパース検証）を実施。
    - --strict オプションで警告を失敗扱いにできる。
- ログ・プロセスユーティリティ
  - ロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - コンソール出力（stdout）と日次ローテートファイル出力（TimedRotatingFileHandler）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL による設定、デフォルト logs/、日次ローテートで30日分保持。
    - ログディレクトリ作成失敗時はファイル出力を無効化してコンソールのみで継続。
  - プロセス優先度・CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows/Linux/macOS を吸収する API を提供（set_process_priority, set_cpu_affinity）。
    - 標準的な "high"/"normal"/"low" レベルをサポート、権限不足時は警告を出してスキップ。
- ポートフォリオ構築ライブラリ
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates（スコア降順、同点は signal_rank 優先）、calc_equal_weights、calc_score_weights（全スコア0なら等配分へフォールバック）。
  - セクター制約・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（既存ポジションに基づくセクター上限チェック。unknown セクターは制限対象外）
    - calc_regime_multiplier（"bull"/"neutral"/"bear" に応じた投下資金乗数。未知レジームは警告して 1.0 フォールバック）
  - 株数決定ロジック（src/kabusys/portfolio/position_sizing.py）
    - allocation_method: "risk_based" / "equal" / "score" をサポート
    - リスクベース（risk_pct, stop_loss_pct）と等配／スコア配分の実装、単元株（lot_size）丸め、per-stock 上限・aggregate cap（available_cash）でスケールダウン、cost_buffer を反映した保守的見積り。
- Paper Trading 検証ツール
  - Paper Trading 向け検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - 稼働率（system_status）、注文成功率・送信率（trade_logs）、リスク却下数（risk_logs）、API レイテンシ（avg/max/P95）を集計。
    - 閾値を定義し、PASS / FAIL を判定して人間向けのレポートを標準出力に出力。
    - --from / --to / --db オプション対応。
- リサーチ（ファクター計算）骨格
  - DuckDB を用いたファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
    - Momentum / Value / Volatility / Liquidity の計算方針を実装計画として記載。モジュールは DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計。
    - 実装の一部（calc_momentum の開始部分）を含む（今後の拡張予定）。

### Changed
- 起動スクリプトの運用仕様を明示
  - いずれの起動スクリプトも起動直後にプロセス優先度を "high" に設定するよう統一。
  - Monitoring は環境にかかわらず本番の sqlite_path を使用する旨を明文化。
  - Execution は paper_trading 環境時に DB を完全分離することでテストと本番の混同を防止。
- .env 読み込みの挙動
  - OS 環境変数を保護する仕組み（protected set）を導入し、.env.local の override を許容しつつ OS 環境変数は上書きされないようにした。

### Fixed
- 安全停止・リソースクリーンアップ
  - 監視と実行の両スクリプトで停止検知（stop flag）および KeyboardInterrupt に対して適切にログ出力・接続クローズを行うように実装。
  - DB / DuckDB 接続は finally ブロックで確実に close されるようにした。

### Known issues / Notes
- research.factor_research.calc_momentum の実装が途中で切れている箇所が存在します。ファクター計算の完全実装は継続作業が必要です。
- portfolio.position_sizing の価格欠損時の取り扱い（price=0.0 による過少見積り）に関する TODO コメントあり。前日終値などのフォールバックを検討する予定です。
- 一部の機能は外部依存（psutil, duckdb, PyYAML 等）に依存します。インストール環境により YAML の検証がスキップされる場合があります（PyYAML 未インストール時）。
- PAPER_FILL_MODE 等の環境変数は厳密なバリデーションを行うため、設定ミスは起動時に例外で停止します。ドキュメント（.env.example 等）を参照してください。

Footer / 参照
--------------
- 詳細な使用法や設定は各モジュールの docstring とスクリプト冒頭のヘルプコメントを参照してください。
- 今後のリリースではファクター計算の完成、テストケースの追加、エラーハンドリングの強化、運用向け監視・アラート機能の追加を予定しています。