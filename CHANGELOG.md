# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載します。  
このファイルでは主に初期リリース（0.1.0）で導入された機能・改善・既知の注意点をまとめています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

特になし

## [0.1.0] - 2026-04-20

初回公開リリース。本リリースは日本株自動売買システム「KabuSys」の基盤機能（設定管理、起動スクリプト、監視、実行フロー、ポートフォリオ構築ロジック、ユーティリティ類、検証ツール等）を提供します。

### Added
- 全体
  - パッケージ初期バージョンを追加（__version__ = "0.1.0"）。
  - プロジェクト配布後も動作する .env 自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml で探索）。
  - .env の柔軟なパース実装（export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメント処理などに対応）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動 env ロード無効化オプションを追加。

- 設定管理 (kabusys.config)
  - Settings クラスを導入し、環境変数から各種設定値（J-Quants、kabu API、DBパス、ログレベル、監視閾値、環境種別など）を取得する統一 API を提供。
  - PAPER_FILL_MODE のバリデーション（有効値: instant/partial/never/reject）を実装。
  - is_live / is_paper / is_dev 等の便利プロパティを追加。

- 設定ウィザード (kabusys.config_setup)
  - 対話式 .env 作成/更新ウィザードを追加。既存値の読み込み、シークレットマスキング、保存確認などをサポート。
  - デフォルト構成テンプレートの .env 書き出しを提供。

- 設定検証 CLI (kabusys.validate_config)
  - 起動前に .env と config/*.yaml を検証するツールを追加。
  - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DBパスの親ディレクトリ存在チェック、YAML パース検証（PyYAML 未インストール時は警告）や本番時のガード項目チェックを実装。
  - --strict オプションで警告をエラー扱いにできる。

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler を組み立てて ExecutionEngine を起動。
    - ストップフラグ（data/stop_requested.flag）検知で安全に停止する仕組み、デーモンスレッドでエンジンを実行。
    - 起動時にプロセス優先度を "high" に設定する挙動を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視（monitoring）データベースは環境にかかわらず本番 sqlite_path を使用。
    - 停止フラグ検知で監視ループを終了。KeyboardInterrupt ハンドリングあり。

- モニタリング DB 初期化
  - init_monitoring_db 呼び出しにより起動時に監視テーブルの存在を保証（冪等）。

- ロギングユーティリティ (kabusys.utils.logging_setup)
  - 統一ログ設定関数 setup_logging を追加。
    - stdout 出力用 StreamHandler と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app_name>.log）をルートロガーに設定。
    - 既存ハンドラはクリーンアップしてから再設定（重複防止）。
    - LOG_LEVEL / LOG_DIR 環境変数による上書きとディレクトリ作成のフェールバック処理を実装。

- プロセス優先度ユーティリティ (kabusys.utils.process_priority)
  - set_process_priority / set_cpu_affinity を追加。
    - Windows / POSIX（Linux/Mac/FreeBSD）差分を吸収して nice 値や Windows 優先度クラスを設定。
    - アクセス権限不足や未対応 OS では警告を出して安全にスキップ。

- ポートフォリオ構築 (kabusys.portfolio)
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順で選定（同スコア時は signal_rank によるタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分を実装。全銘柄スコアが 0 の場合は等金額にフォールバックして警告。
  - risk_adjustment:
    - apply_sector_cap: セクター集中を抑制するための候補フィルタリングを実装（sell 対象除外、unknown セクター扱いの動作は明記）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供。未知レジームは 1.0 にフォールバックして警告。
  - position_sizing:
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に応じて発注株数を決定するロジックを実装。
    - 単元株（lot_size）丸め、per-stock 上限、aggregate cap によるスケーリング、cost_buffer を考慮した保守的見積り、余剰キャッシュによる再配分ロジックを実装。

- Paper Trading 検証ツール (kabusys.tools.paper_verification_report)
  - Paper Trading 用 SQLite ログを解析してレポートを出力する CLI を追加。
  - システム稼働率、注文成立率、送信率、リスク却下数、API レイテンシ指標（平均・最大・P95）を算出。
  - 閾値による PASS/FAIL 判定を実装（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms など）。
  - --from / --to / --db オプションで期間と DB を指定可能。

- research (一部)
  - research.factor_research モジュールにモメンタム等のファクター計算を行う設計と一部実装を追加（DuckDB を使用して prices_daily / raw_financials を参照する方針）。

### Changed
- .env 読み込み順序の明確化: OS 環境 > .env.local > .env（.env.local は override=True で読み込み、ただし OS 環境変数は保護）。
- logging_setup: stdout を StreamHandler に使うよう変更（cron/task scheduler などで stdout/stderr をリダイレクトする運用を考慮）。
- run_execution / run_monitoring: 起動時にプロセス優先度を最初に設定するように変更し、重要処理前の優先度確保を行う。

### Fixed
- .env パーサーの改善により、クォートやエスケープ、コメントの取り扱い不具合を解消。
- validate_config: PyYAML 未インストール時に YAML 検査をスキップして警告を出すよう改善（起動時の不要なクラッシュ回避）。
- logging_setup: ログディレクトリ作成失敗時に stdout のみで継続するフェールセーフを追加。

### Known issues / Notes / TODO
- risk_adjustment.apply_sector_cap:
  - price_map に price が欠損（0.0）の場合、エクスポージャーが過少見積りとなりブロックされない可能性がある（コメントで対処案を記載）。将来的に前日終値や取得原価等のフォールバックを導入予定。
- position_sizing:
  - lot_size は現時点で全銘柄共通での取り扱い。将来的には銘柄別単元数のサポート（stocks マスタへの lot_size 持たせる等）を検討中（TODO コメントあり）。
- research.factor_research:
  - スニペットは途中までの実装を含む。ファクター計算全体（SQL/ロジック・テスト）の完成および検証が必要。
- テスト:
  - 現時点でユニットテストの記載はないため、クリティカルなロジック（position sizing、risk manager、execution flow 等）については追加のテスト整備を推奨。

### Security
- 本リリースではセキュリティ上の重要変更はありませんが、.env ファイルは絶対に Git にコミットしないようドキュメントとウィザードで注意喚起を行っています。

---

もし CHANGELOG の粒度（コミット単位の詳細や既知バグの優先度付け、次回リリース予定の機能一覧など）をさらに細かくしたい場合は、対象となる git コミットログや issue / PR の一覧を提供してください。それらに基づいてより正確で詳細な変更履歴を生成できます。