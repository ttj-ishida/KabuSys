Keep a Changelog
=================

すべての重要な変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

記載方針:
- 変更はコードベースから推測して記載しています。
- リリース日はソースコード取得時点の日付 (2026-04-19) を使用しています。

Unreleased
----------
（今後の変更点をここに記載してください）

0.1.0 - 2026-04-19
-----------------

Added
- 初期リリースとして以下の主要コンポーネントを追加。
  - 実行・監視ランチャー
    - run_execution.py: ExecutionEngine を起動するエントリポイント。KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 用 DB（data/paper_trading.db）と分離して動作する。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する設計。
  - 設定管理 / CLI
    - config.py: .env 自動読み込み（.env, .env.local）と保護付き上書きロジック、プロジェクトルート検出、各種環境変数アクセスを提供する Settings クラスを実装。PAPER_FILL_MODE の検証や KABUSYS_ENV / LOG_LEVEL のバリデーションを含む。
    - config_setup.py: 対話式の .env ウィザード（生成・更新）。既存 .env 読み込み、シークレットのマスク表示、保存用テンプレートを実装。
    - validate_config.py: 起動前の設定検証 CLI。必須環境変数、KABUSYS_ENV の妥当性、YAML ファイルの存在/パース、データベースパスの親ディレクトリ存在チェックなどを行う。--strict オプションで警告も失敗扱いにできる。
  - ロギング・プロセス制御ユーティリティ
    - utils/logging_setup.py: StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を用いた統一ログ設定。既存ハンドラをクリアして重複設定を防止。LOG_DIR/LOG_LEVEL の解決順を実装し、ファイル出力不可時は標準出力のみでフォールバック。
    - utils/process_priority.py: Windows / POSIX（Linux/Mac/FreeBSD）差分を吸収したプロセス優先度設定と CPU affinity 設定ユーティリティ。権限不足時は警告でスキップする安全設計。
  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py: 候補選定・等金額・スコア加重の重み計算（フォールバック挙動を含む）。
    - portfolio/position_sizing.py: 株数決定ロジック（risk_based / equal / score）、単元株（lot_size）丸め、aggregate cap によるスケーリングと残差分配アルゴリズムを実装。
    - portfolio/risk_adjustment.py: セクター集中制限の適用（unknown セクターは除外しない）、市場レジームに基づく投下資金乗数（bull/neutral/bear）と未知レジームでのフォールバック。
    - portfolio/__init__.py: 上記 API をエクスポート。
  - Execution 関連（スケルトン）
    - execution/*: BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager などの呼び口を組み立て、ExecutionEngine をスレッドで起動/停止するランチャー実装。
      - RiskManager 初期設定（デフォルト値）を run_execution 側で構築し、broker.get_available_cash() を initial_portfolio_value に使用。
      - 起動時に stop フラグが立っていれば起動せず終了する安全処理を実装。
  - 監視関連
    - monitoring/*: init_monitoring_db の呼び出し（冪等に監視テーブルを保証）、SystemMonitor の一回チェック呼出しとエラー隔離（例外発生時はログに例外を出し次回まで待機）。
    - run_monitoring はプロセス優先度を高く設定してから監視ループを開始。
  - ツール
    - tools/paper_verification_report.py: ペーパートレード DB を解析して検証レポートを生成する CLI。稼働率、注文成功率、送信率、P95 レイテンシなどを計算して PASS/FAIL を判定する。P95 計算、日付フィルタ、DB 存在チェックを実装。
  - 研究用モジュール（一部）
    - research/factor_research.py: DuckDB を用いたファクター計算（モメンタム等）を想定した実装の骨子。計算窓、定数、出力形式の仕様を定義（実装途中までのコード含む）。
  - パッケージ初期化
    - __init__.py: パッケージバージョン (__version__ = "0.1.0") を追加。

Changed
- ログ出力のデフォルトを stdout に統一（StreamHandler を stdout に設定）。ファイル出力はログディレクトリ作成が成功した場合のみ有効。
- .env パーサーの強化（config.py）
  - export KEY=val 形式への対応。
  - シングル/ダブルクォート内のバックスラッシュエスケープ処理。
  - クォートなしの値におけるインラインコメント（#）処理の改善。
- .env 自動ロードの挙動
  - OS 環境変数は保護され、.env.local の override=True でも OS 環境変数を上書きしないように設計。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
- run_monitoring のポーリング間隔の環境変数 MONITOR_POLL_INTERVAL の検証を追加。0 以下や不正な値はデフォルト（60 秒）へフォールバックして警告を出力。
- run_execution/run_monitoring 共通でプロセス優先度を起動直後に設定するよう変更（set_process_priority("high") を最初に呼び出す）。
- monitoring DB 初期化（init_monitoring_db）を冪等に呼ぶことでスキーマ準備を保証。

Fixed
- 環境変数未設定時の扱いを厳密化
  - Settings._require で必須変数未設定時に ValueError を投げるようにし、validate_config により起動前検出が可能。
- ExecutionEngine の起動/停止フローを安全化
  - 起動前に停止フラグ検査を行い、既に停止フラグが立っている場合は起動せず終了する。
  - 実行中に停止フラグが立ったら engine.stop() を呼んで安全に停止するように実装。
- process_priority と CPU affinity の権限不足や未対応 OS への耐性向上（例外をキャッチして警告を出す）。
- position_sizing の aggregate cap スケーリングで残差処理を改善（lot_size 単位での繰り上げ配分／再現性のため安定ソートを適用）。

Security
- .env ファイルに関する注意喚起を config_setup のテンプレートに明記（.env を絶対に Git にコミットしないこと）。

Notes / Implementation details
- Paper Trading と実運用 DB は分離される設計（Settings.paper_sqlite_path と Settings.sqlite_path を使い分け）。
- monitoring は設計上、環境にかかわらず本番 sqlite_path を参照する（監視データの一元管理を想定）。
- 一部のモジュール（research/factor_research.py）は計算ロジックの骨子が含まれているが、完全実装は継続作業が必要（コード断片が途中で終わっている箇所あり）。
- DuckDB と SQLite の二重接続を多くの実行パスで確立しており、処理終了時に両コネクションを確実にクローズする実装になっている。
- ログのローテーションは daily（midnight）、バックアップ数 30 日で設定。

今後の課題（推奨）
- research/factor_research の完全実装（ファクター計算の SQL/検証）。
- ExecutionEngine / BrokerClient のユニットテスト整備（MockBroker の挙動検証）。
- position_sizing の価格欠損時のフォールバック（TODO コメントあり）。
- 運用時の監視アラート送信（LINE 通知の実装と本番用設定の確認）。

--- 
（補足）この CHANGELOG は提供されたソースコードの内容から推測して作成しています。実際の変更履歴やリリースノートと差分がある場合は、本ファイルを適宜調整してください。