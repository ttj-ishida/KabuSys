# Changelog

すべての重要な変更点を記録します。フォーマットは Keep a Changelog 準拠です。

## [0.1.0] - 2026-04-19

### Added
- 初回リリースとして、KabuSys のコアユーティリティ・起動スクリプト・ポートフォリオ構築ロジック・検証ツール類を追加しました。
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクトルート/data/stop_requested.flag によるフラグ検出で行う。
    - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用する（監視データは本番 DB に保存）。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、Paper Trading 用 DB（data/paper_trading.db）と完全分離して動作。
    - 停止フラグ（data/stop_requested.flag）検知でセッションを停止。実行 PID を data/execution.pid に記録する想定。
    - 実行はデーモンスレッドで行い、メインループで停止フラグを監視する。
- 設定管理
  - config.py
    - .env 自動読み込み（.env → .env.local）の仕組みを追加。プロジェクトルートは .git または pyproject.toml を起点に探索。
    - export KEY=val 形式、シングル/ダブルクォート、インラインコメント等の柔軟なパース処理を実装。
    - 環境変数の必須チェック用 _require、Settings クラスを提供（J-Quants、kabu API、DB パス、ログ設定、監視閾値等）。
    - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject）や KABUSYS_ENV / LOG_LEVEL の検証を実装。
  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加。
    - シークレット項目はマスク表示、デフォルト値・選択肢のサポート、保存確認を実装。
  - validate_config.py
    - 起動前に .env と config/*.yaml の整合性を検証する CLI を追加。
    - 必須環境変数の未設定検出、KABUSYS_ENV や LOG_LEVEL の妥当性検査、DB パスの親ディレクトリ存在チェック、YAML の存在/パース検証（PyYAML 未導入時はスキップ）等を実装。
    - --strict オプションで警告を FAIL 扱いにできる。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順で選択。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等金額にフォールバックし WARNING 出力）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限チェック（既存保有を基に新規候補を除外）。"unknown" セクターは除外しない。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた資金乗数を返す（未知レジームは 1.0 でフォールバックし WARNING）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（"risk_based"/"equal"/"score"）に基づく発注株数決定。単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金 / スケールダウン）、cost_buffer を考慮した保守的見積りなどを実装。
- ユーティリティ
  - utils.logging_setup
    - 共通ロギング設定ユーティリティを追加。StreamHandler（stdout）及び日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app>.log、30日保持）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - ログレベルの解決順: 引数 > 環境変数 LOG_LEVEL > デフォルト INFO。
  - utils.process_priority
    - クロスプラットフォームでプロセス優先度（high/normal/low）設定と CPU affinity 固定を提供。
    - Windows と POSIX（Linux/Mac 等）を吸収する実装。権限不足時は警告を出してスキップ。
- ツール
  - tools.paper_verification_report
    - Paper Trading の検証レポート生成 CLI を追加。対象 DB（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）から稼働率、注文成功率、送信率、P95 レイテンシ等を集計し PASS/FAIL 判定を出力。
    - デフォルト基準値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）を設定。
    - 日付フィルタ（--from/--to）や --db オプションをサポート。
- research.factor_research
  - DuckDB 接続を受け取り、Momentum / Value / Volatility / Liquidity などの定量ファクター計算を行う基盤モジュール（関数の実装開始、ドキュメント参照あり）。
- パッケージ初期化
  - __init__.py にてバージョンを 0.1.0 として追加。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Notes / Implementation details
- DB 分離:
  - 監視（monitoring）は常に Settings.sqlite_path（デフォルト data/monitoring.db）を使用。
  - Execution は paper_trading モード時に Settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 DB と分離される設計。
- セキュリティ / 運用上の注意:
  - .env は生成時に Git へコミットしないよう README 等で周知する想定（config_setup のヘッダに注意書きあり）。
  - validate_config の本番ガード: KABUSYS_ENV=live の場合に LINE 通知設定未設定や KILL_FLAG_CLEAR_ON_START=1 の危険性を警告。
- ロギング:
  - コンソール出力は stdout を使用（cron / scheduler でのリダイレクトに配慮）。
  - 既存ハンドラは初期化時に flush/close 後に削除し、二重設定を防止。
- エラーハンドリング:
  - 起動スクリプトのループ内エラーは例外をログ出力して次のポーリングに継続する実装（monitoring）。
  - 未知の値・不正値が指定された場合は ValueError を送出する箇所を設けて早期検出を促す（Settings の各検証）。

### Known limitations / TODO
- portfolio.position_sizing の価格フォールバック:
  - price が欠損（0.0）の場合にエクスポージャーが過小評価されてしまう可能性がある旨の TODO コメントあり。将来的に前日終値や取得原価等のフォールバックを検討。
- research.factor_research は一部実装が継続中（ファイル末尾が切れているため未完の関数あり）。
- stocks マスタに単元（lot_size）情報を持たせるなど、銘柄ごとの単元対応は将来の拡張予定。

---

今後のリリースでは、Strategy 実装、ExecutionEngine と Broker クライアントの統合テスト、factor_research の完成、監視アラート（LINE 通知など）の実装を予定しています。