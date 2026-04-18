CHANGELOG
=========

すべての重要な変更点はここに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。  

0.1.0 - 2026-04-18
------------------

Added
- 起動スクリプト
  - run_execution: ExecutionEngine を起動するエントリポイントを追加。  
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB を使用し MockBrokerClient を利用可能（本番 DB と完全分離）。
    - スレッドでエンジンをデーモン実行し、data/stop_requested.flag による外部停止をサポート。
    - 実行中 PID を data/execution.pid に出力する仕組み（Engine に PID ファイルパスを渡す）。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告を出してデフォルトにフォールバック。
    - 監視は環境に関わらず本番用の sqlite_path を使用して監視テーブルを初期化する。
    - data/stop_requested.flag による外部停止対応。KeyboardInterrupt もハンドル。

- 設定・環境関連
  - config.py: 環境変数管理クラス Settings を追加。多数のプロパティを通じて設定値を取得できるようにした（J-Quants, kabuapi, LINE, DB パス、監視しきい値、環境判定など）。
    - PAPER_FILL_MODE の厳密な値チェック（valid 値: instant|partial|never|reject）。
    - paper_sqlite_path, sqlite_path, duckdb_path 等の Path 返却。
    - env/log_level の検証（不正値は ValueError）。
  - 自動 .env ロード機能
    - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動読み込み（既存 OS 環境変数は保護）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - .env パーサは export KEY=val 形式、クォート（"'/エスケープ）やインラインコメントを考慮して解析。

- 設定支援 CLI
  - config_setup.py: 対話式ウィザードを追加。.env の初期作成 / 更新をサポート（秘匿入力・選択肢・デフォルト表示など）。
  - validate_config.py: 起動前検証 CLI を追加。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在・パース（PyYAML がある場合）などを検査。--strict により警告も失敗扱いにできる。

- ロギング・プロセスユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。
    - stdout 出力用 StreamHandler（stdout 使用）と日次ローテーションの TimedRotatingFileHandler（logs/<app>.log）を組み合わせて設定。
    - LOG_DIR/LOG_LEVEL 等の解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - utils/process_priority.py: クロスプラットフォーム（Windows / POSIX）でプロセス優先度と CPU affinity を設定するユーティリティを追加。psutil を利用し、権限不足等は警告ログでスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順（同点は signal_rank）でソートして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重配分を提供。全スコアが 0 の場合は等分配にフォールバック（警告ログ）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: 既存保有のセクター別エクスポージャに基づき、セクター上限を超える場合に新規候補を除外。
      - sell_codes を除外して当日売却予定銘柄のエクスポージャを計算可能。
      - "unknown" セクターは上限適用対象外。
      - 実データ欠損に関する TODO（価格欠損時のフォールバック）を記載。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知のレジームは 1.0 にフォールバック（警告ログ）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に応じて個別株数を計算。
      - risk_based: 許容リスク率・損切り率に基づく株数算出。
      - equal/score: 重みに基づく金額配分から株数算出。
      - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash 超過時のスケーリングと残差処理）を実装。
      - cost_buffer によりスリッページ/手数料を保守的に見積もる。
      - 将来的な拡張ポイント（銘柄別 lot_size）を TODO に記載。

- リサーチ / ファクター計算
  - research/factor_research.py: DuckDB 接続を受けてモメンタム等の定量ファクターを計算するモジュールを追加（関数 calc_momentum を含む実装の開始）。  
    - 設計方針、使用する窓サイズ（1M/3M/6M、MA200、ATR20 等）と出力形式のドキュメントを含む。
    - （注）ファイル末尾が途中までのため一部実装は継続中。

- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。
    - PAPER_TRADING_SQLITE_PATH（または --db）で指定した SQLite DB から集計。
    - 指標: 稼働率 (uptime_pct)、注文成功率 (fill_rate)、送信率 (send_rate)、リスク却下数、平均/最大/P95 レイテンシ。
    - デフォルトの合格基準 (稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 latency <= 200 ms) を定義し、PASS/FAIL を出力。
    - 日付フィルタ (--from/--to) に対応。

Changed
- 初期バージョンとして各コンポーネントをモジュール化・分離。
  - DB 周りは sqlite3（監視・履歴）と duckdb（分析）を明示的に使い分ける設計を採用。
  - 監視/実行プロセスともに起動直後にプロセス優先度を "high" に設定するフローを共通化。

Fixed
- 設定読み込みの堅牢化
  - .env パーサでクォートやエスケープ、export プレフィックス、インラインコメントをより正確に扱うよう改善。
  - .env の読み込みで OS 環境変数を保護する仕組みを導入（protected set）。

Security
- 秘匿設定の取り扱い
  - config_setup の出力では JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等の秘匿項目はマスクして表示。README/注意書きとして .env を絶対に Git にコミットしない旨を記載。

Deprecated
- なし（初期リリース）。

Known issues / TODO
- portfolio/risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャが過少見積もられる問題に関する TODO を記載。前日終値や取得原価等のフォールバックを検討する必要あり。
- portfolio/position_sizing:
  - 銘柄ごとの単元株数差異に対応する拡張（stocks マスタに lot_size を持たせる等）の TODO。
- research/factor_research.py:
  - ファイル末尾（calc_momentum の実装の続き）が途中のため、完全実装・テストが必要。

Notes
- ログはデフォルトで logs/<app>.log に日次ローテーションで保存されるが、ログディレクトリ作成に失敗した場合はコンソール出力のみで継続します。
- プロセス優先度や CPU affinity の設定は権限やプラットフォーム依存で失敗する場合があります。その場合は警告ログを出して処理を続行します。
- 本リリースでは多くの機能が「純粋関数」設計で実装されており、ユニットテストが容易になっています。将来的に DuckDB/SQLite との統合テストおよび End-to-End テストを追加することを推奨します。