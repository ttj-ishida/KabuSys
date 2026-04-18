# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠します。  
バージョン付けは SemVer を想定しています。

## [0.1.0] — 2026-04-18

初回リリース。本リポジトリの主な機能・CLI・ライブラリを追加しました。

### Added
- 基本ライブラリとバージョン情報
  - パッケージメタ情報を追加（kabusys/__init__.py: __version__ = "0.1.0"）。

- 起動スクリプト / デーモン風プロセス
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は常に本番用の SQLite (`Settings.sqlite_path`) を使用してテーブルを初期化。
    - 停止フラグファイル（data/stop_requested.flag）検知で安全に終了。
    - プロセス優先度を起動時に "high" に設定。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite を使用（data/paper_trading.db 想定）。
    - BrokerClientFactory によるブローカークライアント生成、OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動・停止連携（stop flag 検知）を提供。
    - PID ファイル出力（data/execution.pid）サポート。

- 設定関連ユーティリティ・CLI
  - config.py
    - .env 自動読み込み機能（プロジェクトルート判定: .git または pyproject.toml を基準）。
    - .env / .env.local のロード順と OS 環境変数保護（上書き制御）。
    - 複雑な行（export 形式、クォート中のエスケープ、インラインコメント）を扱えるパーサを実装。
    - Settings クラスで環境変数をラップ（DB パス、ログレベル、KABUSYS_ENV、Paper Trading 関連設定等）。
    - PAPER_FILL_MODE のバリデーション、PAPER_TRADING_SQLITE_PATH のサポート。
  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援。
    - J-Quants / kabu API トークン、DB パス、ログレベル、KILL_FLAG_CLEAR_ON_START など主要設定項目を対話的に入力・保存可能。
    - 既存 .env の読み込み・マスク表示、保存確認を実装。
  - validate_config.py
    - 起動前の設定検証 CLI を追加。
    - 必須環境変数のチェック、KABUSYS_ENV/LOG_LEVEL の値検証、DB パス（ディレクトリ存在チェック）、config/*.yaml の存在および（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加ガードチェックを実装。
    - --strict オプションで警告も失敗扱いにできる。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 全起動スクリプトで共通使用できるログ設定ユーティリティを追加。
    - stdout 出力用 StreamHandler と 日次ローテート（TimedRotatingFileHandler、30 日分保持）をルートロガーに設定。
    - ログディレクトリの自動作成（失敗時はファイル出力をスキップしてコンソールのみで継続）。
    - LOG_LEVEL / LOG_DIR / level 引数で挙動を切替可能。
  - utils/process_priority.py
    - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
    - 権限不足や未対応 OS の場合は警告を出して安全にフォールバック。

- ポートフォリオ構築ライブラリ（純粋関数）
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）と重み計算（calc_equal_weights, calc_score_weights）を実装。スコア全0 の場合は等分配にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装（売却予定銘柄の除外、"unknown" セクターは制限対象外）。
    - 市場レジームに応じた資金乗数 calc_regime_multiplier を実装（bull/neutral/bear のマッピングと未知レジームのフォールバック）。
    - 実装上の注意点（price が欠損した場合の将来的な改善案）をコメントで明示。
  - portfolio/position_sizing.py
    - position sizing の主要ロジックを実装（risk_based / equal / score の allocation_method 対応）。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash によるスケーリング）、cost_buffer を考慮したスケールダウンロジックを実装。
    - スケールダウン時の小数端数の分配アルゴリズム（残差に基づく lot 単位の追加配分）を実装。

- 研究 / ファクター計算（骨組み）
  - research/factor_research.py
    - モメンタム等のファクターを DuckDB の prices_daily テーブルから計算するための設計と一部実装を追加（horizon 定義・関数ヘッダ等）。
    - （注）ファイル末尾で実装が途中終了している箇所あり（今後の実装予定）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（avg/max/P95）を算出し PASS/FAIL 判定を出力。
    - 日付フィルタ (--from / --to)、DB パスの override (--db) をサポート。
    - P95 計算、データ欠如時の N/A ハンドリング、閾値による判定基準を実装。

- DB 初期化ユーティリティ呼び出し
  - run_* スクリプトや execution 起動経路で monitoring テーブルが存在することを保証する init_monitoring_db 呼び出しを追加（冪等）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- ログディレクトリ作成失敗時のフォールバック動作を明確化
  - logging_setup: ディレクトリ作成に失敗した場合はファイルハンドラをスキップして stdout のみで継続する仕様を実装。

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 環境変数読み込み時に OS 環境（既存の環境変数）を保護する仕組みを導入（.env の上書き制御）。機密値はデフォルトで上書かれない。

## 注意事項 / 既知の制限
- research/factor_research.py の一部実装が途中で終了しており、モメンタム計算の完全実装が未完です。今後のリリースで補完予定です。
- risk_adjustment.apply_sector_cap は price が欠損（0.0）の場合にエクスポージャーを過小見積もる可能性があり、将来的にフォールバック価格（前日終値など）を導入する予定です（TODO コメントあり）。
- process_priority.set_process_priority / set_cpu_affinity は権限やプラットフォームによって実行できない場合があり、その場合は警告を出してスキップします。
- .env 自動ロードはプロジェクトルートが特定できない（.git / pyproject.toml が見つからない）場合はスキップされます。
- Paper Trading と Live の DB は明確に分離されていますが、設定ミスによる混在を防ぐため validate_config を実行して事前検証することを推奨します。

## 今後の予定（短期）
- research/factor_research の完成（DuckDB を用いたファクター計算ロジックの実装完了）。
- テストカバレッジの追加（ユニット/統合テスト）。
- 銘柄別 lot_size 対応（stocks マスタからの単元取得）。
- 監視・レポート機能の拡張（アラート送信：LINE 等）。

---

もし特定ファイルや機能についてより詳細な変更点（関数単位での差分説明やマイグレーション手順）を出力して欲しい場合は、対象を指定してください。