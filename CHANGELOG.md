# Changelog

すべての変更点は「Keep a Changelog」規約に準拠して記載しています。  
このファイルはコードベースから推測して作成した変更履歴です（実際のコミット履歴ではありません）。

## [0.1.0] - 初回リリース
リリース日: 未指定

### Added
- 基本アプリケーション情報とバージョン管理
  - パッケージのバージョンを `kabusys.__version__ = "0.1.0"` として定義。
- 起動スクリプト
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を指定可能（デフォルト 60 秒）。
    - 停止フラグファイル（data/stop_requested.flag）による安全停止。
    - Monitoring は環境に関係なく本番の sqlite_path を使用する挙動を採用。
    - duckdb と sqlite の接続・初期化処理を実装。
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は紙トレード用 DB（data/paper_trading.db）を使用し、MockBrokerClient を利用して本番 DB と分離。
    - スレッドで ExecutionEngine をデーモン起動し、停止フラグで優雅に停止。
    - 実行用 PID ファイル出力（data/execution.pid）に対応。
- 設定・環境管理
  - config: .env 自動読み込み機能（.env, .env.local）を実装。
    - OS 環境変数を保護するため `.env.local` の上書きは保護リストを考慮。
    - `.env` のパース機構を詳細に実装（export 形式、クォート文字列、エスケープ、インラインコメント処理）。
  - Settings クラスを実装し、環境変数のプロパティアクセス、妥当性チェック（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）を提供。
  - 設定ウィザード CLI（config_setup）を追加:
    - 対話式で .env を生成・更新可能。
    - セクション分け・説明つきのプロンプト、既存 .env の読み込み・再利用に対応。
  - 設定検証 CLI（validate_config）を追加:
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性確認、DB パスの親ディレクトリ確認、config/*.yaml の存在/パースチェック（PyYAML 有無で挙動を分岐）。
    - `--strict` オプションで警告をエラー扱いにできる。
- ロギング・ユーティリティ
  - utils.logging_setup.setup_logging を追加:
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定。
    - ログレベル・ログディレクトリは引数・環境変数・デフォルトの順で解決。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
- プロセス優先度ユーティリティ
  - utils.process_priority を追加:
    - クロスプラットフォームでのプロセス優先度設定（Windows の PRIORITY_CLASS / POSIX の nice 値）と CPU affinity 設定を提供。
    - アクセス権限や未対応 OS の場合に警告を出して安全にフォールバック。
- ポートフォリオ構築モジュール
  - portfolio.portfolio_builder:
    - 候補選択（select_candidates）、等分配（calc_equal_weights）、スコア加重（calc_score_weights）を実装。
    - スコアが全て 0 の場合は等分配にフォールバックし警告を出す。
  - portfolio.risk_adjustment:
    - セクター集中制限の適用（apply_sector_cap）と市場レジーム乗数（calc_regime_multiplier）を実装。
    - unknown セクターはセクター上限の対象外にする挙動。
    - レジーム乗数は 'bull'/'neutral'/'bear' をマップ、未知レジームは 1.0 でフォールバック（警告）。
  - portfolio.position_sizing:
    - position sizing（数量計算）を実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金を超えた場合のスケーリング）を実装。
    - cost_buffer による手数料・スリッページの概算を反映。
- Paper Trading 検証ツール
  - tools.paper_verification_report を追加:
    - Paper Trading 用 SQLite DB から稼働率、注文成功率、送信率、API レイテンシ（平均/最大/P95）などを集計してレポート出力。
    - P95 計算、期間フィルタ、CLI オプション（--from/--to/--db）に対応。
    - しきい値（稼働率、成功率、送信率、P95 レイテンシ）に基づく PASS/FAIL 判定を実装。
- 研究用ファクターモジュール（試作）
  - research.factor_research を追加（モメンタム等のファクター計算を意図）。
    - DuckDB を利用して prices_daily / raw_financials を参照する設計。
    - （注）ファイル末尾で関数実装が途中で切れているため未完成部分あり。

### Changed
- なし（初回リリースにつき新規機能の追加が中心）

### Fixed
- 環境変数読み込み・パースの堅牢化
  - export プレフィックス、クォート文字列中のバックスラッシュエスケープ、インラインコメントの取り扱いなどを改善。
- ロギング初期化の堅牢化
  - 既存ハンドラを正しく flush/close してから再設定するように修正（多重設定防止）。
- プロセス優先度/CPU affinity の失敗ケースをキャッチして警告でフォールバックするように実装（管理者権限や OS 非対応時の安全化）。
- run_execution/run_monitoring における DB 初期化は冪等に実行されるよう init_monitoring_db 呼び出しを追加。

### Known issues / Notes
- research.factor_research の calc_momentum 等の実装が途中で切れている箇所がある（ソースが未完）。実運用前に完成化が必要。
- portfolio.position_sizing 内の価格欠損 (price == 0.0) による露出過少見積りに関する TODO コメントあり。将来的に前日終値などのフォールバック価格導入を検討する必要がある。
- run_monitoring は Monitoring 用 DB 接続に常に本番 sqlite_path を使用する挙動を採用しているため、テスト環境での監視分離には注意が必要（意図的な設計）。
- config 自動ロードはプロジェクトルート検出 (.git または pyproject.toml) に依存するため、配布後の挙動や CWD に依存しない設計だが、特殊な配布形態では自動ロードがスキップされる可能性がある。
- PAPER_FILL_MODE の値は厳密に検証され、無効値を与えると例外を送出する（起動時にクラッシュする可能性あり）。設定例を .env.example に用意することが推奨される。

---

今後の作業候補（リスト）
- factor_research の完成（特に calc_momentum 以降の実装完了）。
- ユニットテストの追加（env パーサー、position_sizing の集計/スケーリングロジック、CLI の動作確認）。
- 起動スクリプトのコンテナ/サービス化ドキュメント整備（systemd / docker / k8s）。
- ロギングの構成を環境別に明確化（本番と開発での保存先やレベル差分）。
- config_setup の非対話モード（テンプレートから自動生成）やパスワードマネージャ連携の検討。