# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

注: 下記はソースコードから推測して作成した初期リリース向けの変更履歴です（実装・設計上の注意点や既知の挙動を含みます）。

## [Unreleased]

## [0.1.0] - 2026-03-31
Initial release

### Added
- パッケージ構成
  - kabusys パッケージの基本公開インターフェースを追加（src/kabusys/__init__.py）。
  - サブパッケージとして data, research, ai, monitoring, strategy, execution を公開予定（__all__ に定義）。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env ファイル（.env, .env.local）および OS 環境変数から設定を読み込む自動ロード機能を実装。
    - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - プロジェクトルートは .git または pyproject.toml を基準に探索（CWDに依存しない挙動）。
  - .env パーサの実装（export 形式、クォート、エスケープ、インラインコメント処理を考慮）。
  - Settings クラスを提供し、アプリケーションで使用する主要な環境変数をプロパティ経由で取得。
    - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - 任意・デフォルト: KABU_API_BASE_URL, DUCKDB_PATH (data/kabusys.duckdb), SQLITE_PATH (data/monitoring.db), PID_FILE_PATH, CPU/MEMORY/DISK閾値、KABUSYS_ENV（development/paper_trading/live）、LOG_LEVEL
  - 設定値は妥当性チェックあり（KABUSYS_ENV, LOG_LEVEL の許容値検査）。未設定の必須値は ValueError を送出。

- AI モジュール（src/kabusys/ai）
  - ニュースセンチメント解析（news_nlp）
    - raw_news / news_symbols テーブルのニュースを銘柄毎に集約して OpenAI（gpt-4o-mini）の JSON mode でセンチメントを算出。
    - バッチ処理（1APIコール最大 20 銘柄）、記事数・文字数のトリム制限、リトライ（429/ネットワーク/タイムアウト/5xx）を実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出・results 配列・code/score 検査）を実装。
    - ai_scores テーブルへ冪等に書き込むロジック（対象コードのみ DELETE→INSERT）を実装。
    - ルックアヘッドバイアス回避のため内部で datetime.today() を参照せず、target_date ベースでウィンドウを計算。
    - テスト容易性のため _call_openai_api を patch で差し替え可能に設計。
  - 市場レジーム判定（regime_detector）
    - ETF 1321（225連動）200日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次で regime（bull/neutral/bear）を判定。
    - prices_daily / raw_news / market_regime テーブルと連携し、冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実施。
    - MA 計算でデータ不足時は中立（1.0）を返し、LLM 呼び出し失敗時は macro_sentiment=0.0 にフォールバックする安全設計。
    - OpenAI 呼び出しは独立実装で、モジュール結合を避ける設計。

- データ基盤関連（src/kabusys/data）
  - マーケットカレンダー管理（calendar_management）
    - market_calendar テーブルの夜間バッチ更新 job（calendar_update_job）を実装。J-Quants クライアントから差分取得 → save（冪等）する処理を実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティを提供。
    - calendar データがない場合は曜日（平日）ベースでフォールバックする挙動。
    - 最長探索制限（_MAX_SEARCH_DAYS）や健全性チェック（last_date の未来日チェック）を実装して安全性を確保。
  - ETL パイプライン（pipeline, etl）
    - ETL 実行結果を表す ETLResult dataclass を公開（etl モジュールで再エクスポート）。
    - pipeline モジュールは差分取得・保存・品質チェックを行う設計方針（jquants_client, quality モジュールとの連携を想定）。
    - ETL 実行結果に品質問題（quality.QualityIssue）やエラーの収集機能を実装。

- 研究用ユーティリティ（src/kabusys/research）
  - factor_research
    - モメンタム（1M/3M/6M）、200日MA乖離、ATR(20)、流動性指標、Value（PER, ROE: raw_financials 参照）等を DuckDB 上の SQL で計算する関数群を追加（calc_momentum, calc_volatility, calc_value）。
    - データ不足時は None を返す設計。
  - feature_exploration
    - 将来リターン算出（calc_forward_returns）、IC（calc_ic）、統計サマリー（factor_summary）、ランク変換（rank）等の分析ユーティリティを実装。
    - pandas 等の外部ライブラリに依存せず、標準ライブラリと DuckDB クエリで実行可能に設計。

- 外部依存・連携
  - DuckDB を用いたデータストレージ操作に対応。
  - OpenAI API（OpenAI Python SDK）を使用（モデル: gpt-4o-mini、JSON mode 指定）。
  - J-Quants クライアント（jquants_client）および kabu ステーション API クライアントを利用する想定の設定箇所を用意。
  - Slack 通知用のトークン/チャンネル設定を Settings に追加（Slack 連携を想定）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- API キー等の必須情報は Settings 経由で明示的に取得する。未設定時は ValueError を送出して安全に停止。

### Notes / Usage hints
- 環境変数と .env の読み込み順序:
  - OS 環境変数 > .env.local (上書き) > .env（未設定のキーのみセット）
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定する。
- OpenAI 呼び出しのフォールバック:
  - news_nlp / regime_detector ともに API 呼び出しに失敗した場合は例外を投げずスコアに 0.0 を使用するか、該当 chunk をスキップするフェイルセーフ実装。
- テスト容易性:
  - _call_openai_api を patch することで外部 API への依存を排除してユニットテストが可能。
- ルックアヘッドバイアス対策:
  - 各モジュールは内部で datetime.today() / date.today() を参照しない設計。target_date を明示的に渡して評価を行う。
- DuckDB の executemany の空リスト制約対応:
  - ai_scores への書き込みでは executemany に空リストを渡さない安全チェックを実装。

---

(将来的なリリースでは、各モジュールの詳細な変更履歴（バグ修正、最適化、API 互換性の変更など）をこのファイルに追記してください。)