# Changelog

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

最新リリース
==============

[0.1.0] - 2026-03-28
-------------------

Added
- 初回公開リリース。
- パッケージの公開情報
  - パッケージ名: kabusys、バージョン: 0.1.0（src/kabusys/__init__.py）。
  - パッケージ外部公開 API: data, strategy, execution, monitoring を __all__ でエクスポート。
- 設定・環境変数管理（src/kabusys/config.py）
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動ロードする仕組みを実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - .env パーサ実装：export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理などを適切にパース。
  - .env の読み込みで既存 OS 環境変数を保護する protected 機構を実装（.env.local は override=True で上書き可）。
  - Settings クラスを導入し、アプリケーション設定をプロパティ経由で取得可能に（J-Quants / kabu ステーション / Slack / DB パス / 環境・ログレベル判定など）。
  - バリデーション実装: KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL（DEBUG/INFO/...）の検証。未設定の必須変数は明示的なエラーを返す。

- AI（自然言語処理）関連（src/kabusys/ai/）
  - news_nlp モジュール（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON mode を用いて銘柄ごとのセンチメント（-1.0〜1.0）を算出して ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ（前日15:00 JST〜当日08:30 JST）計算ユーティリティ（calc_news_window）を実装。
    - バッチ処理: 最大 20 銘柄/チャンク、1 銘柄あたり最大記事数・文字数トリム（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）。
    - OpenAI 呼び出しの再試行/指数バックオフ（429/ネットワーク断/タイムアウト/5xx 対応）。非リトライエラーはスキップして継続するフェイルセーフ設計。
    - レスポンス検証とスコアクリッピング（±1.0）。不正レスポンス時は該当チャンクをスキップ。
    - 書き込みは冪等性を考慮（DELETE→INSERT。DuckDB executemany 空リスト回避）。
  - regime_detector モジュール（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）200 日移動平均乖離（ma200_ratio: 重み 70%）とニュース由来のマクロセンチメント（重み 30%）を統合して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ保存する処理を実装。
    - マクロニュースは news_nlp のウィンドウ計算を利用してフィルタし、OpenAI（gpt-4o-mini）で JSON レスポンスを取得。
    - LLM 呼び出しは独自実装（モジュール結合を避ける設計）。API 失敗時は macro_sentiment=0.0 とするフェイルセーフ。
    - MA 計算でデータ不足時は中立（1.0）を採用してルックアヘッドバイアスを排除。
    - 冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）とエラーハンドリング（ROLLBACK 試行、失敗時は警告ログ）。
    - レート制限やサーバーエラーに対するリトライ実装（上限回数・バックオフ）。

- データ関連（src/kabusys/data/）
  - calendar_management モジュール（src/kabusys/data/calendar_management.py）
    - JPX カレンダー管理（market_calendar）と営業日判定ユーティリティを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - DB にカレンダー情報がない場合は曜日ベース（土日休）でフォールバックする一貫したロジックを実装。
    - calendar_update_job により J-Quants から差分取得→保存（バックフィル / 健全性チェック / ON CONFLICT での冪等保存）を実行可能。
    - 最大探索範囲や健全性チェックなど無限ループや誤データを防ぐ仕組みを導入。
  - ETL / pipeline（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを定義し、ETL 実行結果（取得数・保存数・品質問題・エラーなど）を集約。
    - 差分更新・バックフィル・品質チェック（quality モジュール連携）を想定した ETL 設計方針とユーティリティ関数を実装。  
    - jquants_client の save_* 系関数を利用して idempotent に保存する設計を想定。
  - jquants_client 等のクライアントはデータ取得/保存インターフェースとして想定（モジュール参照あり）。

- リサーチ（src/kabusys/research/）
  - factor_research（src/kabusys/research/factor_research.py）
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高変化率）、バリュー（PER、ROE）の計算関数を実装。
    - DuckDB を用いた SQL ベースの計算実装。データ不足時は None を返す設計。
    - 各関数は prices_daily / raw_financials テーブルのみ参照し、安全なローカル計算を保証。
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）: target_date から指定ホライズンのリターンを一括クエリで取得可能。
    - IC 計算（calc_ic）: スピアマンランク相関（ランク化は平均ランクを使用）を実装。データ不足時は None。
    - ランク変換ユーティリティ（rank）: ties は平均ランクで扱う実装、丸めで ties 検出漏れを防止。
    - ファクター統計サマリー（factor_summary）: count/mean/std/min/max/median を算出。
  - data.stats モジュールからの zscore_normalize の再エクスポート（src/kabusys/research/__init__.py）。
  - research パッケージの公開 API を __all__ で整理。

Changed
- （初期リリースにつき該当なし）

Fixed
- （初期リリースにつき該当なし）

Deprecated
- （初期リリースにつき該当なし）

Removed
- （初期リリースにつき該当なし）

Security
- OpenAI API キーは関数引数で注入可能（テスト容易性）かつ環境変数 OPENAI_API_KEY から取得する設計。必須未設定時は ValueError を送出して誤用を防止。

Notes / Implementation details
- すべてのモジュールで「datetime.today()/date.today() を直接参照しない」方針が守られており、ルックアヘッドバイアスを防ぐために target_date を明示的に受け取る設計になっています。
- DuckDB を利用した SQL 実行での互換性（空の executemany 回避や日付型変換）や、API 呼び出しの堅牢性（再試行・バックオフ・フォールバック値）に配慮した実装が行われています。
- OpenAI 呼び出しは JSON mode（response_format={"type":"json_object"}）を利用する前提でレスポンスパースや復元ロジックを備えています。
- ロギングが各所に配置され、フェイルセーフ時には WARNING/INFO/DEBUG により状況把握が可能です。

Acknowledgements
- この CHANGELOG はコードベースから推測して作成しています。実際のリリースノートに追加したい運用上の注意点や互換性の情報があれば追記してください。