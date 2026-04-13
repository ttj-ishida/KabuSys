CHANGELOG
=========

すべての変更は Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）の形式に準拠して記載しています。

未リリース
---------

- なし

[0.1.0] - 2026-04-13
--------------------

初回公開リリース。本リポジトリに含まれる主な機能・変更点をまとめます。

Added（追加）
- 基本パッケージとバージョン
  - kabusys パッケージを追加。__version__ = "0.1.0" を設定。

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。ブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立てを行い、セッションを実行する。paper_trading 環境では専用の SQLite DB（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と完全分離。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き機能を実装。

- 設定読み込み・管理
  - config.Settings: 環境変数アクセスをラップする Settings クラスを追加。多くの設定（DB パス、PID ファイル、閾値、環境判定など）をプロパティとして提供。
  - 自動 .env ロード: プロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を自動読み込み。OS 環境変数の保護（上書き防止）や KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化に対応。
  - .env パーサ実装: export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントルール等に対応。

- 監視・モニタリング関連
  - monitoring_db 初期化を起動時に呼び出してテーブル存在を保証（冪等）。
  - run_monitoring は環境にかかわらず本番 sqlite_path を使用する旨を明示。

- 実行（Execution）周りの構成要素（設計・設定）
  - ExecutionEngine 周辺の組み立てロジック（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler、EngineConfig 等）を実装。RiskConfig により各種閾値（最大ポジション比率、利用率、レートリミット、サーキットブレーカー等）を設定可能。RiskManager の初期 available_cash は broker.get_available_cash() を利用して初期化。

- Paper Trading サポート
  - PAPER_FILL_MODE 環境変数の読み取りと検証（instant/partial/never/reject のみ許容）。
  - paper_trading 用専用 DB（PAPER_TRADING_SQLITE_PATH）を利用することで本番と分離した検証運用を実現。

- ユーティリティ
  - utils.process_priority: プラットフォーム差分を吸収するプロセス優先度設定ユーティリティを追加。Windows / POSIX（Linux, Darwin, FreeBSD）に対応し、失敗時は警告を出してスキップする安全設計。CPU affinity を最初の N コアに固定する機能も追加。

- ポートフォリオ構築（portfolio）
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順でソートして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を提供。全スコア 0 の場合は警告を出して等金額にフォールバック。
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限（max_sector_pct）に基づき候補を除外するロジック。売却予定銘柄を除外して既存エクスポージャーを計算。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知のレジームは警告して 1.0 にフォールバック。
  - position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じて発注株数を計算。単元（lot_size）で丸め、per-position 上限と aggregate cap を実装。投資合計が利用可能現金を超える場合はスケーリングし、残余キャッシュを用いて端数分を lot 単位で配分するロジックを実装。

- リサーチ（research）
  - factor_research:
    - calc_momentum / calc_volatility / calc_value: DuckDB の prices_daily/raw_financials テーブルを用いてモメンタム・ボラティリティ・バリュー系ファクターを計算する関数を実装。200 日 MA、ATR20、平均売買代金、PER/ROE 等を算出。
  - feature_exploration:
    - calc_forward_returns: 将来リターン（1/5/21 営業日等）を計算。
    - calc_ic / rank / factor_summary: IC（Spearmanランク相関）計算、ランク付け、ファクター統計サマリを実装。
  - research パッケージは zscore_normalize をエクスポートして分析ワークフローの補助を提供。

- AI / ニュース NLP
  - ai.news_nlp:
    - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメント（-1.0〜1.0）を ai_scores テーブルに書き込む処理を実装（スコープ内での設計文書・実装ロジックを含む）。
    - バッチサイズ、トークン肥大化対策（1銘柄あたりの最大記事数・最大文字数）、エクスポネンシャルバックオフによるリトライ（429・ネットワーク断・5xx 対応）、レスポンスバリデーション、スコアの ±1.0 クリップ等を実装。
    - target_date に基づくニュース取得ウィンドウ計算（JST→UTC の変換）を提供。
    - API キー解決ロジックを実装（引数 api_key または環境変数 OPENAI_API_KEY）。未設定時は ValueError を送出。

- ツール
  - tools.paper_verification_report:
    - Paper Trading 検証レポート生成ツールを追加（コマンドライン実行可能）。--from/--to/--db オプションを提供。
    - system_status / trade_logs / risk_logs テーブルから稼働率・注文成功率・送信率・リスク却下数・レイテンシ（avg/max/P95）などを集計し、PASS/FAIL 判定（既定閾値）を出力。データ不足やテーブル未存在時の耐性（sqlite3.OperationalError のハンドリング）を実装。

Changed（変更）
- .env 読み込みの優先順を明確化（OS 環境変数 > .env.local > .env）。.env.local は .env の上書きとして扱う。
- MONITOR_POLL_INTERVAL の取り扱いを厳格化。環境変数から整数を解釈し、1 未満の値や不正な値は警告してデフォルト（60 秒）にフォールバック。
- run_monitoring: プロセス優先度設定（high）を起動直後に行うように整理。
- run_execution: paper_trading 環境の DB を明示的に切り替えるよう変更（paper_sqlite_path の利用）。

Fixed（修正）
- process_priority: アクセス拒否や未対応 API による例外を捕捉し、ワーニングログに変換して起動失敗を回避するように修正。
- calc_score_weights: 全てのスコアが 0.0 の場合に等金額配分へ安全にフォールバックするよう修正（警告ログ追加）。
- position_sizing: aggregate cap 適用時に lot_size 単位で丸める処理を改善し、残余キャッシュでの追加配分ロジックを導入してより現実的な発注数量を算出。
- research / feature_exploration: horizons 引数のバリデーションを追加（正の整数かつ <= 252）。
- ai.news_nlp: API キー未設定時に明示的なエラーを返すよう修正。

Security（セキュリティ）
- 環境変数読み込みで OS 環境変数を保護する仕組み（protected set）を導入し、.env による意図しない上書きを避ける。

Notes（備考 / 既知の制限・TODO）
- position_sizing の価格欠損（price が 0.0）の扱い: 現状はスキップし、注意コメント（TODO）を残している。将来的に前日終値や取得原価によるフォールバックを検討。
- risk_adjustment.apply_sector_cap は "unknown" セクターを除外対象にしない（設計上の選択）。
- ai.news_nlp の書き込み処理は部分失敗時に既存スコアを守るために対象コードを絞って DELETE→INSERT を行う設計だが、実行環境や DB の状態によって部分的な失敗が起こり得るため注意。
- 一部 API（psutil の優先度/affinity）や OS 機能はプラットフォーム依存。権限不足時は安全にスキップする実装。

今後の予定（非網羅）
- 銘柄ごとの lot_size サポート（stocks マスタの導入）
- price 欠損時のフォールバック価格ロジック強化
- ai.news_nlp の結果保存周りでのトランザクション性向上（部分失敗のロールバック/リトライ戦略の改善）
- 追加ユニットテストと CI の整備

--------------------------------------------------------------------------------
作成: リポジトリ内のソースコードから推測してまとめました。コード変更履歴が正確に分かれている既存のコミットログがある場合は、コミット履歴に基づいたより詳細な CHANGELOG 作成を推奨します。