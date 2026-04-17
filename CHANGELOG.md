CHANGELOG
=========

すべての重要な変更を記録します。本ファイルは「Keep a Changelog」仕様に準拠しています。

フォーマット:
- 変更はセクション別（Added / Changed / Fixed / Deprecated / Removed / Security）で記載しています。
- 日付はリリース日を示します。

[Unreleased]
------------

（現在未リリースの変更はありません）

[0.1.0] - 2026-04-17
-------------------

初回リリース。以下の主要機能・ユーティリティ群を追加しました。

### Added
- 全体
  - パッケージの初期バージョンを定義（kabusys.__version__ = "0.1.0"）。
  - パッケージ公開用のエクスポートを __all__ で整理。

- 実行 / 監視
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV に応じて paper_trading 用 DB を分離（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。
    - BrokerClientFactory によるブローカークライアント生産、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
    - PID ファイル管理、外部停止フラグ（data/stop_requested.flag）検知により安全に停止可能。
    - 既定の RiskConfig を内蔵（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
  - run_monitoring.py: SystemMonitor をポーリングで実行する監視スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 監視処理は環境にかかわらず本番 sqlite_path を利用する設計。
    - 起動時にプロセス優先度を "high" に設定する処理を実行。

- 設定管理
  - config.py: 環境変数 / .env 自動ロード機能を実装。
    - プロジェクトルートを .git または pyproject.toml から探索して .env / .env.local を読み込む。
    - .env.local は .env を上書き。OS 環境変数は保護される（上書きされない）。
    - export KEY=val 形式やクォート・エスケープ、行内コメントの扱いなどを考慮した堅牢なパーサ実装。
  - Settings クラスを提供し、各種設定値（DB パス、API トークン、監視閾値、ログレベル、環境種別など）をプロパティ経由で取得可能に。
    - KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE の入力バリデーションを実装。
    - paper_trading 用 DB パスや PID/kill フラグのパスなど運用に必要な値を集約。

- ポートフォリオ構築
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルのスコア降順で上位 N を選択（同点は signal_rank でブレーク）。
    - calc_equal_weights, calc_score_weights: 等加重 / スコア加重の重み計算（スコア全体が 0 の場合は等加重にフォールバックし WARNING を出す）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: 既存ポジションのセクター集中を検査し、上限超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた資金乗数を返す（未知レジームはフォールバックで 1.0）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method に応じた発注株数計算を提供（"risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash を超える場合はスケーリング）、cost_buffer による保守的評価などをサポート。
    - スケールダウン時の端数配分ロジックを実装（残余キャッシュで fractional 残差が大きい銘柄から lot 単位で追加）。

- 研究（research）
  - research.factor_research:
    - calc_momentum, calc_volatility, calc_value を実装。DuckDB 経由で prices_daily / raw_financials を参照して複数ファクターを算出（MA200、ATR20、リターンなど）。
    - 不足データ時の None 処理やウィンドウ指定、パフォーマンスを意識したスキャン範囲の実装。
  - research.feature_exploration:
    - calc_forward_returns: 将来リターン（1/5/21 日など）を一括クエリで取得。
    - calc_ic: スピアマンのランク相関（IC）計算（ties の平均ランク処理を含む）。有効レコードが少ない場合は None を返す。
    - factor_summary, rank: ファクターの統計サマリーやランク付けユーティリティを追加。
  - research.__init__: zscore_normalize を含む公開 API を整理。

- ツール
  - tools.paper_verification_report:
    - Paper Trading の検証レポート生成スクリプトを追加（CLI で期間指定可能）。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、リスク却下数、レイテンシ（P95 等）を算出し PASS/FAIL 判定を出力。
    - 閾値（稼働率 99% など）と要約表形式の出力を実装。
    - DB パスの引数/環境変数指定をサポート（--db / PAPER_TRADING_SQLITE_PATH）。

- AI ニュース
  - ai.news_nlp:
    - raw_news を OpenAI API（gpt-4o-mini）でセンチメントスコア化して ai_scores に書き込む処理の骨子を追加。
    - バッチ処理（最大 20 銘柄 / 回）、トークン肥大化防止のための最大記事数・最大文字数トリム、429/5xx/タイムアウトへの指数バックオフリトライ、レスポンスバリデーション、±1.0 クリップなどの設計を導入。
    - ニュースウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）ユーティリティを提供。
    - （注）ファイルは長いため一部実装が切れている箇所がありますが、設計ドキュメントに沿った堅牢な API 呼び出しフローを想定。

- ユーティリティ
  - utils.process_priority:
    - set_process_priority: Windows / POSIX を吸収してプロセス優先度（high/normal/low）を設定。アクセス権限や未対応 OS の場合は警告を出して安全にスキップ。
    - set_cpu_affinity: 指定コア数への CPU affinity 固定を提供（None は全コア使用、1 未満は ValueError）。

### Changed
- .env 読み込みロジック:
  - OS 環境変数を保護しつつ .env/.env.local の自動ロード順序を明確化（OS > .env.local > .env）。
  - プロジェクトルート探索を __file__ 起点で実施することでパッケージ配布後も動作するように変更。

- DB / 実行分離:
  - 実行エンジンは paper_trading モードでは paper_trading 用 SQLite を使用することで本番 DB と分離（安全設計）。
  - 監視プロセスは常に本番 sqlite_path を使用する方針を明示（監視データは本番 DB に集約）。

### Fixed
- 環境変数のパース堅牢化:
  - export プレフィックスやクォート内のバックスラッシュエスケープ、行内コメントの扱いなど多数のケースを考慮して .env パーサの不正解釈を回避。

- ポートフォリオ重み計算のフォールバック:
  - 全銘柄のスコアが 0 の場合に calc_score_weights が等加重に安全にフォールバックするように修正（warning を出力）。

- MONITOR_POLL_INTERVAL のバリデーション:
  - 0 以下や非整数の値を渡された場合にログ警告を出しデフォルト値にフォールバックするように修正（time.sleep の ValueError 回避）。

### Deprecated
- なし

### Removed
- なし

### Security
- OpenAI API キーは明示的に引数または OPENAI_API_KEY 環境変数で指定する必要があり、未設定時には明示的なエラーを発生させ処理を停止する設計とした（誤送信リスクの低減）。

注記 / 既知の制限
- ai.news_nlp モジュールは堅牢性を考慮した設計が実装されていますが、配布コードの一部が切れているため（本 CHANGELOG 作成時点）完全実装を確認のうえで利用してください。
- position_sizing で price が欠損（0.0）の場合にエクスポージャーが過少見積となる可能性がある旨の TODO コメントが残っています。将来的にフォールバック価格の導入を検討しています。
- DuckDB を用いる関数群は prices_daily / raw_financials 等のテーブルスキーマに依存します。運用環境でのテーブル整合性を確認のうえ利用してください。

以上。