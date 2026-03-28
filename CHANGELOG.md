# Changelog

すべての変更は Keep a Changelog に準拠しています。  
このファイルはコードベースの内容から推測して作成した初期のリリースノートです。

注: バージョンはパッケージの __version__（0.1.0）に基づいています。

## [Unreleased]
（今後の変更点メモ）
- CLI／デーモン化、スケジューラ統合や追加の外部ストレージ対応を予定。
- OpenAI のアダプティブ・レート制御や別モデル対応の改善予定。

---

## [0.1.0] - 2026-03-28
初回リリース。日本株自動売買／データ基盤・リサーチ・AI 支援モジュールを提供。

### Added
- パッケージ基盤
  - kabusys パッケージ初版を追加。公開 API は kabusys.__all__ = ["data", "strategy", "execution", "monitoring"] を想定。

- 環境設定 / ロード
  - 環境変数管理モジュール（kabusys.config）を追加。
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動ロードする機能（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env 行の robust なパース（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ処理）を実装。
    - 必須キー取得ヘルパー _require と Settings クラスを提供。
    - 設定項目例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL。
    - KABUSYS_ENV と LOG_LEVEL の値検証（有効な値のみ許可）。

- AI（ニュースNLP・レジーム判定）
  - kabusys.ai.news_nlp
    - raw_news / news_symbols を元に銘柄別にニュースを集約し、OpenAI（gpt-4o-mini, JSON mode）でセンチメントを算出して ai_scores テーブルへ書き込む。
    - バッチ処理（最大 20 銘柄／チャンク）、1銘柄あたりの記事数制限・文字数トリム、リトライ（指数バックオフ）等の堅牢化を実装。
    - レスポンスのバリデーション（JSON 抽出、results 配列、code と score の形式チェック、スコア ±1.0 クリップ）。
    - テスト容易性のため _call_openai_api をパッチ差し替え可能に設計。
    - 時間ウィンドウの計算（JST 基準の前日 15:00 ～ 当日 08:30 を UTC naive に変換）を calc_news_window で提供。
  - kabusys.ai.regime_detector
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来の LLM マクロセンチメント（重み 30%）を合成して market_regime テーブルへ日次で判定結果を書き込む。
    - OpenAI 呼び出しは独立実装で実務環境向けのリトライ/フェイルセーフを備える（API 失敗時 macro_sentiment=0.0）。
    - レジームは 'bull' / 'neutral' / 'bear' のラベルを返す。DB 書き込みは冪等（BEGIN/DELETE/INSERT/COMMIT）。
    - _MACRO_KEYWORDS によるタイトルフィルタリングや最大記事数制限を実装。

- データ / ETL / カレンダー
  - kabusys.data.pipeline / etl / calendar_management を追加。
    - ETLResult データクラス（ETL の取得・保存数、品質問題、エラー要約を保持）。
    - 差分取得・backfill・品質チェックを想定した ETL 設計（J-Quants クライアント経由）。
    - market_calendar の夜間更新ジョブ（calendar_update_job）実装。バックフィル＆健全性チェック、J-Quants からのフェッチと保存処理を想定。
    - 営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。DB データがない場合は曜日（週末）ベースでフォールバック。
    - DuckDB を使用することを前提とした実装（日付変換ユーティリティ、情報スキーマ参照）。
    - 一部処理で DuckDB の executemany の挙動（空リスト不可）を考慮。

- リサーチ / ファクター
  - kabusys.research パッケージを追加。
    - factor_research:
      - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算。
      - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
      - calc_value: raw_financials から EPS/ROE を用いて PER, ROE を計算（PBR/配当利回りは未実装）。
      - DuckDB に対する SQL ベースの実装で、結果は (date, code) キーの dict リストで返却。
    - feature_exploration:
      - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
      - calc_ic: スピアマンランク相関（IC）を計算（3 銘柄未満は None）。
      - rank: 同順位は平均ランクにする実装。
      - factor_summary: count/mean/std/min/max/median を算出する統計サマリー。
    - zscore_normalize をデータモジュールから再エクスポート。

### Changed
- （初回リリースのため該当なし）

### Fixed
- 環境変数パーサーの堅牢化:
  - export プレフィックス対応、クォート内のエスケープ処理、クォートなしでのコメント認識などを実装し .env パースの信頼性を向上。

### Security
- 機密情報の扱いに関する注意をドキュメント化:
  - OpenAI API キーや J-Quants / kabu API の認証情報は環境変数を利用することを想定（Settings._require で必須チェック）。
  - .env 自動ロードを環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能（テストや CI 用）。

### Known limitations / Notes
- OpenAI（gpt-4o-mini）に依存:
  - LLM による JSON レスポンスは完全には保証されないため、応答のパース失敗や予期しない出力はログに記録してフォールバック（スコア 0.0 やスキップ）する設計。
- 時間/タイムゾーン:
  - news ウィンドウや calendar 更新では UTC naive な datetime を内部で使用。JST ↔ UTC の変換ロジックを明示しているが、タイムゾーン混入に注意。
- データベーススキーマ:
  - 以下のテーブル／カラムを参照・更新する実装を前提としている：prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials。
  - 実際のテーブルスキーマはコード内 SQL に従う必要があります（例: ai_scores に date, code, sentiment_score, ai_score 等）。
- DuckDB 互換性:
  - executemany に空リストを渡せない古い DuckDB バージョン（0.10 系）を考慮したガードが含まれる。
- テスト設計:
  - _call_openai_api（news_nlp / regime_detector）は単体テストで差し替え可能（unittest.mock.patch を想定）。
- フェイルセーフ設計:
  - LLM 呼び出し失敗時は例外を投げずにフェイルセーフ値で継続する箇所がある（ETL の一部・AI スコアリング等）。呼び出し元でリトライやアラート処理を行うことを推奨。

### Migration / Usage notes
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など（Settings クラスのプロパティ参照）。
  - OpenAI の利用時は OPENAI_API_KEY を設定するか、score_* 関数に api_key を明示的に渡す。
- .env の自動読み込み:
  - プロジェクトルート判定は __file__ から親ディレクトリを探索して .git または pyproject.toml を探す方式。配布後に動作させる場合は注意。
- DB ファイルパスデフォルト:
  - DUCKDB_PATH は data/kabusys.duckdb、SQLITE_PATH は data/monitoring.db（いずれも expanduser() を使用）。

---

今後のバージョンでは以下を検討しています（非網羅）:
- モデル切替、モデルごとのプロンプト・スキーム抽象化
- スケジューリング（cron / APScheduler）やマネージドワークフロー対応
- より詳細な品質チェックと自動リカバリ機構
- RDBMS（Postgres 等）やクラウドストレージ対応の追加オプション

もし特定のモジュールや関数に関する詳細なリリースノートや使用上の注意（例: SQL スキーマ、期待されるテーブル定義）を出力して欲しい場合は、その旨を教えてください。