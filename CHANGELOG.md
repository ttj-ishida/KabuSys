# Changelog

すべての重要な変更はこのファイルに記載します。本ファイルは「Keep a Changelog」仕様に準拠しており、セマンティックバージョニングを使用します。

現在の最新バージョン: 0.1.0

Unreleased
----------

（なし）

[0.1.0] - 2026-04-09
-------------------

Added
- パッケージ初期リリース。
- 基本メタ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。
  - top-level export: ["data", "strategy", "execution", "monitoring"] を公開。

- 環境変数／設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
  - 自動ロードの優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により無効化可能（テスト用）。
  - .env パーサは:
    - コメント行・空行・`export KEY=val` 形式対応、
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応、
    - インラインコメントの取り扱い（クォート外で直前が空白またはタブの場合はコメントと判定）に対応。
  - 必須項目取得ヘルパ `_require()` を提供（未設定時は ValueError）。
  - 代表的な設定プロパティ:
    - J-Quants: `JQUANTS_REFRESH_TOKEN`（必須）
    - kabuステーション: `KABU_API_PASSWORD`（必須）, `KABU_API_BASE_URL`（デフォルト: `http://localhost:18080/kabusapi`）
    - LINE: `LINE_CHANNEL_ACCESS_TOKEN`, `LINE_USER_ID`
    - DB パス: `DUCKDB_PATH`（デフォルト: `data/kabusys.duckdb`）, `SQLITE_PATH`（デフォルト: `data/monitoring.db`）
    - Paper Trading: `PAPER_FILL_MODE`（"instant"|"partial"|"never"|"reject"。不正値は例外）, `PAPER_TRADING_SQLITE_PATH`
    - 監視: `PID_FILE_PATH`, `KILL_FLAG_PATH`, `KILL_FLAG_CLEAR_ON_START`, CPU/メモリ/ディスク閾値
    - 実行環境: `KABUSYS_ENV`（development|paper_trading|live）, `LOG_LEVEL`

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順、タイブレークは signal_rank で行い上位 N を選択。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア加重配分。全スコアが 0 の場合は等配分にフォールバックし警告ログを出力。
  - risk_adjustment:
    - apply_sector_cap: 既存保有のセクター比率が閾値を超える場合、同セクターの新規候補を除外（"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: 市場レジーム（"bull"/"neutral"/"bear"）に応じた乗数を返す（未定義レジームは 1.0 にフォールバックし警告）。
  - position_sizing:
    - calc_position_sizes: 発注株数決定ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）で丸め、1 銘柄上限・全体の aggregate cap、cost_buffer（スリッページ・手数料見積り）を考慮したスケーリングを実装。
    - risk_based ではリスク許容率（risk_pct）、ストップロス（stop_loss_pct）ベースで株数算出。

- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離を計算。ウィンドウ不足時は None を返却。
    - calc_volatility: 20 日 ATR（true range の扱いに注意）、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務を取得して PER/ROE を算出（EPS 欠損時は PER を None）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括で取得。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。レコード不足や定数分散時は None。
    - factor_summary, rank: 基本統計量・ランク付けユーティリティ。
  - 依存は duckdb（SQL ベース）で、pandas 等の外部数値ライブラリには依存しない設計。

- AI 関連（kabusys.ai）
  - news_nlp:
    - raw_news を LLM（OpenAI gpt-4o-mini）でセンチメント評価し ai_scores テーブルへ書き込む機能（score_news）。
    - ニュース集計ウィンドウの計算（target_date に対する JST → UTC 変換）を提供（calc_news_window）。
    - バッチ処理（最大 20 銘柄 / API 呼び出し）、1 銘柄あたり記事数/文字数上限、JSON mode を用いた厳密なレスポンス検証、スコア範囲クリップ（±1.0）、エクスポネンシャルバックオフによるリトライ実装。
    - レスポンスパース失敗時のロバストな復元処理（最外側の {} を抽出して再パースを試みる）や、部分失敗時に既存スコアを保護するための部分的な DELETE→INSERT ロジックを実装。
    - OpenAI API キー引数または環境変数 `OPENAI_API_KEY` を参照（未設定時は ValueError）。
  - regime_detector:
    - ETF 1321 の MA200 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、'bull'/'neutral'/'bear' を日次判定して `market_regime` テーブルへ冪等書き込み（score_regime）。
    - マクロキーワード検索、LLM 呼び出し（gpt-4o-mini）、API エラー時は macro_sentiment=0.0 にフォールバックするフェイルセーフを実装。
    - OpenAI API キーの解決は news_nlp と同様。

- モニタリング永続化（kabusys.monitoring）
  - monitoring_db: SQLite を使った監視ログ永続化層を提供。冪等的にテーブルとインデックスを作成する init_monitoring_db を実装（system_status, trade_logs, positions, risk_logs 等のテーブル作成スクリプトを含む）。

- モジュール公開整理
  - kabusys.portfolio と kabusys.research の __init__ で主要関数を再公開し、利用しやすくした。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Deprecated
- （初版のため該当なし）

Removed
- （初版のため該当なし）

Security
- OpenAI API キーは引数で渡すか環境変数 `OPENAI_API_KEY` を使用する設計。キー未設定時は例外を発生させる（明示的なエラーで漏洩リスク低減）。

Notes / Known issues / TODO
- apply_sector_cap:
  - price_map に価格が欠損（0.0）だとエクスポージャーが過少評価され、ブロックが外れる可能性がある。将来的に前日終値や取得原価へのフォールバックを検討する旨の TODO コメントあり。
- position_sizing:
  - lot_size は現時点では全銘柄共通（デフォルト 100）。将来的に銘柄別 lot_map を導入する TODO が存在。
- duckdb executemany:
  - DuckDB 0.10 における executemany の空リストバインド制約に対する回避ロジックを実装している。DB バージョン差異に注意。
- ニュース/レジーム検出の LLM 部分:
  - 解析では JSON mode を使うが、稀に余計なテキストが混入するため復元ロジックを実装している。LLM の応答形式に依存するため動作確認を推奨。
- タイムゾーン:
  - news_nlp と regime_detector は UTC naive datetime を扱う設計。raw_news.datetime は UTC 保存が前提。環境や DB のタイムゾーン取り扱いに注意。
- 外部依存:
  - 本コードベースは duckdb, openai を利用する。pandas 等には依存しない方針。
- テスト関連:
  - 環境変数自動ロードはテスト用に `KABUSYS_DISABLE_AUTO_ENV_LOAD` により無効化可能。
  - OpenAI API 呼び出し箇所（_call_openai_api）についてはテストで patch 可能な設計になっている（ユニットテスト容易性を考慮）。

Migration notes
- なし（初回リリース）

Contributing
- バグ報告・プルリクエスト歓迎。AI 呼び出し部分は外部 API を使うため、CI ではモック化を推奨。

License
- （ソースに明記がないためここには記載していません。リポジトリのライセンスファイルを参照してください。）

---- 

この CHANGELOG はソースコードのコメント・実装から推測して作成しています。実際のリリースノートとして使用する場合は、変更点の正確性を確認のうえ必要に応じて修正してください。