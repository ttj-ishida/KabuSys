# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用しています。

## [Unreleased]

- 今後のリリースで追記します。

## [0.1.0] - 2026-04-03

初回リリース — KabuSys の基本機能を実装しました。以下はコードベースから推測される主要な追加点・設計要旨・既知の制約です。

### Added
- パッケージ基礎
  - パッケージ名: kabusys、バージョン: 0.1.0
  - export: data, strategy, execution, monitoring を __all__ で公開。

- 設定管理
  - kabusys.config:
    - .env / .env.local 自動読み込み機能（プロジェクトルートを .git / pyproject.toml から探索）。
    - export 付き行・クォート・エスケープ・インラインコメントの取り扱いを考慮した .env パーサ実装。
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - Settings クラスを提供し、アプリ設定（J-Quants, kabu API, LINE, DB パス, 監視閾値, 環境モードなど）をプロパティ経由で取得。
    - 必須環境変数チェック（_require）: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD などの必須項目を明示。
    - KABUSYS_ENV / LOG_LEVEL の入力検証（許容値チェック）。

- AI（LLM）機能
  - kabusys.ai.news_nlp:
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）へバッチ送信。
    - JSON Mode を期待したレスポンスパースとバリデーション（results リスト、code と score の検証、数値クリップ）。
    - バッチサイズ・文字数・記事数制限（_BATCH_SIZE, _MAX_CHARS_PER_STOCK, _MAX_ARTICLES_PER_STOCK）。
    - 再試行 (exponential backoff) とエラーハンドリング（429/ネットワーク/タイムアウト/5xx のリトライ、その他はスキップ）。
    - DuckDB への冪等書き込み（DELETE → INSERT、部分失敗で既存データ保護）。
    - calc_news_window: JST ベースのニュース収集ウィンドウ計算（前日15:00〜当日08:30 JST）。
    - テスト容易性のため OpenAI 呼び出し箇所を差し替え可能に実装（_call_openai_api の切替）。

  - kabusys.ai.regime_detector:
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次市場レジーム（bull/neutral/bear）を判定。
    - マクロニュース抽出（キーワードベース）と LLM 連携（JSON 出力期待）。
    - LLM 呼び出しの再試行とフォールバック（失敗時 macro_sentiment=0.0）。
    - DuckDB への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。

- データ基盤（DuckDB ベース）
  - kabusys.data.calendar_management:
    - JPX カレンダー取得・保存の夜間バッチ処理（calendar_update_job）。
    - 営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB にデータがない場合は曜日ベースのフォールバック（週末は非営業日）。
    - 最大探索日数制限や健全性チェックを導入（_MAX_SEARCH_DAYS, _SANITY_MAX_FUTURE_DAYS）。
    - J-Quants クライアント経由での差分取得と冪等保存を想定。

  - kabusys.data.pipeline / etl:
    - ETLResult データクラスを実装（取得件数・保存件数・品質問題・エラー等を保持）。
    - 差分更新、バックフィル方針（デフォルト backfill_days）、カレンダー先読みの扱い等を設計に反映。
    - quality モジュールとの連携を想定（品質問題は収集して呼び出し元が判断）。
    - DuckDB テーブル存在チェック等のユーティリティを実装。

- リサーチ機能（オンボードの分析ユーティリティ）
  - kabusys.research.factor_research:
    - Momentum, Volatility, Value, Liquidity などのファクター計算（モジュール内で SQL を駆使して実装）。
    - calc_momentum, calc_volatility, calc_value を提供（prices_daily / raw_financials を参照）。
    - 計算時のデータ不足時の扱い・NULL 処理を明示。

  - kabusys.research.feature_exploration:
    - forward return 計算（calc_forward_returns）、IC（calc_ic）計算（Spearman ランク相関）、rank, factor_summary 等の統計ユーティリティ。
    - pandas 等に依存せず標準ライブラリのみで実装。
    - rank 実装は同順位（ties）を平均ランクで処理する設計。

- ロギングと安全性
  - 各モジュールで詳細な logger 呼び出しを追加し、警告や例外発生時の情報を出力。
  - ルックアヘッドバイアス防止: date.today() の直接参照を避け、target_date を引数で受ける設計。
  - API キーや重要設定値は明示的に要求し、未設定時は ValueError を送出する箇所を用意。

### Changed
- 初版リリースにつき「変更」はありません（初回実装）。

### Fixed
- 初版リリースにつき「修正」はありません（初回実装）。

### Security
- OpenAI や外部 API キーは引数 or 環境変数で注入し、明示的に未設定を検出することで誤実行を防止。

### Notes / Known limitations
- news_nlp の出力は JSON モードを想定しているが、LLM の応答で余分な前後テキストが混入する場合の復元ロジックを実装しているものの、完全な保証はない。
- calc_value では PBR や配当利回りは未実装（ドキュメント内にも注記あり）。
- quality モジュールの詳細実装（QualityIssue 等）はこのリリースで参照されているが、別ファイル/モジュールとして実装される想定。
- DuckDB バインドの互換性を考慮し、executemany に空リストを渡さない等のワークアラウンドを導入。
- OpenAI クライアント呼び出し箇所はテストで差し替え可能だが、実運用では適切なレート制限管理・コスト管理が必要。

### Migration / Usage hints
- 環境変数:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（Settings の各プロパティ参照）
  - OpenAI: OPENAI_API_KEY を設定するか、news_nlp.score_news / regime_detector.score_regime に api_key を渡す。
  - 自動 .env 読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- DuckDB 接続を渡して関数を呼ぶことで、副作用（ネットワークの発注等）を伴わずにデータ処理や分析を実行可能。
- テスト時は kabusys.ai.news_nlp._call_openai_api および kabusys.ai.regime_detector._call_openai_api をモックして LLМ 呼び出しを抑制可能。

---

（注）本 CHANGELOG は提供されたコード内容から実装意図・振る舞いを推測して作成しています。実際のリリースノート作成時は、コミット履歴やリリース管理システムに基づく正式内容で更新してください。