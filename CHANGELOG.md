# CHANGELOG

すべての注目すべき変更をここに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

最新の変更は上位に記載します。

## Unreleased
- （なし）

## [0.1.0] - 2026-04-11
最初の公開リリース。システム全体のコア機能（設定管理、監視・実行用エントリポイント、ポートフォリオ構築、ポジションサイズ計算、リスク制約、リサーチ用ファクター計算、AI ベースのニュースセンチメント判定、市場レジーム判定、プロセス優先度ユーティリティ等）を実装しました。

### Added
- 全体
  - パッケージ初期バージョンを追加（kabusys.__version__ = "0.1.0"）。
  - DuckDB / SQLite を用いたデータ処理基盤を採用（各種モジュールで DuckDB 接続を受け取る設計）。
  - .env ファイル自動ロード機能（プロジェクトルートの検出: .git または pyproject.toml を基準）。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化オプションを提供。

- 設定（kabusys.config）
  - Settings クラス実装: 各種環境変数（J-Quants / KabuAPI / LINE / DB パス / 監視フラグ / スレッショルド等）をプロパティで提供。
  - .env パーサ実装: export 形式・クォート（シングル／ダブル）・エスケープ・インラインコメント対応。既存 OS 環境変数を保護する protected オプションを実装。
  - 環境変数検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）と未設定時のエラー報告。

- 実行エントリポイント
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine.run_session() を実行。
    - duckdb 接続および監視テーブル初期化（冪等）を実施。
    - プロセス優先度を最初に "high" に設定する処理を含む。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視処理は環境に依らず本番 sqlite_path を使用して DB を開く。
    - 例外発生時はログ出力して次のポーリングを継続、KeyboardInterrupt による正常終了処理を実装。

- プロセス制御ユーティリティ（kabusys.utils.process_priority）
  - set_process_priority(level): Windows / POSIX（Linux, macOS, FreeBSD）差分を吸収してプロセス優先度（nice / HIGH_PRIORITY_CLASS 等）を設定。未対応 OS やアクセス拒否時には警告ログでスキップ。
  - set_cpu_affinity(cpu_count): カレントプロセスを最初の N コアにピン留め。引数検証と失敗時の安全ハンドリングを実装。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順（同点は signal_rank 昇順）で選定し上位 N を返す。
    - calc_equal_weights: 等金額配分（1/N）を計算。
    - calc_score_weights: スコア加重配分を計算。全銘柄のスコア合計が 0 の場合は等金額配分にフォールバックして WARNING を出力。
  - risk_adjustment:
    - apply_sector_cap: セクター別既存保有比率が上限を超える場合、そのセクターの新規候補を除外。unknown セクターは上限適用対象外。売却予定銘柄をエクスポージャー計算から除外可能。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（デフォルト: bull=1.0, neutral=0.7, bear=0.3）。未知レジームは警告を出して 1.0 にフォールバック。
  - position_sizing:
    - calc_position_sizes: 複数の配分方式をサポート（risk_based / equal / score）。
      - 単元株（lot_size）丸め、per-stock 上限（max_position_pct）、aggregate cap（available_cash を超える場合のスケーリング）、cost_buffer（手数料・スリッページ見積り）を考慮。
      - risk_based: 損切り率・risk_pct に基づく目標株数算出。
      - aggregate cap 時のスケールダウンでは小数端数処理（lot 単位で再配分）を実装し、再現性維持のため安定ソートを採用。

- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を DuckDB SQL で計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR（atr_20・atr_pct）、20日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算。true_range の NULL 伝播処理で過少評価を避ける設計。
    - calc_value: raw_financials から target_date 以前の最新財務を取得し PER/ROE を計算。
  - feature_exploration:
    - calc_forward_returns: target_date から将来リターン（複数ホライズン）を一度に取得するクエリを実装（horizons 引数は検証あり）。
    - calc_ic / rank / factor_summary: Spearman ランク相関（IC）の計算、同順位は平均ランク扱い、統計サマリー（count/mean/std/min/max/median）等を提供。
  - DuckDB に依存する関数群は、ルックアヘッド回避のため日付条件や範囲計算に注意した実装。

