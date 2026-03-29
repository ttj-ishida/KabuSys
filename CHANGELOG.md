# CHANGELOG

すべての変更は「Keep a Changelog」仕様に準拠して記載しています。日付は本コードベースの現状を反映しています。

## [Unreleased]

## [0.1.0] - 2026-03-29
初回公開リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。主な追加点と設計上の注意点を以下にまとめます。

### 追加（Added）
- パッケージ基盤
  - パッケージのバージョンを `kabusys.__version__ = "0.1.0"` として定義。
  - パッケージ公開インターフェースに data / strategy / execution / monitoring を含める。

- 設定・環境変数管理（kabusys.config）
  - .env/.env.local からの自動読み込み機能を実装。読み込み優先度は OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を設定することで自動読み込みを無効化可能（テスト用途）。
  - .env パーサー実装：
    - export KEY=val 形式のサポート。
    - シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント対応（クォート有無に応じて処理を切り替え）。
    - 無効行のスキップ。
  - 環境変数保護（読み込み時に既存 OS 環境変数を保護する `protected` ロジック）。
  - 必須環境変数取得用ヘルパ `_require` と Settings クラスを追加。
  - Settings が取得する主なキー：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）、SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live）、LOG_LEVEL の検証ロジック
  - Settings に利便性プロパティ is_live / is_paper / is_dev を実装。

- AI（自然言語処理）機能（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini, JSON mode）でセンチメントを評価。
    - バッチ処理（最大 20 銘柄 / チャンク）、1 銘柄あたり記事数・文字数の上限トリム、JSON レスポンスのバリデーション実装。
    - 再試行（429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフ）とフェイルセーフ（失敗時はスキップ）を実装。
    - レスポンスパースの補助ロジック（JSON 前後の余計なテキストから {} を抽出）を実装。
    - ai_scores テーブルへの冪等書き込み（該当コードのみ DELETE → INSERT）で部分失敗を防止。
    - 公開 API: score_news(conn, target_date, api_key: Optional[str]) -> 書き込み銘柄数
    - calc_news_window(target_date) により JST ベースのニュースウィンドウを UTC naive datetime で返す（ルックアヘッド防止）。
    - テストしやすさのため OpenAI 呼び出しを差し替え可能（internal _call_openai_api を patch 可能）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）の 200 日 MA 乖離（重み 70%）とニュース由来 LLM のマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定。
    - prices_daily / raw_news / market_regime を利用し、DuckDB 上で ma200_ratio を算出、マクロ記事抽出、LLM 呼び出し、スコア合成、market_regime テーブルへの冪等書き込みを行う。
    - LLM 呼び出しは gpt-4o-mini を使用（JSON 出力期待）、API エラー時はマクロセンチメントを 0.0 にフォールバックするフェイルセーフ実装。
    - 再試行・バックオフ、5xx とそれ以外で挙動を分ける処理を実装。
    - 公開 API: score_regime(conn, target_date, api_key: Optional[str]) -> 1（成功時）

- データプラットフォーム（kabusys.data）
  - ETL パイプライン（kabusys.data.pipeline）
    - 差分取得・保存・品質チェックのための ETLResult データクラスを実装（target_date, fetched/saved counts, quality_issues, errors 等）。
    - DuckDB のテーブル最終日取得ユーティリティ、テーブル存在チェックなどを実装。
    - backfill 等の設計方針を明示。
    - ETLResult.to_dict() によるシリアライズ対応（品質問題はタプルではなく辞書化）。
  - ETL の公開インターフェースを etl モジュール経由で再エクスポート（ETLResult）。
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルの存在有無判定、土日フォールバック、is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ロジックを実装。
    - カレンダーの夜間差分更新ジョブ calendar_update_job を追加（J-Quants クライアント経由で差分取得→ save）。
    - DB にデータがある場合は DB 値優先、未登録日は曜日ベースでフォールバックする一貫性設計。
    - 最大探索日数やバックフィル、健全性チェックを導入し無限ループや異常データを防止。

