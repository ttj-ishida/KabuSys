# Changelog

すべての注目すべき変更をここに記録します。  
フォーマットは Keep a Changelog に準拠しています。

## [0.1.0] - 2026-04-17

### Added
- 起動スクリプトを追加
  - run_monitoring.py
    - SystemMonitor をポーリングで実行する常駐ループを提供。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視処理は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用。
    - 起動時にプロセス優先度を "high" に設定（utils の set_process_priority を使用）。
    - 停止制御ファイル（data/stop_requested.flag）を検知して安全にループ終了。
    - SQLite / DuckDB 接続の初期化と確実なクローズ処理を実装。
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合、専用の Paper Trading SQLite（data/paper_trading.db または PAPER_TRADING_SQLITE_PATH）を使用して本番と分離。
    - BrokerClientFactory からブローカークライアントを生成し、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine を組み立てる。
    - エンジンは別スレッドで実行し、停止フラグ検知でエンジン停止を行う。
    - 起動時にプロセス優先度を "high" に設定。
    - 実行 PID ファイル（data/execution.pid）を扱う仕組みを提供。
- 設定管理と自動 .env 読み込み
  - config.Settings を導入。環境変数から各種設定（API トークン、DB パス、監視閾値、動作環境等）を取得。
  - プロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - .env パーサを強化: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理等。
  - 各種検証（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等）を実装。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading の SQLite（デフォルト data/paper_trading.db）から検証レポートを生成する CLI。
    - 稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数などを集計して画面出力。
    - 日付フィルタ（--from / --to）と --db オプション対応。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコア順ソートと上位 N 選出。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（全スコア 0 の場合は等配分へフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェックにより候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームは警告を出して 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数算出。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash）を考慮したスケーリング、スケーリング後の端数分配ロジックを実装。
    - cost_buffer を用いた保守的コスト見積り（スリッページ等を考慮）。
- ユーティリティ
  - utils/process_priority.py
    - set_process_priority: Windows（psutil の優先度定数）と POSIX（nice 値）を吸収する API。
    - set_cpu_affinity: プロセスを最初の N コアにピンニングする機能（保護・例外処理あり）。
    - 権限不足や未対応プラットフォームでは警告を出してスキップ。
- リサーチ / ファクター計算
  - research/factor_research.py
    - calc_momentum / calc_volatility / calc_value: DuckDB 上の prices_daily / raw_financials を参照して各種ファクターを計算する SQL 実装。
    - 精度・欠損ハンドリング（ウィンドウサイズ未満は NULL）を明示。
  - research/feature_exploration.py
    - calc_forward_returns: 将来リターン（複数ホライズン）を高速に一度のクエリで取得。
    - calc_ic / rank / factor_summary: IC（Spearman ランク相関）の計算、ランク変換、ファクターの統計要約を実装（外部依存なし）。
  - research/__init__.py で主要関数をエクスポート。
- AI ニュース NLP（設計/実装開始）
  - ai/news_nlp.py
    - ニュース記事を銘柄ごとに集約し OpenAI（gpt-4o-mini）でスコアリングして ai_scores テーブルに書き込む設計を実装。
    - バッチサイズ、トークン肥大化対策（記事数・文字数制限）、リトライ（指数バックオフ）、レスポンス検証、スコアクリッピング等の仕様を実装。
    - calc_news_window 関数（JST→UTC のウィンドウ計算）を実装。
- パッケージ情報
  - kabusys.__version__ を "0.1.0" に設定。

### Changed
- （初回リリースのため変更履歴なし。内部的に堅牢化・ログ出力の整備を実施。）

### Fixed / Improved
- .env 読み込みのロバストネス向上
  - 引用符付き値のバックスラッシュエスケープ、export プレフィックス、インラインコメント処理などをサポート。
  - .env と .env.local の読み込み優先度 / 上書き保護ロジックを明確化（OS 環境変数は protected）。
- 配分・重み付けの安全性向上
  - calc_score_weights: 全スコアが 0.0 の場合に等金額配分へフォールバックし WARNING を出力。
  - calc_regime_multiplier: 未知レジームで警告を出しフォールバック。
- プロセス優先度 / CPU ピン留め処理での権限不足や未対応プラットフォーム時の安全ハンドリングを追加。
- ExecutionEngine 起動時に monitoring テーブルの初期化を冪等的に保証（init_monitoring_db を呼ぶ）。

### Known issues / Notes
- ai/news_nlp.score_news の記事取得部分（_fetch_articles 呼び出し以降）が提示コードで途中までで終わっており、完全実装が必要。API 呼び出し・DB 書き込みの細部は引き続き確認・テストが必要。
- portfolio/risk_adjustment.apply_sector_cap: price が欠損（0.0）時のエクスポージャー過少見積りについて TODO コメントあり。フォールバック価格（前日終値等）を使う拡張を検討中。
- position_sizing: 将来的に銘柄毎の lot_size をサポートするための拡張が TODO として残されている。
- DuckDB に対する executemany の制約（空パラメータを渡さないこと）に関する注意書きがツール実装側にあるため、部分的失敗時のロバストなトランザクション処理は要注意。
- 自動 .env 読み込みはプロジェクトルートが特定できない環境ではスキップされるが、CI/配布後は明示的に KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して動作を制御することを推奨。

### Security
- 本リリースで新たにセキュリティ修正はありません。環境変数管理（.env の読み込み）に注意して運用してください（機密情報は OS 環境変数で保護する等）。

---

このリリースは初期実装のまとまりです。今後のリリースでは AI スコアリングの完遂、単体テストの拡充、エンドツーエンドのフェイルセーフ強化（DB トランザクションや部分失敗時のリカバリ）を予定しています。