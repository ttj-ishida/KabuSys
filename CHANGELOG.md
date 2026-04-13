CHANGELOG
=========

すべての注目すべき変更点を記録します。本ファイルは "Keep a Changelog" の形式に準拠しています。

フォーマット:
- 変更はセマンティクスごとにカテゴリ分け（Added, Changed, Fixed, Deprecated, Removed, Security）。
- 日付はリリース日時を示します。

[Unreleased]
------------

（現時点で未リリースの作業はありません）

[0.1.0] - 2026-04-13
-------------------

Added
- 基本機能の初期実装を追加（初回リリース）。
  - パッケージ識別子 / バージョン:
    - kabusys.__version__ = "0.1.0"
- 設定・環境変数管理（kabusys.config）
  - .env 自動読み込み機能（プロジェクトルート検出: .git / pyproject.toml 基準）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD サポート。
  - .env パースロジックを強化（export 形式、クォート文字列、インラインコメント処理、エスケープ処理対応）。
  - 必須変数取得関数 _require と、各種設定プロパティ（DB パス、PID ファイルパス、監視閾値、環境判定等）を実装。
  - 入力検証を追加（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の検証）。
- 実行系スクリプト
  - run_execution: ExecutionEngine の起動スクリプトを追加。
    - プロセス優先度を高に設定（set_process_priority("high")）。
    - Paper Trading モード（KABUSYS_ENV=paper_trading）では専用 SQLite（data/paper_trading.db をデフォルト）を使用し、本番 DB と分離。
    - DuckDB 接続の初期化を行う。
    - BrokerClientFactory を経由して Broker クライアントを生成。
    - OrderRepository、OrderManager、RiskManager、Reconciler を組み立てて ExecutionEngine を起動。
    - RiskConfig のデフォルト値（max_position_pct=0.20 等）を設定。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバック。
    - 監視処理は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（監視は常に本番 DB を見る設計）。
    - プロセス優先度を高に設定し、例外はログに記録してループを継続するフェイルセーフ実装。
- 監視 DB 初期化ユーティリティ（init_monitoring_db 呼び出し）を run スクリプトに組み込み。
- ユーティリティ: プロセス優先度・CPU affinity 設定（kabusys.utils.process_priority）
  - set_process_priority(level) — Windows / POSIX の差を吸収して優先度を設定。
  - set_cpu_affinity(cpu_count) — 指定コア数へのピン留め（実行環境で未対応・権限なしの場合は警告でスキップ）。
  - 権限不足や未対応 OS に対しては安全にスキップするロバストな動作。
- Portfolio 構築モジュール（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates: BUY シグナルのスコア降順選定（同スコア時は signal_rank でブレーク）。
    - calc_equal_weights / calc_score_weights: 等重み・スコア加重配分（スコア合計が 0 の場合は等重みにフォールバック）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中制限の適用（既存保有のセクター別エクスポージャーを計算して候補をフィルタ）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。
  - position_sizing:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく株数算出、単元株丸め、per-stock 上限・aggregate cap、cost_buffer 考慮のスケーリング。
    - lot_size, cost_buffer 等のパラメータを受け取り将来拡張を想定した設計。
- Research / Factor モジュール（kabusys.research）
  - factor_research:
    - calc_momentum / calc_volatility / calc_value: DuckDB の prices_daily / raw_financials を参照してモメンタム・ボラティリティ・バリュー指標を計算。
    - 一定期間のスキャン範囲や不足データに対する None ハンドリングを実装。
  - feature_exploration:
    - calc_forward_returns: 将来リターン（任意ホライズン）を計算。horizons 引数の検証あり。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（有効レコードが 3 未満は None）。
    - factor_summary / rank: 基本統計量、ランク付け（同順位は平均ランク）。
  - research パッケージの __all__ を整備して主要関数をエクスポート。
- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news を OpenAI（gpt-4o-mini）でスコアリングして ai_scores テーブルへ保存する設計を追加。
  - ニュース収集ウィンドウ（JST基準: 前日 15:00 ～ 当日 08:30）を calc_news_window にて計算。
  - バッチ処理（最大 20 銘柄 / API コール）、トリム（最大記事数 / 最大文字数）等のトークン肥大化対策を実装。
  - リトライ（429/5xx/タイムアウト等）に対する指数バックオフ、レスポンス検証、スコアの ±1.0 クリップ、部分成功時の DB 保護（該当コードに絞った置換）などを設計。
  - API キー未設定時は明示的な ValueError を送出。
- Tools
  - paper_verification_report: Paper Trading 検証レポート生成スクリプトを追加。
    - CLI (--from, --to, --db) による期間指定・DB 指定をサポート。
    - システム稼働率、注文成功率（fill率）、送信率、P95 レイテンシ等を集計して PASS/FAIL 判定（デフォルト閾値を定義）。
    - DB が見つからない場合のエラーメッセージと安全な終了。
    - P95 計算、NULL データの扱い、テーブルがない場合の例外ハンドリングを実装。

Changed
- 設計方針として "本番データアクセスと研究用処理を明確に分離"。
  - research / ai モジュールは本番発注 API へアクセスしない設計（DuckDB / ローカル DB のみ参照）。
  - Paper Trading は専用 SQLite を用いることで本番データと完全分離。
- .env パーサーとロードの挙動を強化して現場での柔軟性を向上（export プレフィックス、クォート内エスケープ、インラインコメントの扱い）。

Fixed
- 複数箇所での堅牢性改善とフォールバック動作を追加。
  - MONITOR_POLL_INTERVAL に不正値が設定された場合はログを出してデフォルトにフォールバック（run_monitoring）。
  - process_priority / cpu_affinity 設定時の権限不足や未サポート OS を警告して処理をスキップ（クラッシュしない）。
  - DB テーブル未存在による OperationalError を paper_verification_report 内で捕捉して安全にレポート生成を継続。
  - calc_score_weights でスコア合計が 0 の場合は等金額配分にフォールバック（警告ログ）。
  - calc_position_sizes のスケーリング処理は端数配分を再現性を持って行う実装（lot 単位での丸めと残余配分）。
  - factor_research / feature_exploration の各関数でデータ不足時に None を返す等の安全処理を明確化。

Security
- OpenAI API キーは明示的に引数または環境変数 OPENAI_API_KEY から取得。未設定時はエラーにより処理を中断し誤ったキー利用を防止。
- .env ロード時に OS 環境変数を保護する仕組みを実装（protected set により既存 OS 環境変数を上書きしない）。

Deprecated
- なし（初回リリース）。

Removed
- なし（初回リリース）。

注記 / 今後の改善案（コードから推測）
- position_sizing: 銘柄ごとの lot_size をサポートするため将来的に銘柄マスタからの lot_map を取り込む余地がある旨 TODO 記載あり。
- apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過小評価される可能性があり、前日終値等のフォールバック価格導入が検討対象。
- ai/news_nlp の実装（コード末尾が途中で切れている）に関しては、API レスポンス処理・DB 書き込みの最終部分の実装が必要（部分的に未完の可能性あり）。
- DuckDB バージョン依存（executemany の制約など）を踏まえたテストが推奨される。

--- 

以上。必要であれば各変更点を個別に詳述したセクション（関数単位の例、利用方法、環境変数一覧など）も作成できます。どの粒度で追記するか指示ください。