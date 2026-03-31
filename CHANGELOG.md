# Changelog

すべての注目すべき変更を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。

- フォーマット: https://keepachangelog.com/ja/1.0.0/
- セマンティックバージョニングを使用します。

## [Unreleased]

## [0.1.0] - 2026-03-31
初回リリース。日本株自動売買システム「KabuSys」の基本モジュール群を追加しました。

### Added
- パッケージ初期化
  - パッケージ名 kabusys、バージョン 0.1.0 を追加。
  - 公開モジュール: data, strategy, execution, monitoring を __all__ で定義。

- 設定 / 環境変数管理 (kabusys.config)
  - .env / .env.local 自動読み込み機能をプロジェクトルート（.git または pyproject.toml 基準）から提供。
  - 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パースの強化:
    - export KEY=val 形式対応。
    - シングル／ダブルクォートとバックスラッシュエスケープに対応。
    - インラインコメントの扱い（クォート無しは '#' の直前が空白/タブならコメントとして扱う）を実装。
  - _load_env_file による保護付き上書きロジック（OS 環境変数の保護）を実装。
  - Settings クラスを導入し、各種必須/任意設定プロパティを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須取得。
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KABUSYS_ENV 等のデフォルト/検証ロジック。
    - env 値の検証（development / paper_trading / live のみ許容）とログレベルの検証。
    - is_live / is_paper / is_dev の便宜プロパティ。

- AI 関連 (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news と news_symbols を用いて銘柄別にニュースを集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（-1.0〜1.0）を算出。
    - 時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）算出ユーティリティ calc_news_window を実装。
    - バッチ処理（最大 20 銘柄/呼び出し）、記事数/文字数のトリム、レスポンス検証、スコアのクリップ（±1.0）を実装。
    - API の一時的失敗（429/ネットワーク/タイムアウト/5xx）に対する指数バックオフリトライを実装。
    - OpenAI 呼び出し部分はテスト用にモック差し替え可能（_call_openai_api を patch 可能）。
    - レスポンスの JSON 耐性を確保（前後ノイズを含む場合に最外層の {} を抽出して復元）。
    - 書き込み処理は部分失敗時に既存データを保護する戦略（対象コードのみ DELETE→INSERT）で行う。
    - フェイルセーフ: API 失敗時は当該チャンクをスキップし、例外を上位に伝播しない。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（225連動）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news から必要データを取得し、OpenAI（gpt-4o-mini）でマクロセンチメントを算出。
    - レジームスコアの合成式と閾値（BULL_THRESHOLD / BEAR_THRESHOLD）を実装。スコアは -1.0〜1.0 にクリップ。
    - DB への冪等書き込み（BEGIN / DELETE WHERE date = ? / INSERT / COMMIT）を実装、失敗時は ROLLBACK。
    - API エラー時のフォールバック（macro_sentiment = 0.0）とリトライロジックを実装。
    - テスト用に OpenAI 呼び出しを差し替え可能。

- データプラットフォーム (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - JPX カレンダーを扱うユーティリティ群を追加（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar が未取得の場合は曜日ベース（土日除外）のフォールバックを使用。
    - カレンダーデータの夜間バッチ更新 job（calendar_update_job）を実装：J-Quants から差分取得・バックフィル・保存処理（jq.fetch_market_calendar / jq.save_market_calendar 呼び出し）。
    - _MAX_SEARCH_DAYS による探索上限で無限ループを防止、健全性チェック（将来日付の異常検出）を実装。
    - 全ての日付は datetime.date オブジェクトで扱う（タイムゾーン混入回避）。

  - ETL パイプライン (kabusys.data.pipeline, kabusys.data.etl)
    - ETLResult データクラスを追加（ETL の取得/保存件数、品質問題、エラー概要の集約）。
    - 差分取得・バックフィル・品質チェック・冪等保存（jquants_client の save_*）の設計方針を実装。
    - _get_max_date、_table_exists 等のユーティリティを実装。
    - kabusys.data.etl で ETLResult を再エクスポート。

- 研究用ユーティリティ (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - モメンタム (calc_momentum): 1M/3M/6M リターン、200日 MA 乖離を計算。
    - ボラティリティ / 流動性 (calc_volatility): 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - バリュー (calc_value): raw_financials を用いた PER / ROE の計算（target_date 以前の最新財務データを参照）。
    - 入力データ不足時の None 扱い、戻り値は (date, code) をキーとした dict のリスト。

  - 特徴量探索 (kabusys.research.feature_exploration)
    - 将来リターン計算 (calc_forward_returns): 任意ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons のバリデーションあり。
    - IC 計算 (calc_ic): Spearman のランク相関（情報係数）を実装。有効レコードが 3 未満なら None を返す。
    - ランク関数 (rank): 同順位は平均ランクにする実装（丸めで ties 判定を安定化）。
    - 統計サマリー (factor_summary): count/mean/std/min/max/median を計算。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Migration
- 必須環境変数:
  - OPENAI_API_KEY（ai モジュールを使用する場合）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（それぞれの機能利用時）
- DuckDB のテーブル構成（prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials 等）が前提です。該当テーブルが存在しない場面へのフォールバック/早期リターンが実装されていますが、フル機能を使うには事前に適切なスキーマ/データが必要です。
- OpenAI API 呼び出しは外部サービス依存のため、API キーとコストに注意してください。テスト時には _call_openai_api をモックしてコストやレイテンシを回避できます。
- .env の自動読み込みはプロジェクトルート検知に基づきます。配布パッケージ等で意図せず読み込みたくない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

(作成: KabuSys v0.1.0 のソースコードから推測して CHANGELOG を自動生成)