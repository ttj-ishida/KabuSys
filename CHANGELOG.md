CHANGELOG
=========

All notable changes to this project will be documented in this file.

The format is based on "Keep a Changelog" and this project adheres to Semantic Versioning.

[Unreleased]
------------

- （現状なし）

[0.1.0] - 2026-04-25
-------------------

Added
- 基本的なパッケージ構成と初期機能を実装（初回リリース）。
- 環境設定 / 設定管理
  - .env ファイルの自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。
  - 複雑な .env 構文をパース（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱い等）。
  - 環境変数の必須チェックを行う Settings クラスを実装。多数の設定プロパティを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE など）。
  - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject）と PAPER_TRADING_SQLITE_PATH の切替を実装。

- 設定ツール / 検証
  - 対話式設定ウィザード (kabusys.config_setup.run_wizard / python -m kabusys.config_setup) を実装。.env の生成・更新を支援。
  - 設定検証 CLI (kabusys.validate_config / python -m kabusys.validate_config) を実装。必須環境変数、KABUSYS_ENV 値、ログレベル、DB パス、config/*.yaml の存在・パース（PyYAML が使える場合）や本番環境向けガードをチェック。--strict オプションで警告を FAIL 扱いにできる。

- 実行・監視用エントリポイント
  - 実行エンジン起動スクリプト (run_execution.py)
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db）を使用し、本番 DB と完全に分離。
    - ブローカークライアントを BrokerClientFactory 経由で生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止制御: data/stop_requested.flag と data/execution.pid を用いた起動停止ロジック（スレッドで実行、停止フラグ検知で安全停止）。
  - 監視ループ起動スクリプト (run_monitoring.py)
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下や不正値はデフォルトにフォールバック）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する（monitoring データは本番 DB を想定）。
    - 停止フラグ（data/stop_requested.flag）でループを終了。check_once() 中の例外はログに残して次ポーリングへ継続。

- ロギング / プロセス制御ユーティリティ
  - 統一ロギングセットアップ (kabusys.utils.logging_setup.setup_logging)
    - stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップし stdout のみで継続。ローテーションは 30 日分保持。
    - ログレベル、ログディレクトリは引数 > 環境変数 > デフォルト の優先順位で解決。
  - プロセス優先度 / CPU affinity ユーティリティ (kabusys.utils.process_priority)
    - Windows と POSIX 系を吸収し、"high" / "normal" / "low" レベルでカレントプロセスの優先度を設定。psutil の権限問題や未対応 OS は警告を出してスキップ。
    - CPU affinity を最初の N コアに固定する関数も提供。権限や環境で失敗した場合は警告を出す。

- ポートフォリオ構築ライブラリ (kabusys.portfolio)
  - 候補選定: select_candidates — スコア降順、同点時は signal_rank をタイブレーク。上位 N を返す。
  - 重み計算: calc_equal_weights / calc_score_weights — スコア合計が 0 の場合は等配分へフォールバック（警告ログ）。
  - セクター集中制限: apply_sector_cap — 既存保有のセクター別エクスポージャーを計算し、上限を超えるセクターの新規候補を除外。"unknown" セクターは上限適用対象外。
  - レジーム乗数: calc_regime_multiplier — "bull"/"neutral"/"bear" に対してそれぞれ 1.0/0.7/0.3 を返す。未知レジームは警告を出して 1.0 にフォールバック。
  - ポジションサイズ決定: calc_position_sizes
    - allocation_method: "risk_based" / "equal" / "score" をサポート。
    - risk_based: 許容リスク率（risk_pct）と stop_loss_pct を使って基準株数を算出し単元（lot_size）丸め。
    - equal/score: weight に基づいて株数を算出。1 銘柄上限（max_position_pct）、aggregate 上限（available_cash, max_utilization）、cost_buffer（スリッページ等の保守見積り）を考慮。
    - aggregate cap を超える場合はスケーリングと端数処理（lot 単位での優先配分）を行う。
    - 価格欠損や price<=0 の場合はログにてスキップ。

- リサーチ / ファクター計算（骨子実装）
  - kabusys.research.factor_research: Momentum / MA / ATR / Volume 系ファクター計算の設計を実装。DuckDB 接続を受け取り prices_daily / raw_financials を参照して処理する設計（注: ファイル末尾で未完の箇所が存在するため一部処理は継続実装が必要）。

- ツール
  - Paper Trading 検証レポート generator (kabusys.tools.paper_verification_report)
    - PAPER_TRADING_SQLITE_PATH（または --db）からペーパートレード DB を読み取り、システム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計してレポート出力。
    - パス/フェイル基準を定義（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200 ms）。データ不足やテーブル未存在時は適切に N/A を表示。

Other
- パッケージ情報: バージョンを __version__ = "0.1.0" として設定。

Notes / Implementation details
- DB 接続: 実行・監視スクリプトで sqlite3 / duckdb 接続を使用。監視テーブルの初期化（init_monitoring_db）は冪等で呼び出す設計。
- 停止制御はファイルベース（data/stop_requested.flag, data/kill.flag, KILL_FLAG_CLEAR_ON_START の設定）を採用しており、本番運用時の安全対策をサポート。
- ログ出力・プロセス優先度設定は起動直後に行うよう設計されている（高優先度での実行を想定）。
- 一部のモジュール（factor_research 等）は設計コメント・定数まで実装済みだが、計算ロジックの続きが未完の可能性があるため今後の実装・テストが必要。

If you find omissions or want more granular changelog entries (e.g. file-by-file feature list or TODOs),教えてください。