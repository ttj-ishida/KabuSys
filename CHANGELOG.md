CHANGELOG
=========

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

※このログはソースコードの内容から推測して作成しています。

Unreleased
----------

（なし）

[0.1.0] - 2026-03-31
--------------------

Added
- 初回公開: kabusys パッケージの追加。日本株自動売買 / データ基盤 / リサーチ用のユーティリティ群を提供。
- パッケージ情報
  - src/kabusys/__init__.py に __version__ = "0.1.0" を定義、主要サブパッケージを __all__ に公開。
- 環境設定
  - src/kabusys/config.py:
    - .env / .env.local 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env パースの詳細実装（コメント・export 形式・クォート・エスケープ処理対応）。
    - OS 環境変数保護（既存変数の保護／override フラグ、protected set の利用）。
    - Settings クラスを提供し、必要な環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）をプロパティ経由で取得。検証ロジック（KABUSYS_ENV, LOG_LEVEL の検査）とユーティリティプロパティ（is_live / is_paper / is_dev）を実装。
- AI（自然言語処理）関連
  - src/kabusys/ai/news_nlp.py:
    - score_news(conn, target_date, api_key=None): ニュース記事を OpenAI（gpt-4o-mini、JSON mode）でバッチ解析して銘柄ごとのセンチメント（ai_scores テーブル）を算出・書き込み。
    - ニュース収集ウィンドウ計算（calc_news_window）：JST ベースのウィンドウ（前日15:00〜当日08:30）を UTC naive datetime として返す。
    - バッチ処理（最大20銘柄/コール）、1銘柄あたり記事上限・文字数上限のトリム、レスポンスの厳密なバリデーションと ±1.0 のクリップを実装。
    - リトライ戦略（429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ）とフォールバック（失敗時は該当チャンクをスキップ）。
    - テスト容易性のため _call_openai_api の差し替えを想定（unittest.mock.patch を想定）。
  - src/kabusys/ai/regime_detector.py:
    - score_regime(conn, target_date, api_key=None): ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出（キーワードフィルタ）、LLM 呼び出し（gpt-4o-mini）、リトライ＆フェイルセーフ（API失敗時は macro_sentiment=0.0）を実装。
    - ルックアヘッドバイアス対策: datetime.today()/date.today()を直接参照せず、prices_daily は target_date 未満のデータのみを参照。
- データ基盤
  - src/kabusys/data/calendar_management.py:
    - JPX カレンダー管理ロジック（market_calendar テーブル参照）と営業日判定ユーティリティ群（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - calendar_update_job により J-Quants API から差分取得して market_calendar テーブルへ冪等保存。バックフィル・健全性チェック・フォールバック（カレンダー未取得時は曜日ベース）を実装。
  - src/kabusys/data/pipeline.py と src/kabusys/data/etl.py:
    - ETLResult データクラスを提供（ETL の取得数・保存数、品質問題、エラー情報を集約）。
    - 差分取得のためのユーティリティ（テーブル存在確認、最大日付取得、カレンダーヘルパー等）を実装。backfill・品質チェックの設計方針を反映。
  - src/kabusys/data/__init__.py と etl の再エクスポート: ETLResult を公開。
  - jquants_client との連携を想定した実装呼び出し箇所を含む（fetch/save 関数を利用）。
- リサーチ / ファクター計算
  - src/kabusys/research/:
    - factor_research.py:
      - calc_momentum, calc_volatility, calc_value を実装。prices_daily / raw_financials を参照してモメンタム、ATR、出来高／売買代金、PER/ROE などを計算。
      - DuckDB 上で SQL ウィンドウ関数を活用した実装。データ不足時の None 扱い、ログ出力を実装。
    - feature_exploration.py:
      - calc_forward_returns（将来リターンの一括取得）、calc_ic（スピアマンのランク相関による IC 計算）、rank（平均ランク付け）、factor_summary（基本統計量）を提供。
      - Pandas 非依存で標準ライブラリのみの実装を目指す。
    - research/__init__.py で主要関数を再公開（zscore_normalize は data.stats からインポート）。
- ロギング / 設計方針
  - 各モジュールで詳細な logger を利用し状態を記録。API 失敗時の警告やフォールバック動作を明示。
  - ルックアヘッドバイアス防止を各所で明文化（date.today() 参照回避、DB クエリの排他条件）。

Changed
- （初回リリースのため該当なし）

Fixed
- DuckDB の executemany に空リストを渡すと失敗する点を考慮し、空リストガードを導入（news_nlp.score_news の DELETE/INSERT 部分）。
- JSON モードのレスポンスに前後余計なテキストが混入するケースに対して、最外の {} を抽出して復元する耐性を追加（news_nlp の _validate_and_extract）。

Security
- 環境変数ロード時に既存の OS 環境変数を保護する protected セットを導入（config._load_env_file）。
- 必須環境変数未設定時は ValueError を送出して早期検出（Settings の各必須プロパティ）。

Deprecated
- （初回リリースのため該当なし）

Notes / マイグレーション / 利用上の注意
- OpenAI API を利用する機能（ai.news_nlp, ai.regime_detector）は OPENAI_API_KEY（または各関数に api_key を渡す）を必要とします。未設定時は ValueError を投げます。
- 自動で .env を読み込む動作は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- DuckDB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials など）に依存します。初期化スキーマは別途準備してください（このリポジトリにはスキーマ定義は含まれていない想定）。
- LLM 呼び出しのテスト性を考慮し、_call_openai_api を patch して挙動を差し替えられる設計になっています。

今後の予定（推測）
- モデル微調整やプロンプト改善、より細かな品質チェックモジュールの実装、ETL のジョブスケジューリング機能追加が想定されます。