# チェンジログ

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」準拠です。  
（※ 本ファイルはコードベースの内容から推測して作成しています。）

## [Unreleased]

- ドキュメント・リリースノート用のプレースホルダ。次回リリースでここに記載の項目を移動します。

---

## [0.1.0] - 2026-04-18

初回公開リリース。主な追加・実装内容は以下のとおりです。

### Added
- コアアプリケーション
  - kabusys パッケージ初期実装。バージョンは `0.1.0` に設定。
- 実行ランナー / デーモン化関連
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを実装。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き対応（デフォルト 60 秒）。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止。
    - プロセス優先度を起動時に High に設定。
    - Monitoring 用 DB は環境に依らず本番の sqlite_path を使用する挙動を実装。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを実装。
    - KABUSYS_ENV に応じて paper_trading 用の専用 SQLite DB（data/paper_trading.db）を使用（本番 DB と分離）。
    - MockBrokerClient の利用（paper_trading 時）を想定したブローカーファクトリ呼び出しを組込。
    - PID/停止フラグ管理（data/execution.pid、stop flag）とスレッド管理。
    - 起動時にプロセス優先度を High に設定。
- 設定管理
  - config.py
    - .env の自動読み込み機構（プロジェクトルート自動検出、`.env` と `.env.local` の読み込み順、OS 環境変数保護）。
    - .env パース機能：`export KEY=...` 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、行内コメントルールに対応。
    - 環境変数の必須チェック（_require）。
    - 設定プロパティの豊富なラッパー（DB パス, PAPER_FILL_MODE 検証, PID/kill flag パス, リソース閾値, env/ログレベル判定など）。
    - 自動読み込みを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` フラグ。
- 設定ユーティリティ CLI
  - config_setup.py
    - 対話式ウィザードで `.env` を作成・更新するツールを実装。
    - 秘匿項目のマスク表示、選択肢・デフォルト提示、既存 .env 読込・再利用をサポート。
    - 最終確認後に `.env` を生成・保存するロジック。
  - validate_config.py
    - 起動前の設定検証 CLI を実装。
    - 必須環境変数のチェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース検証（PyYAML 有無で挙動分岐）、本番時の追加ガード（LINE 設定・KILL_FLAG_CLEAR_ON_START）を実施。
    - `--strict` オプションで警告も失敗扱いにできる。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio.portfolio_builder
    - 候補選定（スコア降順、タイブレーク処理）、等金額・スコア加重配分の実装。スコア合計 0 の場合は等分にフォールバック。
  - portfolio.risk_adjustment
    - セクター集中制限（apply_sector_cap）：既存保有と当日売却予定を考慮したセクター別エクスポージャー計算と候補フィルタリング。
    - レジーム乗数（calc_regime_multiplier）：レジームに応じた投下資金乗数（bull/neutral/bear）と未知レジームでのフォールバック。
  - portfolio.position_sizing
    - 複数の配分方式（risk_based / equal / score）に基づく株数計算。単元株（lot_size）丸め、1銘柄上限 / aggregate cap（available_cash）に応じたスケーリング、コストバッファ考慮、端数処理（残差に応じた追加配分）を実装。
- 研究用ファクターモジュール
  - research.factor_research
    - DuckDB から prices_daily を参照し、Momentum（1M/3M/6M、MA200乖離）、Volatility（ATR20、相対ATR）、流動性指標等を計算する機能を実装。対象日指定での抽出、データ不足時の None フォールバックを実装。
- ユーティリティ
  - utils.process_priority
    - Windows / POSIX の差分を吸収するプロセス優先度設定関数（set_process_priority）を実装。CPU affinity 設定関数（set_cpu_affinity）も提供。権限不足や未対応 OS でも安全にフォールバックして警告を出力。
- モニタリング DB / DuckDB
  - run_* スクリプトで sqlite3 と duckdb の両方へ接続する実装を追加（init_monitoring_db を呼んで監視用テーブルの存在を保証）。
- Paper Trading 検証レポートツール
  - tools.paper_verification_report
    - ペーパートレード用 SQLite を読み、システム稼働率・注文成功率・送信率・リスク却下数・レイテンシ（avg/max/P95）を集計して標準出力レポートを生成する CLI を実装。
    - P95 計算、閾値（稼働率/成功率/送信率/P95 レイテンシ）に基づく PASS/FAIL 判定を実装。CLI 引数で期間・DB パス指定可能。

### Changed
- 初回リリースのため該当なし（初期機能群の実装）。

### Fixed
- 設定パース / 安全性
  - .env パーサはクォート内のバックスラッシュエスケープや行末コメント処理などを正しく扱うよう実装（不正な行は無視）。
  - MONITOR_POLL_INTERVAL の値検証を追加し、0 以下や整数以外の場合にデフォルトへフォールバックして例外を回避。
  - calc_score_weights: 全銘柄のスコア合計が 0 の場合に等金額配分へフォールバック（警告ログ出力）。
  - calc_regime_multiplier: 未知のレジーム値に対して 1.0 でフォールバックし警告を出力。
  - init_monitoring_db 呼び出しは冪等で監視テーブル存在を保証（複数起動時の安全化）。
  - run_execution: 起動時に停止フラグが既に立っていれば起動を中止する安全措置を追加。
- エラー耐性
  - run_monitoring のループ内で monitor.check_once() が例外を投げてもループを継続し、ログ出力して次回ポーリングへ復帰するように変更。
  - process_priority, cpu_affinity 設定で権限エラー等が発生した場合は警告を出してスキップする実装。

### Security
- .env の生成スクリプトで注意書きを追加（.env を Git にコミットしない旨）。機密情報は `secret` 項目として対話でマスク表示。

---

過去のリリース履歴は本リポジトリの初期実装に基づくため、本 CHANGELOG では初回リリース（0.1.0）としてまとめています。将来の変更は Unreleased セクションに追加のうえ、リリース時にバージョンと日付を付与して移動してください。