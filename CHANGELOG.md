# Changelog

すべての重要な変更点を記録します。本ファイルは Keep a Changelog の形式に準拠しています。慣例に従い、バージョンごとに「Added / Changed / Fixed / Security」などのセクションを設けています。

最新: [Unreleased] → 直近の開発中の変更はここに追記してください。

## [Unreleased]
- （空）

## [0.1.0] - 2026-04-18
初回公開リリース。基本的な自動売買フレームワークと運用ユーティリティを実装しました。

### Added
- コアパッケージとバージョン情報
  - src/kabusys/__init__.py にバージョン 0.1.0 を追加。

- 環境設定・読み込み
  - src/kabusys/config.py
    - .env 自動読み込み機能を実装（プロジェクトルート検出: .git / pyproject.toml を探索）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
    - 高度な .env パーサ実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントの取り扱い等に対応）。
    - Settings クラスを追加し、J-Quants / kabu API / DB パス /監視閾値等の設定取得用プロパティを提供。
    - PAPER_FILL_MODE のバリデーション、paper_trading 用 sqlite パス（PAPER_TRADING_SQLITE_PATH）などをサポート。

- 環境設定ウィザード CLI
  - src/kabusys/config_setup.py
    - 対話式で .env を生成・更新するウィザードを実装。
    - デフォルト値表示、シークレットマスク、選択肢サポート、生成テンプレートの出力をサポート。
    - .env を Git にコミットしない旨の注意書きを含むテンプレート出力機能。

- 設定検証 CLI
  - src/kabusys/validate_config.py
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在・パースチェック（PyYAML があれば中身も検証）を実装。
    - KABUSYS_ENV=live の場合の追加ガード（LINE 未設定や KILL_FLAG_CLEAR_ON_START の危険設定の警告）。
    - --strict オプションで警告を失敗扱いにできる。

- 起動スクリプト
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックしログ出力。
    - 監視は環境にかかわらず本番 sqlite_path を使用する（監視用 DB を本番と分離せず一貫して監視 DB を参照する設計）。
    - 停止フラグ（data/stop_requested.flag）を監視し、検知時にループを終了。
    - 監視用 DB 初期化 init_monitoring_db 呼び出し（冪等性を保つ）。

  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper 専用 SQLite（data/paper_trading.db など）を使用して本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成（paper_trading 時は MockBrokerClient を使用する想定）。
    - ExecutionEngine をスレッドで起動し、停止フラグ（data/stop_requested.flag）で安全に停止するロジック。
    - PID ファイル出力（data/execution.pid 指定可能）やモジュール依存コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler）を組み立てて起動。

- 監視・レポートツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 実行結果を解析して検証レポート（稼働率、注文成功率、送信率、P95 レイテンシ等）を生成する CLI を追加。
    - 日付フィルタ (--from / --to)、DB パス指定 (--db または PAPER_TRADING_SQLITE_PATH) をサポート。
    - PASS/FAIL 判定し、基準値はスクリプト内定義（稼働率 99%、注文成功率 90% など）。
    - P95 算出、NULL/データ欠如への耐性を実装。

- ポートフォリオ構築・リスク制御モジュール（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - select_candidates（スコア降順選出）、calc_equal_weights、calc_score_weights（スコアが全て 0.0 の場合は等配分へフォールバック）を実装。

  - src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap（セクター集中上限で候補除外）、calc_regime_multiplier（市場レジームに応じた投下資金乗数）を実装。
    - unknown セクターの扱い、フォールバックや警告ログを含む設計。

  - src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes（リスクベース、等配分、スコア配分に対応）。
    - 単元株（lot_size）丸め、max_position_pct、max_utilization、aggregate cap のスケーリング、cost_buffer を使った保守的見積り、残余キャッシュに対する再配分ロジックを実装。

  - src/kabusys/portfolio/__init__.py
    - 上記関数をエクスポートするパッケージインターフェースを提供。

- リサーチ / ファクター計算
  - src/kabusys/research/factor_research.py
    - DuckDB 接続を受け、prices_daily / raw_financials を参照して Momentum / Volatility / Liquidity / Value 等のファクター計算関数を実装（calc_momentum, calc_volatility 等）。
    - ウィンドウ計算に SQL ウィンドウ関数を活用し、データ不足時は None を返す堅牢な設計。
    - 定数（短中長の期間、ATR 期間など）を明示的に定義。

- プロセス優先度・CPU 固定ユーティリティ
  - src/kabusys/utils/process_priority.py
    - set_process_priority（high/normal/low）を実装。Windows / POSIX の差を吸収して扱えるように設計。
    - set_cpu_affinity（最初 N コアにピン留め）を実装。アクセス権限や未対応 OS 時のフォールバック処理あり。
    - psutil による例外（AccessDenied 等）を受けてログ警告してスキップする安全設計。

- その他
  - パッケージ空 __init__ や tools パッケージを追加（モジュール構成の整理）。

### Changed
- （初回リリースのため、変更履歴はなし）

### Fixed
- 監視／実行起動時の DB 初期化やエラー取り扱いを堅牢化
  - init_monitoring_db の呼び出しを追加し、監視テーブルが存在することを保証（冪等）。
  - run_monitoring の monitor.check_once() で例外発生時にループを継続するように例外捕捉を追加。
  - CLI / スクリプトの起動時にリソースが正しくクローズされるよう finally ブロックで sqlite/duckdb 接続を確実に close。

### Security
- 環境変数に関する注意点
  - .env を Git にコミットしない旨をテンプレートに明記（config_setup.py）。
  - 必須の機密情報（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は Settings で未設定時に例外を投げることで起動前に検出。

### Notes / Design decisions
- Paper Trading と本番 DB 分離
  - 実行エンジンは KABUSYS_ENV に応じて paper_trading 用 DB を使用し、本番 DB と記録を分離する設計を採用。
  - 監視（run_monitoring）は環境にかかわらず監視用 sqlite_path（デフォルト data/monitoring.db）を使用する仕様。

- 塩梅（フォールバック）方針
  - 環境変数の不正値やデータ欠如に対してはログ出力で警告し、安全なデフォルトや None を返す方針を基本としています（例: MONITOR_POLL_INTERVAL, PAPER_FILL_MODE, ファクター計算の不足データ）。

- 将来の拡張点（コード内 TODO）
  - 銘柄ごとの単元株情報をマスタに持たせる（position_sizing）。
  - price 欠損時のフォールバック（前日終値や取得原価）やより詳細なコスト見積り。

---

作業履歴のソースは src/ 以下の各モジュールから推測して記載しました。実際のリリースノートでは追加の変更・バグ修正・マイグレーション手順がある場合は随時追記してください。