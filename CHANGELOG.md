# Changelog

すべての重要な変更は Keep a Changelog のフォーマットに従って記載します。  
このファイルはコードベースの現状（リポジトリ内のソースから推測）に基づく初期リリース向けの変更履歴です。

なおバージョンはパッケージ定義（kabusys.__version__ = "0.1.0"）に合わせて記載しています。

## [0.1.0] - 2026-03-28
最初の公開リリース。日本株自動売買システムのコア機能群を実装。

### Added
- パッケージのエントリポイント
  - kabusys パッケージを追加。主要サブパッケージの公開インターフェースを定義（data, strategy, execution, monitoring）。

- 環境設定/ロード
  - kabusys.config
    - .env ファイルおよび OS 環境変数から設定値を読み込む自動ローダーを実装。
    - .env のパース機能を強化（export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、行内コメント処理に対応）。
    - .env と .env.local の読み込み優先度を実装（OS 環境変数を保護する protected 機構）。
    - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
    - 必須環境変数をチェックする Settings クラスを追加（J-Quants / kabu API / Slack / DB パス等のプロパティを提供）。
    - KABUSYS_ENV と LOG_LEVEL のバリデーションを実装（許容値チェック、エラー時は ValueError）。

- データ基盤機能
  - kabusys.data.pipeline
    - ETL パイプライン向けのユーティリティと ETLResult データクラスを追加。取得件数／保存件数／品質問題／エラー概要を収集・出力可能。
    - 差分取得・バックフィル方針や DuckDB の最大日付取得などのユーティリティを実装。
  - kabusys.data.etl
    - pipeline.ETLResult を公開するインターフェースを追加。
  - kabusys.data.calendar_management
    - JPX カレンダー管理（market_calendar テーブル）のユーティリティを実装。
    - 営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を提供。
    - calendar_update_job: J-Quants API から差分取得して冪等保存する夜間バッチ処理を実装（バックフィル、健全性チェックを含む）。
    - カレンダーデータ未取得時の曜日ベースフォールバックを実装。
    - 最大探索日数制限（_MAX_SEARCH_DAYS）やバックフィル日数、安全チェック（_SANITY_MAX_FUTURE_DAYS）を実装。

- リサーチ機能（オフライン分析）
  - kabusys.research パッケージを追加。duckdb を使ったオンプレミス／ローカル分析用ユーティリティ群。
  - factor_research.py
    - ファクター計算関数を実装: calc_momentum, calc_volatility, calc_value。
    - Momentum（1M/3M/6M リターン、MA200 乖離）、Volatility（20日 ATR、相対ATR、出来高関連）、Value（PER, ROE）を算出。
    - 大域定数（ホライズン、ウィンドウ幅等）とデータ不足時の None 戻しを明示。
  - feature_exploration.py
    - 将来リターン計算 calc_forward_returns（任意ホライズン）
    - IC（スピアマンランク相関）計算 calc_ic、rank 関数
    - factor_summary：基本統計量（count/mean/std/min/max/median）計算
  - research パッケージは外部 API にアクセスせず、DuckDB の prices_daily / raw_financials のみ参照する設計。

- ニュース NLP / AI 統合
  - kabusys.ai.news_nlp
    - raw_news / news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）へバッチリクエストしセンチメントを取得、ai_scores テーブルへ書き込み。
    - リトライ（429 / ネットワーク断 / タイムアウト / 5xx）を指数バックオフで実装。チャンク処理（最大 20 銘柄/コール）・1銘柄あたりの最大記事数と文字数制限によるトークン肥大対策を実装。
    - レスポンス検証（JSON 抽出、results 配列、code/score の検査、数値チェック）、スコアを ±1.0 にクリップして保存。
    - API 呼び出し箇所をモジュール内関数として分離し、テスト時に patch できるように設計（_call_openai_api の差し替えが可能）。
    - ETL と同様に書き込み処理は冪等性を考慮し、取得済みコードのみ DELETE → INSERT で置換（部分失敗時に他コードを保護）。

  - kabusys.ai.regime_detector
    - ETF 1321（TOPIX 等に相当）の 200 日移動平均乖離（重み70%）と、news_nlp によるマクロセンチメント（重み30%）を合成して日次の market_regime テーブルへ保存する score_regime を実装。
    - OpenAI 呼出しは独自実装で分離（news_nlp と内部関数を共有しない方針）。
    - LLM の失敗時は macro_sentiment を 0.0 にフォールバック（フェイルセーフ）。
    - DuckDB を使ったデータ取得・計算、MA200 計算時のデータ不足時の警告と中立値使用、冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - OpenAI 呼出しのエラー種別別ハンドリング（RateLimit, APIConnectionError, APITimeoutError, APIError）とリトライロジックを実装。

- パッケージ構成と公開 API
  - kabusys.ai.__init__ にて score_news を公開。
  - kabusys.research.__init__ で主要関数を再エクスポート（zscore_normalize は data.stats から取得）。

### Changed
- （初回リリースにつき該当なし）

### Fixed / Robustness
- ニュースレスポンスの JSON パースにおいて、JSON mode でも前後に余計なテキストが混ざるケースを考慮し、最外の波括弧を抽出して復元するフォールバックを追加。
- OpenAI API の APIError に status_code 属性がない将来の SDK 変化に対して getattr を使って安全に判定する実装。
- DuckDB executemany に対する互換性（空リスト不可）に配慮し、空リストチェックを導入して不要な実行を防止。

### Notes / Known limitations
- AI 評価は OpenAI の Chat Completions（gpt-4o-mini）を前提として実装されており、API キー（OPENAI_API_KEY）を環境変数か引数で指定する必要がある。未設定時は ValueError を投げる。
- research モジュールは外部 API を呼ばず分析専用（本番発注等には影響を与えない）。
- calendar_update_job は外部 J-Quants クライアント（kabusys.data.jquants_client）に依存するため、その API 実装／レスポンス形状に合わせた実行が必要。
- 実際の発注・監視（execution / monitoring）モジュールはパッケージ階層に用意されているが、この差分からは詳細実装が読み取れない（エントリとして公開のみ確認）。

---

この CHANGELOG はソースコードから推測して作成しています。実際のコミット履歴・リリースノートをベースにする場合は、該当コミット／PR 情報を反映して更新してください。必要であれば、各モジュールごとにより詳しい変更点や実装上の注意（関数シグネチャ、期待する DB スキーマ、外部依存ライブラリのバージョン等）を追記します。