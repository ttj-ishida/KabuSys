# CHANGELOG

すべての注目すべき変更点を記録します。  
このプロジェクトでは Keep a Changelog の形式に準拠しています。  

※初版（0.1.0）はパッケージ初期実装に相当する内容をコードベースから推測して記載しています。

## [Unreleased]

## [0.1.0] - 2026-04-04

### Added（追加）
- パッケージ初期実装を追加。
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 環境変数・設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - .env パーサーは export 形式・引用符・インラインコメント等に対応。
  - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB パス / 監視閾値 / 環境（development/paper_trading/live）等の設定をプロパティ経由で取得可能。
  - 必須環境変数未設定時は明確な ValueError を送出（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
  - デフォルト値（例: KABU_API_BASE_URL, データベースパス、監視閾値）を設定。

- AI 関連モジュール（kabusys.ai）
  - news_nlp.score_news
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを算出して ai_scores テーブルへ書き込み。
    - バッチ（最大20銘柄）処理、1銘柄あたり記事数・文字数上限でトリム。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライを実装。
    - レスポンスのバリデーション（JSON 抽出、results 配列、code/score の型チェック、スコアのクリップ）を実施。
    - 失敗時はフェイルセーフで該当チャンクをスキップし、部分成功時の既存データ保護（対象コードのみ DELETE → INSERT）。
    - テスト容易性のため _call_openai_api を差し替え可能。
    - calc_news_window を提供（JST基準で前日15:00～当日08:30 の UTC 変換）。

  - regime_detector.score_regime
    - ETF 1321 の 200 日 MA 乖離（重み70%）とマクロ経済ニュースの LLM センチメント（重み30%）を合成して日次市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - マクロ記事抽出はキーワードマッチ（定義済みキーワード群）で行い、OpenAI（gpt-4o-mini）でセンチメントを取得。
    - API 呼び出しのリトライ/タイムアウト/エラー処理、JSON パース失敗時のフォールバック（macro_sentiment=0.0）を実装。
    - ルックアヘッドバイアスを避ける設計（datetime.today()/date.today() に依存しない、DB クエリは target_date 未満を使用）。
    - テスト容易性のため _call_openai_api はモジュール内で独立実装（news_nlp と共有しない）。

- データプラットフォーム関連（kabusys.data）
  - calendar_management
    - JPX カレンダー管理（market_calendar テーブル）機能を実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティを提供。
    - market_calendar 未取得時は曜日ベース（週末を休日）でフォールバック。
    - 夜間バッチ calendar_update_job を実装し、J-Quants クライアント経由で差分取得 → 冪等保存。バックフィルと健全性チェックを実施。

  - pipeline / etl / ETLResult
    - ETLResult データクラスを公開（etl モジュールから再エクスポート）。
    - ETL パイプライン設計（差分取得・保存（idempotent）・品質チェック）に基づくユーティリティを実装（pipeline モジュールに実装の想定）。
    - quality チェック結果の収集と ETL 結果の辞書化(to_dict)をサポート。

  - jquants_client への参照（実装は別モジュール想定）を使用して外部データ取得を行う設計。

- 研究（research）モジュール（kabusys.research）
  - factor_research
    - モメンタム（1m/3m/6m リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER/ROE）などのファクター計算関数を実装。
    - SQL（DuckDB）を主体とした計算で prices_daily / raw_financials を参照。欠損やデータ不足時の None ハンドリングあり。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic、Spearman ランク相関）、rank、factor_summary 等の統計解析ユーティリティを実装。
    - 外部ライブラリに依存せず標準ライブラリのみで処理。

- 内部設計上の注力点（ドキュメント化された設計方針）
  - ルックアヘッドバイアス防止の徹底（date の取り扱い、DB クエリの排他条件）。
  - DuckDB をデータ層に採用し、実装は SQL + 最小限の Python ロジックで記述。
  - DB への書き込みは冪等性を確保（DELETE→INSERT、ON CONFLICT 戦略を想定）。
  - OpenAI API 呼び出し周りはリトライ/バックオフ・レスポンス検証・フェイルセーフを備える。
  - テスト容易性のため外部呼び出しポイント（OpenAI 呼び出し等）は差し替え可能に設計。

### Changed（変更）
- 初回リリースのため該当なし。

### Fixed（修正）
- 初回リリースのため該当なし。

### Security（セキュリティ）
- 環境変数による機密情報の取り扱いを想定（API キーは環境変数から取得）。コードはクリアなエラーを出すが、実運用では秘密情報管理とローテーションを推奨。

---

注記:
- OpenAI 関連の機能を利用するには OPENAI_API_KEY（または関数引数での api_key 指定）が必要です。未設定時は ValueError を送出します。
- DuckDB のテーブル構成（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等）が前提となります。テーブル定義は本CHANGELOGに含まれていません。
- 実装の詳細（例: jquants_client のエンドポイント / 実際の ETL の orchestration 等）は別モジュール／ドキュメントに委ねられています。

もしリリースノートに追記したい詳細（例えば各関数の戻り値の例、必須環境変数一覧、DB スキーマの期待形など）があれば教えてください。それらを基に CHANGELOG を拡張します。