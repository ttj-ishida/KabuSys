CHANGELOG
=========
この CHANGELOG は「Keep a Changelog」仕様に準拠しており、重要な変更点を時系列で記載します。

フォーマット:
- 日付は YYYY-MM-DD
- セクションは Added / Changed / Fixed / Deprecated / Removed / Security を使用

[0.1.0] - 2026-03-31
--------------------

Added
- パッケージ初期リリース: kabusys 0.1.0 を公開。
- パッケージ公開情報:
  - src/kabusys/__init__.py にて __version__ = "0.1.0"、公開モジュールを __all__ で定義（data, strategy, execution, monitoring）。
- 環境設定管理:
  - src/kabusys/config.py を追加。
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - export KEY=val 形式やクォート（シングル/ダブル）内のバックスラッシュエスケープ、行末コメント処理等を考慮した堅牢な .env パーサを実装。
  - .env.local を .env より優先して上書きする仕組み（既存 OS 環境変数は protected として保護）。
  - Settings クラスでアプリ設定をプロパティ化（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
  - デフォルト値と検証（KABUSYS_ENV の許容値: development / paper_trading / live、LOG_LEVEL の許容値など）を追加。
  - データベースパスのデフォルト（DuckDB: data/kabusys.duckdb、SQLite: data/monitoring.db）を提供。

- AI（NLP）機能:
  - src/kabusys/ai/news_nlp.py を実装。
    - raw_news / news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）でバッチ評価。
    - バッチサイズ制限（最大20銘柄）、1銘柄当たり記事数・文字数制限（_MAX_ARTICLES_PER_STOCK=10、_MAX_CHARS_PER_STOCK=3000）。
    - JST ベースのニュースウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）を提供（calc_news_window）。
    - OpenAI 呼び出しは JSON Mode を期待し、レスポンスの堅牢なパースとバリデーションを実装（結果構造: {"results":[{"code":"XXXX","score":0.0}, ...]}）。
    - リトライ（429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ）と失敗時のフェイルセーフ（該当チャンクはスキップ）。
    - スコアは ±1.0 にクリップ、取得済みコードのみを置換する idempotent な DB 書き込み（DELETE → INSERT）。部分失敗時に他銘柄スコアを保護。
    - テスト容易性のため _call_openai_api を patch 可能に設計。

  - src/kabusys/ai/regime_detector.py を実装。
    - ETF 1321（日経225連動型）200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - MA 計算は target_date 未満のデータのみを利用しルックアヘッドを防止。
    - マクロニュース抽出（マクロキーワード群でフィルタ）→ OpenAI（gpt-4o-mini）でセンチメント評価 → スコア合成（クリップ処理）。
    - API エラー時は macro_sentiment=0.0 として継続、DB へ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）し、失敗時は ROLLBACK とログ。
    - テスト用に OpenAI 呼び出し部分の差し替えが可能。

- データプラットフォーム機能:
  - src/kabusys/data/calendar_management.py を実装。
    - market_calendar テーブルを使った営業日判定 API（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録値を優先し、未登録日は曜日ベース（土日）でフォールバックする一貫したロジックを提供。
    - 夜間バッチ calendar_update_job により J-Quants から差分取得・バックフィル（直近 _BACKFILL_DAYS 再取得）と保存処理を実行。健全性チェック（過度に未来の日付はスキップ）実装。
    - J-Quants クライアントとの連携ポイント（jquants_client.fetch_market_calendar, save_market_calendar）。

  - src/kabusys/data/pipeline.py を実装。
    - ETLResult データクラスを導入し、ETL の取得件数・保存件数・品質問題・エラーを集約。
    - 差分更新・バックフィル・品質チェック統合のためのユーティリティ（最終取得日の取得、テーブル存在チェック等）を実装。
    - ETL 結果を辞書化する to_dict を提供し、quality_issues のサマライズをサポート。

  - src/kabusys/data/etl.py で ETLResult を再エクスポート。

  - src/kabusys/data/__init__.py を用意（パッケージ化）。

- リサーチ / ファクター解析:
  - src/kabusys/research/factor_research.py を実装。
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金/出来高比）、バリュー（PER, ROE）を DuckDB と SQL で計算する関数を提供（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の None 処理、ルックバック/スキャン範囲の設計（営業日バッファ）を実装。

  - src/kabusys/research/feature_exploration.py を実装。
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク化ユーティリティ（rank）、統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず、標準ライブラリのみで計算。欠損・非有限値を適切に除外。

  - src/kabusys/research/__init__.py で主要関数群をエクスポート（calc_momentum, calc_value, calc_volatility, zscore_normalize 等）。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Deprecated
- （初期リリースのため該当なし）

Removed
- （初期リリースのため該当なし）

Security
- 環境変数読み込み時に OS 環境変数を上書きしない保護機構（protected set）を実装。自動ロードは環境変数で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

Notes / 実装上の留意点
- ルックアヘッドバイアス防止のため、いずれのスコアリング/計算処理も datetime.today()/date.today() に依存せず、呼び出し側が target_date を明示する設計。
- OpenAI 呼び出し周りは JSON mode を期待しつつ、余計な前後テキストが混入した場合の復元ロジックやエラーハンドリングを備えている（テスト時に内部関数をモック可能）。
- DuckDB に対する executemany の空パラメータ問題（DuckDB 0.10）を回避するため、空リスト時の分岐を実装。
- 一部の外部依存（jquants_client, quality モジュール、OpenAI SDK）とのインターフェースは実装に依存しており、環境依存の動作は外部クライアントの実装に依存する。

今後の予定（参考）
- strategy / execution / monitoring サブパッケージの実装完備（公開 __all__ に含むがこのリリースでは未実装の可能性あり）。
- 追加の品質チェックルール、より詳細な監査ログ、CI テストの拡充。
- OpenAI モデル周りの抽象化（プロンプト最適化、モデル切替の設定化）。

---- 

（以降のバージョンはここに追記してください）