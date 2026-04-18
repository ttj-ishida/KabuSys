CHANGELOG
=========

すべての注目すべき変更を記録します。本ドキュメントは「Keep a Changelog」の形式に準拠します。

フォーマットの説明:
- 変更はセマンティックにカテゴリ分け（Added, Changed, Fixed, Removed, Security 等）しています。
- 日付はリリース日を表します。

## [Unreleased]
- 進行中 / 未完成の実装や既知の改善点を列挙します。
  - research/factor_research.py のモメンタム計算関数は実装途中（ソースが途中で切れている）で、追加の完成作業が必要。
  - position_sizing.calc_position_sizes における lot_size を銘柄毎に設定する拡張（stocks マスタによる lot_map）の TODO。
  - risk_adjustment.apply_sector_cap で price が欠損した場合のフォールバック（前日終値や取得原価など）の改善予定。
  - ログディレクトリ作成/ファイルハンドラ作成失敗時の挙動は現状 StreamHandler にフォールバックしているが、失敗原因診断やリトライの改善を検討中。
  - 単体テストやドキュメント（PortfolioConstruction.md 等）の整備が必要。

---

## [0.1.0] - 2026-04-18
初期リリース — 基本的な自動売買システムのコアユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、検証ツール群を実装。

### Added
- CLI / 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading 時に専用の Paper Trading SQLite を使用（settings.paper_sqlite_path）。MockBrokerClient を利用して本番 DB と完全分離する想定。
    - プロセス優先度を最初に "high" に設定。
    - 停止フラグ（data/stop_requested.flag）検知により安全に停止可能。
    - 実行時の PID ファイル管理（data/execution.pid）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視用 DB は環境に関わらず本番 sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグ検知でループ終了、KeyboardInterrupt に対応。
- 設定管理・検証・セットアップ
  - config.py
    - Settings クラスにより環境変数ベースの設定取得を統一。多くのプロパティ（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、KABUSYS_ENV 等）を提供。
    - プロジェクトルート検出（.git または pyproject.toml）により .env 自動ロード機能を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化をサポート。
    - 環境変数の検証（有効な列挙値チェックや型変換）を行う。
  - config_setup.py
    - 対話式ウィザードで .env を生成・更新する CLI。
    - シークレット項目のマスク表示、選択肢サポート、既存 .env の読み込み／上書き保存機能を実装。
  - validate_config.py
    - 起動前に .env と config/*.yaml をチェックする CLI。
    - 必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML のパース検証（PyYAML がインストールされている場合）等を実装。
    - --strict モードで警告を FAIL 扱いにできる。
- ユーティリティ
  - utils/logging_setup.py
    - 共通のロギング初期化関数 setup_logging を提供。
    - stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler）をルートロガーに設定。デフォルトログディレクトリは logs/、30日分を保持。
    - 環境変数 LOG_LEVEL / LOG_DIR を尊重し、既存ハンドラをクリアして再設定する。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。
    - Windows と POSIX（Linux/Mac/FreeBSD）を吸収する実装で、psutil を利用してプロセス優先度（nice / HIGH_PRIORITY_CLASS）や CPU affinity を設定。アクセス権限不足等は警告でスキップ。
- ポートフォリオ構築モジュール（純粋関数群・DB 参照なし）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順（同点は signal_rank でタイブレーク）で上位 N を選択。
    - calc_equal_weights: 等金額配分（各銘柄 weight = 1/N）。
    - calc_score_weights: スコア正規化による重み計算。全スコアが 0 の場合は等金額にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中を抑制するフィルタ。既存保有のセクター比率が max_sector_pct を超える場合、そのセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じたレバレッジ乗数を返す（デフォルトマップ: bull=1.0, neutral=0.7, bear=0.3）。未知レジームは警告とともに 1.0 にフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: 重み・候補・ポートフォリオ情報から銘柄ごとの発注株数を決定。サポート機能:
      - allocation_method: "risk_based" / "equal" / "score"
      - 単元株（lot_size）での丸め処理
      - per-stock 上限（max_position_pct）、aggregate cap（available_cash）によるスケーリング
      - cost_buffer による手数料/スリッページを加味した保守的見積り
      - スケーリング時の端数処理は残差に基づき lot_size 単位で再配分する実装
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から期間指定で検証レポートを生成する CLI。
    - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等。
    - デフォルト閾値を定め、PASS/FAIL を判定（閾値: uptime >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 latency <= 200 ms）。
    - --from/--to/--db オプションに対応。
- その他
  - パッケージメタ情報: kabusys.__version__ = "0.1.0"
  - モジュール公開: kabusys.portfolio の __all__ に主要関数を追加して外部利用を簡易化。

### Changed
- 初版のため該当なし。

### Fixed
- 初版のため該当なし。

### Removed
- 初版のため該当なし。

### Security
- 環境変数の自動ロードでは OS 環境変数を保護するため protected セット（既存の os.environ のキー）を考慮して上書きを制御。

---

付記 / 設計上の注意
- 設定・起動時に重要な環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）が未設定の場合、runtime で ValueError を発生させる設計になっています。validate_config CLI で事前検証することを推奨します。
- run_monitoring/run_execution といった長時間稼働プロセスは停止用フラグファイル（data/stop_requested.flag）を検出して安全停止する仕組みを持っています。運用時は stop flag と kill flag（KILL_FLAG_*）の取り扱いに注意してください。
- Paper Trading と Live の DB は分離する設計（paper_sqlite_path）で、本番 DB を誤って汚さない配慮がなされています。

---

作成: 自動生成（コードベースの解析に基づく推測）
日付: 2026-04-18