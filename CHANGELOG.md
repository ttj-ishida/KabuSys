# CHANGELOG

すべての注目すべき変更を記録します。フォーマットは Keep a Changelog に準拠しています。

配布バージョンの指標は `src/kabusys/__init__.py` の `__version__` に合わせています。

## [0.1.0] - 2026-04-17

### Added
- 基本リリース: KabuSys 初期実装を追加。
  - パッケージメタ情報: バージョン 0.1.0 を設定。
- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。スレッドでエンジンを起動し、stop フラグを検知して安全に停止可能。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の専用 SQLite DB（デフォルト: data/paper_trading.db）を使用し、実際の本番 DB と分離する仕組みを実装（Mock ブローカー使用を想定）。
    - 起動直後にプロセス優先度を "high" に設定する処理を組み込み。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。監視ループのポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用の sqlite_path を使用する仕様を明示。
    - 停止はプロジェクトの data/stop_requested.flag ファイルで制御。
- 設定管理・ユーティリティ
  - config.py
    - .env 自動読み込み機能（プロジェクトルートの .env/.env.local）を実装。OS 環境変数を保護する仕組みや自動ロード無効化用フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を提供。
    - .env の行パーサーは `export KEY=val` 形式、クォートされた値（エスケープ考慮）、インラインコメント処理などに対応。
    - 各種設定値へのアクセス用 `Settings` クラスを提供（DB パス、API トークン、監視しきい値、環境判定など）。
  - config_setup.py
    - 対話式 .env 作成/更新ウィザードを提供。デフォルト値、選択肢、シークレットのマスク表示、最終確認とファイル書き込み機能を実装。
  - validate_config.py
    - 起動前の設定検証 CLI を追加。必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証などを実施。`--strict` オプションで警告をエラー扱いにできる。
- 監視・レポート
  - monitoring 周りの初期化を idempotent に行う `init_monitoring_db` を呼び出すフローを run_monitoring/run_execution に追加（監視テーブルがない場合に作成）。
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを追加。システム稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計して PASS/FAIL を判定する。
    - P95 計算、日付フィルタ、DB 存在チェックなどを実装。閾値はソース内で定義（稼働率 99%、注文成功率 90% など）。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（スコア降順 + タイブレーク）、等金額配分、スコア加重配分（全スコア 0 の場合は等金額へフォールバック）を実装。
  - portfolio/risk_adjustment.py
    - セクター集中上限チェック（既存保有を考慮して新規候補を除外）と、マーケットレジームに応じた投下資金乗数計算（bull/neutral/bear）を実装。未知レジームは警告とともにフォールバック。
  - portfolio/position_sizing.py
    - 複数の配分方式（risk_based / equal / score）に基づく株数計算を実装。単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash を超える場合はスケールダウン）や cost_buffer による保守的見積り、残差処理アルゴリズムを実装。
- ユーティリティ
  - utils/process_priority.py
    - プロセス優先度（Windows: HIGH_PRIORITY_CLASS 等、POSIX: nice 値）設定ユーティリティを追加。未対応 OS や権限不足時には安全にスキップして警告を出力。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity 関数を提供（権限やプラットフォーム対応を考慮）。
- 研究用ファクター計算
  - research/factor_research.py
    - DuckDB を用いたファクター計算モジュール（モメンタム: 1m/3m/6m リターン、MA200 乖離、ボラティリティ: ATR、流動性指標等）の骨組みを追加。データ不足時の扱いや SQL の実装方針を含む。

### Changed
- DB 初期化の扱い
  - monitoring テーブル初期化（init_monitoring_db）処理を起動フローに組み込み、監視/実行スクリプトが起動前にテーブル存在を保証するようにした（冪等処理）。
- 環境設定の読み込み順
  - 自動ロード順を OS 環境変数 > .env.local > .env として、.env.local が .env を上書きする仕様を明記。
- run_monitoring の振る舞い
  - 環境変数 `MONITOR_POLL_INTERVAL` のパースと検証を追加（1 未満や非整数はデフォルトにフォールバックして警告を出力）。
  - 停止フラグファイルの存在チェックでループを抜け、接続を確実にクローズするように変更。
- run_execution の振る舞い
  - 起動時に stop フラグが既に存在する場合は起動を中止する安全ガードを追加。バックグラウンドスレッド実行中も stop フラグ検出でエンジンを停止するロジックを追加。
  - RiskManager の初期設定において、`initial_portfolio_value` を broker.get_available_cash() から取得して注入するように変更（ブローカー実装に依存）。
- .env パーサー強化
  - export プレフィックス対応、クォートされた値のバックスラッシュエスケープ対応、インラインコメントの取り扱い改善、空行/コメント行無視などを実装。
  - .env 読込関数に override/protected の仕組みを導入（OS 環境変数保護のため）。

### Fixed
- 例外ハンドリングの堅牢化
  - run_monitoring の polling loop 内で monitor.check_once() が例外を投げた場合でもループ継続して次回ポーリングまで待機するように捕捉し、スタックトレースをログに出力するようにした。
  - DuckDB/SQLite のクエリ系ツール（paper_verification_report 等）でテーブルが存在しない場合に起動失敗しないように OperationalError を捕捉してデフォルト値でレポート作成するようにした。
- プラットフォーム互換性
  - process_priority のモジュールロード時に Windows 固有定数に安全にフォールバックするようにして、モジュールインポートが非 POSIX 環境で失敗しないように修正。

### Security
- .env ファイルについて
  - config_setup にて生成される .env の先頭に「.env を絶対に Git にコミットしないこと」を明記。対話ウィザードで機密値はマスク表示するようにして、ユーザーに注意を促す。

### Documentation / Developer UX
- config_setup と validate_config の CLI を追加して、初期セットアップと起動前チェックをユーザーが簡単に実行できるようにした。
- 各モジュールにドキュメンテーション文字列（docstring）を充実させ、設計思想や重要な注意点（例: レジームの扱い、price 欠損時の挙動など）を明記。

### Known limitations / Notes
- portfolio/position_sizing の単元株処理は現状すべての銘柄で共通 lot_size を想定しており、銘柄別 lot_size を扱う拡張は TODO として残している。
- risk_adjustment.apply_sector_cap は sector_map に存在しない銘柄を "unknown" 扱いとして上限を適用しない仕様であり、price が欠損（0.0）の場合にエクスポージャーが過小評価される可能性がある。将来的にフォールバック価格の導入を検討している。
- research/factor_research.py は主要ロジック（momentum, volatility 等）を実装しているが、DuckDB 上のテーブル構造やデータの前処理が正しく行われていることが前提。

---

過去のリリース履歴はこの時点ではありません（初回リリース）。今後の変更は Unreleased セクションに順次記載していきます。