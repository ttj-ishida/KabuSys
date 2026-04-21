# Changelog

すべての変更は Keep a Changelog の形式に準拠します。  
このファイルは、コードベースの内容から推測して作成しています。

フォーマット:
- Unreleased: 今後の未リリース変更（現時点ではなし）
- 各リリース: 主要な追加・変更点をカテゴリ別に記載

## [Unreleased]
（現在報告すべき未リリース変更はありません）

---

## [0.1.0] - Initial release
初回リリース。自動売買システム KabuSys の基盤機能群を実装・追加。

### Added
- 基本パッケージ情報
  - パッケージバージョンを src/kabusys/__init__.py にて `__version__ = "0.1.0"` として定義。

- 環境設定・読み込み
  - .env 自動ロード機能（プロジェクトルートの判定: .git または pyproject.toml を探索）。
  - .env および .env.local を OS 環境変数を尊重して読み込む実装（環境変数上書き制御あり）。
  - 複雑な .env 行のパーシング機能を実装（コメント、export プレフィックス、クォートとエスケープ対応）。
  - Settings クラス（src/kabusys/config.py）を追加し、主要な環境変数の取得・バリデーションを提供。
    - DB パス、KABUSYS_ENV、ログレベル、paper trading 用設定などのプロパティを提供。
    - PAPER_FILL_MODE の妥当性チェック等の細かい検証を実装。

- 設定ウィザード CLI
  - src/kabusys/config_setup.py: 対話式ウィザードで .env の初期作成・更新を支援するツールを追加。
  - 設定項目定義（KABUSYS_ENV、J-Quants トークン、kabu API パスワード、DB パス、LINE トークン等）を用意。
  - .env 読み取り／書き込みユーティリティを実装。

- 設定検証 CLI
  - src/kabusys/validate_config.py: .env と config/*.yaml の事前チェックツールを追加。
  - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリ確認、YAML のパースチェック（PyYAML 未インストール時はスキップ）、本番向けガード条件などを実装。
  - --strict オプションにより警告を FAIL 扱いにできる。

- 実行エントリ / 監視エントリ
  - src/kabusys/run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を high に設定。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db）を使用して本番 DB と完全分離。
    - ブローカークライアント工場（BrokerClientFactory）を用いて適切なクライアントを生成。
    - OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立て・起動ロジック（スレッド実行、停止フラグ検出、PID ファイルパス設定）。
  - src/kabusys/run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。不正値時はデフォルトにフォールバック。
    - 監視は常に本番 sqlite_path を使用して監視 DB を初期化（init_monitoring_db）。
    - 停止フラグファイル（data/stop_requested.flag）検出で安全にループ終了。

- データベース / 分析連携
  - DuckDB 接続サポート（duckdb を使用して分析向け DB を接続）。
  - 監視 DB 初期化ユーティリティ（init_monitoring_db の呼び出し）を各起動スクリプトから行うことでテーブル存在を保証。

- ロギング・プロセス管理ユーティリティ
  - src/kabusys/utils/logging_setup.py:
    - ルートロガーへ StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定するユーティリティを追加。
    - ログレベル・ログディレクトリの解決ロジック、既存ハンドラのクリーンアップ、ログディレクトリ作成失敗時のフォールバックを実装。
  - src/kabusys/utils/process_priority.py:
    - プロセス優先度（high|normal|low）を Windows/Linux/Mac 向けに吸収するユーティリティを追加。
    - CPU affinity 設定ユーティリティ（最初の N コアに固定）を提供。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。

- ポートフォリオ構築モジュール
  - src/kabusys/portfolio/portfolio_builder.py:
    - 候補選定(select_candidates)、等配分(calc_equal_weights)、スコア加重(calc_score_weights) を実装。
    - スコア全0 フォールバックの警告ロジックあり。
  - src/kabusys/portfolio/risk_adjustment.py:
    - セクター集中制限の適用 (apply_sector_cap)。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear 等）を実装。
  - src/kabusys/portfolio/position_sizing.py:
    - 発注株数計算 calc_position_sizes を実装（risk_based / equal / score の配分方式、単元株丸め、per-stock 上限、aggregate cap のスケールダウンロジック、cost_buffer を考慮した安全弁）。
  - パッケージエクスポート（src/kabusys/portfolio/__init__.py）を用意。

- 研究・分析モジュール（基盤）
  - src/kabusys/research/factor_research.py:
    - ファクター計算モジュール（モメンタム、MA200乖離、ATR、出来高関連、財務系ファクター等）設計・骨子を追加。DuckDB 接続を受けて prices_daily/raw_financials を参照する想定の関数群を開始（calc_momentum 等の実装方針と定数を含む。注: 一部関数は実装途中の可能性あり）。

- 運用ツール
  - src/kabusys/tools/paper_verification_report.py:
    - ペーパートレード検証レポート生成ツールを追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）を集計し PASS/FAIL を判定する。
    - デフォルト閾値: 稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms。
    - --from/--to/--db オプションをサポート。PAPER_TRADING_SQLITE_PATH 環境変数にも対応。
    - DB 存在チェックや SQL 実行時の OperationalError に対するフォールバックを実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Internal
- 各モジュールでロギングを活用するように実装（logger を使用）。
- 起動スクリプトは停止フラグ / PID 管理を行い安全な停止をサポート。
- Paper Trading と Live の DB 分離を明確に実装して本番データの汚染を防止。

### Notes / Known limitations
- research/factor_research.py の calc_momentum 等はいくつか実装継続中の箇所が見られる（ファイル末尾で途中で終わっている可能性がある）。本格運用前に完全な実装とテストが必要。
- process_priority の一部処理は OS 権限（nice、プロセス優先度設定権限）に依存するため、権限不足時には警告が出てスキップされる。
- position_sizing の lot_size は現状全銘柄共通の想定。将来的に銘柄別単元対応が予定されている旨の TODO コメントあり。
- .env の自動ロードはプロジェクトルート検出に依存。ルートが特定できない場合は自動ロードをスキップする設計。

---

（注）この CHANGELOG は提供されたソースコードの内容から推測して作成したものであり、実際のコミット履歴やリリースノートとは差異がある可能性があります。必要であれば、実際の git ログやリリース日付、コミット単位の変更点を反映して更新してください。