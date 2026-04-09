# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

フォーマットに関する詳細は: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-04-09
初回リリース。日本株自動売買プラットフォームの基盤機能群を実装・公開しました。

### Added
- パッケージ基礎
  - パッケージ名 kabusys を追加。バージョンは 0.1.0。
  - top-level の __all__ に data / strategy / execution / monitoring を公開。

- 設定 / 環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - プロジェクトルート自動検出（.git または pyproject.toml を基準）により、実行カレントディレクトリに依存せず .env/.env.local をロード。
  - .env/.env.local の読み込み順序: OS 環境 > .env.local (override) > .env (非上書き)。
  - export KEY=val 形式、クォートやエスケープ、インラインコメント処理に対応した堅牢な .env パーサー実装。
  - 環境変数の自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD サポート（テスト用）。
  - 必須値未設定時に明示的にエラーを返す _require ユーティリティ。
  - J-Quants / kabuステーション / LINE / DB / paper-trading / 監視 / ログレベルなどの設定プロパティを実装（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, PAPER_FILL_MODE, DUCKDB_PATH, PID_FILE_PATH, CPU/MEM 閾値, KABUSYS_ENV 等）。
  - PAPER_FILL_MODE や LOG_LEVEL / KABUSYS_ENV のバリデーション実装。

- AI (ニュース NLP / 市場レジーム判定)
  - kabusys.ai.news_nlp:
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄毎のセンチメント（ai_score）を算出・ai_scores テーブルへ書き込み。
    - タイムウィンドウ: 前日15:00 JST ～ 当日08:30 JST（UTC に変換）を採用する calc_news_window 実装。
    - バッチサイズ、トークン肥大化対策（記事数・文字数上限）、最大リトライ・指数バックオフ、429/ネットワーク/タイムアウト/5xx に対するリトライロジックを実装。
    - API レスポンスの堅牢なバリデーションと復元（JSON 抽出）、スコアの ±1.0 クリッピング、部分失敗時に既存スコアを保護する DB 書き込み（DELETE→INSERT の個別実行）を実装。
    - テスト容易性のため _call_openai_api の差し替えを想定（unittest.mock.patch）。
    - score_news(conn, target_date, api_key=None) を公開。
  - kabusys.ai.regime_detector:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定する score_regime を実装。
    - ma200_ratio 計算でルックアヘッドバイアス対策（target_date 未満のデータのみ使用）。
    - raw_news からマクロキーワードでフィルタしてタイトルを抽出し、OpenAI へ送信して macro_sentiment を取得。API エラー時はフェイルセーフで 0.0 を採用。
    - LLM 呼び出しは独立実装としモジュール間結合を低減。
    - 判定結果を market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - score_regime(conn, target_date, api_key=None) を公開。

- データプラットフォーム（Data）
  - kabusys.data.calendar_management:
    - JPX カレンダー管理（market_calendar テーブル）と営業日判定ロジックを追加。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装。DB 登録値がない場合は曜日ベースのフォールバックを採用。
    - calendar_update_job により J-Quants から差分取得して market_calendar を冪等更新（バックフィルや健全性チェック含む）。
  - kabusys.data.pipeline / etl:
    - ETL パイプラインのインターフェースと ETLResult データクラスを実装（取得件数、保存件数、品質チェック結果、エラー集計等を保持）。
    - ETL 設計方針（差分更新、backfill、品質チェックの扱い等）を反映。
  - kabusys.data.etl: ETLResult を再エクスポート。

- Research（因子・特徴量解析）
  - kabusys.research.factor_research:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER/ROE）を DuckDB 上で計算する calc_momentum / calc_volatility / calc_value を実装。
    - DuckDB のウィンドウ関数を活用し、データ不足時は None を返す等の堅牢な実装。
  - kabusys.research.feature_exploration:
    - 将来リターン計算 calc_forward_returns（任意ホライズン対応、引数検証あり）。
    - Spearman ランク相関（IC）を計算する calc_ic（ランク化と欠損処理含む）。
    - factor_summary（count/mean/std/min/max/median）と rank（同順位は平均ランク）を実装。
  - kabusys.research.__init__ で主要関数を公開。

### Changed
- ドキュメント的記述:
  - 各モジュールの設計方針・処理フロー・フェイルセーフ挙動等をコード内ドキュメンテーションとして追加し、実運用での挙動が明確になるようにした。

### Fixed
- （初回リリースにつき該当なし）

### Deprecated
- （初回リリースにつき該当なし）

### Removed
- （初回リリースにつき該当なし）

### Security
- OpenAI API キーの扱いについては api_key 引数や環境変数 OPENAI_API_KEY の利用を明示。自動ロードされた .env 値はプロセス環境にのみ反映され、設定ファイルの読み取り失敗時は警告で済ます等、直接的な秘密漏洩対策の実装は本バージョンではコードレベルでの扱い説明に留めています。

---

今後のリリースノートには API 変更、バグ修正、性能改善、追加機能などを逐次記載していきます。