# CHANGELOG

すべての重要な変更を記録します。本ファイルは「Keep a Changelog」ガイドラインに準拠しています。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-23
初回リリース。プロジェクトのコア機能と運用用ユーティリティを実装。

### Added
- 実行エントリスクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。スレッドでエンジンを実行し、停止フラグ検知で安全に停止する。
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading SQLite データベース (data/paper_trading.db または PAPER_TRADING_SQLITE_PATH) を使用し、本番 DB と分離。
    - PID ファイル管理（data/execution.pid）と停止フラグ (data/stop_requested.flag) に対応。
    - BrokerClientFactory を利用してブローカクライアントを注入。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine に注入。
    - 起動時にプロセス優先度を "high" に設定。

  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV に関わらず本番用 sqlite_path を参照して初期化（監視テーブルの冪等初期化）。
    - 停止フラグ (data/stop_requested.flag) によりループを終了。
    - duckdb 接続の初期化をサポート。

- 設定管理
  - config.py
    - .env 自動読み込み機構を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env / .env.local の読み込み順序と上書き保護（OS 環境変数保護）に対応。
    - 複雑な .env 行のパース（export プレフィックス、クォート内のエスケープ、インラインコメント扱い等）を実装。
    - Settings クラスを提供し、アプリ全体で環境変数に対する型付きプロパティアクセスを可能に。
    - データベースパス、Paper Trading 用設定、監視の閾値やファイルパス、ログレベルなど多数のプロパティを定義。
    - KABUSYS_ENV、LOG_LEVEL 等のバリデーションを実装。

- 設定ヘルパー CLI
  - config_setup.py
    - 対話式ウィザードで .env ファイルを作成・更新するツールを追加。
    - 項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE 関連, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START 等）を含む。
    - 既存 .env の読み込み・マスク表示・確認・保存まで対応。

  - validate_config.py
    - 起動前に環境変数や config/*.yaml の不備を検出する検証ツールを追加。
    - --strict オプションで警告を FAIL 扱いにできる。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、パス存在確認（親ディレクトリチェック）、YAML パース（PyYAML 利用可）および本番環境向けの追加ガードを実装。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - 銘柄候補選定（スコア降順、同点は signal_rank タイブレーク）。
    - 等配分（calc_equal_weights）およびスコア加重（calc_score_weights）。全スコア 0 の場合は等配分にフォールバックして警告ログを出力。

  - portfolio/risk_adjustment.py
    - セクター集中上限の適用（apply_sector_cap）。既存保有のセクター露出を計算し、上限を超えるセクターの新規候補を除外。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装（bull/neutral/bear をサポート、未知値はフォールバックして警告）。

  - portfolio/position_sizing.py
    - 発注株数計算ロジック（risk_based / equal / score）を実装。
    - 単元株（lot_size）で丸め、1銘柄上限（max_position_pct）、総投下上限（max_utilization）を考慮。
    - aggregate cap 超過時のスケーリングと、余剰キャッシュに対する端数処理（残差順に lot 単位で再配分）を実装。
    - cost_buffer による保守的コスト見積りをサポート。

  - portfolio/__init__.py にエクスポートを追加。

- 運用ユーティリティ
  - utils/logging_setup.py
    - ルートロガーの初期化ユーティリティを追加。stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を組み合わせて設定。
    - ログレベル / ログディレクトリの解決順を実装（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで動作。

  - utils/process_priority.py
    - Windows / POSIX 間の差分を吸収するプロセス優先度設定を実装（high/normal/low）。
    - CPU affinity を固定する set_cpu_affinity を提供（指定なしなら何もしない）。
    - 権限不足や未実装の環境では警告を出してスキップ。

- 研究・分析
  - research/factor_research.py
    - DuckDB 接続を受け取り、Momentum / Value / Volatility / Liquidity 等のファクター計算を行う設計を追加（関数 calc_momentum の素地を実装）。（注: ファイル末尾は未完の可能性あり）

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを追加。
    - 稼働率、注文成功率（fill rate）、送信率（send rate）、レイテンシ（avg/max/P95）などを集計して PASS/FAIL 判定を行う。
    - P95 計算、日付フィルタ（--from / --to）、DB パス解決ロジック（--db / 環境変数 / デフォルト）をサポート。
    - デフォルト閾値を定義（稼働率 99.0%、fill rate 90%、send rate 95%、P95 200 ms）。

- パッケージ情報
  - __init__.py に __version__ = "0.1.0" を追加。

### Changed
- なし（初回リリースのため既存変更なし）

### Fixed
- なし（初回リリース）

### Removed
- なし

### Notes / Limitations
- research/factor_research.py は計算ロジックの大枠を実装しているが、ファイル末尾が未完に見える箇所がある（今後の実装継続予定）。
- 一部のコンポーネント（ExecutionEngine, SystemMonitor, BrokerClientFactory, OrderRepository など）は本変更ログ対象のコードで参照されているが、本差分では実装の詳細は含まれていない（別モジュールとして存在する前提）。
- process_priority の動作は OS 権限に依存するため、権限不足時は設定がスキップされる。
- .env 自動ロードはプロジェクトルートが検出できない場合はスキップされる（パッケージ配布後の安全策）。

--- 

今後の予定（例）
- factor_research の完成、ファクター統合と正規化ユーティリティの追加
- ExecutionEngine / Broker のテスト用モック強化と e2e テスト
- 運用監視・アラート（LINE 通知）の設定強化とリスクガードの追加