# Changelog

すべての注記は Keep a Changelog の形式に準拠します。  
このプロジェクトはセマンティックバージョニングを採用します。

なお、記載内容はソースコードから推測して作成しています（自動生成・実装上の意図を反映）。

## [Unreleased]

## [0.1.0] - 2026-04-09

### Added
- パッケージ初期リリース。
  - パッケージメタ情報:
    - __version__ = "0.1.0"
    - パッケージ説明コメント "KabuSys - 日本株自動売買システム"

- 共通設定 / 環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数の自動読み込み機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルート検出: __file__ を起点に `.git` または `pyproject.toml` を探索
    - 自動ロード無効化: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能
    - .env パーサは export 構文・クォート・エスケープ・インラインコメントをサポート
    - 読み込み失敗時は warnings を出力して安全に継続
  - Settings クラス（settings インスタンスを提供）
    - J-Quants / kabuステーション / LINE / DB パス / 監視設定 / システム設定等のプロパティを提供
    - 必須環境変数未設定時は ValueError を送出する `_require` を利用（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）
    - デフォルト値・入力検証:
      - KABUSYS_ENV: 有効値 {development, paper_trading, live}
      - LOG_LEVEL: 有効値 {DEBUG, INFO, WARNING, ERROR, CRITICAL}
      - PAPER_FILL_MODE: 有効値 {instant, partial, never, reject}
      - ファイルパス系は Path オブジェクトで返却（expanduser される）
    - kill flag 等の監視用設定や閾値（CPU/MEM/DISK）もプロパティで提供

- ポートフォリオ構築モジュール（kabusys.portfolio）
  - portfolio_builder
    - select_candidates: BUY シグナルをスコア降順で選出、同点は signal_rank でタイブレーク
    - calc_equal_weights: 等金額配分 (1/N)
    - calc_score_weights: スコア比率で正規化、スコアが全て 0 の場合は等金額配分にフォールバック（WARNING ログ）
  - risk_adjustment
    - apply_sector_cap: 既存保有のセクター比率が上限を超える場合、新規候補を除外（"unknown" セクターは除外対象外）
    - calc_regime_multiplier: レジームに応じた投下資金乗数を算出（bull=1.0, neutral=0.7, bear=0.3、未知は 1.0 にフォールバック）
  - position_sizing
    - calc_position_sizes: 各銘柄の発注株数を計算
      - allocation_method: "risk_based" / "equal" / "score" サポート
      - risk_based: 許容リスク率 (risk_pct) と損切り率 (stop_loss_pct) から株数算出
      - equal/score: ウェイトを基に配分・単元株（lot_size）で丸め
      - per-stock 上限（max_position_pct）、aggregate cap のスケーリング、cost_buffer を考慮した保守的見積り
      - lot_size 単位での再配分（余剰キャッシュを用いた端数処理）を実装
      - 価格欠損時はログを出してスキップ

- リサーチ / ファクター計算（kabusys.research）
  - factor_research
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を計算（MA200 のデータ不足時は None）
    - calc_volatility: ATR20 / 相対ATR (atr_pct) / 20日平均売買代金 / 出来高比 (volume_ratio) を計算（データ不足は None）
    - calc_value: raw_financials の最新財務データと prices_daily を組み合わせて PER / ROE を計算（EPS 欠損時は None）
    - 実装は DuckDB による SQL 実行 + Python 結果整形（外部 API へアクセスしない設計）
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算、入力検証あり（horizons は 1..252）
    - calc_ic: スピアマンランク相関（IC）を計算。データ不足（有効ペア < 3）の場合は None を返す
    - rank: 同順位は平均ランクとするランク変換（丸めによる ties 対応）
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー（None 値は除外）
  - 研究用ユーティリティは外部ライブラリに依存せず標準ライブラリ + duckdb で実装

- AI 関連（kabusys.ai）
  - news_nlp (ニュース記事を LLM で評価して ai_scores に書き込む)
    - OpenAI（gpt-4o-mini）を利用したニュースセンチメントスコアリング
    - タイムウィンドウ定義（JST ベースで前日 15:00 〜 当日 08:30 を UTC に変換して比較）
    - raw_news + news_symbols から銘柄ごとに最新記事を集約（件数・文字数トリム）
    - バッチサイズ 20 銘柄、JSON Mode を使った応答期待
    - 429/ネットワーク/タイムアウト/5xx は指数バックオフでリトライ（上限あり）。その他は失敗でスキップ（フェイルセーフ）
    - レスポンスの堅牢なバリデーション実装（JSON 抽出、results キー、型・未知コード無視、数値チェック）
    - スコアは ±1.0 にクリップ
    - 成功分のみ ai_scores テーブルへ置換（DELETE → INSERT、部分失敗時に既存スコアを保護）
    - OpenAI クライアント呼び出しは _call_openai_api で抽象化（テスト時に差し替え可能）
  - regime_detector (市場レジーム判定)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で 'bull'/'neutral'/'bear' を判定
    - マクロニュースはタイトルをキーワード検索で抽出（キーワードリストあり）
    - LLM 呼び出しは失敗時に macro_sentiment=0.0 でフォールバック（フェイルセーフ）
    - レジーム合成式: clip(0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment, -1, 1)
    - 判定結果は market_regime テーブルへ冪等に書き込み（BEGIN / DELETE / INSERT / COMMIT）
    - OpenAI 呼び出しはモジュール内 _call_openai_api を使用し、news_nlp と独立した実装を保持

- 監視ログ永続化（kabusys.monitoring.monitoring_db）
  - SQLite ベースの監視 DB 初期化ユーティリティを提供
  - 5 テーブル + インデックスを作成する init_monitoring_db 実装（冪等）
    - 明示的に作成されるテーブルの例:
      - system_status (記録時刻, cpu/memory/disk, process_ok 等)
      - trade_logs (ログ時刻, event_type, client_order_id, code, side, qty, price, filled_qty, state)
      - positions (code 主キー, qty, avg_price, current_price, updated_at)
      - risk_logs （リスク関連ログ）
      - その他（合計 5 テーブルを作成することを意図）
    - テーブルごとに必要なインデックスを作成

- パッケージ再エクスポート / __all__
  - kabusys.portfolio と kabusys.research の主要関数をパッケージルートで再エクスポート（利便性向上）
  - kabusys.ai は score_news を公開

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは引数優先 → 引数未設定時に環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出して安全に停止する箇所を明示。

### Notes / Implementation details / 限界
- Research モジュールは外部ネットワークに依存せず DuckDB の prices_daily / raw_financials テーブルのみ参照する設計。実際のデータを投入して利用する想定。
- news_nlp / regime_detector は OpenAI への依存があり、API のレスポンス不安定時はフェイルセーフで継続（部分的なスコア欠損を許容）。
- .env パーサは一般的な .env 構文に対応しているが、極端なケースのパースは未検証。保護対象の OS 環境変数は .env 読み込み時に上書きされない（.env.local は上書き可能）。
- monitoring_db のスキーマはソース内で定義されているが、将来的に拡張やカラム調整の可能性あり。

----

参考: ソースコードに基づく機能記述です。実際の動作や API の挙動は、実行環境（DB 内容・環境変数・OpenAI の応答など）に依存します。