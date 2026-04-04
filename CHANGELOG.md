# Changelog

すべての重要な変更点はここに記録します。本ファイルは「Keep a Changelog」規約に準拠します。

フォーマット:
- 変更はセクション（Added / Changed / Fixed / Deprecated / Removed / Security）に分類しています。
- バージョンは PEP440 準拠（本リポジトリ初期リリースは 0.1.0）です。

## [Unreleased]

## [0.1.0] - 2026-04-04
### Added
- パッケージ基盤
  - kabusys パッケージの初期公開。__version__ = "0.1.0"。
  - パッケージ公開 API（__all__）に data, strategy, execution, monitoring を想定して定義。

- 設定・環境読み込み（kabusys.config）
  - .env ファイルおよび環境変数からの設定読み込みを実装。
  - プロジェクトルート検出ロジックを導入（.git または pyproject.toml を基準）。
  - .env/.env.local の自動ロード（OS 環境変数優先）。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサは export プレフィックス、引用符、エスケープ、インラインコメントを考慮した堅牢な実装。
  - Settings クラスを提供し、主要設定値をプロパティで取得可能:
    - J-Quants / kabu API / LINE / DB パス（DUCKDB_PATH / SQLITE_PATH）/監視ファイルパス等
    - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の検証（許容値チェック）
    - pid/kill flag の設定、リソース閾値（CPU/MEM/DISK）などのデフォルトと型変換

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）でセンチメント評価を行う機能を実装（score_news）。
  - バッチ処理（1 API 呼び出しで最大 20 銘柄）と、1銘柄あたりの記事・文字数トリム制御を実装（_BATCH_SIZE / _MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
  - JSON Mode を用いた厳密なレスポンス検証と復元ロジック（前後テキスト混入時の {} 抽出）。
  - エラーハンドリング: 429・ネットワーク断・タイムアウト・5xx に対して指数バックオフでリトライ。致命的でないエラーはロギングして該当チャンクをスキップ（フェイルセーフ）。
  - スコアは ±1.0 にクリップし、取得済み銘柄のみ ai_scores テーブルへ置換（DELETE → INSERT）して部分失敗時のデータ保護を実現。
  - テスト容易性のため OpenAI 呼び出し部分を差し替え可能（_call_openai_api を patch 可能）。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - 日次で市場レジーム（bull / neutral / bear）を判定する score_regime を実装。
  - 指標:
    - ETF 1321（日経225連動）の200日移動平均乖離（重み 70%）
    - マクロ経済ニュースの LLM センチメント（重み 30%）
  - マクロニュース抽出は raw_news をマクロキーワードでフィルタ（最大 20 件）。
  - OpenAI 呼び出しは独立実装（news_nlp と内部関数を共有しない）で、API エラー時は macro_sentiment=0.0 として継続（フェイルセーフ）。
  - DuckDB への冪等書き込みを実装（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。

- 研究用ファクター計算（kabusys.research）
  - factor_research: モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（20日ATR、相対ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER/ROE）を計算する関数を実装（calc_momentum / calc_volatility / calc_value）。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（Spearman）計算（calc_ic）、ファクター統計サマリー（factor_summary）、ランク変換ユーティリティ（rank）を実装。
  - 実装方針: DuckDB 接続を受け取り SQL と純粋な Python 標準ライブラリで完結。外部 API や発注処理にはアクセスしないよう分離。

- データ基盤ユーティリティ（kabusys.data）
  - calendar_management:
    - JPX カレンダー管理と夜間更新ジョブ（calendar_update_job）を実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar が空の場合、曜日ベースのフォールバック（祝日データ未取得時の安全動作）。
    - 最大探索日数制限、バックフィルや健全性チェックを実装。
  - pipeline / etl:
    - ETL パイプラインの結果を表現する ETLResult データクラスを提供（パラメータや品質チェック結果、エラー一覧を保持）。
    - 差分更新・バックフィル・品質チェックの設計方針を反映（jquants_client との連携を想定）。
    - data.etl で ETLResult を再エクスポート。

- DuckDB テーブル設計（想定利用テーブル）
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar 等の読み書きを行う実装になっている。

### Design / Implementation notes
- ルックアヘッドバイアス対策:
  - datetime.today() / date.today() を内部処理で直接参照しない（すべて target_date パラメータを明示）。
  - DB クエリは target_date 未満 / 比較範囲を厳密に指定。
- API 呼び出しの堅牢性:
  - OpenAI 呼び出しは共通の retry/backoff 方針を採用し、テストで差し替え可能なポイントを提供。
  - API レスポンスパース失敗や例外は基本的にフェイルセーフ（ゼロやスキップ）で継続する設計。
- DB 書き込みは冪等化を優先（DELETE → INSERT / ON CONFLICT を想定）。
- テスト容易性:
  - 外部 API 呼び出し関数を patch してユニットテストが可能な構成。

### Fixed
- （初版のため該当なし）

### Changed
- （初版のため該当なし）

### Deprecated
- （初版のため該当なし）

### Removed
- （初版のため該当なし）

### Security
- OpenAI API キーや各種トークンは環境変数で管理（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）。コード中にハードコードされた資格情報は含まれない設計。

---

注:
- 本 CHANGELOG はコードベースからの仕様・挙動の読み取りに基づいて推測して作成しています。実際の公開リリースノート作成時は、追加の変更点や担当者コメントを追記してください。