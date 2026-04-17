CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」準拠です。

Unreleased
----------

（現在未リリースの変更はありません）

[0.1.0] - 2026-04-17
-------------------

Added
- 初期リリース: KabuSys の基本機能群を追加。
  - コアパッケージ
    - パッケージバージョンを設定: __version__ = "0.1.0"。
  - 設定管理 (kabusys.config)
    - .env / .env.local の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml）。
    - .env パーサの強化: export プレフィックス対応、シングル／ダブルクォートのエスケープ処理、インラインコメント処理。
    - OS 環境変数の保護（既存変数は上書き防止、.env.local は上書き可能）。
    - Settings クラス: 各種環境変数をプロパティとして提供（DB パス、PID/kill フラグ、閾値、API トークン等）。
    - 入力検証と明確なエラーメッセージ（必須 env 未設定時の ValueError、列挙型の妥当性チェック）。
  - 実行 / 監視スクリプト
    - run_execution: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite を使用して本番 DB と分離。
      - BrokerClientFactory によるブローカークライアント生成。
      - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てと実行制御（スレッド起動・停止フラグ対応）。
      - PID ファイル管理、停止フラグ（data/stop_requested.flag）による安全停止。
    - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - Monitoring は環境にかかわらず本番 sqlite_path を使用する設計。
      - 監視ループの例外ハンドリングと停止フラグ検出。
    - 両スクリプトとも起動時にプロセス優先度を設定（utils.process_priority を使用）。
  - データベース
    - sqlite3 / DuckDB 接続を利用（duckdb への接続埋め込み）。
    - 監視テーブル初期化ユーティリティ init_monitoring_db を呼び出し、冪等にテーブル存在を担保。
  - ポートフォリオ構築 (kabusys.portfolio)
    - portfolio_builder: シグナル選定・重み計算（select_candidates, calc_equal_weights, calc_score_weights）。
      - スコアが全て 0 の場合は警告を出して等配分にフォールバック。
    - risk_adjustment: セクター上限適用とレジーム乗数（apply_sector_cap, calc_regime_multiplier）。
      - unknown セクターはセクター上限適用対象外。
      - レジーム不明時には 1.0 でフォールバックし警告を出す。
    - position_sizing: 発注株数算出ロジック（risk_based / equal / score）。
      - 単元株丸め（lot_size）、per-stock 上限・aggregate cap（available_cash に合わせたスケールダウン）、cost_buffer による保守的コスト見積り、残差分の lot 単位での再配分実装。
      - 各種パラメータ（risk_pct, stop_loss_pct, max_position_pct, max_utilization 等）を引数で指定可能。
  - リサーチ (kabusys.research)
    - factor_research: DuckDB を使ったファクター計算（calc_momentum, calc_volatility, calc_value）。
      - Momentum (1M/3M/6M, MA200 乖離)、ATR、出来高・出来高比率、財務指標（PER/ROE）などを計算。
      - データ不足時は None を返す設計。
    - feature_exploration: 将来リターン計算、IC 計算、統計サマリ（calc_forward_returns, calc_ic, factor_summary, rank）。
      - pandas 等に依存せず標準ライブラリで実装。
  - AI / ニュース NLP (kabusys.ai.news_nlp)
    - ニュース記事の銘柄別集約と OpenAI（gpt-4o-mini）を用いたセンチメントスコア算出の下地を実装。
      - 時間ウィンドウの計算（JST 基準の前日 15:00 〜 当日 08:30 を UTC で変換する calc_news_window）。
      - バッチ送信（最大 _BATCH_SIZE=20）、トークン肥大化対策（記事数・文字数の上限）、リトライ（429/ネットワーク/5xx に対する指数バックオフ）、JSON レスポンス検証、スコアクリッピング（±1.0）、部分置換での安全な DB 更新方針を設計。
  - ツール
    - tools.paper_verification_report: Paper Trading 用検証レポート生成 CLI を追加。
      - 稼働率、注文成功率（Fill）、送信率（Sent）、リスク却下数、レイテンシ（AVG/MAX/P95）などを算出してレポート出力。
      - パス/フェイル判定基準（しきい値）を定義し、期間フィルタ（--from / --to）に対応。
  - ユーティリティ (kabusys.utils)
    - process_priority: Windows / POSIX の差異を吸収してプロセス優先度および CPU affinity を設定するユーティリティを実装（set_process_priority, set_cpu_affinity）。
      - 権限不足や未対応 OS の場合は警告を出してスキップする安全設計。

Changed
- 環境変数の自動読み込みルールを明確化:
  - 読み込み順序: OS 環境 > .env.local > .env
  - OS 環境変数は保護され、.env/.env.local で上書きされない（ただし .env.local は override=True で未保護キーを上書き可能）。
- 実行/監視起動時にプロセス優先度設定を最初に行うように統一。

Fixed
- .env パーサの改善により以下を修正／防止:
  - export KEY=val 形式を正しく扱うように対応。
  - クォート中のバックスラッシュエスケープ処理の不備を修正。
  - クォートなし値のインラインコメント判定をスペース／タブ直前のみコメントとみなすことで誤認を軽減。

Security
- 環境変数の自動ロードで OS 環境を上書きしない設計により、デプロイ環境での誤上書きを防止。
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY から取得。未設定時は明確なエラーを出す。

Known issues / TODO
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性あり。将来的に前日終値や取得原価でのフォールバックを検討。
- news_nlp.score_news:
  - 実装は堅牢化済みだが、外部 API 依存のため運用時のレート制限やコストに注意が必要。
- 一部のモジュールに実装注釈（TODO）あり。将来的な拡張（銘柄別 lot_size、フォールバック価格等）を計画中。

References
- 各モジュールの詳細はソース内ドキュメント（docstring / コメント）を参照してください。