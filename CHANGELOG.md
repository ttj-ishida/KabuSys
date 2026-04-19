# Changelog

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
慣例に従いセマンティックバージョニングを使用します。

※ この CHANGELOG はソースコードから推測して作成したもので、実際のコミット履歴とは異なる場合があります。

全体ポリシー:
- 追加: 新機能・新モジュール
- 変更: 既存機能の振る舞い変更や改善
- 修正: バグ修正や例外処理の追加
- 削除 / 非推奨: 明示的な破壊的変更や削除点（今回該当なし）

## [Unreleased]

（現在のコードベースは初回公開に相当するため、実態は次の 0.1.0 にまとめられています）

## [0.1.0] - 2026-04-19

### Added
- プロジェクト初期版のコア機能およびユーティリティを追加。
- 環境設定 / 起動系
  - kabusys.config
    - 環境変数読み込み・管理クラス `Settings` を追加。多数のアプリ設定（DB パス、API トークン、PAPER_FILL_MODE、閾値等）をプロパティで提供。
    - プロジェクトルート自動探索機能を実装（.git または pyproject.toml を基準）。これにより CWD に依存しない .env 自動読み込みを実現。
    - .env ファイルの自動読み込み（`.env` → `.env.local`、OS 環境変数を保護して上書き制御）をサポート。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - .env の行パーサ実装（export プレフィクス、シングル/ダブルクォート、エスケープ、インラインコメント処理をサポート）。
  - kabusys.config_setup
    - 対話式 .env 作成ウィザードを追加。必須項目・デフォルト・選択肢・シークレットマスク表示対応。`.env` 書き出し機能あり。
  - kabusys.validate_config
    - 起動前検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV 値検証、ログレベル検査、DB パスの親ディレクトリ確認、config/*.yaml の存在・パースチェック（PyYAML が無ければスキップ）を実行。
    - --strict オプションで警告を失敗扱いにできる。
- 起動スクリプト / ランナー
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB は環境にかかわらず production の sqlite_path を使用する設計（意図的な分離）。
    - stop フラグファイル検知による graceful shutdown を実装。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は専用の paper_trading DB（data/paper_trading.db）を使用して発注ロジックと DB を本番から分離。
    - BrokerClientFactory による実行時ブローカー切替（Paper Trading 用 MockBroker を想定）。
    - PID ファイル / stop フラグの取り扱いとデーモンスレッドでのエンジン実行・停止処理を実装。
- ロギング・プロセス制御ユーティリティ
  - kabusys.utils.logging_setup
    - 統一的なログ初期化ユーティリティ `setup_logging` を追加。stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app>.log、30 日分保持）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続する堅牢化を実装。
    - stdout 出力にしているため cron 等の出力リダイレクト運用を想定。
  - kabusys.utils.process_priority
    - クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定関数 `set_process_priority` を追加。アクセス権限のない場合は警告でスキップ。
    - CPU affinity を設定する `set_cpu_affinity` も実装（利用可能コア数より大きい指定は無視して全コア使用）。
- ポートフォリオ構築（純粋関数群）
  - kabusys.portfolio.portfolio_builder
    - シグナル選定関数 `select_candidates`（スコア降順、タイブレーク: signal_rank）を追加。
    - 等配分 `calc_equal_weights`、スコア加重 `calc_score_weights` を追加。全スコア 0 の場合は等配分へフォールバックして警告出力。
  - kabusys.portfolio.risk_adjustment
    - セクター集中上限チェック `apply_sector_cap` を実装。既存保有のセクター別エクスポージャー計算を行い、上限超過セクターの新規候補を除外するロジック。
    - 市場レジームに応じた乗数 `calc_regime_multiplier` を追加（bull/neutral/bear をマップ、未知レジームは 1.0 でフォールバック）。
  - kabusys.portfolio.position_sizing
    - 位置サイズ算出 `calc_position_sizes` を実装。allocation_method に応じて "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金を超える場合のスケーリング）や cost_buffer（スリッページ/手数料見積り）を考慮した安全なスケーリング実装あり。
    - price 欠損時のスキップ・ログや、スケーリング時の残差処理（小数端数の優先配分）を実装。
- リサーチ / ファクター
  - kabusys.research.factor_research
    - ファクター計算の骨子を追加。Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility、Value、Liquidity 指標を想定。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。モジュール定数（ウィンドウ長等）を定義。
    - （注）ファイル末尾で実装途中の箇所あり（スニペットは途中で切れているため、詳細実装は継続が必要）。
- ツール
  - kabusys.tools.paper_verification_report
    - Paper Trading 用検証レポート生成 CLI を追加。PAPER_TRADING_SQLITE_PATH（または --db）で DB を指定し、稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL 判定を出力。
    - デフォルトの閾値（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義。
    - P95 計算実装、日付フィルタリング、SQLite の存在チェック・エラー耐性を備える。

### Changed / Design Decisions
- 監視（run_monitoring）では KABUSYS_ENV にかかわらず監視用 DB 接続先に production の sqlite_path を使用する設計とした（監視は常に本番指標を記録・参照する想定）。
- ログ出力は stdout を第一にしており、cron などからのリダイレクト運用を考慮。
- .env 読み込みの優先度と保護（OS 環境変数を protected set として上書きを防ぐ）を明確化。
- process_priority の実装は例外を握りつぶさず警告ログとして扱い、起動の堅牢性を優先。

### Fixed / Robustness
- .env パーサでのクォート内のバックスラッシュエスケープや export プレフィクス、インラインコメント処理に対応し、より実運用の .env を正しく扱えるようにした。
- logging_setup: ログディレクトリ作成に失敗した場合でも、ファイルハンドラの生成失敗を許容してコンソールログのみで動作継続するようにした（起動失敗を避けるため）。
- process_priority/set_cpu_affinity: 未対応 OS・権限不足・未実装例外に対して警告でスキップする挙動に統一し、起動の阻害を回避。

### Known issues / TODO
- research.factor_research 内の関数実装が途中で終わっている箇所がある（ファイル末尾で途中終了）。ファクター計算の完全実装が必要。
- position_sizing の price が欠損（0.0）の場合のエクスポージャー過少見積りに関する注釈がある。前日終値や取得原価を用いるフォールバック実装などの改善余地あり。
- config/*.yaml のテンプレート生成や strategy/risk/execution の具体的設定は別スクリプト（scripts/generate_config.py 等）に依存している旨のメッセージあり。環境整備手順のドキュメント化を推奨。

### Removed
- なし

### Security
- なし（初期リリース）

---

リリースノートや実装の詳細について追加の情報が必要であれば、どのモジュール／機能に対して詳しく記載するか指定してください。必要に応じて英語版の CHANGELOG も作成可能です。