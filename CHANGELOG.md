# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」を準拠しています。

最近のリリース
----------------

## [Unreleased]
- なし（新規リポジトリ／最初のリリース以降の未リリース変更はありません）

## [0.1.0] - 2026-04-18
最初の公開リリース。以下の主要機能・ユーティリティを含みます。

Added
- 基本アプリケーション情報
  - pakage metadata: kabusys/__init__.py に __version__ = "0.1.0" を追加。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプト。
    - KABUSYS_ENV に応じて paper_trading 用の専用 SQLite DB（data/paper_trading.db）を使用する挙動を実装。
    - BrokerClientFactory を介してブローカクライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - ストップフラグ（data/stop_requested.flag）検知により安全に停止可能。
    - 実行中の PID を data/execution.pid に記録する仕組み（pid_file パスの注入）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する（監視データの一元管理）。
    - 停止フラグファイル検知でループ終了、KeyboardInterrupt による終了処理をハンドル。

- 設定関連
  - config.py
    - Settings クラスを導入し、環境変数からアプリケーション設定を型安全に取得可能に。
    - .env 自動ロード機構（プロジェクトルート検出: .git または pyproject.toml を基準）を実装。OS の環境変数優先、.env.local による上書き対応。
    - 設定値検証とフォールバック（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。
    - データベースパス（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）関連プロパティを提供。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を実装。
    - シークレット入力対応（マスク表示）、既存 .env の読み込み、.env のテンプレートによる書き出しをサポート。
  - validate_config.py
    - 起動前の設定検証 CLI。必須環境変数、パス存在、YAML 設定ファイルの存在・パースチェック（PyYAML 未インストール時はスキップ警告）を実行。
    - --strict フラグにより警告を FAIL 扱いにできる。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 全起動スクリプトで共通利用するログ設定ユーティリティ。
    - stdout 出力の StreamHandler と 日次ローテーション（TimedRotatingFileHandler）を組み合わせる。ログディレクトリ自動作成と失敗時のフォールバック処理あり。
    - ログレベル解決（引数 > 環境変数 > デフォルト）。
  - utils/process_priority.py
    - プラットフォーム差分を吸収したプロセス優先度設定（set_process_priority）を提供。Windows/Linux/macOS に対応し、psutil の利用で AccessDenied 等を安全にハンドリング。
    - set_cpu_affinity による CPU ピンニング機能を提供（存在しない場合は安全にスキップ）。

- ポートフォリオ構築モジュール（純粋関数群、DB 非依存）
  - portfolio/portfolio_builder.py
    - 銘柄選定（select_candidates）、等分配（calc_equal_weights）、スコア加重（calc_score_weights）を実装。スコア全0 の場合は等分配にフォールバックして警告を出力。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限を実装（既存保有を考慮して新規候補を除外）。"unknown" セクターは上限対象外とする挙動。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知レジームは 1.0 でフォールバックし警告を出す。
  - portfolio/position_sizing.py
    - ポジションサイズ計算（risk_based / equal / score の allocation_method）を実装。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap（available_cash）に基づくスケーリング、cost_buffer を考慮した保守的見積り、残余キャッシュに基づく再配分ロジックを搭載。
  - portfolio/__init__.py で上記機能をエクスポート。

- 研究・指標計算（作業中）
  - research/factor_research.py
    - ファクター計算モジュールの骨子を追加（Momentum / Value / Volatility / Liquidity）。DuckDB 接続を受け prices_daily/raw_financials を参照する設計。モメンタム等の定数や関数スケルトンを実装（未完の部分あり）。

- ペーパートレード検証ツール
  - tools/paper_verification_report.py
    - ペーパートレーディング用 SQLite DB（PAPER_TRADING_SQLITE_PATH）からレポートを生成する CLI。
    - 稼働率、注文成功率（Fill Rate）、送信率（Send Rate）、レイテンシ（平均/最大/P95）やリスク却下数を集計し、PASS/FAIL 判定を出力する。
    - P95 算出、期間フィルタ (--from/--to) 対応、閾値を定義（デフォルト値あり）。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Security
- セキュリティ関連:
  - .env の生成時にシークレット項目をマスクし、.env を絶対に Git にコミットしない旨の注記を出力。

Notes / Implementation details
- DB 分離
  - 本番監視 DB（monitoring）は KABUSYS_ENV にかかわらず sqlite_path を使用し、監視データを本番 DB に集約する設計。一方、Execution の paper_trading モードでは paper_sqlite_path を用いて本番 DB と分離する。
- 設定自動ロード
  - 環境変数自動読み込みはデフォルトで有効。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定する。
- ロギング
  - StreamHandler は stdout を使用（cron 等で stdout/stderr を一本化する利用を想定）。
- エラーハンドリング
  - run_monitoring の監視ループや run_execution のスレッド監視などで例外を捕捉してログに残しつつフェイルセーフに待機・停止する実装。

今後の予定（例）
- research/factor_research.py の完全実装（各ファクター計算の SQL / パイプライン）
- ExecutionEngine / RiskManager / Broker の詳細実装のさらなるテストと文書化
- 単体テスト・CI の追加、型チェック強化
- ドキュメント（運用手順、デプロイ手順、監視アラート設定）の整備

----------------

参考: リリースフォーマットは Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠しています。