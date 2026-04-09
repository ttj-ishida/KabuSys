# Changelog

すべての重要な変更点をここに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

---

## [0.1.0] - 2026-04-09

初回リリース。日本株自動売買システム "KabuSys" のコアモジュール群を提供します。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py にてバージョンを "0.1.0" として公開。公開サブパッケージ: data, strategy, execution, monitoring。

- 環境設定・自動.env読み込み
  - src/kabusys/config.py
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml 検出）から自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化可）。
    - export プレフィックス対応、クォート内のバックスラッシュエスケープ、コメント取り扱いなどを考慮した .env 行パーサ実装。
    - .env.local は .env を上書き（ただし OS 環境変数は保護）。
    - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB パス / PaperTrading / 監視閾値 / 環境・ログレベル等をプロパティ経由で取得。
    - 設定値のバリデーション（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等）を実装。
    - 各種パスは Path オブジェクトで提供し expanduser に対応。

- ニュースNLP（AI）処理
  - src/kabusys/ai/news_nlp.py
    - raw_news / news_symbols を集約して銘柄ごとにニューステキストを作成し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄別センチメント（-1.0〜1.0）を算出。
    - タイムウィンドウ計算（前日15:00 JST〜当日08:30 JST）を calc_news_window で提供。
    - バッチ処理（_BATCH_SIZE=20）と 1 銘柄当たりのトリミング（記事数・文字数）によるトークン肥大対策。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフのリトライ実装。
    - レスポンスの堅牢なバリデーションと JSON 復元ロジック（外側の余計なテキストが混入するケースを考慮）。
    - スコアを ±1.0 にクリップし、取得成功分のみ ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT の方式、部分失敗時に既存データ保護）。
    - テスト用に OpenAI 呼び出し箇所を差し替え可能（_call_openai_api を patch できる設計）。
    - score_news(conn, target_date, api_key=None) を公開 API として実装。

  - src/kabusys/ai/__init__.py で score_news を公開。

- 市場レジーム判定（AI + テクニカル合成）
  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を組み合わせ、日次で市場レジーム（bull / neutral / bear）を判定。
    - MA 計算は target_date 未満のデータのみを使用してルックアヘッドバイアスを排除。
    - マクロニュース抽出（マクロキーワードリスト）→ OpenAI 呼出し（gpt-4o-mini）→ JSON パース。API 失敗時は macro_sentiment=0.0 のフェイルセーフ。
    - 再試行（リトライ上限・指数バックオフ）や 5xx とそれ以外の扱いを区別する実装。
    - 最終的なスコア合成後、market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実施。
    - score_regime(conn, target_date, api_key=None) を公開 API として実装。

- データプラットフォーム（ETL / カレンダー）
  - src/kabusys/data/pipeline.py / etl / __init__.py
    - ETLResult データクラスを定義。ETL 実行結果の集約（取得数・保存数・品質問題・エラー一覧など）を提供。
    - ETL の設計方針（差分更新・バックフィル・品質チェック）をコード & ドキュメントで明記。

  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理機能を実装。
    - 営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - market_calendar がない場合は曜日ベースのフォールバックを実施（土日を非営業日扱い）。
    - カレンダーの夜間バッチ更新 job: calendar_update_job(conn, lookahead_days=90) を実装。J-Quants から差分取得→保存（jq.fetch_market_calendar / jq.save_market_calendar を利用）し、バックフィル・健全性チェックを行う。
    - 最大探索日数・サニティチェック等の安全策を導入。

- 研究用ユーティリティ（Research）
  - src/kabusys/research/factor_research.py
    - Momentum, Volatility, Value（per, roe）等のファクターを計算する関数を実装:
      - calc_momentum(conn, target_date)
      - calc_volatility(conn, target_date)
      - calc_value(conn, target_date)
    - DuckDB を用いた SQL + Python 実装で、prices_daily / raw_financials を参照。データ不足時の None 処理やログ出力を実装。
    - 計算ウィンドウやパラメータは定数化（例: 200 日 MA, ATR20, 各モメンタム日数等）。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算: calc_forward_returns(conn, target_date, horizons=None)（デフォルト [1,5,21]）。
    - IC（Information Coefficient）計算: calc_ic(factor_records, forward_records, factor_col, return_col)（スピアマンのランク相関）。
    - ランク変換ユーティリティ rank(values)（同順位は平均ランク）。
    - 統計サマリー関数 factor_summary(records, columns)（count/mean/std/min/max/median）。
    - pandas など外部ライブラリに依存しない純粋な実装を志向。

- 共通・雑多
  - DuckDB を中心にデータアクセスを行う設計（DuckDB のバージョン差異に対する互換性注意をコード中に記述）。
  - 多くの関数で「ルックアヘッドバイアス防止」のために datetime.today()/date.today() を直接参照しない設計を採用し、target_date を明示的に渡す方針を採用。
  - OpenAI 呼び出し箇所に対してテスト容易性を考慮し差し替えポイントを用意。
  - ロギング出力（logger）を各モジュールで利用し、警告や失敗時の状況を詳細に出力。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- APIキーの取り扱いは引数優先、その後環境変数（OPENAI_API_KEY）を参照する方式を採用。未設定時は明示的な ValueError を送出して意図しない API 呼び出しを防止。

---

今後の予定（例）
- strategy, execution, monitoring の具体実装（発注ロジック、実行クライアント、プロセス監視）。
- 単体テスト・統合テストの整備（OpenAI モックや DuckDB のテストフィクスチャ）。
- ドキュメントの充実（Usage / Deployment / ETL 運用手順）。

--- 

注: 上記 CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノート更新時は機能差分・コミットログ・リリース目的に合わせて適宜修正してください。