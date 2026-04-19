# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
現在のバージョンは src/kabusys/__init__.py の __version__ に合わせて v0.1.0 としています。

## [Unreleased]

## [0.1.0] - 2026-04-19
初回リリース（コードベースから推測してまとめた主要機能と修正点）。

### Added
- 基本アプリケーションパッケージを追加（kabusys）。
  - パッケージバージョン: 0.1.0
- 設定/環境管理
  - Settings クラス（kabusys.config）を追加し、環境変数から設定を取得・検証する機能を提供。
  - .env の自動読み込み機能を実装（プロジェクトルートを自動検出し、`.env` と `.env.local` を読み込む。OS 環境変数は保護）。
  - .env パーサーで以下をサポート:
    - export KEY=val 形式
    - シングル/ダブルクォート内のエスケープ処理
    - 行内コメントの扱い（クォートの有無に応じた挙動）
  - 必須設定チェック時に未設定・プレースホルダ値を検出するユーティリティを提供。
- 設定ウィザード CLI
  - `kabusys.config_setup` に対話式ウィザードを追加。`.env` の初期作成・更新を支援。
  - デフォルト項目（環境、API トークン、DB パス、ログレベル、Kill Switch 設定など）を対話的に設定可能。
- 設定検証 CLI
  - `kabusys.validate_config` を追加。環境変数・config/*.yaml の存在や基本整合性を検証。
  - `--strict` オプションで警告を FAIL 扱いにできる。
  - PyYAML が未インストールの場合は YAML 検証をスキップして警告出力。
- 起動スクリプト
  - 実行エンジン起動スクリプト: `run_execution.py`
    - ExecutionEngine を組み立ててスレッドで実行。Paper Trading 環境では MockBroker を使用し、専用の SQLite（`data/paper_trading.db`）に分離して記録。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル管理をサポート。
  - 監視ループ起動スクリプト: `run_monitoring.py`
    - SystemMonitor のポーリングループを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視モジュールは環境に依らず本番用 sqlite_path を使用する旨が明記されている（注意点）。
- ログ管理ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging` を追加。
    - stdout へ StreamHandler、日次ローテートの TimedRotatingFileHandler（デフォルト logs/ ディレクトリ、30日保持）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - LOG_LEVEL / LOG_DIR の優先解決ルールを実装。
- プロセス優先度 / CPU affinity ユーティリティ
  - `kabusys.utils.process_priority` を追加。
    - Windows / POSIX 間の違いを吸収してプロセス優先度（high/normal/low）を設定。
    - CPU affinity を最初の N コアに固定する機能を提供。権限不足や未対応 OS の場合は警告を出してスキップ。
- ポートフォリオ構築ロジック（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`
    - 候補選定 (select_candidates)、等配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を提供。
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中制限を適用する apply_sector_cap、マーケットレジームに応じた投下資金乗数 calc_regime_multiplier を実装。
  - `kabusys.portfolio.position_sizing`
    - 銘柄ごとの発注株数計算を実装（risk_based / equal / score の配分方式、単元株丸め、aggregate cap スケーリング、cost_buffer の考慮など）。
- DuckDB / SQLite 統合
  - DuckDB 接続と SQLite 接続を利用する設計を採用（分析用: DuckDB、監視・履歴: SQLite）。
  - 監視用 DB 初期化ユーティリティ init_monitoring_db が利用されている（冪等にテーブル作成等を保証）。
- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report` を追加。
    - Paper Trading 用 SQLite から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）を集計し、基準値（稼働率 99%、成功率 90% など）に基づく PASS/FAIL レポートを生成。
    - 日付フィルタ、DB パス指定オプションをサポート。
    - P95 計算（サンプルから算出）を実装。
- リサーチ / ファクター計算基盤（基礎実装）
  - `kabusys.research.factor_research` にモメンタム等のファクター計算基盤の実装が開始（DuckDB の prices_daily / raw_financials を想定）。（ファイルは途中まで実装）

### Changed
- DB パス / 環境の振る舞いに関する明示的な設計
  - 監視モジュールは環境にかかわらず本番 sqlite_path を使用する（意図的な仕様として docstring に記載）。
  - ExecutionEngine は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path を使用して DB を完全分離。
- ログ挙動の統一化
  - 全起動スクリプトから同一の setup_logging を使うことでログ出力形式・ローテーションを統一。

### Fixed
- 環境変数の数値パースに対する堅牢性向上
  - MONITOR_POLL_INTERVAL の不正値（非数値、0 以下）を検出してデフォルト値（60 秒）へフォールバックし、警告を出力するロジックを追加。
- PAPER_FILL_MODE のバリデーションを追加（有効値チェック。無効な場合は ValueError を送出）。
- .env 読み込みでファイル読取失敗時に warnings.warn を出すようにし、静かに失敗するのを防止。
- logging_setup でログディレクトリ作成に失敗した際に明示的に警告を出してファイル出力を無効化するフォールトトレランスの実装。
- process_priority のエラー時（権限不足等）に警告を出し処理をスキップする挙動を実装。

### Security
- .env ファイル生成時に注意喚起コメントを追加（.env を絶対に Git にコミットしないことを明示）。

### Notes / その他
- validate_config により起動前に環境変数や設定ファイルの不足を検出できるため、本番環境の事故防止に寄与する設計。
- run_monitoring/run_execution は stop フラグ（data/stop_requested.flag）や kill flag 設定など、運用上の Kill Switch を利用して安全に停止できる実装になっている。
- 一部モジュール（研究系 factor_research 等）はコメントや TODO を含み部分実装のままの箇所があるため、今後の拡張余地あり。

---

今後の作業候補（推奨）
- factor_research の完全実装（計算ロジックの続き、テスト追加）。
- 単体テスト/統合テストの追加（特に position_sizing のスケーリングロジック、config のパース、process_priority のプラットフォーム互換性）。
- ドキュメント整備: 設定項目・運用手順（Kill Switch や PID 管理、paper_trading と live の運用差分）を README や運用ドキュメントに反映。
- エラーハンドリング強化: DB 接続失敗時や broker API 障害時の再試行戦略の明確化。

--- 

（補足）この CHANGELOG は提示されたソースコードからの推測に基づいて作成しています。リポジトリのコミット履歴や実際のリリースノートがある場合はそれに合わせて調整してください。