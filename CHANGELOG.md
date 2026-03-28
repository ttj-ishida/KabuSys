# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  
現在のバージョンはパッケージメタ情報 (kabusys.__version__ = 0.1.0) に合わせています。

## [Unreleased]
- 今後の変更点をここに記載します。

## [0.1.0] - 2026-03-28
初回公開リリース。日本株自動売買システムの基盤機能群を実装しています。
主にデータ取得・ETL、マーケットカレンダー管理、リサーチ（ファクター計算／特徴量解析）、および OpenAI を用いたニュース NLP / 市場レジーム判定の各モジュールを含みます。

### Added
- パッケージ初期化
  - kabusys パッケージの公開 API を定義（data, strategy, execution, monitoring）。バージョン: 0.1.0。

- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動ロード機能（プロジェクトルートの検出は .git または pyproject.toml を使用）。
  - export KEY=val 形式、クォートされた値、インラインコメント付きの解析をサポートする .env パーサを実装。
  - OS 環境変数の保護（既存キーを上書きしない／上書き禁止キーセット）と自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を提供。
  - 必須環境変数チェック (_require) と設定ラッパー Settings を提供（J-Quants, kabu API, Slack, DB パス, 環境・ログレベル検証等）。
  - KABUSYS_ENV / LOG_LEVEL の値検証（許容値の列挙）。

- データプラットフォーム（kabusys.data）
  - ETL パイプライン基盤（kabusys.data.pipeline）
    - ETLResult データクラス（取得数／保存数／品質チェック結果／エラー集計など）。
    - 差分取得やバックフィル方針、DuckDB を用いた最大日付取得ユーティリティ等を実装。
  - ETL インターフェース再エクスポート (kabusys.data.etl -> ETLResult)。
  - マーケットカレンダー管理 (calendar_management)
    - market_calendar テーブルに基づく営業日判定、次/前営業日取得、期間内営業日リスト取得、SQ日判定。
    - DB データ優先・未登録日は曜日ベースでフォールバックする一貫したロジック。
    - calendar_update_job: J-Quants（jquants_client）から差分取得して冪等的に保存する夜間バッチ処理（バックフィル／健全性チェック含む）。
    - 最大探索日数制限で無限ループを防止。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI(gpt-4o-mini) の JSON モードでスコアリングし ai_scores テーブルへ保存する機能を実装。
  - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）の計算（calc_news_window）。
  - バッチ処理（最大 20 銘柄／リクエスト）、記事トリム (_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK)。
  - リトライ（429 / ネットワーク / タイムアウト / 5xx）を指数バックオフで実装。
  - レスポンスの厳密なバリデーション（JSON パース、results 配列、code/score 検査、スコアのクリップ）。
  - 部分成功を考慮した DB 書き込み（対象コードのみ DELETE → INSERT、DuckDB executemany の互換性配慮）。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動）の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を組み合わせて日次で市場レジーム（bull / neutral / bear）を判定。
  - ma200_ratio 計算、マクロ記事抽出、OpenAI 呼び出し（gpt-4o-mini）による macro_sentiment 評価、スコア合成、market_regime テーブルへの冪等書き込み。
  - LLM 呼び出しは独立実装（news_nlp と共有しない）でモジュール結合を低減。
  - API エラー・パースエラー時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
  - リトライとバックオフ、ログ出力の成熟した処理。

- リサーチ / ファクター（kabusys.research）
  - factor_research: calc_momentum / calc_volatility / calc_value を実装（prices_daily / raw_financials ベース、Zスコア等は外部に依存しない）。
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None）。
    - Volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比。
    - Value: PER（EPS が 0/欠損なら None）、ROE（財務データの最新レコードを使用）。
  - feature_exploration: calc_forward_returns（任意ホライズンの将来リターン、入力検証あり）、calc_ic（Spearman rank IC）、rank（同順位は平均ランク）、factor_summary（count/mean/std/min/max/median）。
  - 実装方針: DuckDB の SQL と Python の組合せで完結、外部接続や発注 API にはアクセスしない。

### Changed
- 設計方針・安全策の採用（各モジュール共通）
  - ルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない（score_news, score_regime, research 等）。
  - DuckDB のバージョン依存（executemany の空リスト制約等）に配慮した実装。
  - DB 書き込みはできる限り冪等（DELETE → INSERT、BEGIN/COMMIT/ROLLBACK 管理）。

### Fixed / Implemented edge-case handling
- .env パーサでの以下のケースに対応
  - export プレフィックス対応、クォート内のバックスラッシュエスケープ、インラインコメントの扱い（クォート有無で挙動を分ける）。
- OpenAI 呼び出し周りでの堅牢化
  - RateLimitError / APIConnectionError / APITimeoutError / APIError へのリトライ・ログ、5xx 判定、最終フォールバック。
  - JSON Mode の結果に余計な前後テキストが混ざる可能性への対応（最外の {} を切り出して復元試行）。
- DuckDB 日付値の取り扱いに関するユーティリティ (_to_date) の整備。

### Notes / Requirements
- 環境変数が必須
  - OPENAI_API_KEY（news_nlp / regime_detector）、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等が動作に必要。
  - デフォルトの DB パス: DUCKDB_PATH= data/kabusys.duckdb、SQLITE_PATH= data/monitoring.db（Settings で変更可能）。
- テスト支援
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して .env の自動読み込みを無効化可能。
  - OpenAI 呼び出しは内部関数を patch して差し替え可能（ユニットテスト向け）。
- 前提となる DB スキーマ
  - modules は prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等のテーブル存在を前提とします。スキーマ作成は別途必要です。

### Known limitations / TODO
- Strategy / execution / monitoring パッケージは公開 API に含まれるが本リリースに含まれる実装は限定的（今後の実装予定）。
- 一部のバリデーションやエッジケース処理は実運用データでの追加検証が必要（特に LLM 出力の多様性、DuckDB バインドの互換性）。
- PBR・配当利回りなどのバリューファクターは未実装（calc_value で将来的に拡張予定）。

---

（注）上記はソースコードの実装内容から推測して作成した CHANGELOG です。実際のリリースノートや運用ルールに合わせて文章や分類を調整してください。