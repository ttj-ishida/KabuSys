# CHANGELOG

すべての変更は Keep a Changelog の形式に従っています。  
この CHANGELOG は、リポジトリ内のソースコードから機能追加・設計意図を推測して作成したものです。

## [Unreleased]

## [0.1.0] - 2026-04-25

### Added
- 基本アプリケーション初期リリース（KabuSys 0.1.0）
  - パッケージ基盤とバージョン情報
    - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。
  - 環境設定 / 管理
    - Settings クラスによる環境変数ラッパーを追加（src/kabusys/config.py）。
      - 自動 .env ロード機能: プロジェクトルート（.git または pyproject.toml を基準）を検出して .env/.env.local を読み込む。
      - .env パースは export プレフィックス、クォート（シングル/ダブル）、バックスラッシュエスケープ、インラインコメント等に対応。
      - 多数の設定プロパティを公開（J-Quants / kabu API / DB パス / Paper Trading 用設定 / 監視閾値 / ポートファイル等）。
      - 設定値妥当性チェック（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。
  - 対話式設定ウィザード
    - .env の初期作成・更新を支援する CLI（src/kabusys/config_setup.py）。
    - 入力補助、既存 .env の読み込み、シークレット項目のマスク表示、保存確認機能を提供。
  - 設定検証 CLI
    - 起動前に環境変数や config/*.yaml の存在・基本整合性を検証する CLI（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パス親ディレクトリ検査、YAML パース検査（PyYAML がある場合）、本番向けガードチェックを実施。
    - --strict オプションで警告を失敗扱いにできる。
  - 起動スクリプト
    - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）
      - SystemMonitor を初期化しポーリングループを実行。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。0 以下はデフォルトにフォールバック。
      - 停止はプロジェクト data/stop_requested.flag により制御。
      - 監視は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用する設計。
    - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
      - ExecutionEngine を組み立ててセッションを別スレッドで実行。
      - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper_trading 用 DB（data/paper_trading.db をデフォルト）で分離して記録。
      - 起動時に stop フラグを確認し、既に立っている場合は起動を中止。
      - 停止フラグ検知時は Engine.stop() を呼び安全終了。
  - ログ / 実行ユーティリティ
    - ロギング設定ユーティリティ（src/kabusys/utils/logging_setup.py）
      - StreamHandler（stdout）と TimedRotatingFileHandler（日次, 30 日保持）をルートロガーに設定。
      - LOG_LEVEL / LOG_DIR の優先解決、既存ハンドラのクリーンアップ処理を実装。
      - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - プロセス優先度 / CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）
      - Windows と POSIX（Linux/Mac/FreeBSD）を吸収してプロセス優先度を設定（high/normal/low）。
      - CPU affinity 固定機能（最初の N コアにピン留め）。
      - 権限不足や未対応 OS の場合は警告を出してスキップ。
  - ポートフォリオ構築モジュール（src/kabusys/portfolio/*）
    - 候補選定 / 重み計算（portfolio_builder.py）
      - select_candidates: スコア降順＋タイブレークで上位 N を選択。
      - calc_equal_weights / calc_score_weights: 等金額・スコア重み付け（スコア全て 0 の場合は等分にフォールバック）。
    - セクター集中制限・レジーム乗数（risk_adjustment.py）
      - apply_sector_cap: 既存ポジションを考慮してセクター比率が上限を超える場合は新規候補を除外。
      - calc_regime_multiplier: レジーム（bull/neutral/bear）に基づき投下資金乗数を返す（未知値は 1.0 でフォールバック）。
    - 株数決定・リスク制限・単元丸め（position_sizing.py）
      - risk_based / equal / score の割当方式をサポート。
      - 単元（lot_size）単位で丸め、max_position_pct・max_utilization・cost_buffer（手数料/スリッページ見積り）に基づく aggregate cap スケーリングを実装。
      - 端数配分は fractional remainder を用いて再現性を持って割当。
  - Paper Trading 検証ツール
    - paper_verification_report（src/kabusys/tools/paper_verification_report.py）
      - Paper Trading の SQLite DB（PAPER_TRADING_SQLITE_PATH または引数 --db）を読み、システム安定性（稼働率）、注文成功率・送信率、リスク却下数、API レイテンシ（平均/最大/P95）を算出してレポート出力。
      - CLI オプション --from / --to で日付フィルタを指定可能。
      - デフォルトの判定基準（閾値）を定義：稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200ms。
  - 研究モジュール（部分実装）
    - factor_research（src/kabusys/research/factor_research.py）
      - モメンタム、MA200 乖離、ATR、流動性などの計算方針を実装するための設計と定数を追加。DuckDB 経由で prices_daily / raw_financials を参照する設計。

### Changed
- （初回リリースのため変更履歴なし）

### Fixed
- （初回リリースのため修正履歴なし）

### Deprecated
- （なし）

### Removed
- （なし）

### Security
- （なし）

## Notes / Known limitations / TODO
- risk_adjustment.apply_sector_cap:
  - price_map に欠損（0.0）価格がある場合にエクスポージャーが過少見積りされる旨の TODO コメントあり。前日終値等のフォールバック実装が検討事項。
- position_sizing:
  - 将来的に銘柄別 lot_size を持たせる設計への拡張 TODO が残っている。
- research.factor_research:
  - ファイル末尾が未完の箇所が見られる（作成途中）。ファクター計算関数の詳細実装は継続作業が必要。
- .env 自動ロードはプロジェクトルート検出に依存するため、配布後やルート検出できない環境では自動ロードをスキップする（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- run_monitoring は「監視 DB を本番 sqlite_path で常に使用する」設計であるため、テスト用に監視 DB を分離したい場合は設定やコードの調整が必要。

参考:
- CLI 実行例:
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証:   python -m kabusys.validate_config [--strict]
  - 監視起動:   python -m kabusys.run_monitoring
  - 実行起動:   python -m kabusys.run_execution
  - Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

（この CHANGELOG はコードコメント・関数名・CLI ヘルプ等から推測して作成しています。実際のリリースノートとして使用する場合は、開発履歴やコミットログと突合してください。）