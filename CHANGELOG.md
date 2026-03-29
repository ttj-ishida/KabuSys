# Changelog

すべての注目すべき変更をここに記録します。フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-03-29
初回リリース。日本株自動売買／データ基盤・リサーチ・AI支援のためのコア機能を提供します。

### 追加 (Added)
- コアパッケージ
  - パッケージ名: kabusys、バージョン 0.1.0
  - __all__ に data, strategy, execution, monitoring を公開（パッケージ入口を整理）。

- 設定・環境読み込み (src/kabusys/config.py)
  - .env ファイルの自動読み込み機能を追加（プロジェクトルート判定: .git または pyproject.toml を探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込みの無効化対応。
  - .env パーサーを実装:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理等に対応。
    - protected（OS 環境変数）を保護する override ロジックを実装。
  - Settings クラスを追加し、環境変数をプロパティ経由で取得:
    - 必須トークン取得: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（未設定時は ValueError を発生）。
    - デフォルト値: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH。
    - 環境検証: KABUSYS_ENV（development / paper_trading / live）および LOG_LEVEL の検証。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- AI ニュース NLP (src/kabusys/ai/news_nlp.py)
  - ニュース記事を銘柄単位で集約して OpenAI（gpt-4o-mini、JSON mode）でセンチメントを評価し ai_scores テーブルに書き込む処理を追加。
  - ニュース収集ウィンドウ計算（JST → UTC 変換）を calc_news_window として提供。
  - バッチ処理 (最大 _BATCH_SIZE=20 銘柄)、1 銘柄あたりの記事数および文字数のトリム機能（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）。
  - OpenAI 呼び出しのリトライ（429/ネットワーク断/タイムアウト/5xx）と指数バックオフ実装。
  - レスポンスの厳密なバリデーションと数値化、スコアの ±1.0 クリップ。
  - DuckDB への書き込みは部分失敗時に既存データを保護するため、対象コードのみを DELETE→INSERT する冪等処理（トランザクションと executemany の空リストチェック対応）。
  - API キー注入可能（引数または環境変数 OPENAI_API_KEY）、未設定時は ValueError。

- AI レジーム判定 (src/kabusys/ai/regime_detector.py)
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次市場レジーム（bull/neutral/bear）を算出する score_regime を実装。
  - マクロキーワードによる raw_news フィルタリング、OpenAI 呼び出し（gpt-4o-mini、JSON mode）、リトライ・バックオフ、API 失敗時は macro_sentiment=0.0 とするフェイルセーフ。
  - 計算結果は market_regime テーブルへ冪等的に保存（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。
  - lookahead バイアス防止のため target_date 未満のデータのみを参照する設計。

- データ（Data platform） (src/kabusys/data/…)
  - カレンダー管理 (calendar_management.py):
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days の営業日判定ユーティリティを追加。
    - market_calendar が未取得の場合は曜日ベース（土日除外）でフォールバック。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等更新する夜間バッチ処理を実装（バックフィル / 健全性チェック）。
  - ETL パイプライン (pipeline.py) と ETLResult（dataclass）を追加:
    - 差分更新・バックフィル・品質チェック設計に基づく ETLResult の集計とシリアライズ機能。
    - DuckDB テーブルの存在確認や最大日付取得ユーティリティを実装。
  - etl モジュールで ETLResult を再エクスポート。

- リサーチ（src/kabusys/research/…）
  - factor_research.py:
    - モメンタム（1M/3M/6M リターン、ma200 乖離）、ボラティリティ（20日 ATR 等）、バリュー（PER, ROE）を計算する calc_momentum / calc_volatility / calc_value を実装。
    - DuckDB SQL を用いた効率的な集計、データ不足時の None 処理。
  - feature_exploration.py:
    - 将来リターン計算 calc_forward_returns（任意ホライズン対応）、IC（スピアマン相関）計算 calc_ic、ランク変換 rank、factor_summary（基本統計量）を実装。
    - ties を平均ランクで扱う rank 実装や入力検証、horizons の上限チェックを実装。
  - research パッケージ入口で主要関数を再エクスポート。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- OpenAI API キーは引数で注入可能かつ環境変数 OPENAI_API_KEY を参照する設計。必須未設定時には明確なエラーを返すように実装。

### 設計上の重要な注意点（ドキュメント的メモ）
- ルックアヘッドバイアス対策:
  - news_nlp, regime_detector, research 関数は内部で datetime.today() / date.today() を参照せず、外部から与えられた target_date を基準に計算します。
- DB 書き込みは冪等性を重視（DELETE→INSERT、ON CONFLICT 相当の扱い、トランザクション）。
- OpenAI 呼び出しは JSON mode を利用し、レスポンスパース失敗や API 障害時にはスコアを 0.0 またはスキップしてフェイルセーフにする設計。
- DuckDB の互換性を考慮し、executemany に空リストを渡さないようチェックを行っています。
- ロギングを随所に埋めており、失敗時は警告/例外ログを出力して上位に伝播するかフェイルセーフで継続します。

---

今後のリリースでは、strategy / execution / monitoring の実装充実、テストケース・型チェック強化、API クライアント周りの抽象化やモック容易化、ドキュメント追加を予定しています。