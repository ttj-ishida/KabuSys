# Changelog

すべての注目すべき変更点を記録します。フォーマットは Keep a Changelog に準拠しています。

最新リリース
------------

### [Unreleased]
（今後の変更をここに記載してください）

過去のリリース
--------------

### [0.1.0] - 2026-04-20
初回リリース。リポジトリの主要コンポーネントを追加しました。

Added
- 基本アプリケーション情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として定義。
- 環境設定管理
  - Settings クラスを実装して環境変数/デフォルト値を統一的に取得。
  - .env 自動読み込み (プロジェクトルートの検出: .git / pyproject.toml)。`KABUSYS_DISABLE_AUTO_ENV_LOAD` による無効化対応。
  - .env パースの強化:
    - `export KEY=val` 形式対応
    - シングル/ダブルクォート、バックスラッシュエスケープ対応
    - インラインコメントの処理（クォート有無に応じた挙動）
- 設定ウィザード CLI
  - `kabusys.config_setup` に対話式ウィザードを追加し `.env` の初期作成・更新を支援。
  - よく使う設定項目の定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START など）。
- 設定検証 CLI
  - `kabusys.validate_config` を追加。起動前に .env と config/*.yaml の基本的妥当性を検証。
  - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パス親ディレクトリ存在チェック、YAML パース検証（PyYAML 有無で分岐）、本番向けガードチェックなどを実装。
  - `--strict` オプションで警告を失敗扱いにするモードを追加。
- 起動スクリプト
  - `run_monitoring.py`：SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は環境に関わらず本番用 `sqlite_path` を使用して接続。
    - 停止フラグファイル (`data/stop_requested.flag`) を検知してループを終了。
    - monitor.check_once() 内での例外をキャッチしてログに残し、次のポーリングまで待機。
  - `run_execution.py`：ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 専用 SQLite (`PAPER_TRADING_SQLITE_PATH` / `data/paper_trading.db`) を使用し本番 DB と分離。
    - BrokerClientFactory により環境に応じて Broker クライアントを生成（paper_trading では MockBroker を使用する設計）。
    - 停止フラグ検知で実行エンジンを安全に停止する仕組み（別スレッドで実行）。
    - 起動時に停止フラグが既に立っている場合は起動を中止。
- 監視 DB 初期化ユーティリティ
  - `init_monitoring_db` を呼び出して監視用テーブルの存在を冪等に保証（起動スクリプトから利用）。
- ロギング・プロセス管理ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging` を追加。
    - stdout への StreamHandler（標準出力を使用）と日次ローテーション（TimedRotatingFileHandler、30 日保持）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールログのみで継続するフェールセーフ。
    - ログレベルの解決順序（引数 > 環境変数 LOG_LEVEL > デフォルト）。
  - `kabusys.utils.process_priority` を追加。
    - Windows / POSIX（Linux, macOS, FreeBSD）に対応したプロセス優先度設定（high/normal/low）。
    - CPU affinity 設定ユーティリティを追加（指定コア数にプロセスを固定）。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`：
    - シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。スコアが全て 0 の場合に等配分へフォールバック（WARNING）。
  - `kabusys.portfolio.risk_adjustment`：
    - セクター集中制限 apply_sector_cap（売却予定銘柄の除外対応、"unknown" セクターは上限適用除外）。
    - レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear のマップ、未知レジームは警告ログを出して 1.0 でフォールバック）。
  - `kabusys.portfolio.position_sizing`：
    - 各種配分方式（risk_based / equal / score）に対応した発注株数計算。
    - 単元株（lot_size）丸め、1 銘柄上限・集計上限（available_cash）によるスケーリング、cost_buffer による保守的コスト見積もり。
    - 価格欠損時のスキップとログ出力、合計コストが available_cash を超える場合のスケールダウンと残差配分ロジックを実装。
- 研究系モジュール（部分実装）
  - `kabusys.research.factor_research` を追加（モメンタム / MA / ATR / ボラティリティ等の設計と定数を含む。DuckDB 接続を受けて prices_daily 等を参照する設計）。※ファイル途中までの実装。
- ツール
  - `kabusys.tools.paper_verification_report`：
    - Paper Trading 用の検証レポート生成スクリプトを追加。PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）を参照。
    - システム稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を集計し、閾値比較で PASS/FAIL を判定してレポート出力。
    - P95 計算、日付フィルタリング、SQL による集計を実装。
- パッケージエクスポート
  - `kabusys.portfolio.__init__` で主要関数群をエクスポート。

Changed
- （初回リリースのため変更履歴はありません）

Fixed
- 環境変数ロードと .env パーサーにおいて、実運用で見られる細かなケース（export プレフィックス、クォート内のエスケープ、インラインコメント扱いなど）に対応し、誤読による起動失敗を低減。

Notes / Implementation details
- プロセス優先度設定は起動直後に実行される設計（run_monitoring/run_execution）。権限不足の場合はログに警告を出して継続します。
- run_monitoring は監視側でも本番 sqlite_path を使用する点に注意（環境に依存せず本番 DB を参照する仕様）。
- run_execution は paper_trading 環境では DB を完全分離（data/paper_trading.db）し、実発注が行われないモックブローカーを利用する想定。
- .env はセキュリティの観点から Git にコミットしない旨をウィザードに明記。
- 一部のモジュール（研究系 factor_research など）は設計方針・定数を含むが実装が途中までの箇所があります。

セキュリティ
- .env に API トークン等の秘密情報を含める仕様のため、ウィザードと README 等で .env をリポジトリにコミットしないことを明記する設計。

今後の改善案（参考）
- factor_research の完全実装とテスト。
- 単体テスト・CI の整備（設定検証・DB 初期化ロジック・ポートフォリオロジック等）。
- 銘柄別 lot_size をサポートするための stocks マスター導入と position_sizing の拡張。
- run_monitoring/run_execution のより詳細な健全性チェック（監視テーブルへのメトリクス拡張、リトライ戦略など）。

---

注: 本 CHANGELOG は提供されたコード内容から挙動・意図を推測して記載しています。実際の変更履歴やリリースノートは開発履歴（Git コミットログ等）に基づいて作成することを推奨します。