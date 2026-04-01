CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and follows Semantic Versioning.

Unreleased
----------

- (なし)

0.1.0 - 2026-04-01
------------------

Added
- 初期リリースとして主要モジュールを追加。
  - パッケージ初期化
    - kabusys.__init__ にバージョン "0.1.0" を追加し、公開サブパッケージ（data, strategy, execution, monitoring）を __all__ で定義。

  - 設定 / 環境変数管理 (kabusys.config)
    - .env ファイルまたは環境変数から設定を読み込む自動ローダを実装。読み込み優先順位は OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - プロジェクトルートの検出は __file__ を起点に .git または pyproject.toml を探索して行うため、カレントワーキングディレクトリに依存しない設計。
    - .env 解析は以下に対応:
      - コメント行（#）と空行の無視
      - export KEY=val 形式
      - シングル/ダブルクォートで囲まれた値中のバックスラッシュエスケープ処理
      - クォートなし値のインラインコメント処理（直前が空白/タブの場合のみ）
    - 環境変数の読み込み時に既存の OS 環境変数を保護する「protected」扱いで上書き制御が可能。
    - Settings クラスを提供し、必要な設定値（J-Quantsトークン、kabuステーションパスワード、Slackトークン/チャンネル、DBパス、監視閾値、実行環境など）をプロパティ経由で取得。
    - KABUSYS_ENV と LOG_LEVEL の値検証を実装（許容値チェック）。is_live / is_paper / is_dev ヘルパーを追加。

  - AI: ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news と news_symbols を集約して銘柄ごとのテキストを作成し、OpenAI（gpt-4o-mini）に対してバッチでセンチメント解析を実行。
    - 処理のポイント:
      - ニュース収集ウィンドウ（JST基準）を calc_news_window で計算（UTC naive datetime を返す）。
      - 1銘柄あたり最大記事数・最大文字数のトリム（トークン肥大化対策）。
      - 1API呼び出しで最大 _BATCH_SIZE（デフォルト20）銘柄を送信するチャンク処理。
      - JSON Mode を利用して厳密な JSON レスポンス期待（バリデーション実装）。
      - リトライ実装: 429・ネットワーク断・タイムアウト・5xx は指数バックオフでリトライ。その他のエラーはスキップ（フェイルセーフ）。
      - レスポンス検証: results リスト・各要素の code/score チェック、未知コード無視、スコアを ±1.0 にクリップ。
      - ai_scores テーブルへは取得済みコードのみを DELETE → INSERT の順で置換し、部分失敗時に既存データを保護。
    - score_news API を公開（duckdb 接続・target_date・api_key を受け取る）。APIキー解決は引数優先、未指定で環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出。

  - AI: 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（225連動ETF）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定する score_regime を実装。
    - 処理のポイント:
      - DuckDB から 1321 の終値を target_date 未満のデータで参照し、ルックアヘッドを防止する実装。
      - マクロキーワードによる raw_news フィルタリング（複数キーワード）および最大記事件数制限。
      - OpenAI（gpt-4o-mini）を用いた JSON レスポンス方式でマクロセンチメントを評価。API失敗時は macro_sentiment=0.0 にフォールバック。
      - スコア合成は clip して regime_label を決定。結果を market_regime テーブルへ冪等に（BEGIN / DELETE / INSERT / COMMIT）保存。
    - score_regime API を公開（duckdb 接続・target_date・api_key を受け取る）。APIキー未設定時は ValueError。

  - Data: マーケットカレンダー管理 (kabusys.data.calendar_management)
    - market_calendar を用いた営業日判定ユーティリティを実装:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供。
      - DB にカレンダーがある場合は DB 値を優先、未登録日は曜日ベース（平日）でフォールバックする一貫したロジックを採用。
      - next/prev は最大探索範囲制限 (_MAX_SEARCH_DAYS) を設け、見つからない場合は例外を送出。
    - 夜間バッチ calendar_update_job を実装:
      - J-Quants クライアントを用いて差分取得 → jq.save_market_calendar で冪等保存を行う。
      - バックフィル（日数指定）および健全性チェック（過度に将来の日付はスキップ）を実装。
      - エラー時は例外を捕捉してログ記録し、保存レコード数を返す形でフォールバック。

  - Data: ETL パイプライン (kabusys.data.pipeline, kabusys.data.etl)
    - ETLResult データクラスを追加（ETL 実行結果の集約: 取得数／保存数／品質チェック結果／エラーメッセージなど）。
    - pipeline モジュールの一部ユーティリティ（テーブル存在チェック、最大日付取得など）を実装（差分取得・バックフィル・品質チェックを想定した設計）。
    - kabusys.data.etl で ETLResult を再エクスポート。

  - Research: ファクター計算 & 特徴量探索 (kabusys.research.*, kabusys.research.__init__)
    - factor_research モジュール:
      - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算する SQL ベースの実装。データ不足時は None を返す扱い。
      - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比率（volume_ratio）を計算。
      - calc_value: raw_financials から最新財務を取得して PER, ROE を計算（EPS が 0/欠損の場合は None）。
      - 各関数は DuckDB 接続を受け取り、prices_daily / raw_financials テーブルのみを参照する設計（本番発注等に影響なし）。
    - feature_exploration モジュール:
      - calc_forward_returns: target_date から各ホライズン先（デフォルト 1,5,21 営業日）の将来リターンを LEAD を使って計算。horizons のバリデーションあり。
      - calc_ic: factor_records と forward_records を code で結合し、スピアマンのランク相関（IC）を計算。データ不足（有効レコード < 3）時は None。
      - rank: 同順位は平均ランクを返すランク付けユーティリティ（丸めにより ties 検出漏れを防止）。
      - factor_summary: 各ファクター列の基本統計量（count, mean, std, min, max, median）を算出。
    - kabusys.research.__init__ で主要関数を公開。

  - 小さなユーティリティ / エクスポート
    - kabusys.ai.__init__ で score_news を再エクスポート。
    - kabusys.data.__init__ はモジュールのプレースホルダとして存在。
    - 各モジュールはログ出力（logger）を広く利用して処理状況やフォールバックを記録。

Security
- OpenAI API キーや各種トークンは Settings 経由で取得し必須チェックを実施。未設定時は明示的に ValueError を返す。

Known limitations / Notes
- OpenAI 呼び出しは gpt-4o-mini を利用する想定で実装されている（環境・コストに応じた管理が必要）。
- DuckDB に対する executemany の挙動（空リスト不可）を考慮した実装上の注意点がある（部分書き換えで既存データの保護を行う）。
- 一部のユーティリティ（pipeline 中の最大日付取得関数の続きなど）はコードスニペットの切れにより省略されている箇所があるが、設計意図としては差分 ETL と品質チェックのワークフローを想定している。

Acknowledgements
- 本 CHANGELOG はリポジトリ内のソースコードから推測して作成しています。実際のリリースノート作成時はコミット履歴・PR コメントを元に追記・修正してください。