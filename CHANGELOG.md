CHANGELOG
=========

すべての注目すべき変更をこのファイルに記録します。
このファイルは "Keep a Changelog" の形式に準拠しています。

フォーマットのルール:
- すべての変更はカテゴリー別に整理（Added / Changed / Fixed / …）
- バージョンは Semantic Versioning 準拠を想定

Unreleased
----------
（現在の開発中の変更はここに記載してください）

0.1.0 - 2026-04-20
-----------------

Added
- 基本パッケージ／初期実装を追加
  - package メタ情報: __version__ = "0.1.0"
  - パッケージエクスポート設定（kabusys.__all__）

- 環境設定・管理
  - Settings クラスを実装して環境変数を集約（kabusys.config）
    - J-Quants / kabuステーション / LINE / DB パス /監視閾値 等のプロパティを提供
    - env（KABUSYS_ENV）/ LOG_LEVEL 等の値検証を内蔵
    - paper_trading 用 DB パス（PAPER_TRADING_SQLITE_PATH）と paper_fill_mode（PAPER_FILL_MODE）の検証
  - .env 自動読み込み機能を実装
    - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を読み込み
    - OS 環境変数は保護（上書き不可）し、.env.local は上書きモードで読み込む
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化

- 対話式セットアップ・検証ツール
  - config_setup CLI を追加（kabusys.config_setup）
    - 対話式ウィザードで .env の初期作成・更新を支援
    - シークレット項目はマスク表示、デフォルトや既存値の再利用に対応
  - validate_config CLI を追加（kabusys.validate_config）
    - 必須環境変数・KABUSYS_ENV/LOG_LEVEL の検証、DB パスや config/*.yaml の存在チェック
    - --strict モードで警告も FAIL 扱いにできる

- 実行系 / 監視系ランナー
  - run_execution スクリプトを追加（kabusys.run_execution）
    - ExecutionEngine の起動フロー実装（プロセス優先度設定 → DB 接続 → コンポーネント組立 → エンジン実行）
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB を使用して本番 DB と分離
    - BrokerClientFactory によるブローカークライアント生成（モック/実ブローカー切替）
    - 停止フラグ（data/stop_requested.flag）と PID ファイルの取り扱い、スレッド安全な停止
  - run_monitoring スクリプトを追加（kabusys.run_monitoring）
    - SystemMonitor のポーリングループ実装（デフォルト 60 秒、MONITOR_POLL_INTERVAL で上書き可）
    - 環境に関係なく監視は本番 sqlite_path を使用して監視テーブルを一元管理
    - 例外保護・停止フラグの検知により安全にループを抜ける

- ロギング・プロセス管理ユーティリティ
  - setup_logging を追加（kabusys.utils.logging_setup）
    - stdout への StreamHandler と 日次ローテーションする TimedRotatingFileHandler（30日分保持）をルートロガーに設定
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続
    - LOG_DIR / LOG_LEVEL の解決順を定義
  - process_priority ユーティリティを追加（kabusys.utils.process_priority）
    - Windows / POSIX の差分を吸収してプロセス優先度を設定
    - CPU affinity 設定関数 set_cpu_affinity を提供
    - 権限不足等の例外は警告ログに留めて処理継続

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates（スコア降順で上位 N を選択）
    - calc_equal_weights / calc_score_weights（スコア加重。全スコアが0の場合は等配分にフォールバック）
  - portfolio.risk_adjustment
    - apply_sector_cap（セクター集中を抑制する候補フィルタ）
    - calc_regime_multiplier（市場レジームに応じた投下資金乗数）
  - portfolio.position_sizing
    - calc_position_sizes（risk_based / equal / score の割当方式をサポート、単元株丸め、aggregate cap スケーリング、cost_buffer 考慮）

- リサーチ / ファクター計算（骨組み）
  - research.factor_research にモメンタム等ファクター計算の枠組みを実装（DuckDB 接続前提）
    - モメンタム期間定義や ATR /出来高指標などの定数を定義
    - （calc_momentum の実装開始。以降の計算ロジックが含まれる想定）

- 付帯ツール
  - tools.paper_verification_report を追加
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）からレポートを生成
    - 稼働率、注文成功率（fill/send）、リスク却下数、API レイテンシ（avg/max/P95）を集計
    - 合格基準（稼働率 99% 等）を定義して PASS/FAIL 判定を出力

- DB 初期化
  - init_monitoring_db を参照するコードを複数スクリプトから呼び出し、監視テーブルの冪等初期化を保証

Changed
- .env 読み込みの堅牢化
  - export KEY=val 形式、クォート（シングル・ダブル）、バックスラッシュエスケープ、行内コメント取り扱い等に対応
  - .env.local を上書きモードで読み込みつつ OS 環境変数を保護する実装により CI/環境差を取り扱いやすくした

- ログ出力の標準化
  - 全起動スクリプトで setup_logging を呼ぶことでログフォーマット・回転・出力先が統一

- 実行/監視の挙動修正
  - run_monitoring は監視 DB に常に本番 sqlite_path を使う仕様に（監視データは環境に依存させない）
  - run_execution は paper_trading で専用 DB を使用することで本番と完全分離

Fixed
- 環境変数パース周りの不正入力に対する堅牢性向上（無効行のスキップや警告出力）
- ログディレクトリ作成失敗時にファイルハンドラ生成が原因でアプリ全体が落ちる問題を回避（標準出力のみで継続）

Notes / Implementation details
- 多くのコンポーネント（ExecutionEngine, SystemMonitor, BrokerClientFactory, OrderManager, Reconciler, RiskManager など）はこのリリースで起動フローや依存注入の枠組みを提供しており、個別の振る舞い（発注ロジック、ブローカー具体実装、モニタリングの詳細判定等）はそれぞれのモジュール実装に依存します。
- DuckDB / SQLite の接続は起動スクリプトで適切に閉じられるよう finally ブロックで対処しています。
- ログは stdout とファイルの両方に出力され、ログディレクトリ作成に失敗した場合はファイル出力をスキップして継続します。
- process_priority や set_cpu_affinity の呼び出しは権限不足や未サポート環境でも安全にフォールバックします（警告ログで通知）。

Breaking Changes
- なし（初期リリースのため互換性破壊事項は該当しません）

Deprecated
- なし

Removed
- なし

Acknowledgements
- 本 CHANGELOG はソースコードの実装内容から推測して作成しています。実際のリリースノートにする場合は追加の意図・実装差分・テスト結果などを反映してください。