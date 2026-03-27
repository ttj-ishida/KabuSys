# Changelog

すべての重要な変更はこのファイルに記録します。
このプロジェクトは Keep a Changelog のガイドラインに従います。
日付はリリース日を示します。

全般的な注意
- 本リポジトリはバージョン 0.1.0 で初回リリースしています。
- 実装は duckdb と OpenAI の公式 SDK（openai）に依存します。
- 設計方針として、ルックアヘッドバイアスを避けるために datetime.today()/date.today() を直接利用しない処理や、外部 API エラー時のフェイルセーフ動作（例: 中立スコアへのフォールバック）を多用しています。

Unreleased
- （なし）

0.1.0 - 2026-03-27
------------------

Added
- パッケージ初期実装（kabusys v0.1.0）
  - パッケージ初期エントリポイント: src/kabusys/__init__.py（__version__ = "0.1.0"）
  - サブパッケージを公開: data, research, ai, 等

- 環境設定 / ローダー（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダー実装。
  - 自動ロードの優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを抑止可能。
  - .env パーサ: export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメント処理（クォートあり/なしの挙動を分離）。
  - .env 読み込み時の保護機構: OS 環境変数（既存キー）を protected として上書きを防止する挙動を実装（override フラグあり）。
  - 必須設定を取得する _require() と Settings クラスを提供。以下のプロパティを含む:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live の検証）、LOG_LEVEL（DEBUG/INFO/... 検証）
    - is_live / is_paper / is_dev の便宜プロパティ

- ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news と news_symbols を集約して銘柄ごとにニュースを結合、OpenAI（gpt-4o-mini）へ送信して銘柄別センチメント（-1.0〜1.0）を算出し ai_scores テーブルへ書き込み。
  - 対象時間ウィンドウの算出（JST を基準に UTC 変換）：前日 15:00 JST ～ 当日 08:30 JST（DB 比較は UTC naive datetime）。
  - バッチ処理: 1回の API コールで最大 20 銘柄（_BATCH_SIZE=20）を処理、銘柄あたり記事数/文字数のトリム（_MAX_ARTICLES_PER_STOCK=10、_MAX_CHARS_PER_STOCK=3000）。
  - OpenAI 呼び出しは JSON Mode（response_format={"type":"json_object"}）を使用。レスポンスのバリデーションとパース処理を実装。
  - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ（最大回数とベース待機時間を定義）。
  - スコアは ±1.0 にクリップ。部分失敗時は既存の他銘柄スコアを削除しない（DELETE → INSERT の対象を限定）。
  - テスト容易性のため _call_openai_api を差し替え可能（unittest.mock.patch を想定）。
  - ロギング（処理情報・警告）を充実させ、API エラー時はスキップして継続するフェイルセーフ実装。

- 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次で判定。
  - ETF 毎の MA200 比率計算、マクロ記事のフィルタリング（キーワードリストを実装） → OpenAI（gpt-4o-mini）でマクロセンチメントを評価 → 合成スコアをクリップしてラベルを決定。
  - LLM 呼び出しは単体実装で、news_nlp とプライベート関数を共有しない設計。
  - API 失敗時は macro_sentiment = 0.0 にフォールバックするフェイルセーフ。
  - market_regime テーブルへ冪等（BEGIN / DELETE / INSERT / COMMIT）で書き込み。
  - リトライ、エラー分類（RateLimitError, APIConnectionError, APITimeoutError, APIError）に応じた挙動を実装。

- 研究用モジュール（src/kabusys/research/*）
  - ファクター計算（factor_research.py）
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離（ma200_dev）を計算。データ不足時は None（ma200 は 200 行未満で None）。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率などを計算。NULL の伝播を慎重に扱う。
    - calc_value: raw_financials から最新の財務指標を取得して PER/ROE を計算。EPS が 0/欠損の場合は None。
  - 特徴量探索（feature_exploration.py）
    - calc_forward_returns: 複数ホライズン（デフォルト 1,5,21 営業日）に対する将来リターンを一括で取得。horizons のバリデーションあり。
    - calc_ic: スピアマンランク相関（IC）を計算（同順位は平均ランク、有効レコード < 3 は None）。
    - rank: 値からランクへの変換（丸めて ties を安定化）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー。
  - zscore_normalize は data.stats から再エクスポートするインターフェース（research パッケージ __init__ で公開）。

- データプラットフォーム（src/kabusys/data/*）
  - カレンダー管理（calendar_management.py）
    - market_calendar テーブルに基づく営業日判定関数群を提供:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB 登録がない／未登録日の場合は曜日ベース（土日非営業）でフォールバックする一貫したロジック。
    - 最大探索制限 (_MAX_SEARCH_DAYS) を設けて無限ループを防止。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等保存。バックフィル日数や健全性チェックを実装。
  - ETL パイプライン（pipeline.py / etl.py）
    - ETLResult データクラスを公開（ETL 結果の集約と to_dict の出力）。
    - 差分更新、backfill、品質チェック（quality モジュールと連携）の概念を実装。
    - _get_max_date 等のユーティリティを実装し、テーブル存在チェックや日付取得の互換性を確保。
    - etl モジュールは ETLResult を再エクスポート。

Changed
- （初回リリースのため変更履歴はなし）

Fixed
- （初回リリースのため修正履歴はなし）

Deprecated
- （なし）

Removed
- （なし）

Security
- （なし）

Notes / 実装上の重要な考慮点
- ルックアヘッド防止:
  - AI モジュール（news_nlp, regime_detector）や研究モジュールは内部で datetime.today()/date.today() を直接参照せず、外部から渡された target_date を基準として処理する設計です。これにより将来データの漏洩（ルックアヘッドバイアス）を防いでいます。
- フェイルセーフ:
  - OpenAI API 呼び出し失敗時は例外を上位にそのまま投げず、基本的に中立スコア（0.0）やスキップで継続する方針です（ただし DB 書き込み等で致命的なエラーが発生した場合は例外を伝播します）。
- DuckDB 互換性:
  - executemany に空リストを渡すと失敗する点を回避するため、空チェックを行ってから executemany を呼び出しています（特に ai_scores の更新処理など）。
- テスト性:
  - OpenAI 呼び出しのラッパー関数（各モジュールの _call_openai_api）をテスト用に差し替え可能にしており、ユニットテストでネットワークを伴う呼び出しをモックできます。

既知の制限 / 今後の改善候補
- 現在の AI 評価は gpt-4o-mini + JSON Mode に依存。将来的なモデル差し替えやレスポンスフォーマットの追加バリデーションが想定されます。
- research モジュールは標準ライブラリのみで実装されており、pandas 等の導入でパフォーマンス向上が可能。
- 一部の DB 書き込みは手動で BEGIN/COMMIT を制御しているため、並列実行時のロックやトランザクション管理について追加検討の余地があります。

--- 

作成: kabusys v0.1.0 リリースノート（初版）