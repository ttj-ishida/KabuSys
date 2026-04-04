# CHANGELOG

すべての重要な変更点を記載します。本ファイルは Keep a Changelog の形式に準拠します。

全般的な注意
- 本リリースは初回公開と想定されるため、バージョンを v0.1.0 として記載しています。
- 実装は DuckDB を主なローカルデータストアとして想定しており、OpenAI（gpt-4o-mini）を用いた NLP 呼び出しを含みます。
- 多くの処理は「ルックアヘッドバイアス防止」の設計方針に従い、datetime.today() / date.today() に依存しない実装になっています（テスト／検証時の再現性重視）。

v0.1.0 - 2026-04-04
Added
- パッケージ基盤
  - kabusys パッケージ初期公開。
  - __version__ = "0.1.0" を定義。主要サブパッケージを __all__ で公開（data, strategy, execution, monitoring）。

- 設定／環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートは __file__ 起点で親ディレクトリを探索し、.git または pyproject.toml を基準に特定。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env（.env.local は上書き）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env パーサーの実装:
    - export KEY=val 形式に対応。
    - シングル／ダブルクォートを考慮したエスケープ処理をサポート（バックスラッシュ処理）。
    - コメント扱いはクォートの有無に応じた細かいルールを適用（クォートなしでは '#' の直前が空白の場合をコメント開始と判定）。
  - _load_env_file により OS 環境変数を保護する protected 引数を用いた上書き制御を実装。
  - Settings クラスを実装し、主要設定をプロパティとして提供:
    - J-Quants / kabuステーション / LINE / データベース（duckdb/sqlite）/監視関連（PID ファイル・キルフラグ・閾値）/システム設定（env, log_level）等を取得。
    - 必須値の未設定時に _require が ValueError を投げる挙動。
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）を実装。
    - ファイルパスは Path オブジェクトとして返す（expanduser 対応）。

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - JPX マーケットカレンダー管理機能を実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar が未取得の場合は曜日（平日）ベースのフォールバックを行う設計。
    - 次／前営業日探索は最大探索日数制限（_MAX_SEARCH_DAYS）を採用し、無限ループ防止。
    - calendar_update_job を実装し、J-Quants クライアント経由で差分取得・バックフィル・保存（保存は jquants_client 側に委譲）を行う。健全性チェック（将来日付の異常検出）あり。
  - pipeline / etl:
    - ETLResult データクラスを公開（kabusys.data.etl 経由で再エクスポート）。
    - ETLResult は取得件数、保存件数、品質チェック結果（quality_issues）、エラー列挙を持ち、has_errors / has_quality_errors / to_dict を提供。
    - pipeline モジュール（ETL ワークフローの方針）を文書化。

- ニュース NLP（kabusys.ai.news_nlp）
  - ニュース記事を銘柄ごとに集約して OpenAI に送信し、銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込む処理を実装。
  - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST （内部は UTC naive datetime に変換して DB 比較）。
  - 銘柄ごとに最新記事を最大 _MAX_ARTICLES_PER_STOCK 件、かつ _MAX_CHARS_PER_STOCK 文字でトリムしてプロンプトに含める実装。
  - バッチ処理: 1 API 呼び出しあたり最大 _BATCH_SIZE (=20) 銘柄でチャンク化。
  - OpenAI JSON Mode（厳格 JSON 出力）を期待する実装だが、レスポンスに余計なテキストが混じるケースに対する復元ロジック（最外の {} を抽出）を実装。
  - リトライ戦略: 429/ネットワーク断/タイムアウト/5xx を指数バックオフでリトライ（最大回数は定数化）。
  - レスポンスのバリデーション: results リストの存在、型チェック、未知コードの無視、数値変換と有限性チェックを実施。スコアは ±1.0 にクリップ。
  - DB への書き込みは部分失敗に備え、取得成功したコードのみを先に DELETE（個別 executemany）してから INSERT することで idempotent かつ既存スコア保護を実現（DuckDB 互換性考慮で executemany 空リスト回避）。
  - API キー解決ロジック（api_key 引数優先、未指定で環境変数 OPENAI_API_KEY を参照）。未設定の場合は ValueError を送出。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（年金等の代表ETF）を対象に 200 日移動平均乖離（ウエイト 70%）とマクロニュース LLM センチメント（ウエイト 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定する機能を実装。
  - ma200_ratio の算出は target_date 未満のデータのみを参照し、データ不足時は中立（1.0）を返すフェイルセーフ実装。
  - マクロニュース抽出は news テーブルからマクロキーワードを使ってタイトルを取得（最大 _MAX_MACRO_ARTICLES）。
  - OpenAI 呼び出しは news_nlp と独立した実装とし、API エラー時は macro_sentiment を 0.0 にフォールバック（警告ログ）して継続。
  - レジームスコアの合成式とクリップ、閾値によるラベリングを実装。
  - market_regime テーブルへの書き込みは BEGIN/DELETE/INSERT/COMMIT の冪等操作を行い、失敗時には ROLLBACK を試み例外を上位に伝播。

- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターンと ma200_乖離を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR（true_range の扱いは high/low/prev_close のいずれかが NULL の場合は NULL にする）や相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新報告を取得して PER / ROE を計算（EPS が 0/欠損時は None）。PBR・配当利回りは未実装。
    - すべて DuckDB 内の SQL ウィンドウ関数等を利用して効率的に計算し、結果は (date, code) をキーとする dict のリストで返す。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons のバリデーション（1〜252）あり。
    - calc_ic: ファクターと将来リターンの Spearman ランク相関（IC）を計算。有効レコード数が 3 未満の場合は None。
    - rank: 同順位は平均ランクとする実装。浮動小数の丸め処理で ties 検出漏れを防止。
    - factor_summary: count/mean/std/min/max/median を計算する統計要約関数を提供。

Changed
- （初回リリースのため変更履歴はありません）

Fixed
- （初回リリースのため修正履歴はありません）

Security
- OpenAI API キーや機密情報は Settings を通じて環境変数から参照する設計。自動 .env ロード時に既存 OS 環境変数を保護する仕組み（protected set）を導入。

Notes / Implementation details
- DuckDB のバージョン差（executemany の空リストバインド等）や OpenAI SDK の例外種別差異に対する互換性処理を行っている箇所が複数あります（例: APIError の status_code の安全取得、executemany 前の空チェックなど）。
- LLM 呼び出しは JSON Mode を期待するが、不正なレスポンスやパース失敗時は例外を投げずにフェイルセーフ（0.0 または空スコア）で続行する実装方針です（部分失敗耐性）。
- ルックアヘッドバイアス防止のため、すべての「当日」ロジックは呼び出し側から渡された target_date を基準に実行します。内部で現在日時を直接参照しません。

今後の予定（例示）
- ai モデル周りの抽象化（モデル切替やデバッグ用のロギング強化）。
- strategy / execution / monitoring モジュールの実装拡張（実取引・監視ロジック）。
- より詳細な品質チェック機能（quality モジュールの拡張）。
- テストカバレッジ（単体テスト・統合テスト）の強化。

以上