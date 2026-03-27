# Changelog

すべての注目すべき変更をここに記載します。  
このファイルは「Keep a Changelog」のフォーマットに準拠しています。セマンティックバージョニングを使用します。

## [Unreleased]
- 今のところ未リリースの変更はありません。

## [0.1.0] - 2026-03-27
初回リリース。

### 追加 (Added)
- パッケージ全体
  - kabusys パッケージを追加。__version__ = 0.1.0。
  - パッケージ公開 API: data, strategy, execution, monitoring（__all__）。
  - DuckDB を用いたローカルデータプラットフォーム設計に基づくモジュール群を提供。

- 環境設定 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込みする機能を実装。
    - プロジェクトルートは .git または pyproject.toml を基準に探索（CWD に非依存）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - export KEY=val 形式、クォート（シングル／ダブル）とエスケープに対応。行末コメントの取り扱いも実装。
    - OS 環境変数を保護するため protected キー集合を用いた上書き制御を実装。
  - Settings クラスを公開（settings インスタンス）。
    - 必須環境変数チェック: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（未設定時は ValueError）。
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL（DEBUG/INFO/...）の検証。
    - デフォルト DuckDB/SQLite パス（data/kabusys.duckdb, data/monitoring.db）の提供。

- AI 専用機能 (kabusys.ai)
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄毎にニュースを結合し、OpenAI（gpt-4o-mini, JSON mode）でセンチメントを評価する score_news を実装。
    - JST ベースのタイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供。DB クエリは UTC naive datetime を使用。
    - バッチ処理: 1APIコールで最大 20 銘柄（_BATCH_SIZE）を処理、1銘柄あたりの記事数・文字数上限を実装（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ（最大回数・ベース待機時間は定数化）。
    - レスポンスの堅牢なバリデーション: JSON パース復元（前後余計なテキストが混ざるケースの復元）、results キー検証、未知コードの無視、スコアを ±1.0 にクリップ。
    - 書き込みは部分失敗対策として該当コードのみ DELETE → INSERT の冪等更新。DuckDB の executemany の制約（空リスト不可）に配慮。
    - テスト容易性のため _call_openai_api をパッチ差し替え可能に実装。
    - API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError。
  - レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - MA200 乖離計算は target_date 未満のデータのみを使用してルックアヘッドバイアスを防止。
    - マクロニュースは news_nlp.calc_news_window と raw_news を用いて抽出。LLM 呼び出しは gpt-4o-mini を使用。
    - LLM 呼び出しのリトライ／例外ハンドリング、JSON パース失敗時のフォールバック（macro_sentiment = 0.0）を実装。
    - 最終結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時は ROLLBACK を実施し上位へ例外を伝播。
    - API キーは引数 or OPENAI_API_KEY。

- データプラットフォーム（kabusys.data）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を実装。
    - market_calendar が未取得の場合は曜日ベース（土日非営業）でフォールバック。
    - DB 登録値優先、未登録日は曜日フォールバックで一貫した挙動。
    - calendar_update_job により J-Quants API から差分取得して market_calendar を冪等保存（バックフィル、健全性チェック含む）。
    - 最大探索範囲の上限（_MAX_SEARCH_DAYS）やバックフィル/先読み日数をパラメタライズ。
  - ETL パイプライン補助（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult データクラスを実装（取得数／保存数／品質問題／エラーの収集）。
    - 差分更新、バックフィル、品質チェックの設計方針に基づくユーティリティを提供。
    - _get_max_date やテーブル存在チェックなどの内部ユーティリティを実装。
    - jquants_client（外部モジュール想定）を用いて差分取得・保存処理を行う設計。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離の計算。データ不足時は None（中立）を返す。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務データを取得して PER、ROE を計算（EPS が 0/欠損のときは None）。
    - いずれも DuckDB による SQL 集約で実装し、外部ネットワークアクセスや発注機能とは分離。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: 指定基準日から将来リターンを一括取得（任意ホライズン、入力検証あり）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）計算。3件未満で None を返す。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
    - rank: 同順位は平均ランクにするランク化ユーティリティ。
    - 外部ライブラリに依存せず標準ライブラリ + DuckDB のみで実装。

### 変更 (Changed)
- 初回リリースのため特になし。

### 修正 (Fixed)
- 初回リリースのため特になし（設計上の堅牢化・フォールバック実装多数を初期機能として含む）。
  - 例: OpenAI レスポンスの JSON パース時に前後テキストが混ざるケースからの復元処理、API エラー分類に基づくリトライ制御、DuckDB executemany の空引数回避など。

### セキュリティ (Security)
- 環境変数に以下のシークレットが必要（未設定時は ValueError を発生させる機能あり）:
  - OPENAI_API_KEY（news_nlp / regime_detector で必要）
  - JQUANTS_REFRESH_TOKEN（jquants クライアント用）
  - KABU_API_PASSWORD（kabu ステーション API 用）
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（通知用）
- .env 自動読み込みはプロジェクトルート探索に基づくが、必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。

### 既知の制限 / 注意事項 (Known issues / Notes)
- ニュース NLU とレジーム判定はいずれも外部 LLM（OpenAI）に依存するため API 利用量・料金が発生します。モデルは gpt-4o-mini を想定。
- 一部ファクター（PBR、配当利回り）は現バージョンでは未実装（calc_value 記載）。
- 不足データや API エラー時はフェイルセーフとして中立値（例: ma200_ratio=1.0、macro_sentiment=0.0）やスキップ動作をとる設計。
- 日付処理はすべて target_date を引数で受け、内部で datetime.today()／date.today() を参照しないことでルックアヘッドバイアスを防止。
- DuckDB のバージョンや実行環境による挙動差（例: executemany の空リストバインド）は考慮済み（空リストは送らない実装）。

### 互換性の破壊 (Breaking Changes)
- 初回リリースのため該当なし。

---

（補足）この CHANGELOG は、配布されたソースコードから推測可能な機能・設計方針に基づき作成しています。実際のリリースノートには運用上の追記事項（マイグレーション手順、外部 API のバージョン要件、具体的な DB スキーマ）を併記することを推奨します。