# Changelog

すべての重要な変更は Keep a Changelog の方針に従って記載しています。  
このファイルはコードベースから推測して作成した初回リリース相当の変更履歴です（実装ファイル: src/kabusys/...）。

フォーマット:
- Unreleased / リリースバージョンごとにカテゴリ (Added, Changed, Fixed, Removed, Security) を分けています。

## [0.1.0] - 2026-04-21

### Added
- 初期リリース: KabuSys 自動売買フレームワークの基本コンポーネントを追加
  - パッケージ初期化情報: src/kabusys/__init__.py にバージョン "0.1.0" を設定。
- 実行・監視用エントリポイント（起動スクリプト）
  - run_execution: src/kabusys/run_execution.py
    - ExecutionEngine を起動するためのスクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db をデフォルト）を使用し、MockBrokerClient を利用して本番 DB と完全分離して動作する仕様。
    - 実行中の PID 管理（data/execution.pid）と停止フラグ（data/stop_requested.flag）の監視に対応。スレッドでエンジンを実行し停止フラグ検知で安全に停止する。
  - run_monitoring: src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず production 用 sqlite_path を使用して監視 DB を初期化・更新する（監視テーブルの整備）。
- 設定管理・セットアップ・検証ツール
  - 設定管理: src/kabusys/config.py
    - プロジェクトルートを .git / pyproject.toml から自動検出して .env の自動読み込みを行う（優先順: OS 環境変数 > .env.local > .env）。
    - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env パースはクォート・エスケープ・コメント処理に対応。
    - Settings クラスで各種設定値に対するプロパティを提供（J-Quants, kabu API, DB パス、ログ等）。値の検証ロジックを組み込み（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。
  - 設定ウィザード: src/kabusys/config_setup.py
    - 対話式で .env を作成・更新する CLI。シークレット項目はマスク表示。変更確認後 .env に書き出す。
  - 設定検証: src/kabusys/validate_config.py
    - .env と config/*.yaml の存在・簡易検証を行う CLI。
    - 必須環境変数チェック、KABUSYS_ENV の値チェック、DB パスの親ディレクトリチェック、YAML パース（PyYAML が利用可能な場合）等を実行。
    - --strict オプションで警告を FAIL 扱いにできる。
- ロギング・プロセス管理ユーティリティ
  - ロギング設定: src/kabusys/utils/logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション, 30 日保持）を設定するユーティリティ。
    - ログディレクトリの自動作成、LOG_LEVEL / LOG_DIR 環境変数の解決順、失敗時のフォールバックを実装。
  - プロセス優先度 / CPU affinity: src/kabusys/utils/process_priority.py
    - psutil を利用して Windows / POSIX 間の差を吸収しプロセス優先度を設定。CPU affinity を最初の N コアに固定するユーティリティを提供。
    - 権限不足や未サポート OS の場合は警告を出してスキップ。
- ポートフォリオ構築（純粋関数群）
  - portfolio_builder: src/kabusys/portfolio/portfolio_builder.py
    - シグナルのソート・候補選定 (select_candidates)。
    - 等重み (calc_equal_weights)、スコア加重 (calc_score_weights)。全スコアが 0 の場合は等重みへフォールバックし警告を出す。
  - risk_adjustment: src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限を適用して候補をフィルタする apply_sector_cap。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（"bull"/"neutral"/"bear" をマッピング、未知のレジームは 1.0 でフォールバックし警告）。
  - position_sizing: src/kabusys/portfolio/position_sizing.py
    - 発注株数算出ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、1 銘柄上限・利用率上限・aggregate cap のスケーリング・cost_buffer（スリッページ/手数料見積り）を考慮した配分アルゴリズム。
    - price 欠損時のスキップやログ出力、aggregate スケールダウン時の端数処理ロジックを実装。
- リサーチ・ファクター計算（骨格）
  - src/kabusys/research/factor_research.py
    - Momentum 等のファクター計算の設計と一部実装（DuckDB 接続で prices_daily / raw_financials を参照する前提）。モメンタム計算の定数等を定義（1M/3M/6M、MA200、ATR 等）。
- Paper Trading 検証レポートツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading の SQLite（PAPER_TRADING_SQLITE_PATH）のログから稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計・判定してレポートを標準出力に出力する CLI。
    - デフォルト閾値を設定（稼働率 99.0%、成立率 90.0%、送信率 95.0%、P95 レイテンシ 200ms）。
    - --from/--to/--db オプションをサポート。

### Changed
- 監視の DB 接続ポリシー（設計決定）
  - run_monitoring は KABUSYS_ENV の値に関わらず settings.sqlite_path（本番用の SQLite パス）を使用して監視データを記録・参照する設計となっている点を明示（隔離された paper DB は run_execution 側で使用）。
- .env 自動ロードの既存環境変数保護
  - config モジュールの .env 読み込みは OS 環境変数を保護するため protected set を利用している（.env.local は上書きできるが OS 環境変数は優先）。

### Fixed
- （初期リリースのため特定のバグ修正履歴はなし。コード内に権限不足等に備えた警告・フォールバック処理を多数実装しているため、実行時の失敗を緩和する設計になっています。）

### Deprecated
- なし

### Security
- .env にシークレットを含むため、config_setup のヘッダに「.env は絶対に Git にコミットしないこと」と明記。
- 必須な機密情報（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は Settings で未設定時に ValueError を投げて起動を止める仕組みを提供。

### Notes / TODO（ソース内コメントに基づく）
- price が欠損した場合のフォールバック価格（前日終値や取得原価）を用いる改善案がコメントとして残されている（portfolio/risk_adjustment.py）。
- 将来的に銘柄毎の単元数をサポートするため position_sizing の lot_size 固定実装を拡張する余地あり（コメントあり）。
- research/factor_research.py はモメンタム計算の実装が途中で切れている箇所があり、完全実装は今後の作業を想定。

---

この CHANGELOG は、提供されたソースコードの内容とコメントから推測して作成しています。実際のコミット履歴やリリースノートが存在する場合はそれに合わせて適宜更新してください。