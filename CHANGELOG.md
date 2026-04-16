# Changelog

すべての注目すべき変更をこのファイルに記載します。フォーマットは「Keep a Changelog」に準拠しています。

注: この CHANGELOG はコードベースから推測して作成しています。

## [Unreleased]
- 今後のリリースに向けた未反映の変更点はここに記載します。

## [0.1.0] - 2026-04-16
初期リリース（推測）。自動売買システム「KabuSys」のコア機能群を実装・追加しました。

### Added
- 全体
  - パッケージ初期化情報を追加（kabusys.__version__ = "0.1.0"）。
  - Settings クラスによる環境変数/設定管理を実装。.env 自動読み込み機能（プロジェクトルート検出、.env/.env.local 読み込み）を提供。
  - 環境検証（KABUSYS_ENV, LOG_LEVEL 等）・必須環境変数のチェック機能を実装。
- 実行ランナー
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時に専用の paper_trading DB を使用する機能を追加（本番 DB と完全分離）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) の取り扱いを実装。
  - run_monitoring.py: SystemMonitor 用のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告のうえデフォルトにフォールバック。
    - 監視は環境に関わらず本番 sqlite_path を使用する設計（監視データは本番 DB に集約）。
    - 停止フラグ検知で安全にループを終了する仕組みを実装。
- モジュール：ポートフォリオ構築（portfolio）
  - portfolio_builder.py
    - select_candidates: BUY シグナルのスコアで候補選定（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を実装。スコア合計が 0 の場合は等配分にフォールバック。
  - risk_adjustment.py
    - apply_sector_cap: セクター集中を防ぐセクター上限フィルタを実装（既存ポジション評価・売却予定銘柄の除外対応）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を実装。未知のレジームは警告のうえフォールバック。
  - position_sizing.py
    - calc_position_sizes: 重み・候補・現金状況等を踏まえた株数計算（risk_based / equal / score）を実装。単元株（lot_size）丸め、per-stock 上限、aggregate cap によるスケールダウン、cost_buffer の考慮などをサポート。
- 研究 / リサーチ（research）
  - factor_research.py
    - calc_momentum / calc_volatility / calc_value: DuckDB を利用したモメンタム・ボラティリティ・バリュー系ファクター計算を実装（prices_daily / raw_financials を参照）。
  - feature_exploration.py
    - calc_forward_returns: 将来リターン（複数ホライズン）の一括計算機能を実装（horizons バリデーションあり）。
    - calc_ic: スピアマンのランク相関（IC）を実装（データ不足時は None を返す）。
    - factor_summary / rank: 統計サマリ・ランク付けユーティリティを実装。
  - research package のエクスポートに主要ユーティリティを追加。
- AI / ニュース NLP（ai）
  - news_nlp.py
    - raw_news を OpenAI（gpt-4o-mini 想定）へ送信して銘柄別センチメントを算出し ai_scores テーブルへ保存する処理を実装（バッチ送信、スコアクリップ、リトライ戦略などを設計）。
    - ニュース収集ウィンドウの計算（JST 基準）ユーティリティを実装。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加（稼働率、注文成功率、レイテンシ等の集計・閾値判定）。CLI オプション（--from/--to/--db）対応。
- DB / モニタリング補助
  - monitoring_db.init_monitoring_db の利用（起動時に監視テーブルを冪等的に保証）。
  - DuckDB / SQLite の両方を接続するワークフローを各種ランナーで採用。
- ユーティリティ
  - utils/process_priority.py: プラットフォーム差を吸収したプロセス優先度設定（Windows/HIGH_PRIORITY_CLASS, POSIX の nice 値）と CPU affinity 設定を実装。アクセス権限不足などは警告でスキップ。
  - utils モジュール初期化ファイルを追加。

### Changed
- 設計/挙動
  - .env 自動ロードはプロジェクトルートの検出に依存するように変更（__file__ を起点に親ディレクトリを探索）。プロジェクトルートが見つからない場合は自動ロードをスキップ。
  - .env 読み込みでは OS 環境変数を保護（protected）し、.env.local で上書き可能にする優先度ルールを採用。
  - Paper Trading モードと本番モードで DB を分離（paper_trading 用の専用 SQLite）。
  - 監視ループのポーリング間隔は MONITOR_POLL_INTERVAL で上書き可能だが、不正値はログ警告のうえデフォルトにフォールバックする堅牢化を実施。
  - ExecutionEngine／SystemMonitor 起動時にプロセス優先度を "high" に設定する処理を追加（起動直後に変更）。
  - AI ニューススコアリングは複数銘柄をまとめてバッチ送信、レスポンス検証、部分成功時の既存スコア保護（影響範囲を限定）といった耐障害性方針を採用。

### Fixed
- 入力検証・フォールバック
  - Settings.paper_fill_mode: 無効な値が設定された場合に ValueError を送出するようにバリデーションを追加。
  - Settings.env / log_level: 不正な値に対して明確なエラーメッセージを出すバリデーションを追加。
  - MONITOR_POLL_INTERVAL: 0 以下や非整数が設定された場合にデフォルトへフォールバックし、警告ログを出すように修正（time.sleep に不正な値を渡さないように）。
  - calc_score_weights: 全スコアが 0 の場合に等金額配分へフォールバックし、警告ログを出すように修正。
  - calc_regime_multiplier: 未知のレジーム文字列に対して警告を出し 1.0 をフォールバック値として返すように。
  - factor/feature utilities:
    - calc_forward_returns: horizons の入力検証（正の整数かつ <=252）を追加。
    - calc_ic: 有効レコードが 3 件未満の場合は None を返す（計算不能扱い）。
    - rank: 同順位（ties）を平均ランクで扱う実装にし、丸め誤差に対する安定性向上のため round(..., 12) を導入。
  - position_sizing: lot_size 単位での丸め、aggregate cap によるスケールダウンロジック、残余キャッシュでの再配分を実装して投資合計が available_cash を超えないように制御。
  - volatility / momentum / value 計算: 欠損や十分でない窓長に対して None を返すなど、欠損耐性を向上。

### Security
- 環境変数読み込み
  - .env 自動ロードの際に OS 環境変数を保護（既存の OS 環境変数は上書きされない）する仕組みを導入。

### Notes / Implementation details
- 多くのコンポーネントは DuckDB / SQLite を利用しており、リサーチ系は DuckDB の SQL Window 関数等を用いて計算を行う設計です。
- AI ニュース処理は OpenAI API のエラー（429, ネットワーク等）に対して指数バックオフでリトライする方針ですが、API キー未設定時は ValueError を投げます。
- 一部ファイル（ai/news_nlp.py）は出力途中で切れている可能性があり、実装の続き（記事集約関数等）が存在すると推測されます。

## Deprecated
- なし

## Removed
- なし

もしこの CHANGELOG に追加・修正すべき点があれば、変更内容の意図や差分箇所（コミット/ファイル）を教えてください。それに基づいて更新します。