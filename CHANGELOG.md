# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用しています。

## [Unreleased]

## [0.1.0] - 2026-03-28
初回リリース。日本株自動売買システム「KabuSys」の基礎機能を実装しています。

### Added
- パッケージ初期化
  - パッケージメタ情報を公開（kabusys.__version__ = "0.1.0"）。
  - 公開サブパッケージ一覧（data, strategy, execution, monitoring）。

- 設定・環境変数管理（kabusys.config）
  - .env ファイル自動ロード機能（プロジェクトルートの検出: .git または pyproject.toml を基準）。
  - .env/.env.local の優先順位処理（OS 環境変数の保護、.env.local による上書き）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト向け）。
  - 高機能な .env パーサー（export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント扱い等を考慮）。
  - Settings クラスによる型化された設定アクセス（J-Quants / kabu API / Slack / DB パス / 環境モード / ログレベル判定等）。
  - 環境値検証（KABUSYS_ENV, LOG_LEVEL の妥当性チェック）と利便性プロパティ（is_live, is_paper, is_dev）。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄ごとのニュースを OpenAI（gpt-4o-mini）へバッチ送信し、センチメントスコア（±1.0）を ai_scores テーブルへ書き込む機能を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ（calc_news_window）。
    - バッチ処理（最大 20 銘柄/回）、1 銘柄あたりの記事数・文字数トリム制限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - OpenAI 呼び出しの冗長対応（429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ）。
    - レスポンスの厳格な検証処理（JSON パース、results キー/型、既知コードの検査、数値チェック、スコアのクリップ）。
    - DuckDB への冪等書き込み（DELETE → INSERT）、部分失敗時の既存スコア保護。
    - フェイルセーフ設計（API 失敗時はスキップして継続、致命的例外は投げずログ出力）。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ保存。
    - マクロニュース抽出（マクロキーワードによるフィルタ）、LLM（gpt-4o-mini）によるマクロセンチメント評価。
    - API 呼び出し失敗時のフォールバック（macro_sentiment = 0.0）、レスポンス JSON パース失敗ハンドリング、リトライロジック。
    - レジームスコアの合成・閾値判定・DuckDB トランザクション（BEGIN / DELETE / INSERT / COMMIT）による冪等書き込み。
    - ルックアヘッドバイアス回避の設計（datetime.today() 等を直接参照しない、クエリは date < target_date を使用）。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX 市場カレンダー管理ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - market_calendar が未取得の場合の曜日ベースフォールバック（処理の一貫性を確保）。
    - 夜間バッチ更新ジョブ（calendar_update_job）：J-Quants から差分取得して market_calendar を冪等保存、バックフィル / 健全性チェックを実装。
    - 最大探索日数制限や NULL 値検出時のログ出力等の堅牢性機構。

  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスの導入（ETL 実行結果の構造化: 取得数/保存数/品質問題/エラー一覧 等）。
    - テーブル存在チェックや最大日付取得等のユーティリティを提供。
    - 差分取得・バックフィル・品質チェック（quality モジュールを参照）を想定した設計。jquants_client を用いた idempotent 保存を前提。

  - etl モジュールの公開インターフェース（kabusys.data.etl）で ETLResult を再エクスポート。

- Research（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性指標（20 日平均売買代金・出来高比）およびバリュー（PER, ROE）を計算する関数群（calc_momentum, calc_volatility, calc_value）。
    - DuckDB 上で SQL を用いて計算し、結果を (date, code) キーの辞書リストとして返却。
    - データ不足時の None 処理、営業日ベースのホライズン扱い、性能上のスキャン範囲バッファを考慮。

  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）：任意ホライズン（デフォルト [1,5,21]）の将来リターンを一括で取得。
    - IC（Information Coefficient）計算（calc_ic）：Spearman のランク相関を実装（ランクは平均ランク付与、最小有効レコード数チェック）。
    - ランキングユーティリティ（rank）：同順位は平均ランクで処理、浮動小数の丸めにより ties の検出を安定化。
    - 統計サマリー（factor_summary）：count/mean/std/min/max/median を計算。

- 内部ユーティリティ
  - DuckDB 接続周りの互換性を意識したテーブル存在チェック、および date 型変換ユーティリティ。
  - 各種モジュールでの堅牢なログ出力と例外ハンドリング、トランザクションの ROLLBACK 保護コード。

### Notable design decisions / notes
- ルックアヘッドバイアス防止:
  - AI スコアリング / レジーム評価 / ファクター計算は内部で直接 datetime.today()/date.today() を参照せず、呼び出し側から target_date を受け取る設計。
  - DB クエリは原則として target_date より前（排他）条件を採用。

- OpenAI（LLM）インテグレーション:
  - gpt-4o-mini を想定、JSON Mode を用いた応答受け取り。
  - レスポンスパース失敗や API 障害に対しては安全側（スコア 0.0 や該当銘柄スキップ）で継続するフェイルセーフ実装。
  - テスト容易性のため _call_openai_api をモジュール内で抽象化（unittest.mock.patch で差し替え可能）。

- DB 書き込みの冪等性:
  - ai_scores / market_regime / market_calendar 等は上書きや削除→挿入の手順で冪等に保存。
  - トランザクション制御（BEGIN/COMMIT/ROLLBACK）を明示的に行い、部分失敗時は既存データを保護する戦略を採用。

- 環境変数読み込み:
  - OS 環境変数を保護するため、.env の自動ロード時に既存キーを上書きしない既定挙動。`.env.local` は override=True として上書きを許可。
  - .env のパースは実運用でよくある表記に対応（export 接頭辞、クォート、エスケープ、コメント）。

### Changed
- 初版リリースのため該当なし。

### Fixed
- 初版リリースのため該当なし。

### Security
- 初版リリースのため該当なし。

---

参考: 必須設定（主な環境変数）
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY などが各機能で必要になります。README や .env.example を参照してください。