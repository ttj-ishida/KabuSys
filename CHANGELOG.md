# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」準拠です。

未解決の不具合や改善点は Issue/PR にて追記してください。

## [Unreleased]

- なし（次バージョンでの変更を記載）

## [0.1.0] - 2026-04-25

### Added
- 実行・監視用エントリポイントを追加
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを実装。  
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db）を使用し MockBrokerClient を利用する想定（BrokerClientFactory による生成）。
    - プロセス優先度を起動時に "high" に設定。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル管理（data/execution.pid）に対応。
    - サブスレッドでエンジンを実行し、フラグ検知で安全に停止するループを実装。
  - run_monitoring.py: SystemMonitor（監視）を定期実行するスクリプトを実装。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は実行環境に関わらず本番（設定された）sqlite_path を参照して監視 DB を使用。
    - 停止フラグ検知でループ終了、例外時はログに出力して次サイクルへ継続。

- 設定管理・自動読み込み
  - kabusys.config: .env 自動ロード機能を追加（プロジェクトルートを .git / pyproject.toml で探索）。  
    - .env / .env.local の読み込み順序を実装（OS 環境変数を保護して上書き制御）。  
    - 複雑な .env 行のパースに対応（export 形式、シングル／ダブルクォート内のエスケープ、インラインコメント規則）。  
    - Settings クラスを追加し、アプリケーション設定（API トークン、DB パス、paper_trading 用設定、監視しきい値、環境判定等）をプロパティ経由で提供。  
    - PAPER_FILL_MODE の入力検証、KABUSYS_ENV / LOG_LEVEL の検証を実装。

- 設定ツール / 検証ツール
  - config_setup.py: 対話式ウィザードで .env を作成・更新する CLI を追加。  
    - 秘匿項目のマスク、既存値の再利用、保存前の確認をサポート。  
  - validate_config.py: 起動前チェック用 CLI を追加。  
    - 必須環境変数チェック、KABUSYS_ENV の妥当性検証、DB パスや config/*.yaml の存在チェック（PyYAML の有無に応じてスキップ/解析）、本番用ガード（LINE 通知設定や Kill-Flag 設定の注意喚起）を実装。  
    - --strict オプションで警告を FAIL 扱いにできる。

- ログ／プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一的なログセットアップ関数 setup_logging を提供。  
    - stdout（StreamHandler）出力と日次ローテーション（TimedRotatingFileHandler, 30日保持）を自動設定。  
    - LOG_DIR / LOG_LEVEL の解決順を管理し、ディレクトリ作成失敗時はファイル出力をスキップして安全にフォールバック。
  - utils/process_priority.py: クロスプラットフォームなプロセス優先度設定と CPU affinity 設定関数を追加（psutil 利用）。  
    - Windows / POSIX の差分を吸収し、権限不足等で設定が失敗した場合は警告を出してスキップ。

- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py: 候補選定・重み計算関数を追加。  
    - select_candidates: スコア降順、同点時は signal_rank でタイブレーク。  
    - calc_equal_weights / calc_score_weights: 等配分とスコア加重配分（スコア合計が 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）とレジームに応じた乗数計算（calc_regime_multiplier）を追加。  
    - apply_sector_cap は既存ポジションと売却予定を考慮して候補をフィルタリング。unknown セクターは制限対象外。  
    - calc_regime_multiplier は "bull"/"neutral"/"bear" にマッピングし、未知レジームは警告して 1.0 にフォールバック。
  - portfolio/position_sizing.py: 発注株数算出ロジックを追加。  
    - risk_based / equal / score の割当方式を実装。単元株（lot_size）丸め、per-position 上限・aggregate cap（available_cash）でのスケーリング、cost_buffer（手数料・スリッページ見積り）考慮、スケールダウン時の残差処理を備える。

- リサーチ・ファクター計算（骨格）
  - research/factor_research.py: ファクター計算モジュールの基盤を導入（モメンタム等の計算方針・定数を定義）。（実装途中の箇所あり）

- Paper Trading 検証ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポートを生成する CLI を追加。  
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）等を集計して PASS/FAIL を判定するしきい値を定義。  
    - --from/--to/--db CLI オプションをサポート。DB の存在チェックとエラー耐性を実装。

- パッケージ基本情報
  - __init__.py によるバージョン定義（__version__ = "0.1.0"）およびエクスポート整理。

### Changed
- 実行スクリプト・コンポーネントの堅牢性向上
  - DB 初期化（init_monitoring_db）をエンジン起動前に実行して監視テーブルの存在を保証（冪等）。
  - run_execution/run_monitoring 両スクリプトで duckdb 接続を使用し分析データベースを開く設計。
  - ロギング設定を統一することで各スクリプトのログ挙動を標準化。

### Fixed
- 読みやすさ・安全性の改善
  - .env パースでのクォート・エスケープ・インラインコメント処理を改善し、より実用的な .env フォーマットをサポート。
  - process_priority / CPU affinity 設定で権限不足や未サポート環境時に明示的にログを出し処理を継続するように修正。

### Deprecated
- なし

### Removed
- なし

### Security
- 環境変数・トークンは Settings 経由で参照する設計とし、config_setup の .env ファイルに関する注意書きで Git 管理禁止を明記。

---

注記 / 既知の制限
- research/factor_research.py は一部実装が途中（ファイル末尾が途中で切れている）なので、ファクター計算の完全実装は今後の作業を要します。
- apply_sector_cap の price フォールバック（価格欠損時）については TODO コメントあり。将来的に前日終値等のフォールバックを導入予定です。
- .env の自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます（テスト等の用途向け）。
- PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL 等は値検証が入るため、不正値を設定すると起動時に例外を送出します。環境設定時は validate_config を実行してください。

もし CHANGELOG に追記してほしい具体的な差分や日付、あるいは過去のバージョン履歴があれば教えてください。必要に応じてリリースノートの粒度（詳細レベル）を調整します。