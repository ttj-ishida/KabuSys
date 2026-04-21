# Changelog

すべての変更は Keep a Changelog の規約に従って記載しています。  
このファイルは、リポジトリ内のコードから推測できる機能追加・設計意図・既知の注意点をまとめたものです。

フォーマット:
- Unreleased: 今後の変更（現状は空）
- 各リリースは日付を付与（推定日時）

## [Unreleased]

## [0.1.0] - 2026-04-21

### Added
- 基本パッケージ初期実装（KabuSys v0.1.0）
  - パッケージメタ情報: `__version__ = "0.1.0"`。

- 実行用エントリスクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI 相当のスクリプトを追加。
    - KABUSYS_ENV に応じて paper_trading 用 DB と本番 DB を分離して使用する仕組みをサポート（`PAPER_TRADING_SQLITE_PATH` / `settings.is_paper`）。
    - BrokerClientFactory によるブローカークライアント生成を想定。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて Engine を起動。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）による安全な起動・停止制御。
    - スレッドで Engine セッションを実行し、停止フラグ検知で安全に停止するループを実装。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視 DB は環境にかかわらず本番用 sqlite_path を使用する（監視は常に本番 DB を参照する設計）。
    - 停止フラグ検知でループを終了し、例外時はログ出力のうえ次回ループを継続。

- 設定・環境ロード
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルート検出: `.git` または `pyproject.toml` 基準）。
    - 読み込み優先順位: OS 環境 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
    - .env パーサを実装（コメント行、export プレフィックス、クォート内のエスケープやインラインコメントの扱いに対応）。
    - Settings クラスを実装し、各種設定値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス, PAPER_FILL_MODE, KABUSYS_ENV 等）をプロパティで提供。バリデーションを行う（無効値時は例外）。
    - Paper Trading 用 DB パス・fill モード等の明示的プロパティを追加。

- 設定支援 CLI
  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加。
    - 秘匿項目はマスク表示、デフォルト値や選択肢を提示して入力を簡便化。
    - 書き込み処理は .env を人手で編集する代替として安全に利用可能。

  - validate_config.py
    - 起動前の設定検証 CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV の妥当性、LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在・パース検査（PyYAML がインストールされている場合）を行う。
    - `--strict` オプションで警告も FAIL 扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30 日保持）を設定する共通ユーティリティを実装。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル解決順: 引数 > 環境変数 `LOG_LEVEL` > デフォルト "INFO"。

  - utils/process_priority.py
    - プロセス優先度（"high" / "normal" / "low"）を OS に依存しない API で設定する関数を実装（psutil を使用）。
    - Windows／POSIX (Linux, macOS, FreeBSD) に対応する nice / priority 値のマッピングを行い、失敗時は警告でスキップ。
    - CPU affinity を最初の N コアに固定するユーティリティも提供（設定失敗時は警告でスキップ）。

- ポートフォリオ構築ライブラリ（純粋関数群、DB 非依存）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - スコアが全て 0 の場合は等金額にフォールバックして警告。

  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（既存ポジションのセクター比率が閾値を超える場合の新規候補除外）を実装。
    - レジームに応じた投資乗数 calc_regime_multiplier を実装（bull/neutral/bear のマップ、未知レジームは警告のうえ 1.0 フォールバック）。

  - portfolio/position_sizing.py
    - 発注株数決定ロジックを実装（allocation_method: "risk_based" / "equal" / "score" をサポート）。
    - 単元株（lot_size）丸め、1 銘柄上限・ポートフォリオ総投下上限の考慮、コストバッファを考慮したスケーリング・端数処理（残余キャッシュで残差順に lot 単位追加）等を実装。
    - price 欠損時はスキップや警告を出す設計。将来的な価格フォールバックについて TODO コメントあり。

- 監視関連・DB 初期化
  - run スクリプト内で監視用 DB 初期化関数 init_monitoring_db を呼び出し、監視テーブルの存在を保障する設計（冪等処理）。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading の SQLite DB から稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、API レイテンシ（平均、最大、P95）等の指標を集計してレポートを生成するツールを追加。
    - デフォルトの DB パスは `data/paper_trading.db`。`--db` オプションまたは環境変数 `PAPER_TRADING_SQLITE_PATH` で上書き可。
    - Pass/Fail 判定の閾値（稼働率 99%、fill rate 90%、send rate 95%、P95 レイテンシ 200 ms）を定義して判定を出力。
    - 日付フィルタ（--from / --to）をサポート。

- リサーチ / ファクター計算（スケルトン）
  - research/factor_research.py
    - DuckDB を利用したファクター計算モジュールの骨組みを追加（モメンタム、移動平均乖離、ATR、流動性等の設計詳細をコメントで記載）。
    - 関数インターフェースや定数が定義され、DuckDB 接続を受けて prices_daily / raw_financials テーブルを参照する設計。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 環境変数やシークレットは .env を使用する設計。`.env` は絶対に Git にコミットしないよう README/ウィザードで注意喚起。

---

注意事項・既知の設計上のポイント（コードコメントに基づく推測）
- run_monitoring は MONITOR_POLL_INTERVAL に 0 以下が設定されると time.sleep の ValueError を回避するためデフォルトにフォールバックする旨の処理がある。
- Settings.paper_fill_mode は厳密な列挙（instant / partial / never / reject）を想定しており、不正値は ValueError を発生させる。
- process_priority / set_cpu_affinity は権限不足や未対応環境で失敗する可能性があり、その場合はログ警告で安全にスキップする設計。
- position_sizing や apply_sector_cap ではデータ欠損（price=0 等）による過少見積りのリスクについて注記があり、将来的にはフォールバック価格取得の拡張が想定されている。
- config の .env パーサはクォート・エスケープやインラインコメントの扱いまで対応しているため、複雑な .env の記述にも堅牢に対応することを意図している。
- config_setup のウィザードは既存 .env を読み込んで Enter で再利用できる（秘密値はマスク表示）。

もし特定のコミットや変更点（例: バグ修正、機能追加）をより詳細に分割したい場合は、該当する差分（ファイル / 行）を教えてください。提供コードからさらに細かいリリースノート（例: 各関数の小修正や TODO）を反映して更新します。