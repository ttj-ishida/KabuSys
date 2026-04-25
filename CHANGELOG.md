# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに従います。  
このプロジェクトはまだ初期リリースの段階です。コードベースから推測して主な追加点・仕様を記載しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-04-25
### Added
- 基本アーキテクチャとコアユーティリティを実装（初期リリース）。
  - src/kabusys/__init__.py にパッケージ定義とバージョン情報を追加（__version__ = "0.1.0"）。
- 環境設定・管理
  - .env 自動読み込み機能を実装（.env, .env.local）。環境変数の保護（OS 環境変数を上書きしない）を考慮。
  - 詳細な .env パーサを実装。`export KEY=val`、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント（スペース前の `#` を考慮）に対応。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - Settings クラスを実装し、アプリケーションで利用する各種設定値（J-Quants トークン、kabu API パスワード、DB パス、ログレベル、環境切替など）をプロパティとして提供。
  - PAPER_FILL_MODE（paper trading のモック約定挙動）の検証ロジックを追加（有効値: "instant" / "partial" / "never" / "reject"）。
  - Paper Trading 用の専用 SQLite パス設定（PAPER_TRADING_SQLITE_PATH）をサポート。
- CLI ツール
  - 環境設定ウィザード（config_setup）を追加。対話式で .env を作成・更新する機能を提供（.env の読み書きロジック、マスク表示、デフォルト/選択肢対応）。
  - 設定検証ツール（validate_config）を追加。必須環境変数やファイルパス、config/*.yaml の存在・パース（PyYAML がある場合）などを検証。--strict モードで警告を失敗扱いにできる。
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report）を追加。稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）等を計算して PASS/FAIL 判定を出力。期間フィルタと DB パス指定をサポート。
- 実行ランタイム（起動スクリプト）
  - run_execution: ExecutionEngine 起動用スクリプトを追加。
    - プロセス優先度を High に設定して起動。
    - KABUSYS_ENV が paper_trading の場合は paper_trading 用 DB を使用し、MockBrokerClient を利用する想定（BrokerClientFactory 経由）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで実行。data/stop_requested.flag による停止フラグ処理を実装。
    - エンジン起動前に監視テーブル存在を保証するため init_monitoring_db を呼ぶ。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告ログを出力。
    - 監視は常に本番用 sqlite_path を参照して DB を初期化（init_monitoring_db）。
    - duckdb 接続を利用して分析データ格納先へ接続。
    - data/stop_requested.flag による停止フラグ検出、KeyboardInterrupt のハンドリング、例外発生時のロギングと継続処理を実装。
- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py を追加。ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション）を設定。ログレベルとログディレクトリの解決順を定義し、既存ハンドラの重複登録を防止する。
  - utils/process_priority.py を追加。Windows（HIGH_PRIORITY_CLASS 等）と POSIX 系の nice 値を吸収してプロセス優先度を設定するユーティリティを提供。CPU affinity 設定用の set_cpu_affinity も実装。権限不足や未対応 OS の場合は警告を出してスキップする安全設計。
- ポートフォリオ構築関連モジュール（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順かつ signal_rank でタイブレークして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分を実装（スコア全て 0 の場合は等額配分へフォールバックし WARNING）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター別エクスポージャーを計算し、既存保有が所定比率を超えるセクターの新規候補を除外するロジック（unknown セクターは制限対象外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数を返す（"bull"=1.0, "neutral"=0.7, "bear"=0.3）。未知レジームは 1.0 へフォールバックして警告を出力。
  - portfolio/position_sizing.py
    - calc_position_sizes: 複数の配分方式（"risk_based", "equal", "score"）に対応した発注株数計算。lot_size（単元）丸め、1銘柄上限（max_position_pct）、aggregate cap（available_cash）に基づくスケーリング、cost_buffer を用いた保守的見積りなどを実装。価格欠損時はスキップする堅牢な実装。
- リサーチ（部分実装）
  - research/factor_research.py を追加。DuckDB の prices_daily / raw_financials を用いたファクター計算（Momentum, Value, Volatility, Liquidity）を想定。モメンタム関数のインターフェースが定義され、長期 MA やリターン算出ロジックの定数がセットされている（実装は継続）。
- DB / 分析基盤
  - DuckDB 接続を分析用 DB として利用（duckdb.connect を利用）。
  - SQLite を監視・発注履歴用 DB として利用。Paper Trading 用 DB と本番 DB を分離。
- 監視 DB 初期化ユーティリティ
  - monitoring.monitoring_db.init_monitoring_db を各起動スクリプトから呼び出し、監視テーブル存在を冪等的に保証。

### Changed
- なし（初期リリースとしての追加中心の記述）。

### Fixed
- なし（初期リリースとしての記述）。

### Security
- なし（現時点で明示的なセキュリティ修正は無し）。

注記（実装上の注意・既知の設計判断）
- run_execution/run_monitoring は起動時にプロセス優先度を High に設定しようとするため、権限不足により設定が失敗するケースがある。失敗時は警告出力して続行する設計。
- .env 自動読み込みはプロジェクトルート検出に依存（.git または pyproject.toml）。配布後や CWD が異なる環境でも動作するように設計されているが、ルートが特定できない場合は自動ロードをスキップする。
- apply_sector_cap のエクスポージャー計算では price_map の欠損（0.0）をそのまま扱うため過少評価される可能性がある旨を TODO コメントで残している（将来的なフォールバック価格導入を検討）。
- research/factor_research.py はファクター計算の設計を定義しているが、一部実装が未完（ファイル末尾で実装途中でトランケートされている）。必要に応じて完成が必要。

今後の予定（推測）
- factor_research の完成（モメンタム/ボラティリティ等の計算実装）。
- ExecutionEngine / Broker 周りの詳細実装（実際の API クライアントの具象化、モックの詳細）。
- 追加の監視・アラート送信（LINE 通知等）の統合実装。

--------- 

この CHANGELOG はコードベースの内容から推測して作成しています。必要があれば、実際のコミット履歴やリリースノートに合わせて調整してください。