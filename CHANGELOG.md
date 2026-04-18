# Changelog

すべての非互換性のある変更はメジャー番号の増加によって示します。
このファイルは Keep a Changelog の書式に準拠しています。
Baseline バージョン: 0.1.0

## [Unreleased]
（現在の作業ブランチ向けの未リリース変更はここに記載します）

## [0.1.0] - 2026-04-18
初回リリース。以下の主要機能とユーティリティを提供します。

### Added
- 実行スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを提供。
    - KABUSYS_ENV に応じて paper_trading 用の専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を用いて本番／モックブローカーを切り替え可能。
    - OrderRepository、OrderManager、RiskManager、Reconciler を組み立てて ExecutionEngine を起動・監視する仕組みを実装。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）によるプロセス制御に対応。
    - スレッドで ExecutionEngine を実行し、フラグによる安全停止やタイムアウト付き join を行う。
  - run_monitoring.py
    - SystemMonitor の起動エントリポイントを提供。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正値はデフォルトにフォールバックし警告を出力。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する仕様。
    - 停止フラグ検出でループを終了し、例外発生時はロギングして次のポーリングへ継続。

- 設定管理とセットアップ
  - config.py
    - .env の自動読み込み機構（プロジェクトルート自動検出）。OS 環境変数の保護（上書き禁止）に対応。
    - .env パースは export プレフィックス、引用符、インラインコメント、エスケープを考慮した堅牢な実装。
    - Settings クラスを通じた型付き設定アクセス（パス、閾値、フラグ等）。
    - KABUSYS_ENV / LOG_LEVEL 等の妥当性チェックとデフォルト値の提供。
  - config_setup.py
    - .env 作成・更新のための対話式ウィザードを追加。
    - シークレット項目は画面表示でマスク、選択肢とデフォルト値に対応。
    - 最終的に .env を書き出す際のテンプレート生成機能を実装。
  - validate_config.py
    - 起動前に環境変数と config/*.yaml の存在・基本整合性を検証する CLI を提供。
    - --strict オプションで警告も失敗扱いにできる。
    - PyYAML 未導入時は YAML 検証をスキップして警告を出す。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順にソートして上位 N 件を選択。
    - calc_equal_weights: 等金額配分（各銘柄 1/N）。
    - calc_score_weights: スコアに比例した重み付け（全スコアが 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中を抑制するため、上限超過セクターの新規候補を除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数を提供（未知のレジームはフォールバックで 1.0）。
  - portfolio/position_sizing.py
    - calc_position_sizes: 重み・候補・リスクパラメータから銘柄ごとの発注株数を計算。
    - 複数の allocation_method をサポート（risk_based / equal / score）。
    - 単元株（lot_size）丸め、1銘柄上限・全体利用可能現金による aggregate キャップ、cost_buffer による保守的見積を実装。
    - aggregate スケールダウン時に端数処理（ロット単位）を公平に割り当てるアルゴリズムを搭載。

- ユーティリティ
  - utils/logging_setup.py
    - 共通のロギング初期化ユーティリティを追加。
    - stdout 出力用 StreamHandler と日次ローテーションでログファイルを出す TimedRotatingFileHandler（30 日保持）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - LOG_LEVEL / LOG_DIR / 引数による優先解決をサポート。
  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定を提供（high/normal/low）。
    - cpu_affinity を最初の N コアに固定する関数を追加。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、P95 レイテンシなどを集計して PASS/FAIL を判定。
    - --from / --to / --db オプション対応。
    - DB が存在しない、またはテーブルが無い場合に N/A やデフォルト値で安全に出力。
    - P95 計算ユーティリティを実装。

- リサーチ（ファクター計算）
  - research/factor_research.py（部分実装）
    - DuckDB 接続と prices_daily/raw_financials を前提にモメンタム・ボラティリティ・バリュー等のファクターを計算する設計。
    - calc_momentum の骨子（1M/3M/6M リターン、MA200乖離等）を実装する方針で始められている（ファイル末尾は続きあり）。

### Changed
- パッケージメタ情報
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定（初期バージョン）。
- ロギング・プロセス管理の一貫化
  - 起動スクリプト全体で setup_logging と set_process_priority を最初に呼ぶ共通パターンを採用し、起動時のログ・優先度設定を統一。

### Fixed
- 環境変数パーサ
  - .env 読み込みロジックの細かなケース（export プレフィックス、引用符内のエスケープ、インラインコメントの取り扱い）に対応し、実運用で見られる .env 形式差異に耐性を持たせた。

### Notes / Implementation Details
- Paper Trading と Live の DB は明確に分離（paper_trading 用に paper_sqlite_path を利用）。これにより検証中のデータが本番データに混入しない設計。
- stop_requested.flag / kill.flag 等のファイルベースの Kill Switch を起動スクリプトで参照することで外部から安全にプロセスを停止可能。
- 多くのモジュールは外部副作用を持たない純粋関数（ポートフォリオ計算等）として設計されており、単体テストが容易になるよう配慮されている。
- DuckDB / SQLite / psutil / PyYAML 等のランタイム依存は optional に扱う箇所があり、存在しない場合は機能制限や警告を出して安全にフォールバックする実装になっている。

### Deprecated
- なし

### Removed
- なし

### Security
- 機密情報（API トークン・パスワード）は .env に格納して運用する想定。config_setup の出力で .env を Git に入れないよう明記。

----

今後の予定（例）
- research/factor_research のファクター計算実装完了（Momentum の完全実装、Value/Volatility/Liquidity の算出）。
- モニタリングと Execution 間のメトリクス連携強化（DuckDB を介した分析パイプライン）。
- 単体テスト追加と CI パイプライン整備。