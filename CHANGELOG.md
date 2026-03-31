Keep a Changelog
=================

すべての変更はセマンティックバージョニングに従って記載します。  
このファイルは Keep a Changelog の書式に準拠しています。

[0.1.0] - 2026-03-31
--------------------

Added
- パッケージ初期リリース "kabusys"（バージョン 0.1.0）
  - パッケージルート: src/kabusys
  - パッケージは data, research, ai, config などのモジュールを提供。

- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを提供。
  - 自動 .env ロード:
    - プロジェクトルートを .git または pyproject.toml を基準に探索して決定（CWD に依存しない）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - OS 環境変数は読み込み時に保護（protected）され、不要な上書きを防止。
  - .env パーサは次をサポート:
    - コメント行、空行、export KEY=val 形式
    - シングル/ダブルクォート内でのバックスラッシュエスケープ
    - クォート無しの inline コメント処理（直前が空白またはタブの '#' をコメントとみなす）
  - 必須設定を取得する _require() による明確な例外メッセージ。
  - Settings によるプロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）
    - KABU_API_BASE_URL, データベースパス（DUCKDB_PATH, SQLITE_PATH）、監視設定（PID_FILE_PATH 等）
    - CPU/Memory/Disk のしきい値、KABUSYS_ENV（development/paper_trading/live）の検証、LOG_LEVEL 値検証
    - is_live / is_paper / is_dev のユーティリティプロパティ

- AI モジュール（kabusys.ai）
  - ニュースセンチメント（news_nlp.score_news）
    - raw_news, news_symbols テーブルを集約し、銘柄ごとのニュースを OpenAI（gpt-4o-mini, JSON mode）へバッチ送信してセンチメントを算出。
    - 特長:
      - JST ベースの時間ウィンドウ（前日 15:00 ～ 当日 08:30 JST）を UTC に変換して扱う calc_news_window。
      - 1 銘柄あたりの記事数・文字数上限（記事数 _MAX_ARTICLES_PER_STOCK、文字数 _MAX_CHARS_PER_STOCK）でトリム。
      - 1 回の API コールで最大 20 銘柄をバッチ処理（_BATCH_SIZE）。
      - レート制限(429)、ネットワーク断、タイムアウト、5xx に対する指数バックオフリトライ。
      - レスポンスの堅牢なバリデーション:
        - JSON モードでも前後の余計なテキストが混入する場合の復元処理（最外の {} を抽出）
        - "results" フィールド、各要素の "code" と "score" の検査、未知コードの無視、数値性検査、±1.0 のクリップ
      - 部分失敗対策: 書き込みは取得済みコードのみ DELETE → INSERT（部分失敗時に既存スコアを保護）
      - テスト容易性: _call_openai_api を unittest.mock.patch で差し替え可能
      - API キーは引数 api_key または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError。

  - 市場レジーム判定（ai.regime_detector.score_regime）
    - ETF 1321（日経225 連動型）200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - フロー:
      - ma200_ratio を prices_daily から計算（target_date 未満のみ使用してルックアヘッドを防止）
      - マクロキーワードで raw_news をフィルタしタイトルを抽出（最大件数制限）
      - OpenAI（gpt-4o-mini）でマクロセンチメントを評価（記事がない場合は LLM 呼び出しをスキップ）
      - 失敗時のフェイルセーフ: macro_sentiment = 0.0
      - スコア合成とラベリング（閾値 _BULL_THRESHOLD / _BEAR_THRESHOLD）
      - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）とロールバック処理
    - OpenAI 呼び出し用クライアント生成は引数でのキー注入を許可し、テスト時差替え可能。
    - レトライ・エラー分類（5xx の扱いなど）とログ出力を備える。

- Data モジュール（kabusys.data）
  - カレンダー管理（calendar_management）
    - JPX カレンダー管理ロジック（market_calendar テーブル）:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供
      - DB 登録あり → DB 値優先、未登録日は曜日ベース（週末除外）でフォールバック
      - 最大探索日数制限 (_MAX_SEARCH_DAYS) で無限ループ回避
      - calendar_update_job により J-Quants API から差分取得（バックフィル、健全性チェック、保存は jquants_client 経由）
  - ETL パイプライン（pipeline.ETLResult と etl の再公開）
    - ETLResult データクラス:
      - ETL の実行結果を構造化（取得・保存件数、品質問題、エラー一覧等）
      - has_errors / has_quality_errors プロパティ、to_dict によるシリアライズ
    - pipeline モジュール:
      - 差分更新、backfill、品質チェックのためのユーティリティ（jquants_client, quality を利用）
      - デフォルトの backfill 日数・最小データ開始日等の設定
      - DuckDB を前提としたテーブル存在チェック・最大日付取得ユーティリティ
    - 設計方針:
      - id_token の注入によりテスト容易性を確保
      - 品質チェックはエラーを収集するが即時中断は行わない（呼び出し元が判断）

- Research（kabusys.research）
  - factor_research:
    - モメンタム（calc_momentum）: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）
    - ボラティリティ/流動性（calc_volatility）: 20 日 ATR, 相対 ATR, 20 日平均売買代金, 出来高比率
    - バリュー（calc_value）: PER（EPS が 0 または欠損の場合は None）, ROE（raw_financials の最新レコードを使用）
    - 全関数は DuckDB の prices_daily / raw_financials のみ参照し外部 API を呼ばない
    - データ不足時の None 処理と結果形式は (date, code) をキーとした dict のリスト
  - feature_exploration:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一度に取得（LEAD を利用）
    - calc_ic: スピアマンランク相関（IC）を計算（3 件未満で None）
    - rank: 同順位は平均ランクへの対応、浮動小数誤差対策に round(..., 12) を適用
    - factor_summary: 各列の count/mean/std/min/max/median を算出（None は除外）
    - すべて標準ライブラリと DuckDB のみで実装（pandas 等に依存しない）

Other notable implementation details
- ルックアヘッドバイアス防止:
  - AI / リサーチ / レジーム判定系は内部で datetime.today()/date.today() を参照せず、target_date に依存して計算を行う設計。
- ロギングとフェイルセーフ:
  - 多くの処理で詳細ログ（info/warning/debug）を出力し、API エラー時はフォールバック値（0.0 等）で継続するフェイルセーフを採用。
  - DB 書き込み時は BEGIN/COMMIT/ROLLBACK を利用して一貫性を保つ実装。
- テスト支援:
  - OpenAI を呼び出す内部関数をパッチ可能な実装にし、ユニットテストでのモック化を想定。

Fixed
- 初版につき該当無し。

Changed / Deprecated / Removed / Security
- 初版につき該当無し。

Notes / Required environment variables
- 本リリースの一部機能は外部 API キーやトークンを必要とします:
  - OPENAI_API_KEY（news_nlp / regime_detector）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID
- .env.example を参照して .env を用意してください。

今後の予定（想定）
- execution / monitoring 等の実行・監視モジュールの実装追加
- テストカバレッジ強化、CI 連携、パフォーマンス最適化
- モデル / プロンプト改善、API コールのコスト最適化

[0.1.0]: https://example.com/release/0.1.0