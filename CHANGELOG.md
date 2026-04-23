# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
バージョン番号は semantic versioning に準拠します。

注: 以下の変更点は、提示されたコードベースの内容から推測してまとめた初期リリース向けの変更履歴です。

## [0.1.0] - 2026-04-23

### Added
- 基本アプリケーションの初期実装を追加
  - パッケージメタ情報: kabusys/__init__.py にバージョン "0.1.0" を設定。

- CLI 起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、SQLite / DuckDB 接続、スレッドでのエンジン実行、停止フラグ監視（data/stop_requested.flag）を実装。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し MockBrokerClient を利用可能な設計（BrokerClientFactory 経由）。
    - エンジン用 PID ファイル管理（data/execution.pid）対応。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する仕様。
    - 停止フラグ検知で安全にループ終了、KeyboardInterrupt ハンドリング。

- 設定管理
  - config.py
    - .env 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env ファイルのパース実装（export 形式、クォート／エスケープ、インラインコメントの取り扱いなど）。
    - Settings クラスを提供し、環境変数をプロパティとして安全に取得（必須変数チェック、値検証、デフォルト値の解決など）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応。
    - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH 等の環境変数を扱うプロパティを実装。

  - config_setup.py
    - 対話式ウィザードで .env を作成/更新する CLI を追加。
    - 入力のマスク表示、既存値の再利用、書き込みフォーマットに関する仕組みを実装。

  - validate_config.py
    - 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリチェック、config/*.yaml の存在と YAML パース検証（PyYAML があれば実行）を実装。
    - --strict オプションで警告を失敗扱いにするモードを提供。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等重配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコア合計が 0 の場合のフォールバックと警告を実装。

  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装（当日売却予定銘柄の除外、"unknown" セクターは制限対象外）。
    - 市場レジームに応じた資金乗数 calc_regime_multiplier を実装（bull/neutral/bear とフォールバック挙動）。

  - portfolio/position_sizing.py
    - position sizes の計算ロジックを実装（allocation_method: "risk_based", "equal", "score"）。
    - 単元株（lot_size）丸め、per-position および aggregate のキャップ、コストバッファによる保守的見積もり、スケーリング＆残余配分ロジックを実装。
    - 空価格や価格欠損時のスキップ、ログ出力あり。

  - portfolio/__init__.py
    - 上記関数を公開するパッケージエントリを追加。

- 監視／ツール
  - tools/paper_verification_report.py
    - Paper Trading 結果検証レポート生成ツールを追加。
    - 稼働率、注文成功率（fill rate）、送信率、P95 レイテンシ等の指標を集計・表示。閾値による PASS/FAIL 判定を実装。
    - コマンドライン引数で期間指定（--from/--to）および DB パス指定（--db）に対応。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR / 引数による設定解決、既存ハンドラのクリーンアップ、ファイル出力失敗時のフォールバック実装あり。

  - utils/process_priority.py
    - Windows と POSIX の差分を吸収するプロセス優先度／CPU affinity 設定ユーティリティを追加。
    - set_process_priority(level) で high/normal/low を設定、set_cpu_affinity(cpu_count) で最初の N コアに固定可能。権限不足や未対応 OS は警告でスキップ。

- データ分析（研究用）
  - research/factor_research.py（部分実装）
    - DuckDB を用いたファクター計算モジュール（モメンタム、MA200、ATR、出来高等）を設計。関数ベースで prices_daily / raw_financials を参照する方針を明記（コードは一部未完）。

### Changed
- （初版のため過去変更なし）

### Fixed
- （初版のため過去修正なし）

### Deprecated
- （該当なし）

### Removed
- （該当なし）

### Security
- （該当なし）

---

## 既知の制約・注意事項（コード内コメントに基づく）
- .env パースは多くのケースを想定しているが、特殊なエスケープや複雑な構文は未検証。
- run_monitoring は「監視は環境にかかわらず本番 sqlite_path を使う」設計のため、開発中に誤って本番 DB を参照しないよう注意が必要。
- position_sizing の将来的な拡張点:
  - 銘柄別の lot_size を持たせる設計への拡張（TODO コメントあり）。
  - price が欠損（0.0）だった場合のフォールバック価格（前日終値や取得原価）の考慮が未実装。
- プロセス優先度 / CPU affinity の設定は権限不足やプラットフォーム差分で失敗する可能性があり、その場合はログに警告が出て処理は継続する設計。
- logging_setup はログディレクトリの作成に失敗した場合、ファイル出力を無効化して標準出力のみで継続する。

---

この変更履歴は提示されたソースコードからの推測に基づいて作成しています。追加のファイルやコミット履歴があれば、より正確で詳細な CHANGELOG を作成できます。必要であればコミット単位や機能単位での分割（例: リリースノートの細分化）も作成します。