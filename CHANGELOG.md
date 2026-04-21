# CHANGELOG

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog 準拠のフォーマットで記載しています。

フォーマット:
- 変更はカテゴリ別（Added / Changed / Fixed / Removed / Security）に分けています。
- 各項目はコードベースから推測して記載しています。

## [Unreleased]
- （現在なし）

## [0.1.0] - 2026-04-21
初回リリース。自動売買システム KabuSys のコア機能群を追加しました。

### Added
- 実行・監視ランナー
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db を既定）を使用し、本番 DB と分離して MockBrokerClient を利用する設計。
    - Engine を別スレッドで実行し、データディレクトリの stop_requested.flag による外部停止をサポート。
    - 起動時にプロセス優先度を "high" に設定するユーティリティを呼び出す。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視（monitoring）は環境にかかわらず本番 sqlite_path を使用する仕様。
    - 停止フラグファイルによるグレースフルシャットダウンをサポート。

- 設定・環境管理
  - config.py: 環境変数管理クラス Settings を導入。
    - .env / .env.local の自動ロード機能（プロジェクトルート検出: .git または pyproject.toml）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
    - .env の各種パラメータ（J-Quants, kabuAPI, DBパス, Paper Trading 設定, 監視閾値など）をプロパティで提供。
    - PAPER_FILL_MODE や KABUSYS_ENV / LOG_LEVEL の値検証を実装。
  - config_setup.py: 対話式の .env 作成ウィザードを追加（.env の初期作成・更新を支援）。
  - validate_config.py: 起動前検証 CLI を追加（.env や config/*.yaml の存在・基本チェック、--strict モード対応）。
    - PyYAML が無ければ YAML 内容検証をスキップする柔軟処理。
    - 本番（KABUSYS_ENV=live）向けの追加ガード（LINE通知設定チェック、KILL_FLAG の自動クリア設定警告など）。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順でソートし上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分の計算。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限（既存保有を考慮して新規候補を除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた資金乗数を提供（未知レジームはフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数算出。単元株丸め、per-position 上限、aggregate cap（利用可能現金）へのスケーリング、cost_buffer（手数料・スリッページ見積）対応を実装。

- 実行関連コンポーネント（構成）
  - ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager（および関連設定クラス: EngineConfig / RiskConfig）を組み合わせて起動するための初期実装を追加（run_execution から利用）。
  - BrokerClientFactory により実行環境に応じた Broker クライアント（Mock を含む）を生成。

- 監視・DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を呼び出して監視用テーブルの存在を保証（冪等性を考慮）。

- ロギングとプロセス制御ユーティリティ
  - utils/logging_setup.py:
    - ルートロガーへ stdout 出力用 StreamHandler と日次ローテーション（TimedRotatingFileHandler）を設定する共通ユーティリティ。
    - LOG_LEVEL / LOG_DIR の解決順に対応。ファイル出力失敗時はコンソールのみで継続。
  - utils/process_priority.py:
    - Windows / POSIX を吸収してプロセス優先度を設定（high/normal/low）。
    - CPU affinity 設定機能を提供（psutil ベース）。権限不足等はワーニングでスキップ。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率（fill_rate）、送信率、リスク却下数、レイテンシ（avg/max/P95）などを算出し PASS/FAIL 判定（しきい値はソース中に定義）を行う。
    - --from / --to / --db オプションにより期間・DB を指定可能。PAPER_TRADING_SQLITE_PATH 環境変数に対応。

- リサーチ（ファクター計算）
  - research/factor_research.py:
    - ファクター計算モジュールの追加（Momentum / Value / Volatility / Liquidity 設計）。
    - DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。
    - モメンタム計算関数（calc_momentum）の実装方針が含まれる（営業日ベースの horizon 定義など）。一部実装は継続作業を想定。

### Changed
- パッケージ初期化
  - kabusys.__init__.py にバージョン 0.1.0 を設定。

### Fixed
- .env パーサの堅牢化（config._parse_env_line）
  - export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、行末コメントの取り扱いなどに対応。
  - .env の読み込みで OS 環境変数を保護する仕組み（protected set）を導入。`.env.local` は上書き（override=True）を許容しつつ OS 環境変数は保護。

### Notes / Known limitations
- monitoring はコード上「環境にかかわらず本番 sqlite_path を使用する」と明示されており、意図的な設計です（paper_trading 環境でも監視 DB に本番パスを使う点に注意）。
- process_priority と CPU affinity は権限やプラットフォーム依存で失敗する可能性があり、失敗時はワーニングで継続する設計です。
- research/factor_research の一部（大規模計算ロジックやエッジケース処理）は今後の作業で完成させる必要があります（ファイル内コメント参照）。
- position_sizing では price が欠損（0.0）だとエクスポージャーが過少見積りになる可能性があるため将来的にフォールバック価格の採用が検討されています（TODO コメントあり）。

---

この CHANGELOG はコードの内容から推測して作成しています。実際のリリースノート作成時は変更内容・日付・著者などを実際のコミット履歴やリリース方針に合わせて調整してください。