CHANGELOG
=========

すべての注目すべき変更点をここに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

Unreleased
----------

（なし）

[0.1.0] - 2026-04-20
-------------------

Added
- 初回リリース。KabuSys 自動売買基盤のコア機能を追加。
- 実行エントリ・スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 用に分離された SQLite DB（デフォルト: data/paper_trading.db）を利用する。
    - 起動時にプロセス優先度を "high" に設定する処理を組み込み（utils.process_priority）。
    - 停止制御用 stop flag（data/stop_requested.flag）と execution.pid による PID 管理をサポート。
    - ExecutionEngine を別スレッドで起動し、停止フラグ検出で安全に停止するループを実装。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。  
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視処理は環境に関係なく本番用 sqlite_path を使用して動作（監視 DB の一貫性を担保）。
    - 停止フラグ（data/stop_requested.flag）検出でループを終了、KeyboardInterrupt にも対応。
- 設定管理
  - config.py: 環境変数および .env ファイルの自動読み込み・ラッピングを実装。  
    - プロジェクトルート（.git または pyproject.toml を基準）を自動検出して .env/.env.local を読み込む（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - 必須値チェック用の _require()、各種設定プロパティ（DB パス、PID/kill flag、Paper Trading 関連など）を提供。
    - PAPER_FILL_MODE の妥当性チェック（"instant"|"partial"|"never"|"reject"）を実装。
- 設定関連 CLI
  - config_setup.py: 対話式 .env 作成ウィザードを追加。既存 .env の読み込み・編集、秘密値のマスク表示、保存確認をサポート。
  - validate_config.py: 設定検証 CLI を追加。必須環境変数・KABUSYS_ENV・ログレベル・DB パス・config/*.yaml の存在や YAML パース（PyYAML がある場合）を検証する。--strict オプションで警告をエラー扱いにできる。
- ロギング・ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定ユーティリティを追加。  
    - stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler）を組み合わせて設定する。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続するフォールバック実装。
    - LOG_LEVEL / LOG_DIR / app_name による柔軟な設定。
- プロセス優先度ユーティリティ
  - utils/process_priority.py: Windows / POSIX の差分を吸収してプロセス優先度設定（および CPU affinity 設定）を簡易化するユーティリティを追加。psutil の例外を捕捉して安全にフォールバックする。
- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）・等金額配分（calc_equal_weights）・スコア加重配分（calc_score_weights）を実装。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を実装。未知レジームでのフォールバック動作やログ出力を含む。
  - portfolio/position_sizing.py: 株数決定ロジック（risk_based, equal, score の各方式）、単元株丸め、aggregate cap によるスケールダウンと残差処理（lot 単位での再配分）を実装。
  - portfolio/__init__.py: 上記関数をパブリック API としてエクスポート。
- 解析・検証ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成ツールを追加。  
    - system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）等を算出し、閾値（稼働率 99% 等）に基づき PASS/FAIL 判定を出力。
    - 日付フィルタ（--from / --to）、DB パス上書き（--db）をサポート。
- 研究用ファクターモジュール（途中実装）
  - research/factor_research.py: DuckDB を用いたファクター計算のための骨子を追加。モメンタム / MA / ATR / 出来高等の指標算出を想定（実装は継続）。
- パッケージ情報
  - __init__.py にて __version__ = "0.1.0" を設定。

Changed
- 初版のため該当なし（初回追加のみ）。

Fixed
- 初版のため該当なし。

Security
- 機密値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, LINE のトークン等）は .env に保存し .git へコミットしないよう README と .env 作成スクリプトで注意喚起を行う設計。

Notes / Behavior Highlights
- 監視（monitoring）は環境（KABUSYS_ENV）に依存せず本番用 sqlite_path を参照する設計。監視データの分離に注意が必要。
- Paper Trading は発注挙動を本番と分離するよう設計されており、paper_trading 用 DB を利用して動作検証できる。
- ログディレクトリ作成や psutil による優先度設定が失敗しても、プロセスは起動を継続するよう安全にフォールバックする実装になっている。
- 一部モジュール（research/factor_research.py）は実装が途中のため、今後の強化予定。

Acknowledgements
- 本 CHANGELOG はリポジトリ内のソースコードからの推測に基づき作成しています。実際のリリースノートやプロジェクト方針に応じて適宜修正してください。