- Research / ファクター解析（kabusys.research）
  - factor_research: モメンタム / ボラティリティ / バリュー系ファクター計算関数を実装。
    - calc_momentum(conn, target_date): mom_1m / mom_3m / mom_6m / ma200_dev（200 行未満は None）
    - calc_volatility(conn, target_date): atr_20, atr_pct, avg_turnover, volume_ratio（各条件で None 対応）
    - calc_value(conn, target_date): per, roe（raw_financials の最新レコードを使用）
    - 全関数は DuckDB の prices_daily / raw_financials のみ参照し、本番発注等にはアクセスしない設計。
  - feature_exploration: 将来リターン・IC・統計サマリーなどのユーティリティを実装。
    - calc_forward_returns(conn, target_date, horizons): 複数ホライズンに対応（入力検証あり）。
    - calc_ic(factor_records, forward_records, factor_col, return_col): Spearman 相関（ランク）を算出（有効レコード <3 の場合 None）。
    - rank(values): 平均ランク（同順位は平均）を返す実装（float 丸めに配慮）。
    - factor_summary(records, columns): count/mean/std/min/max/median を計算。
  - 研究用ユーティリティを __all__ 経由で整理して再エクスポート。

### 変更（Changed）
- 設計上の重要方針（コード全体）
  - ルックアヘッドバイアス防止のため、datetime.today() / date.today() をコア処理内で直接参照しない実装方針を徹底（すべての公開関数は target_date を引数で受け取る）。
  - DuckDB 互換性を考慮した実装（executemany の空リスト回避、リストバインドの回避策等）。
  - OpenAI 呼び出しはモジュール間で private 関数を共有せず、各モジュールに独立した _call_openai_api を持たせてテスト容易性を確保。

### 修正（Fixed）
- 再試行とエラーハンドリング
  - OpenAI 呼び出しに対して 429 / 接続断 / タイムアウト / 5xx を対象とした指数バックオフ再試行を導入し、非 5xx エラーは即時フォールバックするように改善。
  - API レスポンスの JSON パース失敗時は例外を投げず安全に 0.0 やスキップで継続するように変更（フェイルセーフ）。

### 注意（Notes）
- 環境変数の設定が必須の機能
  - OpenAI API を使用する機能（score_news / score_regime）は OPENAI_API_KEY の指定が必須です（関数引数で注入可能）。
  - J-Quants 等の外部 API を使うには JQUANTS_REFRESH_TOKEN 等の設定が必要です。
- テスト方法
  - OpenAI 呼び出しは各モジュールの `_call_openai_api` を unittest.mock.patch で差し替え可能に設計されています。ユニットテストではこれをモックして API 呼び出しをエミュレートしてください。
- DB 書き込みはできる限り冪等に設計（DELETE→INSERT や ON CONFLICT 相当の保存）しており、部分失敗時に他データを消さないよう配慮しています。
- 既知の設計選択
  - DuckDB に依存した SQL / ウィンドウ関数を多用しています。DuckDB のバージョン互換性に注意してください（特に executemany の空リスト等）。
  - ニュースウィンドウは JST を基準に UTC naive な datetime に変換して DB クエリに使用します。

### 破壊的変更（Breaking Changes）
- 初期リリースのため該当なし。

### 移行（Migration）
- 初回セットアップ手順（主な環境変数）
  - 必須（プロダクションで機能させる場合）:
    - OPENAI_API_KEY（score_news / score_regime）
    - JQUANTS_REFRESH_TOKEN（データ取得）
    - KABU_API_PASSWORD（kabuステーション API）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（通知連携）
  - 任意（デフォルト値があるが変更可能）:
    - KABUSYS_ENV（development / paper_trading / live）
    - LOG_LEVEL（DEBUG / INFO / ...）
    - DUCKDB_PATH, SQLITE_PATH
  - テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env 読み込みを抑止可能。

### 既知の制約・将来改善候補
- OpenAI のモデル指定は現状 gpt-4o-mini を使用していますが、将来的なモデル変更や JSON mode の挙動変化に備えて拡張可能な設計が必要です。
- news_nlp のレスポンス復元ロジックは堅牢だが、LLM の出力フォーマット逸脱に対するさらなる耐性強化（スキーマ検証等）を検討。
- DuckDB 依存関係と SQL 文の互換性は継続してテストが必要。

---

貢献・質問・バグ報告はリポジトリの Issue を利用してください。