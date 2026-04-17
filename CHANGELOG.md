# Changelog

すべての変更は Keep a Changelog の慣習に従い、重要度の高い変更をカテゴリ別に記載しています。  
言語は日本語です。

## [Unreleased]

## [0.1.0] - 2026-04-17

### Added
- 基本パッケージ情報を追加
  - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

- 実行用エントリポイント（デーモン / 起動スクリプト）
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV に関わらず本番用 sqlite_path を使用する設計。
    - stop フラグ（data/stop_requested.flag）検知による安全停止、KeyboardInterrupt ハンドリング、SQLite / DuckDB 接続のクリーンアップを実装。
    - 起動時にプロセス優先度を "high" に設定する処理を呼び出し。

  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を用いた動的ブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の非同期実行（スレッド）を実装。
    - 停止フラグ（data/stop_requested.flag）検出で Engine.stop() を呼び出して安全に停止。
    - PID ファイルパス管理をサポート。

- 設定読み込み・管理
  - src/kabusys/config.py
    - .env ファイルと環境変数から設定を読み込む機能を実装。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）。これにより CWD に依存せず .env 自動読み込みが可能。
    - .env / .env.local の読み込み順序、OS 環境変数保護（protected）を考慮した読み込みロジックを実装。
    - Settings クラスを追加し、J-Quants / kabu API / DB パス /監視・システム設定などのプロパティを提供。
    - PAPER_FILL_MODE の検証（"instant" | "partial" | "never" | "reject"）や KABUSYS_ENV 検証（development/paper_trading/live）を行う。
    - デフォルト値・パスは ducks/SQLite などを含む合理的なデフォルトを提供。

  - src/kabusys/config_setup.py
    - 対話式 .env 設定ウィザードを追加。
    - J-Quants トークンや kabu API パスワードなどの必須項目や、DB パス、ログレベル、KILL フラグ設定などを対話的に作成・更新可能。
    - 既存 .env の読み込み、シークレットマスク表示、保存前確認を実装。
    - .env の書式を定義して安全にファイルを書き出す。

  - src/kabusys/validate_config.py
    - 起動前に環境変数や config/*.yaml を検証する CLI を追加。
    - 必須環境変数のチェック、KABUSYS_ENV の妥当性、LOG_LEVEL の妥当性、DB パスの親ディレクトリチェック、YAML ファイルの存在・パースチェック（PyYAML 利用可の場合）などを実行。
    - KABUSYS_ENV=live の場合の追加注意（LINE 通知設定の有無、KILL_FLAG_CLEAR_ON_START の危険性）を警告。
    - --strict オプションで警告を FAIL として扱う機能を追加。

- ユーティリティ
  - src/kabusys/utils/process_priority.py
    - プロセス優先度設定ユーティリティを追加（クロスプラットフォーム差異を吸収）。
    - Windows（psutil の PRIORITY クラス）と POSIX（nice 値）に対応。
    - set_process_priority(level: "high"|"normal"|"low")、set_cpu_affinity(cpu_count: int|None) を提供。
    - 権限不足や未サポート環境時は警告を出して安全にフォールバック。

- ポートフォリオ構築関連（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - 候補選定 select_candidates（スコア降順、tie-breaker で signal_rank）を追加。
    - 重み計算 calc_equal_weights（等金額）および calc_score_weights（スコア正規化、全て 0 の場合は等金額にフォールバック）を追加。

  - src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap（セクター集中制限。既存保有のセクター比率が閾値を超える場合、新規候補を除外）を追加。
    - calc_regime_multiplier（市場レジームに応じた投下資金乗数）を追加。既定値マップ: bull=1.0, neutral=0.7, bear=0.3。未知レジームは 1.0 にフォールバック。

  - src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes を追加。以下の特徴を持つ:
      - allocation_method: "risk_based"（リスクベース）, "equal", "score" をサポート。
      - 単元株（lot_size）で丸め、1 銘柄上限（max_position_pct）、利用可能現金で aggregate cap を実施。
      - cost_buffer により手数料・スリッページを保守的に見積もる。
      - total_cost が available_cash を超える場合にスケールダウンし、残余キャッシュで残差分を lot 単位で再配分するアルゴリズムを実装。
      - 設計上の TODO（将来的な銘柄別 lot_size サポート）を注記。

  - src/kabusys/portfolio/__init__.py
    - 上記関数を公開（パッケージエクスポート）。

- モニタリング / 実行の DB 初期化
  - 各スクリプトで監視用 DB テーブルの初期化を保証する init_monitoring_db 呼び出しを追加（冪等）。

- Paper Trading 検証ツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 用 SQLite DB を解析して検証レポートを生成する CLI を追加。
    - 指標:
      - 稼働率（uptime_pct）、総ポーリング数、エラー数
      - 注文成功率（Filled / Created）、送信率（Sent / Created）
      - リスク却下数（risk_logs）
      - API レイテンシ（avg / max / P95）
    - P95 計算ロジックを実装。期間フィルタ（--from / --to）をサポート。
    - デフォルト閾値（PASS/FAIL 判定）を設定:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - DB が存在しない場合やテーブルが無い場合は妥当な N/A / フェールセーフを返す実装。

- リサーチ（DuckDB ベースのファクター計算）
  - src/kabusys/research/factor_research.py
    - DuckDB 接続を受け取り、prices_daily / raw_financials からファクターを算出する関数を実装（部分実装: モメンタム / ボラティリティ系）。
    - calc_momentum: 1m/3m/6m リターン、MA200 乖離を計算（必要データ不足時は None）。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率などを算出する SQL ロジックを追加（NULL 伝播やデータ不足を考慮）。
    - DuckDB を活用して大規模データを効率的に処理する設計。

- パッケージ構成用空ファイル
  - src/kabusys/tools/__init__.py、src/kabusys/utils/__init__.py を追加。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Implementation details / 作業メモ
- 環境変数の自動読み込みはデフォルトで有効。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定する。
- config.Settings は起動環境（KABUSYS_ENV）に基づき is_live / is_paper / is_dev を判断する。設定値のバリデーションで起動前に明示的な失敗（ValueError）を発生させる設計を採用。
- プロセス優先度設定・CPU affinity 設定は権限やプラットフォーム制約で失敗する可能性があるため、失敗時はログ警告に留め安全にフォールバックする実装。
- run_monitoring は監視用の sqlite DB（monitoring.db）を常に本番パスから利用するように設計されている点に注意（環境に依存しない動作）。
- run_execution は paper_trading モード時に DB を分離（PAPER_TRADING_SQLITE_PATH）し、本番データと混ざらないよう配慮。

### Known limitations / TODO
- position_sizing の lot_size は現状グローバル固定で、銘柄ごとの単元差を考慮していない（TODO 注記あり）。
- risk_adjustment.apply_sector_cap は price_map に 0.0 が渡された場合、エクスポージャーが過少見積りされるリスクがあり、将来的にフォールバック価格実装を検討。
- research.factor_research は prices_daily や raw_financials の存在・整合性に依存。DuckDB 側のテーブル定義やデータ整備が前提。

---

改修や追加の意図・挙動について不明点があれば、差分の意図や特定ファイルについてさらに詳しい説明を提供します。