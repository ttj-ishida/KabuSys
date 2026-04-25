# Changelog

すべての注目すべき変更は Keep a Changelog 準拠で記載しています。  
各項目はコードベース（src/kabusys 以下）の実装内容から推測してまとめたものです。

全般
- 本リリースはソース内の実装内容を元に作成した初期リリース相当の変更履歴です（パッケージ版の __version__ は 0.1.0）。
- 日付はこの CHANGELOG 作成時点を使用しています。

## [Unreleased]

## [0.1.0] - 2026-04-25

### Added
- 実行エントリ／運用スクリプトを追加
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。KABUSYS_ENV が `paper_trading` の場合は専用の paper-trading 用 SQLite（データ分離）を使用し、MockBrokerClient が選択される設計。停止フラグ（data/stop_requested.flag）と PID ファイルの取り扱いを実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。環境変数 `MONITOR_POLL_INTERVAL` による間隔上書き（不正値はデフォルト 60 秒にフォールバック）。Monitoring は環境にかかわらず本番 sqlite_path を使用する点を明示。

- 設定・環境読み込み周り
  - config.py: Settings クラスを導入して環境変数をラップ。必須環境変数チェック（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）と各種パス・フラグ・閾値等をプロパティとして提供。`KABUSYS_ENV` / `LOG_LEVEL` / `PAPER_FILL_MODE` のバリデーションを実装。
  - 自動 .env ロード機構: プロジェクトルート (.git または pyproject.toml を基準) を探索して `.env` / `.env.local` を読み込み。OS 環境変数を保護して上書き順序を制御。

- 設定支援ツール
  - config_setup.py: 対話式ウィザードで .env を初期作成・更新する CLI を追加。項目定義、既存値の読み込み、シークレットマスク、保存前の確認などを実装。
  - validate_config.py: 起動前に環境変数や config/*.yaml の存在・簡易パースを検証する CLI を追加。`--strict` オプションで警告を失敗扱いにできる。PyYAML 未インストール時のスキップ挙動や、本番（live）向け追加チェックを実装。

- 監視／メトリクス
  - monitoring 側初期化を idempotent に行うための init_monitoring_db 呼び出しを各起動処理に追加（監視テーブルの存在保証）。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。console (stdout) と TimedRotatingFileHandler（日次ローテーション、30 日保持）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップする保護を実装。
  - utils/process_priority.py: クロスプラットフォームでプロセス優先度（high/normal/low）と CPU affinity 固定を設定するユーティリティを追加。Windows と POSIX の差分を吸収し、失敗時は警告を出して継続。

- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（score に基づくソート）と等重/スコア重み付け関数を追加。スコア全 0 の場合は等配分にフォールバックする警告を実装。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を追加。未知レジーム時のフォールバックとログ出力を実装。
  - portfolio/position_sizing.py: position sizing ロジックを追加。risk_based / equal / score の allocation_method に対応し、単元株（lot_size）丸め、per-position/aggregate cap、cost_buffer を使った保守的なコスト見積り、scale-down（残余を fractional remainder に従って配分）を実装。

- 研究・分析
  - research/factor_research.py: DuckDB を用いるファクター計算の基礎を追加（モメンタム等）。（ファイルは途中まで実装されているが、設計・定数・docstring が整備されている）

- ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシ等を集計し PASS/FAIL を判定する CLI。データベースの存在チェック、期間フィルタ、P95 計算、閾値による判定を実装。

### Changed
- .env パーサーの堅牢化（config._parse_env_line）
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメント処理、クォートなし時のコメント解釈ルールなどを明確化。
  - .env 読み込み時に OS 環境変数を保護する protected 機構を導入（.env.local の override 挙動を制御）。

- ロギング設定のデフォルト挙動
  - コンソール出力は stderr ではなく stdout を使用（cron/task scheduler でのリダイレクト運用を考慮）。
  - 既存ハンドラを一旦 flush/close してから再設定することで二重ハンドラ登録を防止。

- Process priority / affinity の挙動明確化
  - サポート対象 OS の判定と、設定失敗時の警告ログを追加。移植性を考慮した実装に変更。

### Fixed
- 環境変数値の不正対策
  - MONITOR_POLL_INTERVAL が不正（数値でない、0 以下など）な場合に警告してデフォルト（60 秒）にフォールバックする実装を追加（run_monitoring）。
  - PAPER_FILL_MODE の許容値チェックを実装し、不正値では ValueError を送出するようにした（Settings.paper_fill_mode）。
  - Settings.env / log_level の不正値検出で早期にエラーを出すように改善。

- DB 初期化／接続の堅牢化
  - 起動スクリプトで init_monitoring_db を呼ぶことで監視用テーブルが存在しない場合でも起動時に整備される（冪等化）。

- run_execution の停止制御
  - 停止フラグ検知時に ExecutionEngine を安全に停止するループを追加。スレッドのデーモン起動とタイムアウト付き join を組み合わせた終了処理を実装。

### Documentation / Misc
- 各モジュールに詳細な docstring / 使用例を追加。CLI の usage や設定項目の説明、設計上の注意（例: portfolio の純粋関数設計、レジーム乗数の意図）を明記。
- パッケージ __init__.py にバージョン（0.1.0）と主要サブパッケージのエクスポート一覧を追加。

### Known limitations / Notes
- research/factor_research.py はモメンタム等の関数が実装途中である（ファイル末尾が切れているため、完全な実装は今後の作業が必要）。
- position_sizing の price 欠損時（price が 0.0 の場合）の取扱に注釈（TODO）あり。将来的に価格フォールバックを導入する予定。
- logging_setup はログディレクトリ作成失敗時にファイル出力を無効化する挙動だが、その事象の運用上の扱い（権限不足など）は運用手順に追記推奨。

---

（補足）この CHANGELOG は提示されたソースコードの内容から推測して作成したものです。実際のリリースノートではコミット単位の差分やテスト結果、既知のバグ修正の詳細を併記してください。