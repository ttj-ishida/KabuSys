# Changelog

すべての重要な変更をこのファイルに記録します。  
形式は「Keep a Changelog」に準拠します。

## [Unreleased]

- （現在のリリース時点で未反映の変更はここに記載してください）

## [0.1.0] - 2026-04-04

Initial release — 日本株自動売買／データ基盤の初期機能群を実装。

### Added
- パッケージ基盤
  - pakage: kabusys (version 0.1.0)
  - パッケージ公開インターフェースを定義（kabusys.__all__ に data/strategy/execution/monitoring を登録）。

- 設定・環境変数管理（kabusys.config）
  - .env / .env.local を自動ロードする仕組みを実装（プロジェクトルートを .git / pyproject.toml から探索）。
  - .env のパース機能を強化（export KEY=val 形式、クォート内のエスケープ、行末コメント処理などに対応）。
  - OS 環境変数の保護機能（.env.local で既存 OS 環境を上書きしない等）を実装。
  - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB パス / 監視閾値 / 環境（development / paper_trading / live）などのプロパティを公開。値検証（許容値チェック、未設定時の例外）を導入。

- AI（自然言語処理 / レジーム判定）
  - kabusys.ai.news_nlp.score_news
    - 指定日を基準とするニュース収集ウィンドウを算出（JST基準→UTC変換）。
    - raw_news と news_symbols を結合して銘柄ごとに記事を集約、トリムして OpenAI にバッチ送信（gpt-4o-mini、JSON Mode）。
    - バッチサイズ、記事数上限、文字数上限を設定してトークン肥大化対策。
    - レスポンスの厳密なバリデーションとスコアの ±1.0 クリップ。
    - DuckDB への冪等書き込み（対象コードのみ DELETE → INSERT）で部分失敗時のデータ保護。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフのリトライ実装。
  - kabusys.ai.regime_detector.score_regime
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次市場レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news を参照して ma200_ratio を計算、マクロ記事抽出、OpenAI 呼び出し、スコア合成。
    - API 呼び出し失敗時は macro_sentiment=0.0 のフォールバック（フェイルセーフ）。
    - DB へ冪等的に書き込むトランザクション制御（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。

- データ基盤（kabusys.data）
  - calendar_management
    - market_calendar を利用した営業日判定ロジックを実装（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - market_calendar が未登録の期間は曜日ベース（土日除外）でフォールバック。
    - calendar_update_job により J-Quants からの差分取得／バックフィル／保存（fetch/save through jquants_client）を実行する夜間バッチ処理を実装。健全性チェック（将来日付の異常検出）とバックフィル戦略を導入。
  - pipeline / etl
    - ETLResult データクラスを実装（ETL 実行結果、品質問題、エラーメッセージなどを集約）。
    - ETL の設計に関するユーティリティと定数（差分更新、backfill、カレンダー先読み等）を実装。
  - etl モジュールは pipeline.ETLResult を再エクスポート。

- リサーチ（kabusys.research）
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）等の計算。データ不足時の None ハンドリング。
    - calc_volatility: 20 日 ATR（true range を厳密に扱う）、相対 ATR、20日平均売買代金、出来高比率等の計算。
    - calc_value: raw_financials から最新の EPS/ROE を取得して PER/ROE を計算（EPS が 0/欠損の扱いに注意）。
  - feature_exploration
    - calc_forward_returns: 指定日から各ホライズン（デフォルト [1,5,21]）の将来リターンを計算。ホライズン検証と範囲バッファを実装。
    - calc_ic: Spearman ランク相関（Information Coefficient）を実装（結合/欠損除外/最小サンプル要件）。
    - rank: 同順位は平均ランクを返す堅牢なランク関数（丸めで ties 判定の安定化）。
    - factor_summary: 各ファクターの count/mean/std/min/max/median を算出。

- 実装上の設計方針（横断）
  - DuckDB を主たるデータストアとして利用（クエリは DuckDB 接続を受け取る）。
  - ルックアヘッドバイアス防止（datetime.today()/date.today() を直接参照しない設計、target_date に基づく計算）。
  - API 呼び出しのフェイルセーフ化（失敗時に例外を投げずにフォールバック or スキップし、処理を継続）。
  - OpenAI の JSON Mode を利用し、応答を厳密にパースすることで downstream 処理の安全性を確保。
  - ロギングを広範に導入し、警告・情報・デバッグ出力を豊富に提供。

### Changed
- （初期リリースのため「変更」は特になし。以降のリリースで履歴を追加してください。）

### Fixed / Edge-case handling
- DuckDB 関連
  - executemany に空リストを渡せない制約（DuckDB 0.10）を考慮し、空チェックを行ってから executemany を呼ぶ実装に対応。
- OpenAI レスポンスパース
  - JSON mode であっても前後に余計なテキストが混入するケースを考慮して、最外の { ... } を抽出して復元する処理を導入。
- API エラー処理
  - RateLimitError / APIConnectionError / APITimeoutError / 5xx に対する再試行（指数バックオフ）と、非 5xx の APIError はリトライしないロジックを導入。
- 入力検証
  - OpenAI API キー未設定時に分かりやすい ValueError を発生させるように統一。

### Deprecated
- （初期リリースのためなし）

### Removed
- （初期リリースのためなし）

### Security
- 機密情報の扱い
  - 環境変数を使った API キーやパスワードの取り扱いを前提とし、.env 自動ロードを提供。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能（テスト用途）。
- （既知のセキュリティ問題はなし。運用環境では API キーやパスワードの適切な管理を推奨）

---

注意:
- 本 CHANGELOG はソースコードから推測した初期機能一覧です。実際の外部依存（J-Quants API、OpenAI SDK、DuckDB バージョン等）や運用設定に応じて動作が変わる可能性があります。リリースにあたっては README / ドキュメントで導入手順と運用上の注意（APIキー、.env テンプレート、DB スキーマ等）を必ず併記してください。