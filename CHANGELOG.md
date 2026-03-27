# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

現在のリリース方針: 初期バージョンとして 0.1.0 を公開。

[Unreleased]
- （今後の変更をここに記載）

[0.1.0] - 2026-03-27
=================================

Added
-----
- パッケージ初期公開: kabusys (バージョン 0.1.0)
  - src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。
  - パッケージ公開時の外部インターフェースとして data, strategy, execution, monitoring を __all__ に列挙。

- 環境設定管理モジュール (kabusys.config)
  - .env / .env.local 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサを実装:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応。
    - インラインコメントの扱い（クォートあり/なしの差別化）。
  - .env.local が .env を上書きする優先順を採用。
  - OS 環境変数を保護する protected キーセットを導入して意図しない上書きを防止。
  - Settings クラスを提供し、必要な環境変数取得用のプロパティ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）を定義。
  - env/log_level に対するバリデーション（許容値チェック）を実装。
  - データベースパス（duckdb/sqlite）はデフォルト値を持ち Path に変換して提供。

- AI 関連モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news / news_symbols を集約して銘柄別にニュースをまとめ、OpenAI（gpt-4o-mini）の JSON Mode を利用してセンチメントスコアを生成。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST 相当）を calc_news_window として提供。
    - バッチ処理（最大 20 銘柄 / チャンク）、1 銘柄あたりの記事数・文字数制限を実装（トークン肥大化対策）。
    - API 呼び出しはリトライ（429 / ネットワーク断 / タイムアウト / 5xx）を指数バックオフで実施。
    - レスポンス検証ロジックを実装（JSON 抽出、results キー/型検証、コード照合、数値検証、スコアクリップ）。
    - DuckDB への書き込みは部分失敗に備え、書き換え対象コードのみ DELETE → INSERT を行い既存データを保護。
    - score_news(conn, target_date, api_key=None) を公開。OpenAI API キー未設定時は ValueError を送出。
    - テスト容易性のため _call_openai_api の差し替えを想定（unittest.mock.patch）。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成し日次で市場レジーム（bull / neutral / bear）を判定。
    - マクロ記事抽出はキーワードリストでフィルタし、最大 20 件までを LLM に渡す。
    - LLM 呼び出しは独自実装で行い、API エラー時は macro_sentiment を 0.0 にフォールバックするフェイルセーフを採用。
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実施。エラー時に ROLLBACK を試みる。
    - score_regime(conn, target_date, api_key=None) を公開。OpenAI API キー未設定時は ValueError を送出。

- データモジュール (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - market_calendar を利用した営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。
    - DB 未取得時は曜日ベース（週末は非営業日）でのフォールバックを提供。
    - calendar_update_job(conn, lookahead_days=90) を実装し、J-Quants クライアントから差分取得 → 保存（ON CONFLICT または同等処理）を行う夜間バッチを提供。バックフィルと健全性チェックを実装。
    - 検索範囲上限（_MAX_SEARCH_DAYS）で無限ループを防止。

  - ETL / パイプライン (kabusys.data.pipeline, kabusys.data.etl)
    - ETLResult データクラスを導入して ETL の各種取得数・保存数・品質問題・エラーを集約可能に。
    - 差分取得のための内部ユーティリティ（テーブル存在チェック、最大日付取得など）を実装。
    - ETL の設計方針に従いバックフィルや品質チェックの扱いをドキュメント化。
    - kabusys.data.etl で ETLResult を再エクスポート。

- 研究モジュール (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - モメンタム（1/3/6 ヶ月リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（平均売買代金・出来高比）、バリュー（PER, ROE）を計算する関数を実装:
      - calc_momentum(conn, target_date)
      - calc_volatility(conn, target_date)
      - calc_value(conn, target_date)
    - DuckDB の SQL ウィンドウ関数を活用して効率的に集計。データ不足時の None ハンドリング。

  - 特徴量探索 (kabusys.research.feature_exploration)
    - 将来リターン計算: calc_forward_returns(conn, target_date, horizons=None)（デフォルト [1,5,21]）
    - IC（スピアマンランク相関）計算: calc_ic(...)
    - ランキング関数 rank(values)（同順位は平均ランク）
    - 統計サマリー: factor_summary(records, columns)
    - pandas 等に依存せず標準ライブラリ + DuckDB で実装。

Changed
-------
- 多くの設計方針を API ドキュメントやモジュールトップの docstring に明示:
  - ルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない設計を採用（関数引数で日付を注入）。
  - OpenAI など外部 API 呼び出しはフェイルセーフ（失敗時はスコア 0.0 / 処理スキップ）を優先。
  - DuckDB に対する executemany の空リストバインド制約（DuckDB 0.10 等）を考慮した実装。

Fixed
-----
- ニュース / レジーム LLM 呼び出し周りの堅牢性向上:
  - JSON Mode の応答で追加テキストが混入した場合に最外側の {} を抽出して復元する処理を追加。
  - APIError の status_code が存在しない場合にも安全にリトライ判定を行う（getattr 使用）。
  - RateLimitError / APIConnectionError / APITimeoutError / 5xx を共通のリトライ対象として指数バックオフで再試行。
  - リトライ上限に達した場合はロギングしてフェイルセーフ値にフォールバック（例: macro_sentiment=0.0、あるいは該当チャンクをスキップ）。
- DuckDB への書き込み（ai_scores 更新等）で部分失敗時に既存データを不必要に消してしまうリスクを避けるため、対象コードのみを DELETE → INSERT して置換する戦略を採用。
- calendar_update_job にて過度に将来に飛んでいる last_date を検出した場合の健全性チェックを追加。

Security
--------
- 環境変数の自動ロードで OS 環境変数を上書きしないデフォルト挙動を採用し、上書き時も protected セットにより保護（.env/.env.local の扱いを明確化）。
- OpenAI API キー未設定時は ValueError を送出して明示的にエラーとする（無効な動作で API に暴露されることを防止）。

Notes / Compatibility
--------------------
- メインのデータ永続層として DuckDB を想定。SQL には DuckDB のウィンドウ関数等を使用しているため、他の SQL エンジンへの移植には注意が必要。
- OpenAI 呼び出しは openai.OpenAI クライアント（Chat Completions / JSON Mode）を想定。テスト時は内部の _call_openai_api を差し替えてモック化可能。
- 多くの関数は外部副作用（現在時刻の参照や API キーの固定参照）を避ける設計のため、日付や API キーは引数で注入可能／もしくは環境変数参照で容易に切り替え可能。
- 将来的にリリース／セキュリティ修正が入った場合は Unreleased セクションに追記し、バージョンを上げて記載します。

--- 
（この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノートとして公開する場合は、変更点の確認・追記を行ってください。）