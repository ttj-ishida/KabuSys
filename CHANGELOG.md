CHANGELOG
=========

この CHANGELOG は「Keep a Changelog」準拠の形式で記述しています。  
コードベースの内容から推測して作成したため、一部表現は実装意図の解釈に基づきます。

Unreleased
----------

- 環境変数周りの堅牢化
  - MONITOR_POLL_INTERVAL のパースとバリデーションを改善（0以下の値や非整数はデフォルトにフォールバックし、警告ログを出力）。
  - .env / .env.local の自動読み込みロジック（プロジェクトルート検出、export 形式やクォート付き値、インラインコメント対応、既存 OS 環境変数の保護）を整備。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化に対応。
  - Settings の各プロパティに入力検証を追加（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。不正な値は ValueError を送出。

- 監視・実行の起動スクリプト改善
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを提供。MONITOR_POLL_INTERVAL による間隔上書き、停止フラグ検知、SQLite / DuckDB 接続初期化、プロセス優先度設定を実装。
  - run_execution: ExecutionEngine 起動スクリプトを提供。Paper Trading 環境では専用 SQLite(DB) を使用して本番 DB と分離。Broker クライアント生成、OrderManager / RiskManager / Reconciler の組み立て、デーモン・スレッドでのエンジン実行と停止フラグ検知を実装。

- プロセス優先度 / CPU Affinity ユーティリティ
  - set_process_priority(level) を実装（Windows / POSIX を吸収、アクセス権限や未対応 OS では警告ログでフォールバック）。
  - set_cpu_affinity(cpu_count) を実装（利用可能コア数を考慮し、アクセス拒否時は警告でスキップ）。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio_builder:
    - select_candidates: BUY シグナルのスコア降順ソートと上位選定。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（スコア合計が 0 の場合は等金額へフォールバック、警告出力）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中制限（既存ポジションのセクター別エクスポージャー計算、上限超過セクターの候補除外）。unknown セクターの扱い、売却予定銘柄の除外をサポート。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear を定義、未知レジームはフォールバック）。
  - position_sizing:
    - calc_position_sizes: allocation_method（risk_based, equal, score）に基づく発注株数決定。単元株（lot_size）丸め、1銘柄上限・aggregate cap、cost_buffer による保守的見積り、available_cash を超過した際のスケーリングと残差処理を実装。

- リサーチ / ファクター計算
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率の算出（DuckDB SQL ベース）。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率の算出（true_range の NULL 伝播制御等を考慮）。
    - calc_value: raw_financials から最新財務情報を結合して PER / ROE を算出（target_date 以前の最新レコードを取得）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括で算出（LEAD を利用）。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。データ不足時の安全処理あり。
    - factor_summary / rank: 基本統計量算出、ランク変換（同順位は平均ランク）を実装。
  - research パッケージの __all__ に zscore_normalize を組み込み（外部モジュール経由）。

- AI ニュース NLP（OpenAI 統合） - 初期実装
  - news_nlp:
    - calc_news_window: JST→UTC のニュース集計ウィンドウ計算。
    - score_news: OpenAI（gpt-4o-mini）を用いた銘柄別センチメントスコア化の処理フローを設計（バッチ処理、最大記事数・文字数トリム、最大バッチサイズ 20、リトライ/エクスポネンシャルバックオフ、レスポンス検証、±1.0 クリップ、部分更新のDB置換戦略）。API キー解決とエラー時の取り扱いを実装。※スニペット中で記事取得関数呼び出しの先頭が省略されているため、実装の一部は別ファイル/別関数に依存。

- ツール
  - tools.paper_verification_report:
    - Paper Trading 用検証レポート生成 CLI を実装（期間指定 --from / --to、--db オプション、PAPER_TRADING_SQLITE_PATH で DB 指定可）。
    - 指標: 稼働率（uptime_pct）, 注文成功率（fill_rate）, 送信率（send_rate）, レイテンシ統計（avg/max/P95）など。PASS/FAIL 判定基準（稼働率 >=99% 等）と閾値を定義。
    - SQLite クエリは system_status / trade_logs / risk_logs 等のテーブルを参照するように設計。DB が存在しない場合のエラーメッセージ出力あり。

- DB / ストレージ既定
  - Settings に DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH 等のデフォルトパスを定義（data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db）。Monitoring は環境にかかわらず本番 sqlite_path を使用することを明示。

- その他
  - パッケージメタ: __version__ = "0.1.0" を設定。
  - 例外・ログの取り扱い: 監視ループや各処理で例外発生時に logger.exception / logger.warning を使いフェイルセーフに継続する設計。

[0.1.0] - 2026-04-17
--------------------

Added
- 初期公開リリース（v0.1.0）。
- 基幹設定/環境ロード:
  - .env / .env.local の自動読み込み、export 形式とクォート対応、OS 環境変数保護、必須環境変数取得ユーティリティ(_require) を実装。
  - Settings クラスで主要な設定値をプロパティとして提供（API トークン、DB パス、PID/KILL フラグパス、しきい値等）。
- 実行/監視エントリポイント:
  - run_execution: ExecutionEngine 起動、BrokerFactory 経由のブローカ接続、OrderManager/RiskManager/Reconciler の組み立て、Paper Trading の DB 分離を実装。
  - run_monitoring: SystemMonitor のポーリングループ起動、MONITOR_POLL_INTERVAL サポート、停止フラグ検出、DB 初期化を実装。
- ポートフォリオ構築:
  - 候補選定、等配分・スコア配分の重み計算、ポジションサイズ計算（risk_based, equal, score）、集約上限スケーリング、単元株丸め等を実装。
  - セクター上限とレジーム乗数に基づく調整ロジックを実装。
- リサーチ:
  - DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー）、将来リターン計算、IC 算出、統計サマリ等を提供。
- AI / NLP:
  - ニュースを OpenAI でスコアリングする初期実装（バッチ、バックオフ、結果検証、テーブル書き換え戦略等）。
- ユーティリティ:
  - process_priority モジュールで Windows/POSIX 対応の優先度設定、CPU affinity 設定を実装。
- ツール:
  - paper_verification_report CLI による Paper Trading の検証レポート出力（閾値判定、P95 計算など）。

Fixed
- N/A（初期リリース）。

Changed
- N/A（初期リリース）。

Deprecated
- N/A。

Removed
- N/A。

Security
- 環境変数や API キーの扱いについて明示的に未設定時は ValueError を発生させる等、安全側に倒した設計を採用。

注記／既知の制約
- news_nlp の記事収集部分（_fetch_articles 相当）はスニペットで省略されているため、完全動作には関連ヘルパー実装が必要。
- 一部の動作（プロセス優先度設定や CPU affinity の適用）は実行環境の権限に依存し、権限不足時はログ出力のうえスキップする設計。
- DuckDB / SQLite のスキーマ（prices_daily, raw_financials, system_status, trade_logs, risk_logs, ai_scores 等）が前提。環境に合わせた初期データ投入・マイグレーションが必要。
- 本 CHANGELOG はコードスニペットからの推測に基づき作成したため、実際のリリースノートはリリース管理者による確認を推奨します。