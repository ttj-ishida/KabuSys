CHANGELOG
=========

すべての重要な変更はこのファイルで管理します。  
フォーマットは "Keep a Changelog" に準拠します。

Unreleased
----------

- なし

[0.1.0] - 2026-04-17
--------------------

Added
- 実行エントリ / ランナーを追加
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。プロセス優先度を高に設定し、stop_requested.flag による安全停止、SQLite / DuckDB 接続の初期化、check_once() 実行時の例外ハンドリングを実装。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 専用 DB を使用し MockBrokerClient を利用（本番 DB と完全分離）。プロセス優先度設定、PID ファイル対応、バックグラウンドスレッドでの実行と停止フラグ検知による安全停止を実装。

- 設定 / 環境読み込み周りを追加・強化（src/kabusys/config.py）
  - .env 自動読み込み機能を追加（プロジェクトルートを .git または pyproject.toml から検出）。.env と .env.local の優先順位をサポートし、OS 環境変数の上書きを制御。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - .env の行パーサを強化（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの扱いを正しく処理）。
  - Settings クラスを提供し、各種環境変数（J-Quants、kabuAPI、LINE、DuckDB/SQLite パス、Paper trading 設定、監視閾値、ログレベル等）へのアクセスと妥当性検証を統一的に実装。
  - PAPER_FILL_MODE のバリデーションと PAPER_TRADING_SQLITE_PATH のサポートを追加。

- 設定検証 CLI を追加（src/kabusys/validate_config.py）
  - .env と config/*.yaml の初期検証ツールを追加。必須環境変数の未設定検出、プレースホルダ値の警告、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、PyYAML がある場合は YAML パース検証を実施。
  - KABUSYS_ENV=live 向けの追加ガード（LINE 通知設定や Kill Switch の設定確認）。
  - --strict オプションで警告を FAIL 扱いにできる。

- 環境設定ウィザードを追加（src/kabusys/config_setup.py）
  - 対話式ウィザードで .env の初期作成・更新を支援。入力時にシークレットをマスク、選択肢・デフォルト対応、有効な項目一覧を提供し .env をテンプレート形式で書き出す機能を提供。

- Paper Trading 検証レポートツールを追加（src/kabusys/tools/paper_verification_report.py）
  - paper_trading 用 SQLite DB を解析して稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計し PASS/FAIL 判定する CLI を実装。しきい値はスクリプト内定義（稼働率 99% 等）。--from/--to/--db オプションをサポート。

- ポートフォリオ構築・サイズ算出関係を追加（src/kabusys/portfolio/*）
  - portfolio_builder: 候補選定（スコア順）、等配分・スコア加重配分を提供。スコア合計が 0 の場合は等配分にフォールバックして警告を出力。
  - risk_adjustment: セクター集中制限（apply_sector_cap）、マーケットレジームに応じた投下資金乗数（calc_regime_multiplier）を実装。未知レジームのフォールバック挙動やログ出力を追加。
  - position_sizing: allocation_method（risk_based / equal / score）に基づく発注株数算出ロジックを実装。損切り率・リスク許容率を用いる risk_based、単元株（lot_size）での丸め、コストバッファの考慮、aggregate cap によるスケーリングと残差処理（lot 単位での追加配分）を実装。

- プロセス優先度・CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）
  - Windows / POSIX 間の差分を吸収する set_process_priority を実装（psutil を利用。許可不足時は警告でスキップ）。
  - set_cpu_affinity で最初の N コアに固定する機能を追加。無効な引数時の検証を実装。

- リサーチ用ファクタ計算モジュールを追加（src/kabusys/research/factor_research.py）
  - DuckDB 接続を受け取り、Momentum（1M/3M/6M リターン、MA200 乖離）やボラティリティ（ATR 等）を計算する関数を実装。データ不足時の None 返却やスキャン期間の取り扱いを考慮。

Changed
- パッケージ初期バージョンを 0.1.0 に設定（src/kabusys/__init__.py）。
- run_monitoring / run_execution の設計上の挙動を明確化（例: 監視は常に本番 sqlite_path を使用、paper_trading は専用 DB を使用して本番と分離）。

Fixed
- なし（初期リリースのため主に追加が中心）。

Security
- .env を生成するテンプレートに注意事項を追加（.env を絶対に Git にコミットしない旨の警告を明記）。

Notes / Implementation details
- stop フラグ・PID ファイルを用いたプロセス制御を導入し、手動での停止や外部オーケストレーションに対応可能にしています。
- .env のパース/ロードは既存の OS 環境変数を保護しつつ、.env.local による上書きもサポートします。
- Paper trading 実行は本番 DB と完全に分離されるよう設計されており、テスト／検証実行時に誤って本番を汚染しない配慮があります。
- position_sizing の aggregate スケーリングは小数端数を lot_size 単位で処理し、再現性ある残差配分アルゴリズムを採用しています。

Authors
- 初回実装: KabuSys 開発チーム

----