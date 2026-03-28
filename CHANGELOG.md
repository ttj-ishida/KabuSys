# Changelog

すべての変更は Keep a Changelog 規約に準拠して記載しています。  
このリポジトリはセマンティックバージョニングを採用しています。

## [Unreleased]

- （現時点では未リリースの変更はありません）

## [0.1.0] - 2026-03-28

初回公開リリース。日本株自動売買・分析プラットフォーム「KabuSys」の基礎機能群を実装。

### Added
- 基本パッケージ情報
  - パッケージ初期化: `kabusys.__version__ = "0.1.0"`、公開モジュール `data`, `strategy`, `execution`, `monitoring` を定義。

- 環境設定/ロード機能（kabusys.config）
  - .env ファイル（.env/.env.local）およびプロセス環境変数から設定を読み込む自動ロード機能を提供。プロジェクトルートは `.git` または `pyproject.toml` を基準に探索して決定するため、CWD に依存しない。
  - .env の行パーサーは `export KEY=val`、シングル/ダブルクォート内のエスケープ、インラインコメントの扱いなどに対応。
  - 自動ロードを無効化するための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` に対応。
  - `Settings` クラスを提供し、以下の主要設定プロパティを公開:
    - J-Quants / kabuステーション / Slack / データベースパス / 実行環境（development/paper_trading/live）/ ログレベル
  - 必須環境変数未設定時は明示的に ValueError を送出する `_require()` 実装。
  - 環境値の検証（`KABUSYS_ENV` の許容値、`LOG_LEVEL` の許容値）を実装。

- ニュース NLP モジュール（kabusys.ai.news_nlp）
  - `score_news(conn, target_date, api_key=None)`：raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）で銘柄ごとのセンチメント（-1.0〜1.0）を算出し、ai_scores テーブルへトランザクションで書き込む。
  - バッチ処理（1 API 呼び出しで最大 20 銘柄）、記事数・文字数のトリム、JSON Mode による厳密なレスポンス期待。
  - リトライ/バックオフ戦略（429・ネットワーク断・タイムアウト・5xx を対象）を実装。非リトライ例外はスキップして継続するフェイルセーフ設計。
  - レスポンスのバリデーション機能（JSON 抽出、"results" 構造検証、未知コード無視、数値チェック、±1.0 クリップ）。
  - DuckDB の互換性（executemany に空リストを渡さない等）に配慮した DB 書き込みロジック。
  - テスト用フック: OpenAI 呼び出し部分を patch しやすいよう `_call_openai_api` を分離。

- 市場レジーム判定モジュール（kabusys.ai.regime_detector）
  - `score_regime(conn, target_date, api_key=None)`：ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して market_regime テーブルへ冪等書き込みする。
  - マクロニュースは `news_nlp.calc_news_window` を使ってウィンドウを決め、raw_news からマクロキーワードでフィルタしたタイトルを取得。
  - OpenAI への呼び出しは独立実装。API エラー・パースエラー時は macro_sentiment=0.0 にフォールバックするフェイルセーフを装備。
  - 各種閾値・重み・モデルなどは定数化され分かりやすく管理。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（calendar_management）:
    - JPX カレンダー（market_calendar テーブル）を参照した営業日判定ユーティリティを提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - market_calendar がない場合は曜日ベース（土日除く）でフォールバックする堅牢設計。
    - calendar_update_job(conn, lookahead_days=90): J-Quants API から差分取得して market_calendar を冪等的に保存するジョブ。バックフィル・健全性チェックを実装。
  - ETL パイプライン（pipeline）
    - ETL 実行結果を表す dataclass `ETLResult` を実装（取得数・保存数・品質問題・エラー等を保持）。`to_dict()` で品質問題をシリアライズ可能。
    - 差分取得、バックフィル、品質チェックの基本方針をコメントで明示（実装の骨組み）。
  - etl モジュールは pipeline.ETLResult を再エクスポート。

- リサーチ/ファクター群（kabusys.research）
  - factor_research:
    - `calc_momentum`, `calc_volatility`, `calc_value` を実装。すべて DuckDB の SQL を活用して計算を行い、(date, code) 毎の辞書リストを返す。
    - Momentum（1/3/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、相対 ATR、20 日平均売買代金、出来高比）、Value（PER, ROE）をサポート。データ不足時には None を返す挙動。
  - feature_exploration:
    - `calc_forward_returns`（任意ホライズンの将来リターンを一度のクエリで取得）、`calc_ic`（スピアマンのランク相関による IC）、`rank`（同順位は平均ランクへ処理）、`factor_summary`（count/mean/std/min/max/median）を実装。
    - パフォーマンス／安全性のため SQL 範囲スキャンや引数検証を実装。
  - research パッケージは data.stats の zscore_normalize を re-export。

### Changed
- 初回リリースのため、変更履歴は無し。

### Fixed
- 初回リリースのため、修正履歴は無し。

### Removed
- 初回リリースのため、削除履歴は無し。

### Notes / 実装上の重要ポイント（ユーザー向け）
- OpenAI 統合
  - 使用モデルは gpt-4o-mini。API キーは関数引数または環境変数 `OPENAI_API_KEY` で与える。キー未指定時は ValueError を送出する設計。
  - LLM の失敗時は基本的に例外を上位へ投げず、スコアを 0.0 にフォールバックする（フェイルセーフ）。ただし DB 書き込みで例外が発生した場合はロールバックして例外を伝播する。
- DuckDB 前提
  - 内部は DuckDB 接続（DuckDBPyConnection）を前提に SQL を直接実行する実装。テーブル構成（prices_daily, raw_news, ai_scores, market_regime, market_calendar, raw_financials, news_symbols など）が存在していることが前提。
  - DuckDB のバージョン差分に対する互換性考慮（executemany の空リスト回避等）を行っている。
- ルックアヘッドバイアス防止
  - date 判定やスコア計算で datetime.today()/date.today() を直接参照しない設計。すべて関数引数（target_date）を基に処理することで、後付けバイアスを防止。
- テスト容易性
  - OpenAI 呼び出し箇所を分離しているため、ユニットテストでは `unittest.mock.patch` などで差し替えが容易。
- 未実装/制約
  - Value ファクターの PBR・配当利回りは未実装（コメントで明記）。
  - ETL の具体的な API 呼び出し（jquants_client）実装は別モジュールに委譲している（fetch/save 関数を利用）。
  - .env パーサーは多くのケースに対応しているが、特殊なシェル構文すべてを網羅しているわけではない。

### Breaking Changes
- 初回リリースのため、互換性破壊は無し。

---

参考: 主要な環境変数（このリリースで利用されるもの）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（省略可、デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN（必須）
- SLACK_CHANNEL_ID（必須）
- DUCKDB_PATH（省略可、デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（省略可、デフォルト: data/monitoring.db）
- KABUSYS_ENV（省略可、allowed: development, paper_trading, live。デフォルト: development）
- LOG_LEVEL（省略可、allowed: DEBUG, INFO, WARNING, ERROR, CRITICAL。デフォルト: INFO）
- OPENAI_API_KEY（OpenAI 呼び出しに必要）

もし追加で項目分け（例えばセキュリティ、マイグレーション手順、既知のバグ一覧）や好みのリリース日付修正があれば、指示に従って更新します。