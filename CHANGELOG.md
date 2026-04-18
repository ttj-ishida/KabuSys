CHANGELOG
=========

すべての変更は Keep a Changelog 準拠の形式で記載しています。  
主にコードベースから推測される追加機能・改善点・既知の制約を反映しています。

Unreleased
----------
- Added
  - factor_research モジュールの計算ロジックを一部実装開始（モメンタム等）。まだ未完（実装途中の関数あり）。
  - いくつかの TODO / 将来拡張点をコードに明示（例: 価格フォールバック、銘柄別 lot_size 対応など）。

- Known issues / Notes
  - factor_research の一部関数は途中で切れており、完全な実装が必要。
  - position_sizing にて価格が欠損した場合のフォールバックは未実装（コメントに注意喚起あり）。

0.1.0 - 2026-04-18
------------------

Added
- パッケージ全体
  - 初期リリース相当の主要機能群を追加。
  - __version__ を "0.1.0" に設定。

- 設定管理
  - Settings クラスを追加し、環境変数から設定を取得する統一インターフェースを提供。
  - .env 自動読み込み機能を実装（プロジェクトルート検出: .git / pyproject.toml を基準）。
  - .env 読み込み時の上書き制御（override/protected）をサポートし、OS 環境変数を保護。
  - .env パース機能を強化（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理などに対応）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能。

- 環境セットアップ / 検証 CLI
  - config_setup ウィザードを追加（対話式で .env を生成/更新、シークレットはマスク表示）。
  - validate_config CLI を追加し、必須環境変数・KABUSYS_ENV・ログレベル・db パス・config/*.yaml の存在と YAML パース（PyYAML が存在する場合）を検証。--strict オプションで警告を失敗扱いに可能。
  - validate_config は本番向けガード（LINE トークン未設定や KILL_FLAG_CLEAR_ON_START の警告）も実施。

- 実行・監視スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db をデフォルト）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立てを実装。
    - RiskConfig のデフォルト値を設定（max_position_pct, max_utilization, rate_limit_per_sec 等）し、initial_portfolio_value を broker.get_available_cash() から取得。
    - ExecutionEngine は別スレッドで実行し、data/stop_requested.flag および _EXECUTION_PID による停止・PID 管理をサポート。
    - 起動時にプロセス優先度を "high" に設定（set_process_priority を使用）。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告してデフォルトにフォールバック。
    - 監視 DB は環境にかかわらず本番 sqlite_path を使用する（監視用テーブル初期化を実施）。
    - stop_requested.flag の検知でループ終了、例外発生時もログ出力して次ポーリングに続行。

- データベース / 分離
  - DuckDB（分析用）と SQLite（監視・履歴用）を併用する設計を導入。Settings でパス制御可能。
  - Paper Trading 用に専用 SQLite を用意（PAPER_TRADING_SQLITE_PATH 環境変数で上書き可）。

- ロギング・プロセス制御ユーティリティ
  - setup_logging: ルートロガー設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を組み合わせて設定。
    - LOG_DIR/LOG_LEVEL の解決順と、ディレクトリ作成失敗時のフォールバック（コンソールのみ）に対応。
  - process_priority: set_process_priority/set_cpu_affinity を追加。
    - Windows/Linux/macOS を吸収する実装。psutil を用いる。
    - 権限不足や未サポート環境では警告を出してスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio_builder:
    - select_candidates: スコア降順で候補選定（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 重み計算（スコア全0 は等分にフォールバック）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限をチェックして候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じた乗数（bull/neutral/bear）を返却。未知値は警告して 1.0 フォールバック。
  - position_sizing:
    - calc_position_sizes: allocation_method (risk_based / equal / score) に応じて発注株数を計算。
    - 単元株丸め（lot_size）、1 銘柄上限、aggregate cap スケーリング、cost_buffer による保守的見積り、残差処理（fractional remainder）を実装。
    - raw_shares → scaled の流れで利用可能現金を尊重する実装。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py を追加。
    - 指定期間の system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）を集計。
    - 閾値を定め、PASS/FAIL 形式のレポートを標準出力に出力。
    - DB が存在しない場合のエラーメッセージ、各テーブルが存在しない場合のフォールバックに対応。

- リサーチ
  - research/factor_research.py を骨組み実装（Momentum, Value, Volatility, Liquidity の仕様・定数を定義）。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。

Changed
- なし（初期リリース相当の追加が中心のため変更履歴は追加として記載）。

Fixed
- 例外処理の強化
  - run_monitoring のポーリングループで check_once() 内の例外をキャッチしてログ出力し、ループ継続するようにした（監視継続性向上）。
  - setup_logging: 既存ハンドラを適切に flush/close してから再設定することで多重ハンドラ登録を防止。

Security
- .env ファイルについて注意喚起
  - config_setup は .env を生成する際に「絶対に Git にコミットしないこと」を明示。

Removed / Deprecated
- なし

Notes / Known limitations
- factor_research の実装は途中（ファイル終端で途中の関数が存在）。リサーチファクター計算の完成が必要。
- position_sizing:
  - price が欠損（0.0）の場合のフォールバック（前日終値や取得原価の使用）は未実装。コメントで将来的な拡張を示唆。
  - 将来的に銘柄別 lot_size を導入する設計（現在はグローバル lot_size）。
- set_process_priority / set_cpu_affinity は環境や権限によって機能しない場合があり、その場合は警告ログを出して処理を継続。
- logging のファイル出力はログディレクトリ作成に失敗した場合は無効化され、コンソールのみで継続。

参考
- 本 CHANGELOG はコード内容から推測して作成しています。実際のコミット履歴や意図と差分がある可能性があります。必要であればコミット履歴・担当者に確認の上、追補してください。