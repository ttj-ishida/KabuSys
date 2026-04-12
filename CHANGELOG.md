CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。
意味のある変更のみを記載しています（内部のリファクタリングや小さなコメント修正は省略）。

[0.1.0] - 2026-04-12
--------------------

Added
- 初回リリースを追加。主要サブシステムを実装。
  - 実行／監視スクリプト
    - run_execution.py: ExecutionEngine の起動エントリポイントを追加。環境に応じて paper_trading 用の専用 SQLite DB を使用し、MockBrokerClient を利用できる設計。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関係なく本番 sqlite_path を使用する仕様。
  - 設定管理
    - config.Settings: 環境変数に基づく設定ラッパーを実装。DB パス、PID/kill フラグパス、監視閾値、env/log レベル判定、paper_trading 用設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH）などを提供。値検証と明示的なエラー報告を備える。
    - .env 自動読み込み機能: プロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を自動読み込み。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化をサポート。
    - .env パーサ実装: export 形式、クォート／エスケープ、インラインコメントの扱い、既存 OS 環境変数の保護（protected）などに対応。
  - Execution コンポーネント（起動時に組み立てられる主要クラスの利用例を含む）
    - BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager 等を組み合わせる起動フローをサンプル実装。
    - RiskConfig のデフォルト値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker_* 等）を明示化。
  - Portfolio 構築ライブラリ
    - portfolio.portfolio_builder: シグナルから候補選定（スコア降順、tie-breaker）と重み計算（等重、スコア重み）。スコアが全て 0 の場合は等重へフォールバックして警告を出力。
    - portfolio.position_sizing: 発注株数計算（risk_based / equal / score）、単元（lot_size）丸め、1銘柄上限／aggregate cap（利用可能現金に合わせたスケーリング）、cost_buffer を考慮した保守的見積り、端数処理ロジックを実装。
    - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。未知レジームはフォールバックして警告を出力。
  - Research / ファクター計算
    - research.factor_research: Momentum / Volatility / Value ファクター実装（DuckDB 接続を受け取り、prices_daily/raw_financials を参照して計算）。200 日移動平均や ATR、各種リターンを営業日ベースで算出する SQL を提供。
    - research.feature_exploration: 将来リターン計算（任意ホライズン）、Spearman ランク相関（IC）計算、ファクター統計サマリー、ランク計算ユーティリティを実装。外部ライブラリに依存せずに純 Python で実装。
    - research パッケージの公開 API を __all__ で整理。
  - AI / ニュース NLP
    - ai.news_nlp: raw_news を OpenAI（gpt-4o-mini）に送って銘柄別センチメント（-1.0〜1.0）を算出し ai_scores テーブルに書き込む処理を実装。処理フローにはタイムウィンドウ計算、記事トリミング（記事数・文字数制限）、バッチ化（最大 20 銘柄 / 回）、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンス検証、スコアクリッピング、部分失敗時の既存スコア保護（対象コードのみ削除して挿入）などを含む。
    - calc_news_window: target_date に対するニュース収集ウィンドウ（JST→UTC 変換）を提供。ルックアヘッドバイアス対策として datetime.today() への依存を避ける設計。
  - ツール
    - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。システム稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数などの指標を抽出して PASS/FAIL 判定を行う。期間フィルタ（--from/--to）、DB パス指定（--db / 環境変数）をサポート。P95 計算や各クエリで DB のテーブル不存在に対する例外ハンドリング（OperationalError からのフォールバック）を備える。
  - ユーティリティ
    - utils.process_priority: Windows / POSIX の差分を吸収するプロセス優先度設定ユーティリティ（set_process_priority）を実装。CPU affinity 設定（set_cpu_affinity）も提供。サポート外 OS や権限不足時は警告を出してフォールバックする。
  - パッケージメタ
    - kabusys.__init__.py に __version__ = "0.1.0" を設定。

Changed
- （初回リリースに相当するまとめ記載）

Fixed
- .env ファイル読み込み時のファイルオープン失敗を警告に置き換え、プロセスを継続するように安定化。
- ポーリングループ内の例外処理強化: monitor.check_once() 内で発生した例外は個別にキャッチしてログに残した上で次のポーリングに復帰。KeyboardInterrupt でのクリーン終了処理を実装。

Notes / Implementation details（主な設計上の注意）
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と完全に分離されることを想定。paper_trading 用の SQLite パス（PAPER_TRADING_SQLITE_PATH）や fill モード（PAPER_FILL_MODE）で動作を制御できる。
- Monitoring は運用上の重要性が高いため、本番 sqlite_path を参照する設計（KABUSYS_ENV に依存しない）。
- DuckDB を分析用途（prices_daily, raw_financials 等）に使用。research モジュールは DuckDB 接続を受け取り SQL ベースで高効率にファクターを算出する。
- AI スコア処理では API キー未設定時に ValueError を投げる明示的な扱いとし、API 呼び出しエラーはリトライ/ログ出力でフェイルセーフに従う。
- position_sizing のスケーリングや端数処理は単元株（lot_size）単位で丸め、再現性のため残差ソートに二次キーとしてコードを使用。

Security
- OpenAI API キー等の機密情報は環境変数で管理する前提。自動 .env 読み込みは DISABLE フラグで無効化可能。

未記載（今後の改善候補）
- 銘柄別 lot_size のサポート（現状は全銘柄同一 lot_size を想定）。
- price が欠損（0 や None）の場合のフォールバック価格（前日終値や取得原価など）。
- ai.news_nlp: さらに堅牢な JSON 検証や部分失敗時のリトライ戦略の細分化。

-----