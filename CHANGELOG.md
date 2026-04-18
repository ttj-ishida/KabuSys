# Changelog

すべての変更は Keep a Changelog の仕様に準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

注: このリリースはコードベースから推測して作成した概要です。実装の詳細や将来の変更点はソースをご確認ください。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-18

初期リリース。システム全体のコア機能、CLI ユーティリティ、ポートフォリオ構築ロジック、監視/実行用起動スクリプト、及び補助ユーティリティを実装。

### Added
- 全体
  - パッケージ初期化とバージョン定義を追加（__version__ = "0.1.0"）。
  - DuckDB / SQLite を利用するデータアクセス基盤の導入（設定経由でパス指定可能）。
  - ログ設定ユーティリティを追加（kabusys.utils.logging_setup）。
    - stdout 出力（StreamHandler）と日次ローテーションのファイル出力（TimedRotatingFileHandler）を提供。
    - LOG_DIR 環境変数 / 引数でログ保存先を指定可能。ディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
- 環境設定
  - 環境変数 / .env ファイルの自動読み込み機能を実装（kabusys.config）。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）。
    - .env と .env.local の読み込み順序を適用（OS 環境変数を保護）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード抑止をサポート。
    - .env の行パースは export 構文、クォート、バックスラッシュエスケープ、インラインコメント等に対応。
  - Settings クラスを実装し、各種設定値（J-Quants, kabu API, DB パス, モニタ閾値, 環境種別など）をプロパティで取得可能にした。値検証（有効な KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等）を行う。
  - 対話式 .env 作成ウィザードを追加（kabusys.config_setup）。
    - 各設定項目の説明、既存値の再利用、シークレットマスク表示、最終確認 → .env 保存機能を提供。
- 検証ツール
  - 起動前設定検証 CLI を追加（kabusys.validate_config）。
    - 必須環境変数の有無チェック、KABUSYS_ENV と LOG_LEVEL の妥当性確認、DB パスの親ディレクトリ存在確認、config/*.yaml の存在・パース検証（PyYAML が利用可能な場合）。
    - --strict オプションで警告を失敗扱いにできる。
- 実行 / 監視ランチャー
  - Execution 起動スクリプトを追加（run_execution.py）。
    - 起動時にプロセス優先度を "high" に設定（kabusys.utils.process_priority を使用して OS 差分を吸収）。
    - KABUSYS_ENV が paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db をデフォルト）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て ExecutionEngine をスレッドで起動。停止フラグ（data/stop_requested.flag）検知で安全停止。
    - Execution 用の PID ファイル生成管理（pid_file）。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を含む。
  - Monitoring 起動スクリプトを追加（run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。0 以下の値や非整数は警告してデフォルトにフォールバック。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する（監視テーブルは常に production path に初期化）。
    - 停止フラグ検知でループを終了し、KeyboardInterrupt をハンドリングしてクリーンアップ。
- ポートフォリオ構築（純関数群）
  - 銘柄選定 / 重み計算（kabusys.portfolio.portfolio_builder）
    - select_candidates: スコア降順で上位 N を選択（同点は signal_rank でタイブレーク）。
    - calc_equal_weights, calc_score_weights（スコアが全て 0 の場合は等金額配分にフォールバックし警告）。
  - セクター集中制限・レジーム乗数（kabusys.portfolio.risk_adjustment）
    - apply_sector_cap: 既存保有のセクターエクスポージャが閾値を超える場合に当該セクターの新規候補を除外。unknown セクターは除外対象外。
    - calc_regime_multiplier: 'bull'/'neutral'/'bear' をそれぞれ 1.0/0.7/0.3 にマップ。未知レジームは 1.0 にフォールバックして警告。
  - ポジションサイジング（kabusys.portfolio.position_sizing）
    - risk_based / equal / score の allocation_method をサポート。
    - 単元株（lot_size）で丸め、per-position 上限、aggregate cap（available_cash）に基づくスケーリングを実装。cost_buffer を使った保守的コスト見積りを考慮。
    - スケーリング後に残余キャッシュで端数分を優先度（fractional remainder）順に lot_size 単位で配分するロジックを実装。
- ユーティリティ
  - process_priority ユーティリティ（kabusys.utils.process_priority）
    - Windows / POSIX の差分吸収（nice / HIGH_PRIORITY_CLASS 等）を実装。権限不足や未対応 OS の場合は警告してスキップ。
    - set_cpu_affinity により最初の N コアにピン留めする機能を提供（権限エラーは警告してスキップ）。
- ツール
  - Paper Trading 検証レポート生成ツール（kabusys.tools.paper_verification_report）。
    - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）。--db, --from, --to オプションをサポート。
    - システム稼働率、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシなどを集計し PASS/FAIL 判定を行う（閾値はソース内で定義）。
    - P95 は簡易計算実装、DB テーブルが存在しない場合は適切に N/A を表示。
- リサーチ
  - ファクター計算モジュール（kabusys.research.factor_research）を追加（モメンタム、MA200、ATR、流動性等の定義と計算の設計方針を含む）。
    - DuckDB を用い prices_daily / raw_financials を参照してファクターを生成する設計。

### Changed
- 初期リリースのため該当なし

### Fixed
- 初期リリースのため該当なし

### Removed
- 初期リリースのため該当なし

### Security
- 初期リリースのため該当なし

---

## 補足 / 注意事項
- Monitoring は意図的に環境に関係なく本番 sqlite_path を使用する設計です。監視対象 DB の分離を望む場合は設定を見直してください。
- Execution は paper_trading 環境で専用 paper_trading DB を使用して本番 DB と完全分離するよう設計されています（デフォルト: data/paper_trading.db）。
- .env の自動読み込みはプロジェクトルートを探索して行います。CI / テスト等で自動ロードを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 一部コード内に将来の改善のための TODO コメントがあります（例: 価格欠損時のフォールバックロジック）。
- ロギングやプロセス優先度設定は権限に依存するため、環境によっては一部機能が警告を出してスキップされます。

もしリリースノートに追加したい詳細（例: 各 CLI の利用例、設定例、既知のバグや既存の TODO 事項の優先度など）があれば教えてください。必要に応じて CHANGELOG を更新します。