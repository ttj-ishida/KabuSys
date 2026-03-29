CHANGELOG
=========

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。

注: 日付・バージョンはコードベースから推測して作成しています。実際のリリース日・バージョン管理ポリシーに合わせて適宜調整してください。

Unreleased
----------
- 今後の作業予定やマイナー改善（例: strategy / execution / monitoring の追加実装、テストカバレッジ拡充、ドキュメント整備など）。

[0.1.0] - 2026-03-29
--------------------
初期リリース。日本株自動売買プラットフォーム「KabuSys」のコア機能を実装。

Added
- パッケージ構成
  - kabusys パッケージを導入。主要サブパッケージとして data, ai, research を含む設計（__init__.py でバージョン 0.1.0 を定義）。
- 環境設定/読み込み（kabusys.config）
  - .env/.env.local ファイルおよび OS 環境変数から設定を読み込む自動ロード機能を実装。
  - .env パーサを実装: コメント、export プレフィックス、シングル/ダブルクォート、エスケープ文字、行末コメント処理などに対応。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - Settings クラスを導入し、主要設定値をプロパティ経由で提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）
    - KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）、SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live の検証）および LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
  - 未設定の必須環境変数取得時は ValueError を投げる設計。
- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols を基に銘柄別に記事を集約し、OpenAI（gpt-4o-mini、JSON Mode）でセンチメントスコアを取得して ai_scores テーブルへ保存する機能を実装。
  - タイムウィンドウ定義: 前日 15:00 JST ～ 当日 08:30 JST（内部では UTC naive datetime を使用）。
  - バッチ処理: 1 API 呼び出しで最大 20 銘柄を処理、1銘柄あたりの最大記事数・文字数でトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
  - リトライ戦略: 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ。
  - レスポンスバリデーション: JSON の抽出・検証、スコアの数値チェック、既知コードのみ採用、スコアを ±1.0 にクリップ。
  - フェイルセーフ: API エラー時は当該チャンクをスキップし、処理継続（例外を投げずにログ出力）。
  - テスト容易性: OpenAI 呼び出しを差し替え可能（unittest.mock.patch を想定）。
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を組み合わせて market_regime テーブルに日次判定を行う score_regime を実装。
  - マクロセンチメントは news_nlp の記事集約ロジックを再利用しつつ、regime_detector 側で OpenAI を直接呼び出して JSON を解析。
  - API エラー時のフォールバック（macro_sentiment = 0.0）、最大リトライ回数、エクスポネンシャルバックオフを実装。
  - DB 書き込みは冪等: BEGIN / DELETE WHERE date = ? / INSERT / COMMIT、例外時には ROLLBACK。
  - ルックアヘッドバイアス対策（datetime.today() を直接参照しない、prices_daily クエリは date < target_date といった排他条件）。
- データ ETL（kabusys.data.pipeline, etl）
  - ETLResult データクラスを提供（取得件数、保存件数、品質チェック結果、エラーリストなどを含む）。
  - 差分更新のための最終取得日取得ユーティリティ、テーブル存在チェック、日付変換ヘルパーを実装。
  - ETL 設計方針をコードと docstring に明記（バックフィル、部分失敗時の保護、品質チェック方針）。
  - etl モジュールは pipeline.ETLResult を再エクスポート。
- カレンダー管理（kabusys.data.calendar_management）
  - market_calendar テーブルを用いた営業日/SQ判定ロジックを実装:
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
  - DB データがない場合は曜日ベースのフォールバック（土日を非営業日扱い）。
  - calendar_update_job: J-Quants クライアント経由で JPX カレンダーを差分取得し market_calendar に冪等更新（バックフィルや健全性チェックを含む）。
  - 最大探索日数・ルックアヘッド・バックフィルの日数等を定数化して安全性を担保。
- リサーチ / ファクター計算（kabusys.research）
  - factor_research モジュール: momentum, value, volatility（ATR, 平均売買代金, 出来高比など）を DuckDB SQL + Python で実装。
  - feature_exploration モジュール:
    - calc_forward_returns: 複数ホライズン（デフォルト 1,5,21）で将来リターンを一括取得。
    - calc_ic: スピアマン（ランク相関）による IC 計算（同順位は平均ランク処理）。
    - rank: 値から適切なランク配列を生成（丸め誤差対策で round を使用）。
    - factor_summary: 各カラムの基本統計量（count, mean, std, min, max, median）。
  - 実装方針として DuckDB のみに依存し、外部ライブラリに依存しない設計。
- DuckDB を主要なローカル DB として利用する設計を採用（関数は DuckDB 接続を引数に受ける）。
- ロギング/エラーハンドリング
  - 各モジュールで詳細な logger 出力（info/debug/warning/exception）を実装。
  - 外部 API 呼び出し失敗時は適切にログを残し、フォールバックや部分スキップで堅牢性を確保。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- OpenAI API キーなどの機密情報は環境変数経由で取得。必須キー未設定時は明確なエラーメッセージを出力して処理を停止。

Notes / Upgrade / Migration
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - OpenAI を利用する機能を使う場合は OPENAI_API_KEY が必要（news_nlp, regime_detector）。
- 環境変数自動読み込み:
  - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して決定するため、配布後もワークフローに依存せず .env ファイルを検出します。自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- DuckDB バインドの互換性:
  - DuckDB の executemany に空リストが渡せないバージョン（例: 0.10 系）を考慮した実装になっています。DuckDB のバージョン差異に注意してください。
- テスト支援:
  - OpenAI 呼び出し部分はモジュール内でラップされており unittest.mock.patch による差し替えが容易です。

今後の計画（例）
- strategy / execution / monitoring の実装拡充（本リリースではインターフェース・パッケージ名のみ存在）。
- テストケース追加とCI パイプラインの整備。
- モデル/スコアリングのチューニングと性能測定結果の導入。
- Slack 等通知経路の統合強化。

ライセンス、貢献方法等のメタ情報は別途 README / CONTRIBUTING に記載してください。