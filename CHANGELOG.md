Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは "Keep a Changelog" の慣習に従います。

[Unreleased]
------------

（未リリースの変更はここに記載します）

[0.1.0] - 2026-03-29
-------------------

Added
- 基本パッケージ
  - kabusys パッケージを初期リリース。__version__ = "0.1.0"。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ でエクスポート。

- 設定・環境変数管理（kabusys.config）
  - Settings クラスを導入。環境変数経由でアプリ設定を取得（J-Quants / kabuステーション / Slack / DB パス等）。
  - .env 自動読み込み機能を実装：
    - プロジェクトルート判定は .git または pyproject.toml を基準に行い、CWD に依存しない。
    - 読み込み順序: OS 環境変数 > .env.local > .env。環境変数は保護されたキーとして扱われる。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env のパースは export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメントなどに対応。
    - _require(key) により必須環境変数が未設定の場合に ValueError を送出する（ユーザに明確に通知）。
  - KABUSYS_ENV / LOG_LEVEL の値検証（許容値チェック）とユーティリティプロパティ（is_live / is_paper / is_dev）。
  - デフォルトの DB パス（DUCKDB_PATH / SQLITE_PATH）を設定。

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - JPX カレンダー管理機能を提供（market_calendar テーブルを利用）。
    - 営業日判定 API: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 登録データがない場合は曜日（土日）ベースのフォールバックを使用。
    - next/prev は _MAX_SEARCH_DAYS（上限）を設け無限ループを防止。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等保存、バックフィルと健全性チェックを実装。
  - pipeline / etl:
    - ETLResult データクラスを公開。ETL 実行結果（取得数・保存数・品質問題・エラー）を集約。
    - 差分更新、バックフィル、品質チェックを念頭に置いた ETL 用ユーティリティを実装（内部ユーティリティとしてテーブル存在確認や最大日付取得など）。
    - jquants_client と quality モジュールを想定した設計（fetch/save を呼び出して冪等保存）。
  - etl モジュールは pipeline.ETLResult を再エクスポート。

  - 実装上の互換性配慮:
    - DuckDB の executemany に空リストを渡せない点へ対処（空チェックを行う）。
    - DuckDB から返る日付値を date に変換するユーティリティを提供。

- 研究モジュール（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す設計。
    - calc_volatility: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金、出来高比率などを計算。
    - calc_value: raw_financials から最新の eps/roe を取り、PER/ROE を計算（EPS が 0/欠損の場合は None）。
    - いずれも DuckDB 上で SQL を中心に実装し、外部 API にはアクセスしない。
  - feature_exploration:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons の検証あり。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算。有効レコードが 3 未満なら None を返す。
    - rank: 同順位は平均ランクとするランク変換（丸めで ties 検出の安定化）。
    - factor_summary: count/mean/std/min/max/median を返す基本統計集計。
  - すべて標準ライブラリのみで実装（pandas 等への依存なし）。

- AI / NLP（kabusys.ai）
  - news_nlp:
    - score_news: raw_news と news_symbols からニュースを銘柄別に集約し、OpenAI（gpt-4o-mini、JSON Mode）でバッチセンチメント評価を行い ai_scores テーブルへ書き込む。
    - タイムウィンドウは JST ベースで定義（前日 15:00 JST ～ 当日 08:30 JST → UTC に変換）。
    - 1 チャンク当たり最大 _BATCH_SIZE（20）銘柄、各銘柄は最新 _MAX_ARTICLES_PER_STOCK（10）件・_MAX_CHARS_PER_STOCK（3000 文字）でトリム。
    - API 呼び出しはリトライ（429/ネットワーク/タイムアウト/5xx を対象に指数バックオフ）。非リトライ例外はスキップして継続。
    - レスポンスの厳密バリデーション（JSON 抽出、"results" リスト構造、既知コードのみ抽出、スコア数値化、±1.0 でクリップ）。
    - DB 書き込みはコードを絞って個別 DELETE → INSERT の冪等更新を行い、部分失敗時に既存スコアを保護する。
    - API キーは引数または環境変数 OPENAI_API_KEY。未設定時は ValueError を送出。
  - regime_detector:
    - score_regime: ETF 1321 の 200 日移動平均乖離（_MA_WINDOW=200）とマクロセンチメント（news_nlp の calc_news_window を使用して抽出したタイトルを OpenAI で評価）を 70%/30% の重みで合成し market_regime に保存。
    - ma200_ratio 計算は target_date 未満のデータのみ使用してルックアヘッドを防止。データ不足時は中立値 1.0 を使用。
    - マクロキーワードによる記事抽出（最大 _MAX_MACRO_ARTICLES=20）。
    - OpenAI 呼び出しはリトライ・エラーハンドリングを持ち、API 失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT のトランザクション。失敗時は ROLLBACK を試みる。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Notes / 実装上の注意事項
- OpenAI 関連機能は API キー（OPENAI_API_KEY）に依存。キー未提供時は明示的な例外を発生させる設計。
- 外部 API 呼び出し（OpenAI / J-Quants）は失敗時にログを残して可能な限り処理を続行する（フェイルセーフ）。ただし、ETL のように重要なステップの失敗は ETLResult.errors に集約される。
- DuckDB のバージョン依存（executemany の挙動やリストバインド）を考慮した実装上の配慮あり。
- news_nlp と regime_detector はそれぞれ内部で OpenAI 呼び出し用のプライベート関数を持ち、モジュール間で共有しないことで結合を低く保つ設計。
- .env パーサは実運用の .env 慣習（export、クォート、コメント）に広く対応するよう実装。

Known issues / TODO
- PBR・配当利回りなどのバリューファクターは現バージョンでは未実装（calc_value に注記あり）。
- strategy / execution / monitoring パッケージの公開は __all__ に含まれているが、今回提供されたソースにはそれらの実装は含まれていない（別途実装が想定される）。
- news_nlp/regime_detector のテスト時は _call_openai_api を unittest.mock.patch して外部通信を抑止する想定。

License
- （ソースにライセンス表記がないため、必要に応じてライセンスを追記してください）