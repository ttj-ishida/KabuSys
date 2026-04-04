CHANGELOG
=========

すべてのリリースは Keep a Changelog の形式に準拠し、セマンティック バージョニングを採用します。
https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- （なし）

0.1.0 - 2026-04-04
------------------

初回リリース。日本株自動売買プラットフォームのコアライブラリを提供します。主な追加点は以下の通りです。

Added
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = "0.1.0", エクスポート: data, strategy, execution, monitoring）。

- 設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みする機能を実装。
  - .env パーサを実装（コメント行、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応）。
  - OS 環境変数を保護するため、.env 読み込み時に既存の OS 環境変数を上書きしない仕組み（.env.local は override=True）。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用）。
  - Settings クラス（settings インスタンス）を公開。J-Quants、kabuステーション、LINE、DBパス、監視閾値、環境（development/paper_trading/live）、ログレベル等のプロパティを提供。
  - 必須環境変数未設定時に ValueError を送出する _require ユーティリティ。
  - KABUSYS_ENV と LOG_LEVEL の値検証を実装（不正値は ValueError）。

- AI（自然言語処理）機能（kabusys.ai）
  - news_nlp.score_news
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON mode を使って各銘柄のセンチメント（-1.0〜1.0）を算出して ai_scores テーブルへ書き込む。
    - タイムウィンドウは前日 15:00 JST ～ 当日 08:30 JST（UTC 換算で前日 06:00 ～ 23:30）。calc_news_window を公開。
    - 1銘柄あたり最大記事数・文字数のトリム制限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - バッチ処理（1回あたり最大 20 銘柄）とリトライ（429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ）。
    - レスポンスの堅牢なバリデーション（JSON 抽出、"results" 構造チェック、未知コード無視、数値チェック、±1.0 クリップ）。
    - 部分失敗時に既存の他コードスコアを保持するため、DELETE → INSERT をコード単位で実行（DuckDB の executemany 空リスト制約に配慮）。
    - API キーは引数で注入可能（api_key）、テスト容易性を考慮。

  - regime_detector.score_regime
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定する機能。
    - マクロ記事抽出はマクロキーワードリストに基づくフィルタ（最大 20 件）。
    - OpenAI 呼び出し（gpt-4o-mini）でマクロセンチメントを JSON 形式で取得、失敗時はフェイルセーフで macro_sentiment = 0.0 を採用。
    - レジームスコア合成とラベリング（閾値パラメータを定義）。
    - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK と例外伝播）。
    - API キー注入可能（api_key）。

  - テスト支援
    - OpenAI 呼び出しを行う内部関数（_call_openai_api）に対して unittest.mock.patch で差し替え可能な設計。

- データプラットフォーム（kabusys.data）
  - calendar_management
    - JPX カレンダー管理（market_calendar）と営業日判定ユーティリティを提供。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days の実装。
    - market_calendar 未取得時の曜日ベースフォールバック（週末を非営業日扱い）。
    - 最大探索範囲制限（_MAX_SEARCH_DAYS）やバックフィル、健全性チェックを実装。
    - calendar_update_job: J-Quants から差分取得し market_calendar を冪等更新（バックフィル、健全性チェック、例外ハンドリングあり）。

  - pipeline / etl
    - ETLResult データクラスを公開（取得数／保存数／品質問題／エラーの収集と to_dict）。
    - 差分更新とバックフィルの方針を実装する ETL 基盤（jquants_client との連携を想定）。
    - テーブル存在チェックや最大日付取得等のユーティリティを含む（pipeline モジュール）。

- リサーチ（kabusys.research）
  - factor_research
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR、相対 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER、ROE）の計算関数を提供（calc_momentum, calc_volatility, calc_value）。
    - DuckDB 内で SQL を駆使して効率的に計算。データ不足時は None を返す設計。
    - ルックアヘッドバイアス対策として target_date 未満／以前データのみを使用する実装指針に従う。

  - feature_exploration
    - 将来リターン計算（calc_forward_returns、複数 horizon 対応、ホライズン検証あり）。
    - IC（Information Coefficient）計算（calc_ic：Spearman 相関に相当するランク相関の実装）。
    - ランク変換（rank：同順位は平均ランク、丸めにより ties 対応）。
    - 統計サマリー（factor_summary：count/mean/std/min/max/median）。
    - research パッケージの __all__ に主要関数を公開（zscore_normalize は data.stats から再利用）。

- 実装・堅牢性
  - DuckDB を主要なデータストアとして想定した設計。
  - ルックアヘッドバイアス防止のため、datetime.today()/date.today() をスコア計算内部で直接参照しない方針を明記。
  - 外部 API（OpenAI / J-Quants）呼び出しはリトライ/バックオフ、エラーハンドリングを行い、API 失敗時は安全なフォールバック（スコアを 0 にする等）で継続する設計。
  - ロギングと警告を多用して運用時の診断を容易に。

Security
- .env ロード時に既存の OS 環境変数を保護する仕組みを実装（.env の値が OS 環境変数を意図せず上書きしない）。
- 自動 .env ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD を提供（テストや CI 用）。

Notes / Known limitations
- DuckDB に依存するためローカル環境での実行には DuckDB が必要。
- OpenAI / J-Quants API の利用にはそれぞれの API キーが必要（api_key 引数で注入可能）。
- AI モデルは gpt-4o-mini を想定している（変更は将来対応可能）。
- 現バージョンでは PBR・配当利回りなど一部バリューファクターは未実装。
- 一部の SQL バインドや DuckDB の executemany の挙動に対して互換性対策（空リスト回避等）を行っている。

もし CHANGELOG に追加したい詳細（例: リリース日を別の日にする、項目の粒度を細かくする、カテゴリ分けを変更する等）があれば指定してください。