# Changelog

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の形式に従います。  
（以下の記載は提供されたコードベースの内容から推測して作成しています）

※ 日付はこの CHANGELOG を生成した日付です。

## [Unreleased]
- （未リリースの変更はここに記載）

## [0.1.0] - 2026-04-01

初回リリース。以下の主要機能・モジュールを実装しています（コード内容から推測）。

### Added
- パッケージ基盤
  - kabusys パッケージ初期バージョンを公開（__version__ = 0.1.0）。
  - パッケージ公開 API として data, strategy, execution, monitoring を __all__ に登録。

- 設定・環境変数管理（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込みする機能を追加。
  - 読み込みの優先順位は OS 環境変数 > .env.local > .env（.env.local は上書き）として実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env のパースは以下に対応：
    - 空行/コメント行（#）の無視
    - export KEY=val 形式のサポート
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理
    - クォートなしの場合のインラインコメント扱い（'#' の直前が空白/タブの場合にコメントとして扱う）
  - 環境変数上書き時に OS 環境（起動時点の os.environ）を保護する protected 機構を導入。
  - Settings クラスを提供し、必要な設定をプロパティ経由で取得：
    - J-Quants / kabuステーション / Slack 等の必須トークンの取得（未設定時は ValueError を送出）
    - データベースパス（duckdb, sqlite）、監視用閾値（CPU/Memory/Disk）、PID ファイルパスなどの取得
    - 環境（development/paper_trading/live）や LOG_LEVEL の検証、is_live/is_paper/is_dev のユーティリティプロパティ

- AI（自然言語処理）モジュール（kabusys.ai）
  - news_nlp モジュール（score_news）
    - raw_news / news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）の JSON モードでセンチメント分析を行い ai_scores テーブルへ書き込む処理を実装。
    - JST ベースのニュースウィンドウ（前日 15:00 ～ 当日 08:30 JST）を UTC 変換して利用する calc_news_window を提供。
    - バッチ処理（1 API 呼び出しで最大 20 銘柄）、1 銘柄あたりの最大記事数・文字数制限、429/ネットワーク/5xx に対する指数バックオフリトライを実装。
    - レスポンスのバリデーション（JSON 抽出、"results" フォーマット、コード照合、数値チェック）を厳格に行い、スコアは ±1.0 にクリップ。
    - API キー注入（引数 or 環境変数 OPENAI_API_KEY）。未設定時は ValueError。
    - 部分失敗時に既存スコアを保護するため、取得成功したコードのみ DELETE → INSERT による置換を行う（DuckDB executemany の互換性考慮）。
    - テスト容易性のため、_call_openai_api をモック差し替え可能に設計。

  - regime_detector モジュール（score_regime）
    - ETF 1321（日経225 連動 ETF）の 200 日移動平均乖離（ma200_ratio）とニュース由来のマクロセンチメントを合成して、日次の market_regime テーブルにレジーム（bull/neutral/bear）を書き込む機能を実装。
    - ma200_ratio 計算は target_date 未満のデータのみを使用し、データ不足時は中立（1.0）にフォールバックしてルックアヘッドバイアスを防止。
    - マクロセンチメントは news_nlp 側で抽出したマクロ関連記事タイトルを gpt-4o-mini に渡して JSON で取得。API エラー時は macro_sentiment = 0.0 にフェイルセーフ。
    - 合成ウェイトは 70%（MA） / 30%（マクロ）、スコア合成後に閾値を使ってラベル付与。
    - DB 書き込みは冪等（BEGIN / DELETE WHERE date = ? / INSERT / COMMIT）で実装。
    - OpenAI 呼び出しのリトライ、レスポンスパースの例外処理、ログ出力を備える。

- リサーチ／ファクター（kabusys.research）
  - factor_research モジュール
    - Momentum: 約1M/3M/6M のリターン計算、200 日移動平均乖離の算出（データ不足時は None）。
    - Volatility: 20日 ATR（true range の扱いに注意）、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
    - Value: raw_financials から直近財務を取得して PER（EPS が 0/欠損時は None）・ROE を計算。
    - DuckDB のウィンドウ関数（LAG/AVG/ROW_NUMBER 等）を活用して効率的に計算。
    - 全ての関数は prices_daily / raw_financials のみ参照し、本番発注 API 等へのアクセスは行わない設計。

  - feature_exploration モジュール
    - 将来リターン計算（calc_forward_returns）：指定ホライズン（デフォルト [1,5,21]）の LEAD を使った計算、入力検証（horizons は 1..252 の整数）。
    - IC（Information Coefficient）計算（calc_ic）：Spearman ランク相関を実装（同順位は平均ランク）。
    - rank ユーティリティ：浮動小数の丸めを行って同順位を正しく扱う実装。
    - 統計サマリー（factor_summary）：count/mean/std/min/max/median を計算（None/非有限値は除外）。
    - これらは外部ライブラリに依存せず、標準ライブラリと DuckDB による実装。

  - research パッケージは data.stats の zscore_normalize を再エクスポートし、factor 計算群をまとめて公開。

- データ基盤（kabusys.data）
  - calendar_management モジュール
    - market_calendar を用いた営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を提供。
    - market_calendar が空の場合は曜日（平日）ベースのフォールバックを行う設計。
    - 最長探索日数やバックフィル日数、健全性チェック等の保護ロジックを導入。
    - calendar_update_job：J-Quants からカレンダーを差分取得して market_calendar に冪等保存する夜間バッチ処理（バックフィルや健全性チェックあり）。
    - J-Quants クライアント（jquants_client）を経由した fetch/save の呼び出しで実装。

  - pipeline / ETL
    - ETLResult dataclass を提供（取得件数・保存件数・品質チェック結果・エラー情報等を保持）。to_dict で品質問題を辞書化可能。
    - pipeline モジュール（差分取得、保存、品質チェックのワークフロー）を想定した実装（jquants_client と quality モジュールとの連携、差分/バックフィルロジック、DuckDB 特性への配慮）。
    - data.etl は ETLResult を再エクスポート。

- テスト・運用を考慮した実装上の配慮
  - 日時処理関数（score_news / score_regime 等）は内部で datetime.today()/date.today() を直接参照しない（ルックアヘッドバイアス防止のため target_date を受け取る設計）。
  - OpenAI 呼び出しを内部関数でラップしテスト時に差し替え可能にしている。
  - DuckDB の executemany が空配列を受け付けない問題への対応が盛り込まれている（空リストチェック）。

### Changed
- 初回リリースのため該当なし（全機能は Added）。

### Fixed
- 初回リリースのため該当なし。

### Deprecated
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- 初回リリースのため該当なし。

---

注記：
- 上記の記載は提供されたソースコードの解析に基づく推測的な CHANGELOG です。実際の変更履歴（コミット単位の差分やレビジョン情報）に基づく公式な履歴はリポジトリの VCS ログを参照してください。