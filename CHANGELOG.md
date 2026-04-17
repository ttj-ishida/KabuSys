# Changelog

すべての注目すべき変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。

全てのバージョンはセマンティックバージョニングに従います。

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 2026-04-17

初回公開リリース。

### Added
- コアランタイム / 起動スクリプトを追加
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを提供。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔の上書き（デフォルト 60 秒）。
    - 起動時にプロセス優先度を設定（utils.process_priority.set_process_priority を使用）。
    - 停止フラグファイル (data/stop_requested.flag) の検知による安全停止。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを提供。
    - KABUSYS_ENV=paper_trading 時は専用の MockBrokerClient と paper_trading DB（data/paper_trading.db）を使用し、本番 DB と分離。
    - 起動時にプロセス優先度を設定し、停止フラグの監視による安全停止を実装。
    - ExecutionEngine をバックグラウンドスレッドで実行し、スレッド終了まで監視する仕組みを提供。

- 設定・環境変数管理
  - config.py
    - .env 自動読み込み機能（プロジェクトルート検出: .git / pyproject.toml ベース）。
    - .env のパースでシングル/ダブルクォート、export プレフィックス、インラインコメント、バックスラッシュエスケープに対応。
    - OS 環境変数を保護して .env を上書きするか制御する仕組み（protected）。
    - 必須環境変数チェック用の _require、各種設定プロパティ（DB パス、paper_trading 用設定、監視閾値、KABUSYS_ENV 判定など）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化サポート。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成 / 更新する CLI を提供。
    - シークレット項目は表示をマスクして取り扱い、デフォルト・選択肢のサポート、保存確認を実施。
    - .env の書き出しテンプレートを提供（Git にコミットしない旨の注意文付き）。

- 設定検証ツール
  - validate_config.py
    - 環境変数や config/*.yaml の存在・基本検証を行う CLI。
    - --strict オプションで警告を FAIL 扱いにするモードを提供。
    - PyYAML がない場合は YAML 内容検証をスキップして警告を出力。
    - 本番 (KABUSYS_ENV=live) 用の追加ガード（LINE 通知設定未設定や KILL_FLAG_CLEAR_ON_START の危険設定等）を実装。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順選定 + tiebreaker（signal_rank）。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分（スコア合計が 0 の場合は等配分にフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく銘柄ごとの発注株数算出。
    - lot_size による単元丸め、max_position_pct による per-stock cap、available_cash による aggregate cap のスケーリング、cost_buffer を考慮した保守的見積りと端数配分ロジックを実装。
  - portfolio.risk_adjustment
    - apply_sector_cap: 同一セクター集中制限により候補除外を行うロジック（unknown セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を返すユーティリティ。未知レジームはフォールバックで 1.0。

- 研究用ファクター計算
  - research.factor_research
    - DuckDB 接続を受け取り、prices_daily テーブルを基にモメンタム（1M/3M/6M、MA200乖離）やボラティリティ（ATR20）、流動性指標等を計算する関数を実装。
    - 大規模データを SQL ウィンドウ関数で効率的に処理する実装方針。

- ユーティリティ
  - utils.process_priority
    - Windows / POSIX（Linux/Mac 等）の差を吸収してプロセス優先度を設定するユーティリティ（high/normal/low）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
    - 権限不足や未対応 OS に対してフォールバックし、失敗時は警告ログでスキップ。

- 運用ツール
  - tools.paper_verification_report.py
    - Paper Trading の SQLite DB を参照して稼働率、注文成功率、送信率、レイテンシ（平均 / 最大 / P95）などを集計し、PASS/FAIL 判定付きレポートを標準出力に出力する CLI。
    - デフォルト DB パスは data/paper_trading.db。--from / --to / --db オプションをサポート。
    - P95 の計算や入力データ欠損時の N/A ハンドリングを実装。

- パッケージ初期化
  - __init__.py に __version__ = "0.1.0" を設定。

### Changed
- （初回リリースのため該当なし）

### Fixed
- 設定パーサーの堅牢性向上
  - .env パースで引用符付き文字列のバックスラッシュエスケープ、export プレフィックス、インラインコメントを正しく扱うように改善。
- 実行時の安全性・耐障害性
  - run_monitoring.py / run_execution.py で停止フラグ検出や例外発生時のログ出力を追加し、単一ポーリングでの例外がループ全体を止めないように保護。
  - DB 初期化（init_monitoring_db）は冪等的に呼び出せるよう確保。

### Security
- config_setup の表示でシークレット項目をマスクして表示することで、対話中の漏洩リスクを軽減。
- .env は「絶対に Git にコミットしない」旨の注記をテンプレートに含める。

### Notes / Known limitations
- position_sizing の lot_size は現状全銘柄共通設定（将来的に銘柄別単元対応を想定）。
- apply_sector_cap では price_map に値が欠損（0.0）だとエクスポージャーが過少見積りされる可能性があり、将来的にフォールバック価格導入を検討。
- research.factor_research は prices_daily / raw_financials テーブルに依存しており、DuckDB 側のテーブル整備が前提。
- process_priority の設定は権限や OS により失敗することがあり、その場合は警告ログを出力してスキップする。

---

（今後のリリースでは変更点をカテゴリー別に記載します）