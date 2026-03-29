CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
このプロジェクトはセマンティックバージョニングに従います。

Unreleased
----------

（なし）

0.1.0 - 2026-03-29
------------------

Added
- パッケージ初回リリース。
- 基本情報:
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として公開。
  - `__all__` に主要サブパッケージ（data, strategy, execution, monitoring）を登録。

- 環境設定・ローダー（kabusys.config）:
  - .env ファイル自動読み込み機能を実装（プロジェクトルートは`.git` または `pyproject.toml` を基準に決定）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロードを無効化するためのフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - .env パーサーの実装:
    - `export KEY=val` 形式対応。
    - シングル／ダブルクォート内のエスケープ処理を考慮した値抽出。
    - インラインコメント処理（クォート無し時は '#' の直前が空白/タブならコメント判定）。
  - OS 環境変数を保護するための protected キーセットを導入し、`.env.local` の上書き動作を制御。
  - 必須環境変数取得ヘルパー `_require` と、Settings クラスを提供（J-Quants, kabuAPI, Slack, DB パス, 環境種別/ログレベル検証など）。
  - `KABUSYS_ENV` と `LOG_LEVEL` の許容値チェックを実装。

- AI（kabusys.ai）:
  - ニュースNLP（kabusys.ai.news_nlp）:
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを計算して `ai_scores` テーブルへ書き込み。
    - タイムウィンドウ（JST 前日15:00〜当日08:30、内部は UTC で扱う）を計算する `calc_news_window` を実装。
    - 1銘柄あたりの記事数・文字数上限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）によるトリミング。
    - 最大バッチサイズ `_BATCH_SIZE = 20`、JSON Mode を用いた API 呼び出し、レスポンスバリデーション（results リスト・code/score 等）。
    - スコアを ±1.0 にクリップして保存。
    - API エラー（429・ネットワーク断・タイムアウト・5xx）に対する指数バックオフによるリトライ実装。
    - API レスポンスの JSON パース失敗時は最外の `{...}` 抽出による回復を試み、無理なら当該チャンクをスキップ（フェイルセーフ）。
    - DuckDB の executemany が空リストを受け取れない制約への対応（空チェックの実装）と、部分失敗時に既存スコアを保護するための「対象コード絞込み」戦略。
  - 市場レジーム判定（kabusys.ai.regime_detector）:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 0.7）と、マクロニュースの LLM センチメント（重み 0.3）を合成して 'bull'/'neutral'/'bear' を判定。
    - マクロキーワードで raw_news をフィルタし、最大件数を制限して LLM に渡す。
    - LLM 呼び出し（gpt-4o-mini / JSON Mode）とレスポンスパース、リトライ（429・タイムアウト・5xx に対する指数バックオフ）を実装。API 失敗時は macro_sentiment = 0.0 のフォールバックを行う。
    - レジームスコアを market_regime テーブルへ冪等に（BEGIN / DELETE / INSERT / COMMIT）書き込み。

- Research（kabusys.research）:
  - factor_research:
    - モメンタム（1M/3M/6M リターン）、200日 MA 乖離、ATR（20日）、流動性（20日平均売買代金、出来高比）等の算出関数 `calc_momentum`, `calc_volatility`, `calc_value` を実装。
    - DuckDB 上の SQL ウィンドウ関数を活用し、データ不足時は None を返す設計。
    - 各関数は `prices_daily` / `raw_financials` のみ参照し、本番注文 API へはアクセスしない安全設計。
  - feature_exploration:
    - 将来リターン計算 `calc_forward_returns`（horizons 検証、単一クエリでまとめ取得）。
    - IC（Spearman）の計算 `calc_ic`（ランク変換、最小レコード数チェック）。
    - ランク変換 `rank`（同順位は平均ランク、丸めによる ties 対応）。
    - 統計サマリー `factor_summary`（count/mean/std/min/max/median の算出）。
  - research パッケージは外部依存を避け、標準ライブラリ＋DuckDB による実装。

- Data（kabusys.data）:
  - カレンダー管理（kabusys.data.calendar_management）:
    - JPX カレンダー（market_calendar）を管理するユーティリティ群を実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB データ優先、未登録日は曜日ベースでフォールバックする一貫した挙動。
    - next/prev_trading_day は最大探索日数 `_MAX_SEARCH_DAYS` を設定し無限ループを防止。
    - 夜間バッチ `calendar_update_job` を実装し、J-Quants API から差分取得 → `jquants_client.save_market_calendar` で冪等保存。バックフィルと健全性チェックを実装。
  - ETL パイプライン（kabusys.data.pipeline, etl）:
    - ETL の結果を表す `ETLResult` データクラスを追加（品質問題やエラー情報を含む。`to_dict` によるシリアライズ対応）。
    - 差分取得、保存、品質チェックの設計方針を実装（backfill、calendar lookahead などの定義を含む）。
    - 内部ユーティリティ（テーブル存在チェック、最大日付取得、調整ヘルパー）を提供。

Changed
- 設計上のルールの明文化:
  - AI / リサーチ / ETL の各モジュールで datetime.today() / date.today() を直接参照しない方針を徹底（ルックアヘッドバイアス防止）。
  - DuckDB 固有の挙動（executemany の空リスト不可、日付型取扱い）を考慮した実装に統一。
  - モジュール間の結合を抑えるため、同様の内部ユーティリティ（OpenAI 呼び出し等）はモジュールごとに独立実装（テスト用モンキーパッチを容易にするため）。

Fixed
- .env 読み込みでの堅牢性向上:
  - ファイルが読み込めない場合は警告を出して続行（例外で停止しない）。
  - クォート内のバックスラッシュエスケープ、`export` プレフィックス、コメント処理などを正しく扱うことで .env の柔軟な記述に対応。
- OpenAI レスポンス処理の堅牢化:
  - JSON モードの応答でも前後に余計なテキストが混ざる場合に最外の `{...}` を抽出して復元するロジックを追加。
  - API の 5xx / 429 / ネットワークエラー・タイムアウトに対して指数バックオフで複数回リトライし、全リトライ消費時はフェイルセーフ値（例: macro_sentiment=0.0）で継続する挙動を実装。
- DuckDB 書き込みの安全性:
  - executemany に空リストを渡さないようチェックを追加（DuckDB のバージョン互換性対応）。
  - ai_scores / market_regime への書き込みは部分失敗時に既存データを不要に消さないよう、対象コードを絞って DELETE → INSERT を行う。

Security
- API キー取り扱い:
  - OpenAI API キーは引数（api_key）で注入可能。未指定時は環境変数 `OPENAI_API_KEY` を参照。未設定時は ValueError を送出して明示的に失敗させる。

Known issues / Notes
- このリリースはデータ収集・解析・判定ロジックを中心とした初期実装であり、下記は今後の改善候補です:
  - 実稼働（live）環境での詳細な運用テストおよび負荷試験。
  - ai モジュールのモデル切替やトークン・コスト管理のための抽象化。
  - `kabusys.data.jquants_client` の具体的実装（この変更履歴では参照のみ）と外部 API の例外網羅。
  - logging 設定の共通化（現在は各モジュールで logger を利用）。

ライセンス、貢献、リリースノートの追加情報はリポジトリのドキュメントを参照してください。