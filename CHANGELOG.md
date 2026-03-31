# CHANGELOG

全ての重要な変更をここに記載します。本ファイルは Keep a Changelog の形式に準拠しています。  
フォーマットの詳細: https://keepachangelog.com/ja/

## [0.1.0] - 2026-03-31

初回公開リリース

### 追加 (Added)
- パッケージ概要
  - kabusys: 日本株自動売買 / データプラットフォーム / リサーチ用の基盤ライブラリを初版として公開。
  - パッケージバージョン: 0.1.0（src/kabusys/__init__.py）。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装（優先順: OS 環境変数 > .env.local > .env）。
  - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサは `export KEY=val`、クォート（シングル・ダブル）、コメント、バックスラッシュエスケープをサポート。
  - 重要な設定の取得用 Settings クラスを提供 (例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID)。
  - 各種デフォルト値を提供（KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH、PID_FILE_PATH、閾値等）。
  - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL の値検証を実装。
  - settings = Settings() を公開。

- AI 関連 (kabusys.ai)
  - ニュース NLP スコアリング (news_nlp.score_news)
    - raw_news / news_symbols を集約し、OpenAI (gpt-4o-mini, JSON mode) にバッチ送信して銘柄ごとのセンチメントを算出。
    - バッチサイズ、記事数・文字数上限、リトライ (429/ネットワーク/5xx 用の指数バックオフ) を実装。
    - レスポンスのバリデーションとスコアの ±1.0 クリッピング、失敗時は安全にスキップするフェイルセーフ実装。
    - calc_news_window により JST 時間帯のウィンドウを UTC naive datetime で算出（ルックアヘッドバイアス回避）。
  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成し日次でレジーム（bull/neutral/bear）を算出。
    - OpenAI 呼び出しは独自関数で実装し、API エラー時は macro_sentiment=0.0 として処理継続（フェイルセーフ）。
    - DuckDB へ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。

- データプラットフォーム (kabusys.data)
  - カレンダー管理 (calendar_management)
    - market_calendar テーブルを参照した営業日判定ユーティリティを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB が未取得のときは曜日ベース（土日非営業）でフォールバック。
    - 夜間バッチで J-Quants からカレンダーを取得して保存する calendar_update_job（バックフィル、健全性チェックを含む）。
  - ETL パイプライン (pipeline.py)
    - 差分取得・保存・品質チェックフロー設計に対応する ETLResult データクラスを実装して公開（kabusys.data.etl で再エクスポート）。
    - バックフィル、カレンダー先読み、品質チェックの概念を導入。
    - DuckDB を用いた idempotent 保存想定（ON CONFLICT / 個別 DELETE + INSERT による保護）。

- リサーチモジュール (kabusys.research)
  - ファクター計算 (factor_research)
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER, ROE）などの計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB のウィンドウ関数によるSQL中心の実装。外部 API 呼び出し無し。
    - 結果は (date, code) をキーとする dict のリストで返す設計。
  - 特徴量探索 (feature_exploration)
    - 将来リターン計算 (calc_forward_returns)、IC（calc_ic）、統計サマリー (factor_summary)、ランク変換 (rank) を実装。
    - pandas 等に依存せず純標準ライブラリ＋DuckDBで実装。
  - zscore_normalize は kabusys.data.stats から再エクスポート。

### 変更 (Changed)
- （初版のため該当なし）

### 修正 (Fixed)
- （初版のため該当なし）

### 破壊的変更 (Breaking Changes)
- （初版のため該当なし）

### 注意事項 / 制約 (Notes & Limitations)
- OpenAI API
  - score_news / score_regime は OpenAI API キー（api_key 引数または環境変数 OPENAI_API_KEY）が必須。未設定時は ValueError を発生させる。
  - LLM の応答は JSON モードを期待するが、応答パースに失敗した場合は該当チャンクをスキップまたは macro_sentiment=0.0 として処理継続する安全設計。
- DuckDB
  - 多くの集計・ウィンドウ処理は DuckDB に依存。テストや実運用では DuckDB 接続オブジェクトを渡す必要あり。
  - 一部の executemany に対する空リストの扱い（DuckDB 0.10 の制約）を考慮している。
- 時間・タイムゾーン
  - ルックアヘッドバイアスを避けるため、内部実装では datetime.today() / date.today() を直接参照しない設計方針（ただし calendar_update_job はバッチ実行用に date.today() を使用）。
- 環境変数の必須項目
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など、運用に必要な環境変数がある（Settings のプロパティ参照）。
- ログと検証
  - KABUSYS_ENV と LOG_LEVEL の値チェックを実装しているため、不正な値設定時には例外が発生する。
- 部分的な実装・将来の拡張
  - 現時点では PBR・配当利回りなど一部バリューファクターは未実装（calc_value の docstring に記載）。
  - 将来的に ai スコアと sentiment_score の差分化、より詳細なエラーハンドリングやメトリクス収集を予定。

### セキュリティ (Security)
- （初版公開時点で既知のセキュリティ修正はなし）
- 注意: API キー等の機密情報は .env / 環境変数で管理し、リポジトリやログに出力しないこと。

---

今後のリリースでは以下を想定:
- AI モジュールの応答検証強化・モデル差し替えの容易化
- ETL の並列化、品質チェックルールの追加
- リアルタイム監視・実行モジュール（execution / monitoring）の実装拡張

（必要であれば、この CHANGELOG を英訳する、あるいはより詳細な変更ログ（コミット単位）を追加します。）