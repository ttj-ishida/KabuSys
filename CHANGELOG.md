Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記録されています。
このプロジェクトは [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の方針に従います。

[Unreleased]

0.1.0 - 2026-04-03
------------------

初回リリース（初期実装）。主要な機能・モジュールを追加しました。

Added
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = 0.1.0）。
  - パッケージの公開モジュール一覧を __all__ で定義（data, strategy, execution, monitoring）。

- 設定・環境変数管理（kabusys.config）
  - .env ファイル自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
  - .env のパースを独自実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ対応、行コメントの扱い等）。
  - .env と .env.local の読み込み順序を実装：OS 環境変数 > .env.local > .env。OS 環境変数は保護（上書き不可）。
  - 自動ロードを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加（テスト用途）。
  - Settings クラスを実装し、J-Quants / kabu API / LINE / DB パス / 監視閾値 / ログ・環境設定等のプロパティを提供。
  - KABUSYS_ENV と LOG_LEVEL の検証（許可値チェック）および is_live / is_paper / is_dev のユーティリティを実装。
  - 必須環境変数未設定時に明示的なエラーを返す _require 関数を追加。

- AI（自然言語処理）機能（kabusys.ai）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - score_news(conn, target_date, api_key=None)：raw_news / news_symbols からニュースを銘柄別に集約し、OpenAI（gpt-4o-mini, JSON mode）へバッチ送信して ai_scores テーブルへ書き込み。
    - タイムウィンドウ計算（calc_news_window）：JST 基準で前日15:00〜当日08:30 に対応する UTC 範囲を算出。
    - バッチ処理（最大20銘柄/チャンク）、1銘柄あたりの記事数・文字数制限（_max_articles_per_stock/_max_chars_per_stock）。
    - API 呼び出しは 429/ネットワーク/タイムアウト/5xx を対象に指数バックオフでリトライ。その他のエラーはスキップして継続（フェイルセーフ）。
    - レスポンスの厳密バリデーション（JSON 抽出、results 配列、各項目の型検証、既知コードのみ採用、数値チェック）。
    - スコアは ±1.0 にクリップ。部分失敗に備え、書き込みは対象コードのみを DELETE→INSERT（冪等性確保、既存スコア保護）。
    - テストしやすさのため _call_openai_api を差し替え可能に設計。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - score_regime(conn, target_date, api_key=None)：ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して market_regime テーブルへ書き込み。
    - ma200_ratio の計算（_calc_ma200_ratio）：target_date 未満のデータのみ使用してルックアヘッドを防止。データ不足時は中立判定（1.0）。
    - マクロキーワードによるニュース抽出（_fetch_macro_news）、LLM 呼び出しと JSON パース、リトライ／フォールバック（失敗時 macro_sentiment=0.0）。
    - スコア合成後、label を bull/neutral/bear に分類して DB に冪等書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時 ROLLBACK）。

- リサーチ（kabusys.research）
  - factor_research：calc_momentum / calc_volatility / calc_value を実装。
    - モメンタム：1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None）。
    - ボラティリティ：20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率（欠損時の扱いに注意）。
    - バリュー：最新の raw_financials と株価を結合して PER / ROE を計算（EPS=0/NULL の場合は None）。
    - いずれも DuckDB の SQL ウィンドウ関数を活用し、date/code をキーとするリスト（dict）を返す。
  - feature_exploration：calc_forward_returns（複数ホライズン対応、入力検証含む）、calc_ic（Spearman ランク相関）、rank（平均ランク処理）、factor_summary（count/mean/std/min/max/median）を実装。
  - research パッケージの __all__ に主要関数を公開。zscore_normalize を data.stats から再エクスポート。

- データ基盤（kabusys.data）
  - calendar_management：JPX カレンダー管理と営業日ロジックを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - market_calendar の登録値を優先し、未登録日は曜日（平日）をフォールバックとして一貫性を保つ設計。
    - calendar_update_job(conn, lookahead_days)：J-Quants クライアント経由で差分取得し market_calendar に冪等保存。バックフィルと健全性チェック（過度な未来日を検出してスキップ）を実装。
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult dataclass を実装（取得数 / 保存数 / 品質問題 / エラー等を格納）。to_dict メソッドで品質問題を辞書化。
    - ETL の補助ユーティリティ（テーブル存在チェック、最大日付取得など）を実装。
  - etl モジュールで ETLResult を再エクスポート。

- エラーハンドリング・ログ
  - 各処理は可能な限りフェイルセーフに設計（OpenAI/API エラーや部分失敗時もプロセス継続）。
  - DB 書き込みは冪等性を考慮（DELETE→INSERT、トランザクション、ROLLBACK の保護ログ）。
  - 重要箇所に詳細な logger 出力を追加（INFO / WARNING / DEBUG）。

Changed
- 設計方針（全体）
  - ルックアヘッドバイアス対策のため、各所で datetime.today()/date.today() の直接参照を避け、呼び出し側から target_date を受け取る設計を採用。
  - DuckDB の制約（executemany の空リスト扱い等）を考慮した実装の調整。

Fixed
- （初回リリースのため該当なし）

Security
- OpenAI API キーは引数で注入可能（テスト容易性）かつ環境変数 OPENAI_API_KEY から取得。未提供時は明示的に ValueError を送出して誤使用を防止。

Notes / 注意事項
- OpenAI 呼び出しは gpt-4o-mini と JSON Mode を想定した実装。API 仕様や SDK 変更により挙動が変わる可能性があるため、テスト時は _call_openai_api をモックすることを推奨します。
- DuckDB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials, market_regime 等）が前提です。実行前にスキーマ準備を行ってください。
- 環境変数読み込みはプロジェクトルート探索に依存するため、配布後や別配置での使用時は KABUSYS_DISABLE_AUTO_ENV_LOAD の利用や明示的な環境設定を検討してください。

将来の予定（例）
- strategy / execution / monitoring 周りの実装（現状パッケージエントリは公開されているが実装は今後拡充予定）。
- ai モジュールの評価用メトリクスやキャッシュ、追加の品質チェック拡張。

以上。