# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

なお、本CHANGELOGは提供されたコードベースの内容から推測して作成しています。

## [0.1.0] - 2026-04-23

初回リリース。日本株自動売買システム「KabuSys」のコアユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、設定関連ツール類を追加。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py
    - パッケージ名とバージョン（0.1.0）を定義。

- 起動スクリプト
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はログ警告の上でデフォルトにフォールバック。
    - 停止フラグファイル（data/stop_requested.flag）を監視して安全にループ終了。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する旨の挙動（明示）。
    - duckdb 接続と sqlite 接続の初期化を行い、例外を捕捉してロギング。

  - src/kabusys/run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB を使用（data/paper_trading.db がデフォルト）して本番 DB と分離。
    - BrokerClientFactory を利用してブローカークライアントを抽象化。
    - OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine の組み立てと実行スレッド管理を実装。
    - 停止フラグと PID ファイルの取り扱い（停止検知で安全停止、PID ファイルパス指定）。

- 設定管理
  - src/kabusys/config.py
    - Settings クラスを追加。環境変数から各種設定を取得するプロパティを提供（DB パス、API トークン、ログレベル、KABUSYS_ENV 等）。
    - .env 自動読み込み機構（プロジェクトルート検出：.git または pyproject.toml を基準）。
    - .env のパースは export プレフィックス対応、引用符内のエスケープ、インラインコメント処理などをサポート。
    - PAPER_FILL_MODE の妥当性チェック、KABUSYS_ENV / LOG_LEVEL の検証ロジックを実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。

  - src/kabusys/config_setup.py
    - 対話式 .env 作成/更新ウィザードを追加。
    - 主要な設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス, LOG_LEVEL, など）のプロンプトを実装。シークレットはマスク表示。
    - 既存 .env の読み込み・既存値再利用、確認プロンプト、ファイル書き込みを実装。

  - src/kabusys/validate_config.py
    - 設定検証 CLI を追加。必須環境変数、KABUSYS_ENV の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在チェック（PyYAML があればパース検証）等を実施。
    - --strict オプションで警告も失敗扱いにできる。
    - 本番環境（KABUSYS_ENV=live）向けの追加ガード（LINE トークン未設定や KILL_FLAG_CLEAR_ON_START の危険設定に対する警告）。

- ロギング・プロセス管理ユーティリティ
  - src/kabusys/utils/logging_setup.py
    - 統一ログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保存）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL の解決順やファイルハンドラ作成失敗時のフォールバックを実装。
    - 既存ハンドラのクリア処理を行い二重設定を防止。

  - src/kabusys/utils/process_priority.py
    - プロセス優先度（high/normal/low）と CPU affinity 設定ユーティリティを追加。
    - Windows と POSIX（Linux/Mac/FreeBSD）の差分を吸収して動作。権限不足時は警告ログを出して安全にスキップ。

- ポートフォリオ構築ライブラリ（純粋関数）
  - src/kabusys/portfolio/portfolio_builder.py
    - 候補選定（スコア降順で上位 N）select_candidates を追加。
    - 等重配分 calc_equal_weights、スコア加重 calc_score_weights（全スコア 0 の場合は等重にフォールバック）を追加。

  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中上限を適用する apply_sector_cap を追加（既存ポジションのセクター比率を計算して候補をフィルタ）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を追加（bull/neutral/bear をマッピング。未知のレジームは 1.0 でフォールバック）。

  - src/kabusys/portfolio/position_sizing.py
    - position sizing ロジックを追加。allocation_method として "risk_based", "equal", "score" をサポート。
    - 単元株（lot_size）での丸め、1 銘柄上限・aggregate cap（available_cash）によるスケールダウン、cost_buffer を考慮した保守的見積り、残差に基づく追加配分ロジック等を実装。

  - src/kabusys/portfolio/__init__.py
    - 上記関数群をエクスポートするパッケージ入口を追加。

- 研究／分析ユーティリティ（スケルトン）
  - src/kabusys/research/factor_research.py
    - Momentum / Value / Volatility / Liquidity 等のファクター計算モジュールを追加（DuckDB 接続を受け prices_daily / raw_financials を参照する設計）。
    - モメンタム計算 calc_momentum の基本方針と定数を実装（注：ソースの末尾に未完の部分あり。以降の実装は継続予定）。

- ツール類
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 指標: 稼働率 (uptime)、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシなどを算出して PASS/FAIL 判定を行う。
    - 日付フィルタ（--from/--to）、DB 指定（--db / 環境変数 PAPER_TRADING_SQLITE_PATH）をサポート。
    - P95 計算ロジックと各種フォールバックを実装。

### Changed
- （初回リリースのため変更履歴は特になし）

### Fixed
- （初回リリースのため修正履歴は特になし）

### Notes / Implementation details
- 監視（run_monitoring）はコードコメント通り「環境にかかわらず」monitoring 用 DB（Settings.sqlite_path）を使用する実装になっているため、開発環境での監視データを本番 DB に混ぜたくない場合は設定で sqlite_path を変更するか実行ポリシーの見直しが必要。
- run_execution は paper_trading モード時に paper_sqlite_path を使い、本番 DB とペーパートレード DB を分離する設計。RiskManager 初期化時に broker.get_available_cash() を初期ポートフォリオ値として参照するため、Broker 実装が期待どおりの値を返すことが依存条件となる。
- .env パーサは export プレフィックス・引用符内エスケープ・インラインコメントの扱いなど多くのケースをサポートするが、極端なケースは想定外の動作をする可能性がある（詳細は config.py の実装を参照）。
- logging_setup はログディレクトリ作成に失敗した場合でも標準出力ログは継続するようフォールバック処理を行う（cron 等で権限が厳しい環境でも安全に起動可能）。
- research/factor_research.py の calc_momentum 関数以下がソース提供時点で未完（末尾が途中）であるため、完全なファクター計算は今後の実装が必要。

### Known Issues / TODO
- factor_research モジュールの一部（calc_momentum の続き）が未完。ファクター算出の完全実装とユニットテストが必要。
- position_sizing の lot_size は現状グローバル固定（引数で渡せるが銘柄別単元対応は未実装）。将来的に銘柄別 lot_map をサポートする予定（コード内コメントあり）。
- apply_sector_cap 内の price が 0.0 の場合のフォールバック（過小見積の問題）に対する TODO コメントあり。前日終値や取得原価へのフォールバック実装検討が示唆されている。

---

今後のリリースでは以下を予定しています（候補）:
- factor_research の完遂とユニットテスト追加
- 戦略および execution コンポーネントの詳細実装と統合テスト
- 各種ログ・モニタリング指標の拡充とアラート連携（LINE 等）

（以上）