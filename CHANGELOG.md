CHANGELOG
=========
（この CHANGELOG は Keep a Changelog の形式に準拠しています）

全般
----
- 本リポジトリは日本株自動売買システム "KabuSys" の初期公開的なリリース内容を記録しています。
- バージョンはパッケージ定義に合わせて 0.1.0 としています。

[0.1.0] - 2026-04-09
-------------------

Added
- パッケージ基盤
  - パッケージルート: src/kabusys/__init__.py により data, strategy, execution, monitoring を公開。
  - バージョン定義: __version__ = "0.1.0"。

- 環境設定 / 設定管理 (src/kabusys/config.py)
  - .env / .env.local による設定自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env のパースは export 形式やクォート内のエスケープ、行末コメント等に対応する堅牢な実装。
  - Settings クラスを実装し、以下のプロパティ等を提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
    - DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH
    - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
    - CPU/MEMORY/DISK 閾値、KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL 検証
  - 必須環境変数未設定時に ValueError を投げる _require() を提供。

- AI（ニュース NLP / レジーム判定） (src/kabusys/ai/)
  - news_nlp モジュール:
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）の JSON Mode でセンチメント評価。
    - バッチ処理（最大 20 銘柄 / API コール）、1 銘柄あたり記事数・文字数制限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - 再試行（429/ネットワーク/タイムアウト/5xx）に対する指数バックオフの実装。
    - レスポンスの厳密なバリデーション（JSON 抽出、results 配列、コード照合、数値チェック）、スコアを ±1.0 にクリップ。
    - DuckDB への書き込みは部分失敗を避けるため取得できたコードのみ DELETE→INSERT の冪等書き込み。
    - テスト容易性のため _call_openai_api の差し替え（モック）を想定。
    - calc_news_window(target_date) により JST 時刻ウィンドウを UTC naive datetime で返す（ルックアヘッド防止）。
  - regime_detector モジュール:
    - ETF 1321（日経225連動 ETF）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定。
    - LLM 呼び出しは gpt-4o-mini、JSON Mode、API キーは引数または環境変数 OPENAI_API_KEY で指定。
    - MA 計算・ニュース取得ではルックアヘッドを避ける設計（target_date 未満のデータのみ使用）。
    - API エラー時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）、リトライとバックオフを実装。
    - 計算結果は market_regime テーブルへ冪等（BEGIN / DELETE / INSERT / COMMIT）で書き込み。

- データプラットフォーム（src/kabusys/data/）
  - calendar_management:
    - JPX カレンダー管理（market_calendar）用のユーティリティを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar が未取得の場合は曜日ベースのフォールバック（週末を非営業日）を採用。
    - calendar_update_job を実装し、J-Quants API から差分取得して market_calendar を更新（バックフィル・健全性チェックを含む）。
  - pipeline / ETL:
    - ETLResult データクラスを実装し、ETL の取得数・保存数・品質問題・エラー概要を集約。
    - ETL 設計は差分更新、idempotent 保存（jquants_client の save_*）、品質チェック（quality モジュール）を前提とした構成。
    - デフォルトのバックフィル日数、最小データ日付等の定数を定義。
    - kabusys.data.etl で ETLResult を再エクスポート。

- リサーチ（src/kabusys/research/）
  - factor_research:
    - モメンタム（1M/3M/6M）、ma200 偏差、ATR（20 日）、流動性（20 日平均売買代金・出来高比）などのファクター計算機能を実装。
    - DuckDB の window 関数を活用し、target_date ベースで日付窓を限定して計算。
    - 欠損やデータ不足は None を返す設計で安全に扱う。
  - feature_exploration:
    - 将来リターン calc_forward_returns（デフォルト horizons=[1,5,21]）、IC（Information Coefficient）calc_ic、rank、factor_summary を提供。
    - pandas 等に依存せず純 Python + DuckDB で統計量・ランク・スピアマン ρ を算出。
  - kabusys.research パッケージは主要関数を __all__ で再公開（zscore_normalize の再エクスポート含む）。

Changed
- （初期リリースのため変更履歴はなし）

Fixed
- （初期リリースのため修正履歴はなし）

Notes / 備考
- ルックアヘッドバイアス対策の方針として、各モジュールは内部で datetime.today()/date.today() を直接参照せず、呼び出し側から target_date を受け取る設計になっています。
- OpenAI 呼び出しは gpt-4o-mini の JSON Mode を利用することを想定しており、API の失敗に対するフォールバック動作を多くの箇所で実装しています。テスト容易性のため API 呼び出し箇所はモック差し替えを想定した設計です。
- DuckDB の executemany に関する互換性対策（空リストの扱い等）に配慮した実装が行われています。
- .env の自動読み込みはプロジェクト配布後の環境でも安定して動作するよう、__file__ を基準にプロジェクトルートを探索します。

ライセンスや既知の制約、互換性に関する注記は別ドキュメント（README / DataPlatform.md / StrategyModel.md 等）を参照してください。