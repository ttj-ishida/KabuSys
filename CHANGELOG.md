# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

現在のバージョンは package の __version__ に合わせて 0.1.0 を基点としています。

## [Unreleased]
（今後の変更をここに記載してください）

---

## [0.1.0] - 2026-03-31
初回リリース（コードベースの現状に基づく機能追加・設計方針のまとめ）

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - パッケージ公開用の __all__（data, strategy, execution, monitoring）を定義。

- 設定管理
  - 環境変数 / .env 読み込みユーティリティ（kabusys.config）。
    - プロジェクトルートの自動検出機能（.git または pyproject.toml を探索）。
    - .env, .env.local の優先順位に基づく自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - export KEY=val 形式、クォート付き値、コメント処理などに対応する .env パーサー実装。
    - Settings クラスを公開し、J-Quants / kabu ステーション / Slack / DB パス / 監視閾値 / 環境・ログレベル等のプロパティを提供。
    - 必須環境変数未設定時に分かりやすいエラーメッセージを送出する _require() 実装。
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）。

- AI（自然言語処理）
  - ニュースセンチメント解析（kabusys.ai.news_nlp）
    - raw_news と news_symbols を元に銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON モードでスコアリング。
    - バッチ処理（最大 20 銘柄 / チャンク）・記事数・文字数のトリミング制限を実装。
    - 再試行（429・ネットワーク・タイムアウト・5xx に対する指数バックオフ）やレスポンス検証を実装。
    - レスポンスの復元処理（JSON 外ぶれの復元）やスコアの ±1.0 クリップを実装。
    - 結果は ai_scores テーブルへ冪等的に（DELETE → INSERT）保存。
    - calc_news_window() により JST ベースのニュース収集ウィンドウ（UTC 変換）を提供。
    - score_news(conn, target_date, api_key=None) を公開。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を組み合わせて日次でレジーム判定。
    - マクロ記事フィルタ（キーワードリスト）を用いて raw_news のタイトルを抽出。
    - OpenAI 呼び出しは専用実装で行い、再試行ロジック・フェイルセーフ（API 失敗時は macro_sentiment=0.0）を備える。
    - 計算結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - score_regime(conn, target_date, api_key=None) を公開。

- データ処理（Data Platform）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルの有無に応じた営業日判定ロジック（DB 値優先、未登録日は曜日フォールバック）。
    - next_trading_day / prev_trading_day / get_trading_days / is_trading_day / is_sq_day を提供。
    - calendar_update_job により J-Quants からの差分取得・バックフィル・健全性チェック・保存処理を実装。
    - DB がまばらな場合でも一貫性を保つ設計（最大探索日数制限など）。

  - ETL パイプライン（kabusys.data.pipeline / kabusys.data.etl）
    - ETL 実行結果を表す dataclass ETLResult を提供（品質問題検出結果・エラー一覧含む）。
    - 差分取得、保存（idempotent）、品質チェックの設計方針の実装骨子。
    - _table_exists / _get_max_date 等のDBユーティリティを実装。
    - kabusys.data.etl が ETLResult を再エクスポート。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離率の計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率の計算。
    - calc_value: raw_financials と株価から PER / ROE の計算。
    - DuckDB を用いた SQL ベースの実装、欠損時の None 扱い等を設計。
  - feature_exploration:
    - calc_forward_returns: 将来リターン計算（任意 horizon）。
    - calc_ic: スピアマンランク相関（IC）計算。
    - rank: 同順位を平均ランクで扱うランク化ユーティリティ。
    - factor_summary: カラムごとの count/mean/std/min/max/median を算出する統計サマリー。

### 変更 (Changed)
- （初版のため過去変更はなし。ただし設計上の重要な方針を明記）
  - ルックアヘッドバイアス回避のため、全ての主要処理で datetime.today() / date.today() を直接参照しない設計（target_date を明示的に与える）。
  - OpenAI 呼び出しはモジュール間でプライベート関数を共有せず、それぞれのモジュールで独立実装（モジュール結合防止）。
  - DuckDB の互換性・制約（executemany の空リスト不可など）を考慮した実装。

### 修正 (Fixed)
- API 応答や外部依存の不安定性に対するフォールバック実装を随所に導入。
  - OpenAI API の 5xx / タイムアウト / レート制限に対するリトライと最終的なデグレード（ゼロスコアやスキップ）を実装。
  - JSON 解析失敗時の安全なフォールバック（レスポンスから最外側の {} を抽出する等）。

### ドキュメント / 設計ノート (Documentation)
- 各モジュールに詳細な docstring を記載し、処理フロー・設計方針・入力制約・副作用（DB 書き込みの冪等性等）を明示。
- news_nlp, regime_detector, calendar_management, pipeline 等で処理フローとフェイルセーフ戦略を明確に記述。

### 非互換 / 注意事項 (Breaking Changes)
- なし（初回リリース）。ただし環境変数や DB スキーマ（prices_daily, raw_news, ai_scores, market_regime, market_calendar, raw_financials など）の前提があるため、導入時はスキーマ整備と必須環境変数の設定が必要。

---

メンテナンスや将来の変更（バグ修正、API 拡張、監視・実行モジュールの追加等）は [Unreleased] セクションに記載してください。