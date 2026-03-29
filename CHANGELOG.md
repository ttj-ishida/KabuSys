# Changelog

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

全てのリリースはセマンティックバージョニングに従います。

## [Unreleased]

## [0.1.0] - 2026-03-29
初回公開リリース。

### Added
- パッケージ基盤
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - public API: kabusys.data, kabusys.strategy, kabusys.execution, kabusys.monitoring を __all__ で公開。

- 設定管理
  - 環境変数/.env 読み込み機能を実装（src/kabusys/config.py）。
  - プロジェクトルート自動検出: .git または pyproject.toml を基準に .env を探索。
  - .env パースの強化:
    - export KEY=val 形式対応
    - シングル/ダブルクォートのエスケープ処理対応
    - インラインコメント処理（クォート有無での挙動差分）
  - 自動ロード制御: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - 必須キー取得ヘルパー _require() と Settings クラスを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等のプロパティをラップ。
  - デフォルト値とバリデーション:
    - KABUSYS_ENV は development/paper_trading/live のいずれかで検証。
    - LOG_LEVEL 値検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - DB パスのデフォルト: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"。

- データモジュール / ETL
  - ETL 結果表現: ETLResult dataclass を実装・公開（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）。
  - 差分更新・バックフィル設計を反映した ETL パイプライン基盤を実装（pipeline.py）。
    - 最小データ日 (_MIN_DATA_DATE)、カレンダー先読み、backfill パラメータ等の定義。
    - DuckDB のテーブル存在チェックや最大日付取得ユーティリティを提供。
  - market_calendar（JPX カレンダー）管理と夜間バッチ（calendar_update_job）を実装（src/kabusys/data/calendar_management.py）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティ。
    - DB 登録有無に応じた「DB優先・未登録は曜日フォールバック」設計。
    - 保存処理は冪等（ON CONFLICT 等を想定）で実行。
    - バックフィル、健全性チェック（最大未来日数の検査）を実装。

- 研究（Research）モジュール
  - ファクター計算群を実装（src/kabusys/research/）
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率等を計算。
    - calc_value: raw_financials の最新財務データと価格を結合して PER・ROE を算出。
  - 特徴量解析ユーティリティ（feature_exploration.py）
    - calc_forward_returns: 将来リターン（任意ホライズン）を効率的に取得。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算。
    - rank: 同順位は平均ランクにするランク化ユーティリティ（丸め処理で ties の誤差を低減）。
    - factor_summary: count/mean/std/min/max/median の統計サマリー。
  - 研究用ユーティリティは DuckDB 接続を受け取り、prices_daily / raw_financials 等のローカル DB テーブルのみを参照（発注API等にはアクセスしない設計）。

- AI（LLM）関連
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode により銘柄別センチメントスコアを取得。
    - ウィンドウ定義（JST 基準）:
      - 前日 15:00 JST 〜 当日 08:30 JST（内部は UTC naive datetime で処理）。
    - バッチ処理: 最大 _BATCH_SIZE=20 銘柄ごとに API 呼び出し。
    - トークン肥大対策: 1 銘柄あたり _MAX_ARTICLES_PER_STOCK=10、_MAX_CHARS_PER_STOCK=3000。
    - エラーハンドリング・リトライ: 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ。
    - レスポンスバリデーション: JSON 抽出、"results" 構造検査、スコア数値検証、未知コード無視。
    - 書き込み: 成功したコードのみを対象に ai_scores テーブルを DELETE → INSERT（部分失敗時に既存スコアを保護）。
    - テスト容易性: _call_openai_api を patch で差し替え可能に実装。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - マクロ記事の抽出はキーワードリストに基づくフィルタ（_MACRO_KEYWORDS）。
    - LLM 呼び出しは独立実装（news_nlp と内部関数共有なし）でテストしやすく設計。
    - API 失敗時は macro_sentiment=0.0 でフォールバック（フェイルセーフ）。
    - 出力は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。

- 汎用設計方針・品質
  - ルックアヘッドバイアス回避:
    - モジュール内部で datetime.today() / date.today() を直接参照しない（target_date を明示的に受け取る）。
    - DB クエリは target_date 未満/以前などの排他条件を厳密に扱う。
  - DB 書き込みは冪等性を重視（DELETE→INSERT、ON CONFLICT 想定）。
  - OpenAI 関連は JSON Mode を期待しつつ、パースの堅牢化（前後余計なテキストの復元）を行う。
  - リトライ戦略とエラーハンドリングを明示（ログ出力・フェイルセーフ）。
  - DuckDB 0.10 の制約（executemany に空リスト不可等）への配慮を実装。

### Notes / 必要な環境変数
- 必須（Settings._require により未設定時は ValueError）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
- OpenAI
  - OPENAI_API_KEY は news_nlp.score_news や regime_detector.score_regime に渡すか環境変数に設定する必要がある（未設定時は ValueError）。
- 自動 .env ロード
  - .env / .env.local をプロジェクトルートから自動読み込み。OS 環境変数は保護され上書きされない（.env.local は override=True だが protected を尊重）。
  - 自動読み込み停止: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

### 使用する DB テーブル（想定）
- prices_daily
- raw_news
- news_symbols
- ai_scores
- market_regime
- raw_financials
- market_calendar
（各モジュールの説明に従い DuckDB 上でこれらのテーブルを用いることを前提としています）

### Breaking Changes
- 初回リリースのため該当なし。

### Known limitations / 今後の改善候補
- OpenAI モデルは現時点で gpt-4o-mini を想定。将来のモデル差分や API 仕様変更への対応が必要。
- news_nlp の結果検証は JSON Mode に依存しているが、LLM 出力の揺らぎをさらに堅牢に処理する余地あり。
- ETL の品質チェックは pipeline モジュールで定義されるが、チェックルールの拡張や自動リカバリの仕組みは今後改善可能。
- calendar_update_job は jquants_client の fetch/save 実装に依存するため、実環境での挙動確認が必要。

---

開発に関する問い合わせや提案があれば README や Issue を通じて報告してください。