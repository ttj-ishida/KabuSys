# Changelog

すべての重要な変更点はこのファイルに記載します。  
フォーマットは "Keep a Changelog" に準拠しています。  

参考: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-04-18
初期リリース。

### Added
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。環境変数 KABUSYS_ENV により paper_trading 時は MockBrokerClient を使用し、Paper Trading 用の SQLite（data/paper_trading.db、環境変数で上書き可）と分離して動作する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。停止はプロジェクト直下の data/stop_requested.flag によって制御。
- 設定管理
  - config.py: .env 自動読み込み機能（.env, .env.local、OS 環境変数優先）と Settings クラスを追加。各種環境変数の取得・検証ロジック（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE、SQLite/DuckDB パスなど）を実装。
  - config_setup.py: 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加。秘密情報のマスク表示やデフォルト値サポートを実装。
  - validate_config.py: 起動前の設定整合性を検証する CLI を追加。必須環境変数の存在確認、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在および YAML パースチェック（PyYAML 未インストール時はスキップ）を実装。--strict オプションで警告をエラー扱いにできる。
- ポートフォリオ構築（純粋関数群、DB 参照なし）
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を追加。スコア全てが 0 の場合は等配分にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py: セクター集中制限を適用する apply_sector_cap と、市場レジームに応じた資金乗数 calc_regime_multiplier を追加。未知のレジームはフォールバックで 1.0 を返し警告を出す。
  - portfolio/position_sizing.py: 発注株数決定ロジック calc_position_sizes を追加。risk_based / equal / score の複数配分方式をサポートし、単元株（lot_size）丸め・個別上限・aggregate cap（利用可能現金との調整）・cost_buffer（スリッページ等の保守的見積り）に対応。
  - portfolio/__init__.py: 上記モジュールをまとめて公開。
- 監視・分析関連
  - monitoring 用 DB 初期化の呼び出し（init_monitoring_db）を run_execution/run_monitoring に組み込み、冪等に監視テーブルが存在することを保証。
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成ツールを追加。稼働率・注文成功率・送信率・P95 レイテンシ等を集計し PASS/FAIL 判定を行う。--from/--to/--db オプションをサポート。P95 計算、閾値（稼働率 99% 等）をデフォルト実装。
- ユーティリティ
  - utils/logging_setup.py: ルートロガーの一括設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日保持）を設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップする安全策を実装。LOG_LEVEL / LOG_DIR の解決順をサポート。
  - utils/process_priority.py: psutil を利用したプロセス優先度設定と CPU affinity 設定ユーティリティを追加。Windows / POSIX（Linux/Mac/FreeBSD）を吸収する実装。権限不足など失敗時は警告を出して続行。
- パッケージ化
  - __init__.py に __version__ = "0.1.0" を設定。

### Changed
- （該当なし — 初期リリースのため存在しない既存挙動の変更はありません）

### Fixed / Robustness
- .env パーサー（config._parse_env_line）を強化し、以下に対応:
  - export KEY=val 形式のサポート
  - シングル/ダブルクォート内のバックスラッシュエスケープ処理
  - インラインコメントの扱い（クォートあり/なしでの正しい認識）
  - 空行・コメント行の無視
- .env 読み込み（config._load_env_file）で OS 環境変数を保護する protected パラメータを導入し、.env.local の上書き時にも OS 環境を保護する挙動を実装。
- run_monitoring のポーリング間隔取得ロジックで不正値に対するフォールバック（デフォルト 60 秒）とログ警告を追加。0 以下や非整数入力を安全に扱う。
- run_execution/run_monitoring: 起動直後にプロセス優先度を設定するようにし、失敗してもログ警告を出して続行する安全挙動を実装。
- calc_score_weights: 全スコア合計が 0 の場合に等配分へフォールバックし、ログで警告するようにした。
- calc_regime_multiplier: 未知のレジームで警告を出しフォールバック値を返すようにした。
- logging_setup: 既存ハンドラを再設定する際に flush/close を試みハンドラの二重登録を防止する処理を追加。
- Paper Trading レポート: DB が存在しない場合のエラーメッセージと、テーブル欠落（OperationalError）を受けても部分的にレポートを生成する耐障害処理を追加。

### Security
- .env 生成ウィザードの出力時に「.env を絶対に Git にコミットしないこと」を明示。

### Notes
- run_monitoring は KABUSYS_ENV にかかわらず production 用 sqlite_path（Settings.sqlite_path）を使用して監視データを扱います（監視データは本番 DB を想定）。
- Paper Trading 環境では実売買と完全分離された SQLite（paper_sqlite_path）を使用する設計になっています。
- 一部の機能（YAML 検証など）は外部ライブラリ（PyYAML）の有無に依存し、未インストール時は該当検証をスキップします。

---

生成された変更履歴は、ソースコードから推測した主要な追加・改善点をまとめたものです。必要であれば、より細かいファイルレベルの差分やコミットメッセージ風の項目を追加できます。