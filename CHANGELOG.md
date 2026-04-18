# Changelog

すべての重要な変更点を記録します。本ファイルは Keep a Changelog の形式に準拠しています。セマンティックバージョニングを採用します。

## [0.1.0] - 2026-04-18

### Added
- 初回リリース。KabuSys の基本機能群を追加。
  - パッケージ情報
    - パッケージバージョンを `__version__ = "0.1.0"` として設定。
  - 実行スクリプト
    - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
      - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 停止はプロジェクト内の `data/stop_requested.flag` ファイルで検出。
      - 監視用 DB は環境にかかわらず本番 `sqlite_path` を使用する設計。
      - 起動時にプロセス優先度を "high" に設定。
      - SQLite / DuckDB 接続を開き、監視テーブルの初期化を行う。
      - `check_once()` 実行時の例外はログに記録して次サイクルに継続。
    - run_execution: ExecutionEngine 起動スクリプトを追加。
      - `KABUSYS_ENV=paper_trading` の場合は paper 用専用 SQLite（デフォルト `data/paper_trading.db`）を使用し、本番 DB と分離。
      - 停止フラグ `data/stop_requested.flag` の存在で起動を抑止または実行中に停止。
      - ExecutionEngine は別スレッドで実行し、PID ファイル管理・安全シャットダウンを行う。
      - 起動時にプロセス優先度を "high" に設定。
      - BrokerClient の抽象化（BrokerClientFactory）を利用して本番 / モックを切り替え。
  - 設定管理
    - config.Settings クラスを追加。
      - 各種環境変数（J-Quants, kabu API, DB パス, ログ設定, 監視閾値など）をプロパティとして提供。
      - `env`（KABUSYS_ENV）は `development`/`paper_trading`/`live` の検証を行う。
      - `paper_fill_mode` のバリデーション（"instant"|"partial"|"never"|"reject"）。
      - `paper_sqlite_path`, `pid_file_path`, 各種閾値プロパティを提供。
    - 自動 .env 読み込み機能を追加
      - プロジェクトルート（.git または pyproject.toml を基準）を自動検出して `.env` / `.env.local` を順に読み込む（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
      - `.env` のパースは export 形式、クォート文字列、エスケープ、インラインコメント等に対応。
  - 設定ユーティリティ & CLI
    - config_setup: 対話式ウィザードで `.env` を初期作成・更新する CLI を追加。
      - シークレット項目はマスクしてプロンプト表示。
      - デフォルト値・選択肢・説明文をサポート。
      - 最終的に `.env` を安全に書き出す。
    - validate_config: 起動前の設定検証 CLI を追加。
      - 必須環境変数チェック（例: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`）。
      - KABUSYS_ENV / LOG_LEVEL の妥当性検証。
      - DUCKDB / SQLITE パスの親ディレクトリ存在確認。
      - `config/*.yaml` の存在確認および PyYAML が利用可能な場合はパース検証（PyYAML 未インストール時はスキップと警告）。
      - `--strict` オプションで警告も失敗扱いにできる。
  - ポートフォリオ構築（純粋関数群）
    - portfolio.portfolio_builder
      - select_candidates: BUY シグナルをスコア降順で選択、同点は signal_rank でタイブレーク。
      - calc_equal_weights: 等金額配分の重みを算出。
      - calc_score_weights: スコア比率で重み付け（全スコアが 0 の場合は等分配にフォールバックして WARNING）。
    - portfolio.risk_adjustment
      - apply_sector_cap: セクター集中上限チェック。既存ポジションのセクター比率が閾値を超える場合に当該セクターの新規候補を除外（"unknown" セクターは除外対象外）。
      - calc_regime_multiplier: 市場レジーム (bull/neutral/bear) に応じた投下資金乗数を返す（未知のレジームは 1.0 でフォールバックし警告）。
    - portfolio.position_sizing
      - calc_position_sizes: 各銘柄の発注株数算出ロジックを実装。
        - `allocation_method` に "risk_based" / "equal" / "score" をサポート。
        - risk_based: 損切り幅・許容リスク率からベース株数を算出。
        - equal/score: 重みと max_utilization を基に算出。
        - lot_size（単元株）で丸め、単元単位での切り捨て・付与ロジックを実装。
        - aggregate cap: 全体コストが available_cash を超える場合にスケールダウンし、残余キャッシュで端数分を再配分するロジックを実装。
        - cost_buffer を考慮して手数料・スリッページを保守的に見積もる。
  - ユーティリティ
    - utils.logging_setup
      - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30 日保持）を設定するユーティリティを追加。
      - ログディレクトリ作成に失敗した場合はファイル出力をスキップし、コンソール出力のみで継続。
      - stdout を利用することで cron 等からの標準出力リダイレクトを考慮。
    - utils.process_priority
      - プラットフォーム差分（Windows / POSIX）を吸収してプロセス優先度や CPU affinity を設定するユーティリティを追加。
      - psutil を用い、サポートされない環境や権限不足時は警告を出してスキップ。
  - モニタリング DB 初期化
    - monitoring.monitoring_db:init_monitoring_db を run_monitoring / run_execution の起動時に呼び出し、監視テーブルの存在を保証（冪等）。
  - Paper Trading 検証ツール
    - tools.paper_verification_report: Paper Trading 用 SQLite を解析して検証レポートを生成するスクリプトを追加。
      - 指標: 稼働率 (uptime), 注文成功率 (fill rate), 送信率 (send rate), レイテンシ（avg, max, P95）等。
      - デフォルト閾値:
        - 稼働率 >= 99.0%
        - 注文成功率 >= 90.0%
        - 送信率 >= 95.0%
        - P95 レイテンシ <= 200 ms
      - CLI 引数で期間（--from, --to）と DB パス（--db）を指定可能。
      - P95 の算出ロジックと欠損データへの耐性（データ不足時は N/A 表示）。
  - 研究用ファクター計算（着手）
    - research.factor_research: モメンタム等のファクター計算モジュールの骨格を追加（DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計）。
      - モメンタム計算（calc_momentum）などの定義が始まっており、長期 MA/各種リターン・ATR 等の計算方針が記載されている（実装は継続中）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Known limitations
- .env 自動読み込みはプロジェクトルートの検出に依存するため、パッケージ配布後などプロジェクト構造が変わる場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して手動管理することを推奨します。
- position_sizing の価格フォールバック（価格が欠損した場合の扱い）や銘柄別 lot_size の拡張は TODO としてコード内で指摘されています。
- research.factor_research の一部機能は作成途中です。詳細なファクター計算は今後の実装で追加予定です。
- PyYAML がインストールされていない環境では validate_config の YAML 検証がスキップされ、警告のみ出力されます。

---
このリリース以降は変更点をバージョン単位で追記していきます。必要であれば、各モジュールの詳細な設計メモや API リファレンスを別途作成します。