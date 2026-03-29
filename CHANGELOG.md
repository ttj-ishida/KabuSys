# Changelog

すべての注目すべき変更点を Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) 準拠で記載します。

全体方針：
- モジュールごとに明確な公開 API を提供
- ルックアヘッドバイアス（未来データ参照）の防止を設計方針に明示
- OpenAI / 外部 API 呼び出しにはフェイルセーフ（フォールバック）とリトライ処理を実装
- DuckDB をデータ処理の主要ストアとして利用
- 単体テストしやすいように外部呼び出しポイントを差し替え可能に実装

## [0.1.0] - 2026-03-29

### Added
- パッケージ基盤
  - パッケージ初期化 `kabusys.__init__` を追加し、バージョン `0.1.0` とサブパッケージ（data, strategy, execution, monitoring）の公開を定義。

- 設定/環境変数管理 (`kabusys.config`)
  - .env ファイルと環境変数を読み込む自動ローダーを実装（プロジェクトルートを .git または pyproject.toml から探索）。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。
  - 自動ロードを無効化するための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。
  - `.env` パース機能を実装（コメント、export プレフィックス、シングル/ダブルクォート内のエスケープに対応）。
  - OS 環境変数の保護（既存キーを protected として上書きから除外）をサポート。
  - 必須設定を取得する `_require` と `Settings` クラスを実装。J-Quants や kabu ステーション、Slack、DB パス、実行環境（development/paper_trading/live）、ログレベルのバリデーションを提供。

- AI（NLP）関連 (`kabusys.ai`)
  - news_nlp モジュールを追加（`score_news` を公開）
    - raw_news / news_symbols を集約して銘柄ごとのニュースを生成し、OpenAI (gpt-4o-mini) の JSON mode でバッチスコアリング。
    - チャンク処理（最大 20 銘柄/リクエスト）、1 銘柄あたり記事数・文字数制限、結果のバリデーションと ±1.0 クリッピングを実装。
    - リトライ（429/ネットワーク/タイムアウト/5xx）を指数バックオフで行い、最終的に失敗したチャンクはスキップ（フェイルセーフ）。
    - レスポンスの JSON パース耐性（余分テキストを含む場合の最外側の {} 抽出）を実装。
    - テスト向けに OpenAI 呼び出しポイントを差し替え可能（_call_openai_api の patch が可能）。
    - 時間ウィンドウ計算 util `calc_news_window` を提供（JST ベースの前日 15:00 〜 当日 08:30 を UTC naive datetime に変換）。
    - 成功した銘柄分のみ ai_scores テーブルへ冪等的に（DELETE→INSERT）保存。部分失敗時に既存データを保護する設計。

  - regime_detector モジュールを追加（市場レジーム判定: `score_regime`）
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）と、news_nlp によるマクロセンチメント（重み 30%）を合成して日次でレジーム判定（bull/neutral/bear）を行う。
    - prices_daily / raw_news を参照し、OpenAI を用いたセンチメント評価を行う（最大記事数制限、JSON パース、リトライ/バックオフ、失敗時は macro_sentiment=0.0 にフォールバック）。
    - DuckDB への書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で行う。
    - 設計方針として datetime.today() 等によるルックアヘッドを避けることを明記。

- データプラットフォーム (`kabusys.data`)
  - calendar_management モジュールを追加
    - JPX カレンダー管理ロジック（market_calendar テーブルの使用、祝日・半日・SQ判定）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day といったヘルパーを提供。
    - DB にデータがない場合は曜日ベースのフォールバックを行う（土日は非営業日）。DB 登録値があればそれを優先する設計で一貫性を保つ。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を更新する夜間バッチ処理を実装。バックフィルと健全性チェックを実装。

  - ETL / パイプライン (`kabusys.data.pipeline`)
    - ETL 層の設計と実装（差分取得、save_* の idempotent 保存、品質チェックの実行を想定）。
    - `ETLResult` データクラスを追加（取得件数・保存件数・品質問題・エラー一覧を保持し、to_dict でシリアライズ可能）。
    - 内部ユーティリティ（テーブル存在チェック、最大日付取得、market_calendar 調整ロジックなど）を実装。

  - `kabusys.data.etl` で `ETLResult` を再エクスポート。

- リサーチ/ファクター解析 (`kabusys.research`)
  - factor_research を実装（`calc_momentum`, `calc_value`, `calc_volatility`）
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None を返す挙動）。
    - Volatility & Liquidity: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率。
    - Value: raw_financials から EPS/ROE を取得して PER/ROE を算出。
    - 全て DuckDB SQL を用いた実装。外部 API へのアクセスなし（安全）。
  - feature_exploration を実装（`calc_forward_returns`, `calc_ic`, `factor_summary`, `rank`）
    - 将来リターンを任意ホライズン（デフォルト [1,5,21]）で計算する `calc_forward_returns`。
    - Spearman ランク相関に基づく IC 計算（`calc_ic`）。有効レコードが 3 未満なら None を返す。
    - ランク変換ユーティリティ `rank`（同順位は平均ランク、丸め処理で ties の検出安定化）。
    - 基本統計量を返す `factor_summary` を追加（count/mean/std/min/max/median）。

- パッケージエクスポートの追加
  - `kabusys.ai.__init__` で `score_news` を公開。
  - `kabusys.research.__init__` で主要関数を公開。

### Changed
- ドキュメント的・設計的な変更（ライブラリ初期構成の一部）
  - 各モジュールに詳細な docstring を追加して、処理フロー、設計方針、入出力・例外挙動を明記。

### Fixed
- レジリエンス／パース改善
  - OpenAI レスポンスの JSON パースの脆弱性に対する耐性強化（余分テキストが混入した場合にも最外側の JSON オブジェクトを抽出して復元する試みを実装）。
  - news_nlp / regime_detector ともに API 呼び出しで発生する 429 / ネットワーク断 / タイムアウト / 5xx エラーに対して指数バックオフでリトライするロジックを実装、最大リトライ到達時はログを残してフォールバックする。

### Security
- 環境変数管理の安全策
  - `.env` 読み込み時に OS 上の既存環境変数を上書きしないデフォルト動作とし、.env.local による上書きは許容するが既存 OS 環境変数を protected として上書きしない設計。
  - 自動ロードの無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を用意し、テストや特殊環境での誤読を防止。

### Behavior
- 未来データ参照の回避（重要）
  - AI モジュール（news_nlp, regime_detector）、リサーチ／ETL の各処理は内部で datetime.today() / date.today() を用いず、明示的な target_date 引数に基づいて計算を行う実装になっている。これによりルックアヘッドバイアスを防止。
- DuckDB 互換性
  - executemany の空リストバインド回避など DuckDB の挙動に配慮した実装（部分書き換えで既存データ保護）。

### Notes / Migration
- 本リリースは初期版（0.1.0）。API、テーブルスキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials 等）に依存します。既存環境へ導入する場合はテーブル定義と .env の整備（.env.example の参照）を行ってください。
- OpenAI API を利用する機能（news_nlp, regime_detector）は環境変数 OPENAI_API_KEY または関数引数で API キーを渡す必要があります。キー未設定時は ValueError を送出します。
- 自動 .env ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

もし特定モジュールについて詳細な変更点（例: 関数の引数/戻り値の仕様、DB スキーマ想定など）をCHANGELOGに追記したい場合は、どのモジュールを深掘りするか指示してください。