- AI 機能（kabusys.ai）
  - news_nlp.score_news:
    - raw_news / news_symbols から銘柄毎に前日 15:00 JST ～ 当日 08:30 JST の記事を集約し、OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを -1.0〜1.0 のスコアで取得。
    - バッチ処理（最大 20 銘柄/API 呼び出し）、1 銘柄あたりの記事数・文字数上限トリムを実装。
    - レート制限（429）・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライを実装。その他のエラーは安全にスキップ。
    - LLM レスポンスの厳密な JSON 検証（results キー存在・型・code の既知性・数値チェック）。必要に応じてレスポンスから最外側の {} を抽出して復元。
    - スコアは ±1.0 にクリップ。部分成功時でも既存の他銘柄スコアを消さない形で DELETE→INSERT による冪等書き込み（トランザクション）を行う。
    - OpenAI API キー未設定時は ValueError を送出。
  - regime_detector:
    - ETF 1321 の 200 日 MA 乖離とマクロニュースの LLM センチメントを組み合わせて日次レジーム（'bull'/'neutral'/'bear'）を判定する機能を追加。
    - prices_daily のクエリでは target_date 未満のみを参照（ルックアヘッド防止）。
    - マクロセンチメントの LLM 呼び出しは失敗時に 0.0 を採用（フェイルセーフ）。判定結果は market_regime テーブルへ冪等的に書き込む。

### Changed
- 設計上の明示
  - ほとんどの計算関数は DuckDB/SQLite のテーブル（prices_daily, raw_financials, raw_news 等）を参照し、外部 API（取引 API 等）にはアクセスしないよう分離。
  - 日次計算モジュールは datetime.today()/date.today() を直接参照しない設計（target_date を引数に取りルックアヘッドを防止）。

### Fixed / Robustness improvements
- 環境変数パース／検証
  - MONITOR_POLL_INTERVAL の不正値（非数・0 以下）に対して警告を出しデフォルト（60 秒）へフォールバックするように修正。
  - PAPER_FILL_MODE や KABUSYS_ENV、LOG_LEVEL の不正値検出と明確なエラーメッセージを追加。
  - .env のクォート処理でバックスラッシュエスケープに対応、インラインコメント処理の改善。

- AI レスポンス / API
  - OpenAI レスポンスの JSON パース失敗時に例外を投げずに警告ログを出してスキップする堅牢化を実施。
  - API 呼び出し時のリトライ対象例外の選別と指数バックオフを導入（RateLimitError / APIConnectionError / APITimeoutError / 5xx 相当の APIError）。
  - レスポンス検証で未知コードは無視し、スコアが数値でない場合は警告を出して除外。

- DB トランザクション
  - ai_scores へ書き込む際の DELETE/INSERT をトランザクションで囲み、失敗時に ROLLBACK を試行。DuckDB の executemany の制約（空リスト不可）へ対応。

- 計算ロジック
  - calc_score_weights: 全スコアが 0 の場合に等配分へフォールバック（警告ログ）。
  - apply_sector_cap: unknown セクターを上限適用除外とする明示的動作。
  - position_sizing: lot_size 丸め、_max_per_stock の上限、aggregate cap スケールダウン時の安定した残差配分を実装。

### Deprecated
- （なし）

### Removed
- （なし）

### Security
- OpenAI API キーは環境変数 OPENAI_API_KEY か関数引数で明示的に渡す実装。未設定時は ValueError を発生させ安全に失敗させます。

---

注記:
- 本 CHANGELOG はソースコードの内容から推測して作成したものであり、実際のコミット履歴とは異なる場合があります。必要に応じて実際の変更点・日付・バージョン番号を更新してください。