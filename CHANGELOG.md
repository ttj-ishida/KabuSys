Changelog
=========
すべての重要な変更点をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。

Unreleased
----------
（現在のところなし）

[0.1.0] - 2026-04-17
-------------------

Added
- 基本パッケージの初期実装を追加しました（バージョン: 0.1.0）。
- ランタイム/運用スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。  
    - 停止はプロジェクト内 data/stop_requested.flag ファイルで行う仕組み。監視処理は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様。
    - 起動時にプロセス優先度を "high" に設定する呼び出しを追加。
    - sqlite3 / DuckDB 接続の初期化と安全な例外ハンドリング（check_once の例外はログに残してループ継続）。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用し、本番 DB と完全分離。  
    - MockBrokerClient の切替を BrokerClientFactory 経由で行う設計（paper/live の切替サポート）。  
    - 停止フラグ（data/stop_requested.flag）検知でエンジン停止、実行用 pid ファイル管理。
- 設定管理
  - config.py
    - 環境変数自動読み込み機能を追加（プロジェクトルートの .env / .env.local を読み込み、OS 環境変数を保護）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。  
    - .env パーサを耐障害性高く実装（コメント行、export プレフィックス、クォート・エスケープ対応、インラインコメント処理など）。  
    - Settings クラスを提供し、アプリ全体で使う設定プロパティを集中管理（DB パス、Paper Trading パス、閾値、env / log level バリデーション等）。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject のみ許容）。KABUSYS_ENV（development/paper_trading/live）の検証。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - 銘柄選定（select_candidates: スコア降順、タイブレークに signal_rank）と重み計算（等金額、スコア加重）。スコアが全て 0 の場合は等配分にフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）を実装。既存保有や当日売却予定を考慮して候補を除外。unknown セクターは上限適用除外。  
    - 市場レジームに応じた資金乗数 calc_regime_multiplier（bull/neutral/bear のマッピング）。
  - portfolio/position_sizing.py
    - 発注株数算出（risk_based / equal / score の各方式）、単元（lot_size）丸め、per-position 上限、aggregate cap（利用可能現金を超える場合のスケールダウン）、cost_buffer を考慮した保守的見積りと残差処理を実装。
- リサーチ / ファクター計算
  - research/factor_research.py
    - Momentum / Volatility / Value ファクター計算を実装（DuckDB を用いて prices_daily / raw_financials を参照）。MA200乖離、ATR20、平均売買代金、PER/ROE などを算出。
  - research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC 計算（calc_ic：Spearman ランク相関）、ファクター統計サマリー（factor_summary）、ランク計算ユーティリティを実装。外部ライブラリに依存しない純 Python 実装。
  - research/__init__.py
    - 主要関数をパッケージ公開。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。期間指定（--from/--to）可能で、稼働率 / 注文成功率 / 送信率 / レイテンシ指標（P95）などを計算して PASS/FAIL 判定を出力。
    - デフォルト DB は data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）。複数の SQL クエリで不足データに対して寛容に動作する設計。
- AI ニュース NLP
  - ai/news_nlp.py
    - raw_news を OpenAI（gpt-4o-mini）でセンチメント評価し、銘柄ごとに ai_scores テーブルへ保存する処理フローを実装。  
    - タイムウィンドウ算出（JST ベース）、記事集約、バッチ送信（最大 20 銘柄）、JSON モード検証、スコアの ±1.0 クリップ、エクスポネンシャルバックオフによる再試行、部分成功時の DB 更新戦略などを採用。
- ユーティリティ
  - utils/process_priority.py
    - プロセス優先度（set_process_priority）と CPU affinity（set_cpu_affinity）ユーティリティを追加。Windows と POSIX 系を吸収し、権限不足や未対応 OS の場合は警告してスキップするフォールバック処理あり。

Changed
- プロジェクト構成設計を統一
  - DuckDB と SQLite を組み合わせたデータ処理基盤を採用（分析は DuckDB、運用ログ/監視は SQLite）。
  - 実行時のプロセス優先度を標準化して起動直後に設定するように変更（run_monitoring/run_execution）。

Fixed
- .env 読み込みの堅牢化
  - クォート内のバックスラッシュエスケープや export プレフィックス、インラインコメントの取扱いを改善し、誤読による設定ミスを低減。

Security
- 環境変数の自動ロード時に OS 環境変数を保護する仕組みを導入（.env による上書きを制御）。

Notes / Known issues / TODO
- apply_sector_cap:
  - price_map に価格が無い（0.0）の場合、エクスポージャーが過少見積りされる可能性がある旨の TODO コメントあり。将来的に前日終値や取得原価でのフォールバックを検討。
- position_sizing:
  - 将来的には銘柄別単元サイズ（lot_size）を stocks マスタで保持することを想定する TODO コメントあり（現状は全銘柄共通 lot_size を想定）。
- ai/news_nlp.py:
  - 実装はエラーハンドリング・再試行等を考慮した設計になっているが、OpenAI API のレート制限やレスポンス形式の不整合に対する部分的なフェイルセーフが設計に組み込まれているため、運用時は API キー・コスト・レート制限の監視が必要。
- run_monitoring:
  - 監視は「監視 DB に本番 sqlite_path を常に使用する」ため、運用者は監視用 DB の配置・権限に注意すること（意図的仕様）。
- 一部ファイル・関数は将来の拡張（細かなログ、エラーレポート、単体テストの充実など）を想定して実装されている。

作者注
- 初期リリースでは「安全性・可観測性」を重視しており、外部 API 呼び出し部（OpenAI、証券ブローカー API 等）は抽象化・切替可能な実装になっています。運用環境へ導入する際は環境変数や DB パス、権限設定を確認してください。