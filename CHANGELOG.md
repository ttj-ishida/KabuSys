# CHANGELOG

すべての注目すべき変更点を記載します。フォーマットは「Keep a Changelog」に準拠しています。

- リリースノートの語調は日本語です。
- バージョンはパッケージ内の __version__（0.1.0）に基づき作成しています。

## [Unreleased]

（現在、未リリースの変更はありません）

---

## [0.1.0] - 2026-03-28

初回公開リリース。日本株の自動売買およびリサーチ用ユーティリティ群を提供します。主要な機能群と設計上のポイントを以下に示します。

### Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0。
  - パッケージ公開 API（__all__）に data, strategy, execution, monitoring を用意（将来的な拡張を意図）。

- 環境設定 / ロード
  - 環境変数管理モジュール（kabusys.config）を追加。
    - .env / .env.local の自動ロード（プロジェクトルートを .git または pyproject.toml から検出）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - .env の行パーサは export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント（一定条件）に対応。
    - OS 環境変数と .env 上書きの保護（protected set）を実装。
    - 必須環境変数取得用の _require と Settings クラスを提供。
    - Settings で取得する主な環境変数（例）:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
      - OPENAI_API_KEY（AI 関連関数の引数経由でも指定可能）
      - DUCKDB_PATH / SQLITE_PATH（デフォルト値あり）
      - KABUSYS_ENV（development / paper_trading / live の検証）
      - LOG_LEVEL（DEBUG/INFO/... の検証）

- データプラットフォーム（DuckDB ベース）
  - データ ETL パイプライン（kabusys.data.pipeline）を追加。
    - 差分取得、バックフィル、品質チェックの概念をサポート。
    - ETLResult dataclass により実行結果（取得/保存件数、品質問題、エラー等）を統一的に表現。
  - ETL インターフェース再公開（kabusys.data.etl が pipeline.ETLResult を再エクスポート）。
  - カレンダー管理モジュール（kabusys.data.calendar_management）を追加。
    - market_calendar テーブルを基に営業日判定・次/前営業日取得・期間内営業日取得・SQ判定を提供。
    - market_calendar が未取得の場合は曜日ベースのフォールバック（週末を休場とみなす）。
    - カレンダー更新バッチ（calendar_update_job）: J-Quants から差分取得し冪等保存（バックフィルと健全性チェック付き）。
    - 最大探索日数、先読み日数、バックフィル期間、健全性チェック等の保護ロジックを実装。

- 研究（Research）モジュール
  - kabusys.research パッケージを追加（研究/ファクター解析用）。
    - 提供関数群を再エクスポート: calc_momentum, calc_value, calc_volatility, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank。
  - ファクター計算（kabusys.research.factor_research）
    - Momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を計算する calc_momentum。
    - Volatility / Liquidity: 20日 ATR、相対ATR、20日平均売買代金、出来高比率を計算する calc_volatility。
    - Value: 最新の raw_financials と当日の株価から PER / ROE を計算する calc_value。
    - すべて DuckDB 上の prices_daily / raw_financials テーブルのみ参照し、外部 API に依存しない設計。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン算出（calc_forward_returns）：任意ホライズン（デフォルト [1,5,21]）のリターンを一括取得。
    - IC（Information Coefficient）算出（calc_ic）：スピアマンのランク相関を実装（ties を平均ランクで処理）。
    - ランク関数（rank）およびファクター統計サマリー（factor_summary）を提供。
    - pandas 等に依存せず標準ライブラリと DuckDB で完結。

- AI / NLP 機能（OpenAI 統合）
  - kabusys.ai パッケージを追加。公開関数: score_news（ニュース NLP）および score_regime（市場レジーム判定）。
  - News NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を基に銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini, JSON mode）でセンチメントスコアを生成。
    - バッチ処理（最大 20 銘柄/コール）、記事数・文字数上限（トークン肥大対策）に対応。
    - 429 / ネットワーク断 / タイムアウト / 5xx はエクスポネンシャルバックオフでリトライ。その他はスキップして継続（フェイルセーフ）。
    - レスポンスの厳密なバリデーションを実施し、スコアを ±1.0 にクリップ。DuckDB への書き込みはコード単位で DELETE → INSERT の冪等処理。
    - テスト容易性のため _call_openai_api をパッチ可能に実装。
  - レジーム検出（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（70%）とニュース由来のマクロセンチメント（30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - OpenAI 呼び出しは独立実装（モジュール間でプライベート関数を共有しない設計）。
    - API の失敗時は macro_sentiment=0.0 として継続、DB への書き込みは BEGIN/DELETE/INSERT/COMMIT の冪等トランザクション。
    - リトライ・バックオフ、JSON パース失敗時のフォールバックロジックを備える。

### Changed
- （初回リリースのため過去変更なし）

### Fixed
- （初回リリースのため過去修正なし）

### Removed
- （初回リリースのためなし）

### Security
- .env ローダで OS 環境変数を protected として保護（自動上書きを防止）。
- 必須環境変数未設定時は明示的に ValueError を投げる（明確なエラーと早期検出）。
- OpenAI API キーは引数で注入可能（テストや外部キー管理に柔軟）。

### Notes / 互換性・運用上の注意
- AI 機能（score_news / score_regime）は OpenAI API（OPENAI_API_KEY または api_key 引数）に依存。キーが設定されていない場合は ValueError を送出します。
- .env の自動ロードはプロジェクトルートを .git または pyproject.toml から探索するため、配布後の実行環境では期待通りに動作しない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して手動で環境管理してください。
- DuckDB をデフォルトのストレージとして使用（DUCKDB_PATH のデフォルト: data/kabusys.duckdb）。SQLite は監視用途に別途参照（SQLITE_PATH）。
- 日付取扱い: ルックアヘッドバイアスを避けるため、各モジュールは datetime.today() / date.today() に直接依存しない設計（target_date を明示的に渡す）。
- テスト容易性: OpenAI 呼び出し部分はパッチ可能な関数で分離。DB 書き込みは明示的なトランザクション管理（BEGIN/COMMIT/ROLLBACK）を行う。
- DuckDB のバージョンに依存する挙動（executemany に空リストを渡せない等）を考慮した実装あり。

---

今後のリリース案としては、strategy / execution / monitoring の実装拡張、J-Quants クライアントの明示的内容・バージョン情報、CI 用のテストケースやサンプル ETL 実行例を追加する計画が想定されます。必要であれば CHANGELOG の文言をより詳細に分割（細かいコミット単位や PR 単位）して作成できます。どの程度の粒度で詳述するか指示してください。