# CHANGELOG

すべての重要な変更点は Keep a Changelog の方針に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-19

初回リリース。KabuSys のコア機能群を追加しました。主な追加点は以下の通りです。

### 追加 (Added)
- CLI / 起動スクリプト
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止用フラグファイル（data/stop_requested.flag）を検知して安全に終了。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合はペーパートレード用 DB（data/paper_trading.db）を使用し MockBrokerClient 経由で完全に分離して動作。
- 設定・環境変数管理
  - config.py: Settings クラスを実装。.env /.env.local の自動ロード（プロジェクトルート自動検出）、必須変数チェック用の _require、各種パスやフラグのプロパティを提供。
    - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等の値検証を実装。
  - config_setup.py: 対話式ウィザードで .env を作成・更新する CLI を追加。入力中止の扱いやシークレットマスク表示、書き込みテンプレートを提供。
  - validate_config.py: .env と config/*.yaml の起動前検証ツールを追加。--strict オプションで警告も失敗扱いにできる。PyYAML が無ければ YAML 検証をスキップして警告を出力。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一ロギング設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次, 30 世代保持）をルートロガーに設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続。
  - utils/process_priority.py: クロスプラットフォーム（Windows / POSIX）でプロセス優先度と CPU affinity の設定関数を追加。psutil を使い、権限不足や未対応環境では警告を出してフォールバック。
- ポートフォリオ構築ライブラリ（純粋関数）
  - portfolio/portfolio_builder.py: シグナル選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）を実装。スコアが全てゼロの場合に等配分へフォールバック。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジーム乗数（calc_regime_multiplier）を実装。未知レジームは警告を出してフォールバック。
  - portfolio/position_sizing.py: 複数の配分方式（risk_based, equal, score）に対応した株数決定ロジックを実装。単元株（lot_size）丸め、銘柄・合計の上限（max_position_pct、max_utilization）、cost_buffer を考慮したスケーリングと残差配分アルゴリズムを備える。
  - portfolio/__init__.py: 上記関数群をエクスポート。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計して検証レポートを出力するスクリプトを追加。閾値（稼働率99%、成功率90% 等）に基づく PASS/FAIL 判定を実装。
- 研究用ファクター計算（下流での価格テーブル参照を前提）
  - research/factor_research.py: Momentum / Value / Volatility / Liquidity といったファクター計算基盤を追加（DuckDB 接続を受けて prices_daily / raw_financials を参照して計算する設計）。（モジュールはファイル内で計算パラメータやスキャン範囲等を定義）
- DB / 分析基盤
  - DuckDB を分析 DB として統合（duckdb_path を Settings で管理）。monitoring 用 SQLite（sqlite_path）と併用。monitoring 初期化関数（init_monitoring_db）を起動時に呼び出して監視テーブルの存在を保証。
- 実行時安全機構
  - PID ファイル / stop flag / kill flag の取り扱いを導入（Settings の pid_file_path / kill_flag_path / KILL_FLAG_CLEAR_ON_START）。ExecutionEngine は停止フラグを検知してセッション停止を行う。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- .env パーサーの堅牢化
  - config._parse_env_line: export プレフィックス、シングル／ダブルクォートのエスケープ処理、行内コメント処理、空白トリムなどをサポートし、より現実的な .env の記述に耐えるように改善。
  - .env の自動ロードは OS 環境変数を保護（protected）しつつ .env.local で上書き可能にした。
- ロギング周りのフォールバック挙動を実装
  - ログディレクトリ作成が失敗した場合はファイルハンドラの追加をスキップし、コンソール出力のみで継続。既存ハンドラの二重追加を防ぐためハンドラ再設定時に既存ハンドラをクリア。

### セキュリティ (Security)
- config_setup の対話画面と出力テンプレートでシークレット値はマスク表示（****）され、.env ファイル作成時にユーザーが明示的に保存確認を行うようにした。必須環境変数が未設定の場合は validate_config でエラー通知。

### 注意事項 / 既知の制限 (Known issues)
- research/factor_research.py は DuckDB の prices_daily / raw_financials テーブルを前提とした実装設計（外部データ取得機構は含まれない）。
- 単元株（lot_size）は現状グローバル定数扱い（将来的には銘柄マスタで個別指定する設計を想定）。
- process_priority や CPU affinity の設定は権限不足やプラットフォーム差分により失敗することがある（その場合はログ警告を出してスキップ）。
- YAML 検証には PyYAML が必要。インストールされていない場合はファイル存在チェックのみ行いパースはスキップ（警告が出る）。

---

リリース以降の変更やバグ修正は本 CHANGELOG に逐次追記していきます。ご要望や問題報告は Issue を作成してください。