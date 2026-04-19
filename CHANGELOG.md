Changelog
=========
すべての重要な変更は Keep a Changelog の仕様に準拠して記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------
（なし）

0.1.0 - 2026-04-19
-----------------
初回公開リリース。

Added
- 基本アプリケーション構成
  - パッケージのバージョンを `__version__ = "0.1.0"` として追加。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル data/stop_requested.flag を監視して安全に停止。
    - monitoring 用 DB は環境に依らず本番 sqlite_path を使用する設計。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を用い、paper_trading 用の専用 SQLite（data/paper_trading.db）に記録して本番 DB と分離。
    - 停止フラグ・PID ファイルの取り扱いとスレッド実行管理を実装。

- 設定関連ユーティリティ
  - config.py
    - .env 自動読み込み機能を追加（プロジェクトルート自動検出: .git または pyproject.toml を基準）。
    - .env のパース機能を強化（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱いなど）。
    - 各種設定プロパティを提供（J-Quants / kabu API / DB パス / ログ設定 / 監視閾値 / 環境判定プロパティ等）。
    - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - config_setup.py
    - 対話式 .env 設定ウィザードを追加（.env の初期作成・更新支援）。
    - 必須・任意項目、シークレット入力、選択肢のサポート、保存前の確認表示などを実装。
  - validate_config.py
    - 起動前に .env と config/*.yaml を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリチェック、YAML ファイルの存在/パースチェック、本番環境用ガードチェックなどを実装。
    - --strict オプションで警告をエラー扱いにするモードを提供。

- ロギング / プロセス設定ユーティリティ
  - utils/logging_setup.py
    - ルートロガーを統一的に設定するユーティリティを追加。
    - コンソール出力は stdout、ファイル出力は日次ローテーション（TimedRotatingFileHandler）で 30 日保管。
    - LOG_DIR 作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定を追加。
    - CPU affinity 設定機能を提供（指定コア数にプロセスを固定）。
    - 権限不足や非対応プラットフォームで安全にフォールバックする実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定（スコア降順）、等金額配分、スコア加重配分を実装。
    - スコアが全て 0 の場合は等金額配分へフォールバック（警告ログ）。
  - portfolio/risk_adjustment.py
    - セクター集中制限の適用（apply_sector_cap）。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数算出ロジックを実装（risk_based / equal / score）。
    - 単元株丸め、1銘柄上限、利用可能現金に基づく aggregate cap（スケーリング）、cost_buffer の取り扱い。
    - lot_size や手数料・スリッページの簡易考慮をサポート。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポートを生成する CLI を追加。
    - system_status / trade_logs / risk_logs テーブルから稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）などを集計。
    - PASS/FAIL 用の閾値（稼働率、成功率、送信率、P95 レイテンシ）を定義し判定を出力。
    - --from/--to/--db オプションで期間・DB を指定可能。

- DuckDB / SQLite の併用
  - 多くのコンポーネントで SQLite（監視・注文履歴）と DuckDB（分析・リサーチ）を併用する設計を採用。
  - 起動スクリプトで init_monitoring_db を呼び出し、監視用テーブル存在を保証する（冪等）。

- リサーチ（部分実装）
  - research/factor_research.py
    - モメンタム等のファクター計算を行うための基盤を追加（DuckDB 接続を受けて prices_daily / raw_financials を参照して計算）。
    - 定数や関数スケルトン（calc_momentum 等）を追加。実装は継続（ファイル末尾で未完の箇所あり）。

Changed
- ログ設定の挙動
  - logging_setup.setup_logging で既存ハンドラを一旦クローズ／削除してから再設定するようにし、二重ハンドラ設定を防止。

Fixed
- 起動時の安全性・堅牢性向上
  - run_monitoring / run_execution 起動時にプロセス優先度を最初に設定するよう変更し、実行環境での優先度を確保。
  - DB 接続後に監視テーブルが存在することを保証する init_monitoring_db 呼び出しを導入。
  - run_execution で停止フラグが既に立っている場合に起動を中止するガードを追加。

Deprecated
- なし

Removed
- なし

Security
- なし（セキュリティ関係の明示的修正は含まれません）

Notes / 注意事項
- config.py の Settings は必須環境変数未設定時に ValueError を投げます。起動前に validate_config を実行して設定を確認することを推奨します。
- .env 自動読み込みはデフォルトで有効です。テスト等で自動読み込みを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- research/factor_research.py は部分的に未完の実装が含まれています。ファクター計算を利用する前に該当モジュールの残り実装を確認してください。

Acknowledgements
- 本リリースは以下の主要機能の追加により自動売買／検証フローの基盤を構築しました:
  - 起動スクリプト（監視・実行）
  - 設定管理・ウィザード・検証ツール
  - ロギング・プロセス制御ユーティリティ
  - ポートフォリオ構築ロジック
  - Paper Trading 用検証レポート生成

---