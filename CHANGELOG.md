CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。
セマンティックバージョニングを採用します。

フォーマット:
- Added: 新機能
- Changed: 変更
- Fixed: 修正
- Removed: 削除
- Security: セキュリティ関連

[Unreleased]
------------

なし

[0.1.0] - 2026-03-31
-------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージエントリポイント（src/kabusys/__init__.py）を追加。公開モジュール: data, strategy, execution, monitoring。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機能:
    - プロジェクトルート検出 (.git または pyproject.toml を探索) に基づき .env / .env.local を自動で読み込む。
    - 読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。
    - OS 環境変数は保護（protected set）され、上書き回避の仕組みを提供。
  - .env パーサの強化:
    - export KEY=val 形式に対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理（クォート無し時は # の直前が空白/タブならコメント扱い）などの仕様を実装。
    - ファイル読み込み失敗時は警告を出力して継続。
  - 必須環境変数取得用の _require ヘルパーと Settings プロパティ群を提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等を想定。
    - DB パスのデフォルト（DuckDB: data/kabusys.duckdb、SQLite: data/monitoring.db）を設定。
    - KABUSYS_ENV / LOG_LEVEL の検証（許容値チェック）を実装。
    - is_live / is_paper / is_dev のユーティリティプロパティを提供。

- AI モジュール (src/kabusys/ai)
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news / news_symbols から銘柄毎に記事を集約し、OpenAI（gpt-4o-mini, JSON mode）へバッチ送信して銘柄ごとのセンチメント ai_score を算出し ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ定義（JST 基準）: 前日15:00 JST 〜 当日08:30 JST（UTC に変換して DB と照合）。calc_news_window ユーティリティを提供。
    - バッチ設計: 1 回の API 呼び出しで最大 20 銘柄（_BATCH_SIZE=20）。記事のトリム措置（最大記事数・最大文字数）を実装。
    - 再試行ポリシー: 429 / ネットワーク断 / タイムアウト / 5xx は指数バックオフでリトライ（最大 _MAX_RETRIES=3）。
    - レスポンスのバリデーションを厳格に実装（JSON 抜き出し、results リスト構造チェック、code/score の型検証、スコアを ±1.0 にクリップ）。
    - 処理は部分失敗に強く設計（取得成功したコードのみを DELETE → INSERT で置換し、他の既存スコアを保護）。
    - テスト用フック: API 呼び出し関数 _call_openai_api をモック差し替え可能に設計。
    - フェイルセーフ: API 失敗時は個別チャンクをスキップして継続（例外を投げずにログ出力）。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定し market_regime テーブルへ冪等書き込みを行う score_regime() を実装。
    - マクロ記事抽出はマクロキーワードリスト（日本語・英語混在）によるタイトルフィルタリング。
    - OpenAI 呼び出しは gpt-4o-mini（JSON mode）を使用。API の失敗やパースエラー時は macro_sentiment=0.0 にフォールバック。
    - 再試行・エラー分類のロジックを実装（RateLimitError / APIConnectionError / APITimeoutError / APIError の扱い）。_MAX_RETRIES=3、指数バックオフを採用。
    - ルックアヘッドバイアス対策: prices_daily クエリは target_date 未満のデータのみを使用し、datetime.today()/date.today() を直接参照しない設計。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT で冪等に行い、失敗時は ROLLBACK（失敗時のロールバック失敗もログで報告）。

- データプラットフォーム (src/kabusys/data)
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - JPX カレンダー管理ユーティリティを実装: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day など。
    - market_calendar の有無に応じたフォールバック（DB 登録値優先、未登録日は曜日ベースの判定）を実装。
    - 夜間バッチ更新 calendar_update_job() を実装（J-Quants API から差分取得、バックフィル、健全性チェック、保存処理）。
    - 探索の最大幅やバックフィル期間、健全性チェックのパラメータ（_MAX_SEARCH_DAYS, _BACKFILL_DAYS, _SANITY_MAX_FUTURE_DAYS 等）を設定。
  - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスを公開し、ETL 実行結果の集約（取得件数・保存件数・品質問題・エラー一覧など）を提供。
    - 差分更新、バックフィル、品質チェック（quality モジュール利用）を想定した設計。DB テーブルの最終日取得ユーティリティ等を実装。
    - jquants_client を介した idempotent な保存（ON CONFLICT DO UPDATE）と品質チェック結果の収集を想定。

- リサーチ / ファクター (src/kabusys/research)
  - factor_research.py
    - Momentum, Volatility, Value, Liquidity などの定量ファクター計算関数を実装:
      - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日 MA 乖離）を計算。
      - calc_volatility: 20 日 ATR（atr_20）, atr_pct, avg_turnover, volume_ratio を計算。
      - calc_value: PER / ROE を raw_financials と prices_daily から計算（最新の報告日ベース）。
    - DuckDB 上で SQL を駆使して効率的に計算。データ不足時は None を返す設計。
  - feature_exploration.py
    - calc_forward_returns: 各銘柄の将来リターン（デフォルト horizons=[1,5,21]）を計算。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算するユーティリティを提供（欠損や ties を考慮）。
    - rank, factor_summary: ランク変換、各ファクターの基本統計量（count, mean, std, min, max, median）を計算。
    - 外部依存を避け、標準ライブラリのみで実装。

- 共通設計上の注意点（全体）
  - DuckDB を主要な分析データベースとして利用する想定。すべての分析・ETL処理は DuckDB 接続を受け取る設計。
  - ルックアヘッドバイアス防止の明確な設計指針（datetime.today()/date.today() の不使用、クエリにおける排他条件など）。
  - IDempotent な DB 書き込み（DELETE→INSERT、ON CONFLICT 等）とトランザクション制御（BEGIN/COMMIT/ROLLBACK）。
  - API 呼び出し（OpenAI / J-Quants）に対しては再試行・バックオフ・パース耐性を備えた堅牢な実装。
  - テストしやすさの配慮（OpenAI 呼び出しの差し替え可能性など）。

Fixed
- 初回リリースのため無し

Changed
- 初回リリースのため無し

Removed
- 初回リリースのため無し

Security
- AI モジュールの利用には OpenAI API キー（OPENAI_API_KEY の設定または api_key 引数）が必須。未設定時は ValueError を送出する箇所があるため、運用時は環境変数設定に注意。

Notes / Known limitations
- strategy, execution, monitoring パッケージの公開は __all__ に含まれているが、本リリースで示されたファイル群にはこれらの具象実装は含まれない（将来のリリースで追加予定）。
- DuckDB の executemany に対する空リストバインドの挙動（バージョン依存）に配慮して、空リストのときは executemany を呼ばない防御実装を行っている。
- 一部の外部クライアント（jquants_client 等）はモジュール参照のみで、実際の API クライアント実装は別モジュールとして想定。

--- 

このリリースは設計文書（DataPlatform.md / StrategyModel.md 等）に基づく機能群の初期実装を含みます。将来的にモジュールの分割・API 仕様の変更・追加の安全対策や運用機能（監視・アラート・自動デプロイ）を計画しています。