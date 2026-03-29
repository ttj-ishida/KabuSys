# Changelog

すべての重要な変更はこのファイルに記録します。  
形式は "Keep a Changelog" に準拠します。  
このプロジェクトはセマンティックバージョニングを採用しています。

※注: リリース内容はソースコードから推測して記載しています。

## [Unreleased]

## [0.1.0] - 2026-03-29
初回公開リリース

### Added
- パッケージ初期化
  - kabusys パッケージのバージョンを 0.1.0 として公開。
  - __all__ に data, strategy, execution, monitoring を登録。

- 設定/環境変数管理 (`kabusys.config`)
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env パーサーは `export KEY=val` 形式、クォート文字・バックスラッシュエスケープ、インラインコメントの取り扱い等に対応。
  - OS 環境変数を保護するため `.env.local` 上書き時に保護リストを考慮。
  - Settings クラスを提供し、以下の設定をプロパティとして取得可能:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live のバリデーション）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL のバリデーション）
    - is_live / is_paper / is_dev の簡易判定プロパティ

- AI 関連 (`kabusys.ai`)
  - news_nlp.score_news
    - raw_news と news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ書き込む。
    - JST 前日 15:00 ～ 当日 08:30 を対象とするウィンドウ計算（UTC に変換）を実装。
    - バッチサイズ、トークン肥大化対策（記事数上限・文字数トリム）、JSON モードレスポンスのバリデーション、スコアクリップ（±1.0）、エクスポネンシャルバックオフによるリトライを実装。
    - API キー注入によるテスト容易性（api_key 引数または OPENAI_API_KEY 環境変数）をサポート。
    - フェイルセーフ設計: API/パース失敗は個別チャンクのスキップやスコア未取得で継続。

  - regime_detector.score_regime
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と news_nlp ベースのマクロセンチメント（重み 30%）を合成して market_regime テーブルへ冪等書き込み。
    - OpenAI 呼び出しは独立実装、API エラーに対するリトライ・フォールバック（macro_sentiment=0.0）を実装。
    - ルックアヘッドバイアス防止: target_date 未満のデータのみを使用、datetime.today() を参照しない。

- データ/ETL (`kabusys.data`)
  - calendar_management
    - JPX カレンダーの管理（market_calendar テーブル）と夜間更新ジョブ calendar_update_job を実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。DB に登録がない日については曜日ベースでフォールバック。
    - 最大探索日数・バックフィル・健全性チェックを含む安全な実装。
  - pipeline
    - ETLResult データクラスによる ETL 実行結果の収集（品質チェック結果・エラー一覧を含む）。
    - 差分取得・バックフィル・品質チェックの設計方針およびユーティリティ関数（最終取得日の取得等）を実装。
  - etl: ETLResult を公開インターフェースとして再エクスポート。

- リサーチ/ファクター (`kabusys.research`)
  - factor_research: calc_momentum, calc_volatility, calc_value を実装（prices_daily / raw_financials を参照）。
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank を実装（外部依存なし、標準ライブラリのみ）。
  - research パッケージの __all__ に主要関数をエクスポート。

- その他実装上の注意点（設計方針）
  - DuckDB を主要な永続化先として利用。複数箇所で DuckDB 接続を直接受け取る設計。
  - ルックアヘッドバイアス対策として datetime.today()/date.today() を直接参照する処理を避ける実装方針。
  - エラー時は「できる限り継続」するフェイルセーフな振る舞い（API 失敗時の無害化や部分書き込み保護など）。
  - DuckDB 互換性に配慮（executemany に空リストを渡さない等の対策）。

### Changed
- 初版のため該当なし（初期実装）。

### Fixed
- 初版のため該当なし（ただし堅牢性向上のため各種フォールバック/ログ/リトライ実装を含む）。

### Security
- OpenAI API キーや各種シークレットは環境変数経由で取得する設計。`.env` 自動ロードは環境変数で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
- 設定値は protected な OS 環境変数上書きを防ぐ仕組みを用意。

### Notes / Migration / Usage
- 必須環境変数（設定例）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
  - (必要に応じて) OPENAI_API_KEY または score_* 関数に api_key を直接渡す
- DuckDB 上に以下のテーブルが前提となる（各モジュール参照）:
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials
- AI スコア関連:
  - score_news(conn, target_date, api_key=None) は書き込んだ銘柄数を返す。
  - score_regime(conn, target_date, api_key=None) は成功時 1 を返す。
- calendar_update_job は jquants_client.fetch_market_calendar / save_market_calendar を呼び出すため、J-Quants クライアント実装が必要。
- テスト容易性:
  - OpenAI 呼び出し箇所（_call_openai_api 等）はテストで patch しやすい構造になっている。

---

今後のリリースでは以下が想定されます（未実装・改善案）:
- strategy / execution / monitoring の実装およびドキュメント追加
- API クライアントの抽象化・モック提供
- より詳細な品質チェック報告機能・監査ログ
- パフォーマンス最適化（大規模データ向けのバッチ戦略など）