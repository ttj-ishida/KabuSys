# CHANGELOG

※ 以下は提示されたコードベースの内容から推測して作成した変更履歴です。実際のコミットログではなく、ソースコードの構成・実装内容に基づく概要的な記述になります。

フォーマット: Keep a Changelog 準拠（https://keepachangelog.com/ja/）

## [Unreleased]

- 開発中の変更点はありません（コードから推測された現状の機能を 0.1.0 として記録しています）。
- 将来の変更: research モジュール（factor_research）の未完部分の実装継続、テスト・ドキュメント整備などを想定。

## [0.1.0] - 2026-04-21

### Added
- 基本パッケージ初期リリース。
- 実行エントリ／ユーティリティ
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の専用 SQLite（data/paper_trading.db をデフォルト）を使用して本番 DB と完全分離。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) による起動・停止制御を実装。
    - ブローカークライアントの抽象化（BrokerClientFactory）を利用して実行時に適切なクライアントを生成。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒、無効値は警告後デフォルトにフォールバック）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する（監視 DB の初期化を行う）。
    - 停止フラグによるループ終了処理を実装。
- 設定・環境管理
  - config.py: 設定管理クラス (Settings) を実装。
    - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート。
    - 環境変数の取得ラッパ、必須チェック（_require）や各種既定値・検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）を実装。
    - データベースパス（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）や PID / kill flag のパスなどを提供。
  - config_setup.py: 対話式の .env 作成ウィザードを追加。
    - 初期 .env の対話式作成・更新、秘密値のマスク表示、保存前の確認を実装。
    - デフォルト値・選択肢を用意（KABUSYS_ENV、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START など）。
  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パス親ディレクトリ存在チェック、config/*.yaml の存在・パースチェック（PyYAML がインストールされていない場合は検証をスキップして警告）。
    - `--strict` オプションで警告も失敗扱いにできる。
- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを実装。
    - stdout 出力の StreamHandler と、日次ローテーション（TimedRotatingFileHandler）でのファイル出力をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の解決順序を実装し、ログディレクトリの作成失敗時にファイル出力を無効化してフォールバック。
    - 既存ハンドラのクリアを行って二重設定を防止。
  - utils/process_priority.py: プロセス優先度設定と CPU affinity ユーティリティを実装。
    - Windows / POSIX (Linux, Darwin, FreeBSD) の差分を吸収してカレントプロセスに対して優先度 (high/normal/low) を設定。
    - set_cpu_affinity() で最初の N コアにプロセスを固定可能。権限不足・未対応環境は警告を出してスキップ。
- ポートフォリオ構築関連（純関数群）
  - portfolio/portfolio_builder.py: 候補選定と重み計算
    - select_candidates: スコア降順、同点は signal_rank でタイブレークして上位 N を返す。
    - calc_equal_weights / calc_score_weights を実装。スコア合計が 0 の場合は等配分にフォールバック（警告ログ）。
  - portfolio/risk_adjustment.py: セクター集中制限とレジーム乗数
    - apply_sector_cap: 既存保有のセクター別エクスポージャを計算し、max_sector_pct を超えるセクターの新規候補を除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: "bull"/"neutral"/"bear" に対してそれぞれ 1.0/0.7/0.3 の乗数を返す。未知レジームは 1.0 でフォールバック（警告）。
  - portfolio/position_sizing.py: 株数計算ロジック
    - allocation_method に応じた株数算出（"risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、aggregate cap（available_cash）超過時のスケールダウン、cost_buffer を使った保守的見積り、余剰での lot 単位追加割当アルゴリズムを実装。
- ツール / レポート
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成ツールを追加。
    - system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）を集計してレポート出力。
    - デフォルト閾値を定義（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）と基準に基づく PASS/FAIL 判定を出力。
- research/factor_research.py: ファクター計算モジュール（部分実装）
  - モメンタム、MA200、ATR、流動性などのファクター計算方針を実装（DuckDB 接続を受け取り SQL + Python で計算する設計）。（ファイルの途中まで実装あり）

### Changed
- プロジェクト構成に合わせてログ・DB・設定周りの標準パスを整理（data/、logs/ など）。
- ログ出力は stdout を標準とする仕様（cron/Task Scheduler 等からの運用を考慮）。

### Fixed
- 環境変数パーサの改善（config._parse_env_line）
  - export 付き行、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理、コメントと値の区別などに対応して堅牢性を向上。
- MONITOR_POLL_INTERVAL の不正値処理: 非正の値や整数変換失敗時に警告を出してデフォルトにフォールバック。

### Deprecated
- なし（初期リリース）。

### Removed
- なし（初期リリース）。

### Security
- 環境設定ウィザードと .env 書き出しで秘密値は表示をマスク（コンソール）するなど、運用上の取扱いに配慮。

---

開発者向けメモ（推測）
- 必要な外部依存: psutil（プロセス管理）、duckdb（分析 DB）、sqlite3（標準ライブラリだが DB ファイル操作）、PyYAML は config 検証時に利用（未インストール時は警告）。
- 本番運用時の注意:
  - KABUSYS_ENV=live の場合は LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）や KILL_FLAG_CLEAR_ON_START の設定に注意する旨のチェックを実装済み。
  - 監視コンポーネントは監視用 sqlite_path（デフォルト data/monitoring.db）を参照する設計のため、環境分離の運用設計に留意。
- 未完事項:
  - research.factor_research の完全実装（ファイル途中で切れている）。
  - テスト・CI 設定、ドキュメント（API リファレンスや運用手順）の追加。