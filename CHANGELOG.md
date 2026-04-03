Keep a Changelog 準拠の CHANGELOG.md（日本語）

全ての変更は semver に従って記述しています。  
フォーマットについて: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------
（今後の変更をここに記載します）

[0.1.0] - 2026-04-03
-------------------
Added
- パッケージ初期リリース: kabusys (v0.1.0)
  - パッケージ公開情報:
    - src/kabusys/__init__.py に __version__ = "0.1.0"、公開モジュール一覧 __all__ を定義（data, strategy, execution, monitoring）。
- 設定 / 環境変数読み込み機能（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード実装。
  - プロジェクトルート検出: .git または pyproject.toml を基準に探索（cwd 非依存）。
  - 自動ロード順序: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env パーサの強化:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応。
    - コメント扱い判定（クォート外の # を扱うロジック）。
  - 環境値検証・ユーティリティ:
    - Settings クラスを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / env/log_level 判定）。
    - 必須キー未設定時は ValueError を投げる _require。
    - KABUSYS_ENV と LOG_LEVEL の許容値検証を実装。
- AI 関連機能（kabusys.ai）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄ごとのニューステキストを作成。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB クエリに使用）。
    - OpenAI（gpt-4o-mini）を JSON Mode で呼び出し、銘柄ごとのスコアを取得。
    - バッチ処理: 1回の API 呼び出しで最大 20 銘柄（_BATCH_SIZE）。
    - 1銘柄あたりの記事数・文字数のトリム機能（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - リトライ（429/ネットワーク断/タイムアウト/5xx）を指数バックオフで実装。
    - レスポンス妥当性検証（results 配列、code/score の存在、数値チェック、既知コードのみ採用）。
    - スコアは ±1.0 にクリップして ai_scores テーブルへ書き込み（DELETE → INSERT の冪等置換、部分失敗時に既存データ保護）。
    - テスト容易性: _call_openai_api を patch して差し替え可能。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジームを判定（'bull'/'neutral'/'bear'）。
    - MA200 の計算は target_date 未満のデータのみを使用してルックアヘッドを防止。
    - マクロニュースはニュースタイトルをマクロキーワードでフィルタ（複数キーワード列挙）。
    - OpenAI 呼び出しでのリトライ・エラー対処、API 失敗時は macro_sentiment = 0.0 にフォールバック（例外を投げず継続）。
    - レジームスコア合成後、market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実施。DB 書き込み失敗時は ROLLBACK を試み上位へ例外伝播。
    - テスト容易性: news_nlp とは別実装の _call_openai_api を使用（モジュール分離）。
- Data / ETL / カレンダー（kabusys.data）
  - calendar_management
    - JPX カレンダーを扱うユーティリティ群を実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day 等。
    - DB に calendar データがある場合は DB の値を優先し、未登録日は曜日ベース（土日除外）でフォールバックする方針。
    - next/prev_trading_day に最大探索日数（_MAX_SEARCH_DAYS）を導入し無限ループ防止。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等に更新。バックフィル・健全性チェック（将来日付異常検出）を実装。
  - pipeline / ETLResult（kabusys.data.pipeline / kabusys.data.etl）
    - ETLResult データクラスを公開（target_date, fetched/saved counts, quality_issues, errors 等）。
    - ETL パイプラインの方針を実装（差分更新、idempotent 保存、品質チェックを収集して呼び出し元に委ねる）。
    - デフォルトのバックフィル日数や最小データ日など運用用定数を明示。
- Research（kabusys.research）
  - factor_research
    - モメンタム / ボラティリティ / バリュー等のファクター計算を実装（DuckDB SQL ベース、prices_daily・raw_financials を参照）。
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None）。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比など。
    - calc_value: raw_financials から最新財務データを取り出し PER/ROE を計算（EPS=0/欠損時は None）。
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21] 営業日）で将来リターンを計算するクエリ化実装（LEAD）。
    - calc_ic: スピアマンランク相関（IC）を実装（必要なレコード数が不足する場合は None を返す）。
    - rank: 同位順位を平均順位で扱うランク関数（浮動小数の丸め対策あり）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
- テスト支援 / 実装上の配慮
  - DuckDB 互換性を考慮した実装（executemany の空リスト回避、リストバインドの互換性回避等）。
  - ルックアヘッドバイアス防止: datetime.today()/date.today() 直接参照を避け、target_date ベースで全てを計算。
  - API 呼び出し箇所にテスト用の patch ポイントを用意（_call_openai_api）。

Changed
- 該当なし（初回リリース）

Fixed
- 該当なし（初回リリース）

Notes / Known behaviour
- OpenAI API 使用: gpt-4o-mini の JSON Mode を前提に動作。実行には OPENAI_API_KEY の設定が必要（各関数は api_key 引数でも注入可能）。
- DuckDB を主要なローカル DB として想定（接続は呼び出し側で用意する）。
- monitoring / execution / strategy 等のエントリはパッケージ公開対象に含まれているが、このリリースでの詳細実装はモジュール単位で差があるため、運用時は実装済みの各モジュールでの動作確認を推奨。
- エラー処理方針: 外部 API エラーは可能な限りフェイルセーフ（スキップして継続し、ログで警告）とし、DB 書き込み等の致命的エラーは上位へ伝播して呼び出し側で対処する設計。

開発者向け補足
- .env の自動ロードはパッケージが pip 等で配布後も .git / pyproject.toml によるプロジェクトルート探索に依存するため、配布環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して明示的にロード制御することを想定しています。
- 各 OpenAI 呼び出しのリトライ挙動やログ出力は config / 環境変数でのチューニングを検討してください。

--- 
（以降のバージョンでは機能追加・バグ修正・API 変更等を上記フォーマットで追記してください）