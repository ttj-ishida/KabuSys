# Changelog

すべての重要な変更はこのファイルに記録します。本ファイルは「Keep a Changelog」規約に準拠しています。バージョンは SemVer を想定します。

## [0.1.0] - 2026-03-31

初回リリース。以下の主要機能・モジュールを追加しました。

### 追加 (Added)
- パッケージ基盤
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - パッケージ公開 API: __all__ = ["data", "strategy", "execution", "monitoring"]（将来モジュール用エクスポート）

- 設定・環境変数管理 (kabusys.config)
  - Settings クラスを導入し、アプリケーション設定を環境変数から取得可能に。
  - 自動 .env ロード機能:
    - プロジェクトルートはこのモジュールのファイル位置から .git または pyproject.toml を探索して特定。
    - 読み込み優先順位: OS 環境 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト向け）。
  - .env パーサ実装:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォートのエスケープ対応。
    - インラインコメントの取り扱い（クォート無しは直前が空白/タブならコメントとして無視）。
  - 環境変数保護:
    - .env の上書き時に既存の OS 環境変数を保護する機構（protected set）。
  - 利用可能な設定プロパティ（主なもの）:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（省略時デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live のいずれか）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL のいずれか）

- データプラットフォーム (kabusys.data)
  - ETL パイプライン
    - ETLResult データクラス（pipeline.ETLResult）を公開（kabusys.data.etl 経由で再エクスポート）。
    - pipeline モジュールは差分取得・保存・品質チェックのインフラを実装する設計に基づくユーティリティを提供。
  - 市場カレンダー管理 (calendar_management):
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day 等の営業日判定ユーティリティを実装。
    - calendar_update_job による J-Quants からのカレンダー差分取得と market_calendar テーブルの冪等保存。
    - DB にカレンダーデータがない場合は曜日（土日）ベースのフォールバックを行う設計。
    - lookahead / backfill / 健全性チェックの導入。

- 研究用ユーティリティ (kabusys.research)
  - factor_research モジュール:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離などのモメンタムファクター。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率等。
    - calc_value: PER, ROE を raw_financials と prices_daily から計算。
    - 実装は DuckDB の SQL ウィンドウ関数中心で副作用なし（読み取り専用）。
  - feature_exploration モジュール:
    - calc_forward_returns: 将来リターン（任意ホライズン）計算（デフォルト [1,5,21]）。
    - calc_ic: スピアマンランク相関（IC）計算（ランク処理含む）。
    - rank: 平均ランク（同順位は平均ランク）実装（丸めによる ties 安定化）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
  - 研究向け API は外部ライブラリ非依存（標準ライブラリ + duckdb）で実装。

- ニュース NLP / AI (kabusys.ai)
  - score_news (news_nlp.py):
    - raw_news / news_symbols を銘柄ごとに集約し、OpenAI（gpt-4o-mini）にバッチで問い合わせて銘柄ごとのセンチメント ai_score を ai_scores テーブルに書き込む。
    - 時間ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（内部は UTC naive の時間範囲変換）。
    - バッチサイズ、記事数・文字数トリム (_BATCH_SIZE, _MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK) を導入。
    - JSON Mode を利用し厳密な JSON レスポンスを期待。レスポンスのパース失敗や余剰テキストの復元処理を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx サーバーエラーは指数バックオフでリトライ。その他はスキップして継続（フェイルセーフ）。
    - 書込みは部分失敗対策として対象コードのみ DELETE → INSERT（冪等性確保）。
    - DuckDB 0.10 の executemany 空リスト挙動に配慮して空チェックを実装。
  - score_regime (regime_detector.py):
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定し market_regime テーブルへ書き込み。
    - マクロニュースは raw_news からマクロキーワードでフィルタ（_MACRO_KEYWORDS）して最大 20 記事を LLM に投入。
    - OpenAI 呼び出しは専用のラッパーを利用し、API エラー時は macro_sentiment=0.0 にフォールバックして処理継続。
    - レジームスコアはクリップ処理と閾値判定でラベル化。DB 書込みは BEGIN/DELETE/INSERT/COMMIT の冪等操作を行う。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- API レスポンスのパースに関する堅牢性向上:
  - OpenAI の JSON Mode でも余分なテキストが混じる場合へ対応するため、最外の {} 抽出ロジックを追加。
  - openai SDK の APIError について status_code の有無に依存しない安全な判定（getattr を利用）。
- DuckDB 互換性修正:
  - executemany に空リストを渡すと失敗するバージョン対策として事前に空チェックを行う実装を導入。

### セキュリティ (Security)
- .env 自動読み込みはデフォルト有効だが、テスト等で無効化できるフラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を用意。
- .env の読み込み時に既存の OS 環境変数は protected set により誤って上書きされない設計。

### 既知の注意点 / 運用メモ
- OpenAI API キーは score_news / score_regime の引数 api_key または環境変数 OPENAI_API_KEY で指定する必要があります（未指定時は ValueError を送出）。
- 本パッケージは DuckDB をデータバックエンドとして使用する想定であり、以下のテーブルを参照／更新します:
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar
  - ETL や研究関数を利用する前にスキーマと必要データの準備が必要です。
- 時刻や日付の扱いは「ルックアヘッドバイアス防止」を重視しており、内部実装では datetime.today() / date.today() を参照しない関数設計がなされています。ターゲット日を明示的に渡して利用してください。

### 将来の改善案（未実装）
- news_nlp / regime_detector の単体テスト用の抽象化（API クライアント注入の更なる拡張）。
- OpenAI レスポンスのバリデーション強化（スキーマ検証ライブラリ導入検討）。
- strategy / execution / monitoring に対応するエンドツーエンドの統合テストとサンプル戦略の追加。

---

このリリースの内容に関して不明点や補足してほしい箇所があればお知らせください。必要に応じてセクション分割や例の追加（環境変数一覧、DB テーブルスキーマ想定など）を行います。