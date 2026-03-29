Keep a Changelog 準拠 — 変更履歴（日本語）
====================================

すべての変更はこのファイルに記録します。形式は「Keep a Changelog」に準拠しています。

注意
----
この CHANGELOG は与えられたコードベースの内容から機能・設計意図を推測して作成した初期リリース向けの記述です。実際のコミット履歴がある場合はそちらに合わせて調整してください。

Unreleased
----------
- 現時点で未リリースの変更はありません。

[0.1.0] - 2026-03-29
-------------------

Added
- 新規パッケージ kabusys v0.1.0 を追加。
  - パッケージのトップレベルは kabusys.__init__ により version=0.1.0 を公開。
  - パッケージ公開 API の意図として data, strategy, execution, monitoring を __all__ に設定（将来のモジュール拡張を想定）。
- 環境設定管理（kabusys.config）を実装。
  - プロジェクトルート検出（.git または pyproject.toml）に基づいて .env / .env.local を自動読み込み（自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート）。
  - .env パーサの実装: export 形式対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント解釈ルール（非クォート時は直前がスペース/タブの # をコメント扱い）。
  - Settings クラスを提供し、必要な環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）をプロパティで取得。検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）を実装。
  - デフォルトの DB パス（duckdb/sqlite）や kabu API ベース URL のデフォルト値を設定。
- AI モジュール（kabusys.ai）を追加。
  - news_nlp モジュール:
    - calc_news_window: JST ベースのニュース収集ウィンドウ計算（前日15:00〜当日08:30 JST を UTC へ変換）。
    - score_news: raw_news / news_symbols を集約して銘柄ごとに OpenAI（gpt-4o-mini）でセンチメントを評価し ai_scores テーブルへ書き込むバッチ処理を実装。
      - 銘柄ごとに最新 N 記事を結合し文字数をトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
      - バッチ送信（_BATCH_SIZE）、429/ネットワーク断/タイムアウト/5xx に対する指数バックオフによるリトライ、レスポンスのバリデーション、スコアの ±1.0 クリップ。
      - DuckDB の executemany の互換性を考慮し、書き込み前に空パラメータを避ける実装。
    - レスポンスパースの堅牢化（JSON mode でも前後テキストが混入した場合に {} を抽出して復元する処理）。
  - regime_detector モジュール:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して market_regime テーブルへ冪等的に書き込む機能を実装。
    - マクロキーワードで raw_news をフィルタし、最大件数まで記事タイトルを LLM に送信して macro_sentiment を算出（API リトライ/バックオフ、フェイルセーフ時は 0.0）。
    - ルックアヘッドバイアス防止（target_date 未満のデータのみ使用、datetime.today() を参照しない）。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT で冪等化し、例外時は ROLLBACK を試行。
- Research モジュール（kabusys.research）を追加。
  - factor_research:
    - calc_momentum: 1M/3M/6M リターンおよび 200 日 MA 乖離を DuckDB SQL で算出。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を算出。NULL 伝播やカウントでデータ不足を取り扱い。
    - calc_value: raw_financials から最新の財務データを結び付けて PER / ROE を算出（EPS 無しや 0 を考慮）。
  - feature_exploration:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一度の SQL クエリで取得。horizons の検証（正の整数かつ <=252）。
    - calc_ic: Spearman ランク相関（Information Coefficient）を算出する実装。レコード不足や分散 0 の場合は None を返す。
    - rank: 平均ランク（同順位は平均）を算出するユーティリティ（丸めによる ties 対応）。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで算出。
  - いずれも外部 API へアクセスせず DuckDB のみ参照する設計。
- Data モジュール（kabusys.data）を追加。
  - calendar_management:
    - 市場カレンダー管理（market_calendar）用ユーティリティを提供。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装。market_calendar の有無に応じた DB 優先ルールと曜日ベースのフォールバックを持つ。
    - calendar_update_job: J-Quants API（jquants_client）からの差分フェッチと保存処理、バックフィル／健全性チェック（将来日付の異常検出）を実装。
  - pipeline:
    - ETLResult データクラスを実装（取得件数・保存件数・品質問題・エラー等を集約）。has_errors / has_quality_errors / to_dict を実装。
  - etl パッケージから ETLResult を再エクスポート（kabusys.data.etl）。
- 内部ユーティリティや設計上の配慮を多数実装。
  - DuckDB 互換性（executemany の空パラメータ回避等）。
  - DB 書き込みの冪等化とトランザクション制御（BEGIN/COMMIT/ROLLBACK）。
  - API 呼び出しのフェイルセーフ化（OpenAI 呼び出し失敗時は例外を上位に伝えずスコアにフォールバックする箇所がある）。
  - Lookahead バイアス対策（すべてのバッチ処理で target_date 未満や target_date を基準としたウィンドウのみを使用）。
  - .env 読み込みの堅牢化（読み込み失敗は警告で継続）。

Changed
- 新規リリースのため該当なし（初回公開）。

Fixed
- 新規リリースのため該当なし（初回公開）。

Security
- 機密情報取り扱いに関する注意点を追加（コード設計上の留意事項）。
  - OpenAI API キーや各種トークンは環境変数で提供する想定。未設定時は ValueError を発生させる箇所があるため、デプロイ前に必須環境変数の設定が必要。
  - .env 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用途）。

Notes / Known limitations
- monitoring モジュールが __all__ に含まれているが、実装ファイルはこのリポジトリ断片には含まれていません。将来のモジュール追加が想定されます。
- OpenAI 呼び出し部分は外部 SDK（openai）に依存するため、API 仕様や SDK のバージョン差異により挙動が変わる可能性があります。エラー処理はその変化をある程度考慮している（status_code の有無等）。
- DuckDB の型返却や日付型取扱いの互換性から _to_date 等の変換ユーティリティを使用しています。環境や DuckDB バージョンによっては追加の互換処理が必要になる場合があります。
- ETL / calendar 更新等は jquants_client（外部クライアント）に依存しており、外部 API のレスポンスや認証設定に応じた動作確認が必要です。

開発者向けメモ
- テスト時は OpenAI 呼び出しをモック（unittest.mock.patch）することを想定している（kabusys.ai.news_nlp._call_openai_api や kabusys.ai.regime_detector._call_openai_api を差し替え可能）。
- .env パーサは export 形式やクォート内のエスケープ処理をサポートしているため、複雑な値設定もある程度扱えます。
- DuckDB による大量データ処理は SQL 内でウィンドウ関数を多用しているため、適切なインデックス・メモリ設定がパフォーマンスに影響します。

ライセンス／作者
- パッケージのメタ情報（ライセンス・作者など）はソース中に明示されていないため、配布前に適切なライセンス情報を付与してください。