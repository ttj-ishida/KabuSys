# CHANGELOG

すべての重大な変更を記録します。本ファイルは Keep a Changelog の形式に準拠します。  
日付はリリース日を示します。

全般方針:
- 変更は利用者に影響があるものを中心に記載しています（内部実装の微細なリファクタ等は省略）。
- 本プロジェクトは DuckDB をデータ層に用い、OpenAI（gpt-4o-mini）を NLP に利用します。  
- 設計上の重要な安全策（ルックアヘッドバイアス回避、冪等書き込み、APIフェイルセーフ等）は明記しています。

## [Unreleased]
- 開発中の変更はここに記載します。

## [0.1.0] - 2026-03-27
初回公開リリース。

### Added
- パッケージ基本情報
  - kabusys パッケージの公開 API を定義（src/kabusys/__init__.py）。
  - バージョン情報: 0.1.0。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動ロードする仕組みを実装。
  - .env のパース機能を独自実装（コメント、export プレフィックス、クォート・エスケープ処理、行無視等に対応）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを提供し、アプリで利用する各種必須/任意設定値をプロパティとして公開（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, DUCKDB_PATH 等）。
  - KABUSYS_ENV / LOG_LEVEL の入力検証（許容値チェック）とユーティリティプロパティ（is_live, is_paper, is_dev）。

- ニュースNLP（src/kabusys/ai/news_nlp.py）
  - raw_news / news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini、JSON mode）で銘柄別センチメント（-1.0〜1.0）を算出して ai_scores テーブルへ書き込み。
  - タイムウィンドウ計算（JST基準の前日15:00〜当日08:30 → UTC に変換）を提供（calc_news_window）。
  - バッチ処理（最大 20 銘柄/チャンク）、1銘柄あたり最大記事数・文字数制限（肥大化対策）を実装。
  - API 呼び出しのリトライ（429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ）を実装。失敗時はスキップして継続するフェイルセーフ挙動。
  - レスポンスの厳密なバリデーションとスコアのクリッピング（±1.0）。
  - DuckDB の互換性を考慮した DB 書き込み（部分失敗時に他銘柄スコアを保護するため、該当コードのみ DELETE → INSERT）。

- 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定し、market_regime テーブルへ冪等書き込み。
  - macro_sentiment の取得にはニュースタイトルの抽出（マクロキーワードフィルタ）と OpenAI 呼び出しを行う。記事が無い場合は LLM 呼び出しを行わず macro_sentiment=0.0 を使用。
  - OpenAI 呼び出しは最大リトライ回数を設け、失敗時は macro_sentiment=0.0 にフェイルバックする安全策を採用。
  - ルックアヘッド防止のため、内部で datetime.today()/date.today() を参照しない実装方針を明記。

- 研究（research）モジュール（src/kabusys/research/*）
  - ファクター計算（factor_research.py）
    - Momentum: 1M/3M/6M リターン、200日 MA 乖離。
    - Volatility: 20日 ATR（および相対 ATR）、20日平均売買代金、出来高比率。
    - Value: PER、ROE（raw_financials から取得）。
    - すべて DuckDB の prices_daily / raw_financials を参照する安全な計算（外部 API にはアクセスしない）。
    - 欠損・不足データ時の None 処理。
  - 特徴量探索（feature_exploration.py）
    - 将来リターン計算（calc_forward_returns、複数ホライズン対応、入力検証）。
    - IC（Information Coefficient）計算（Spearman の ρ、rank ユーティリティ含む）。
    - ファクター統計サマリー（count/mean/std/min/max/median）。
  - zscore_normalize を data.stats から再エクスポート。

- データ（data）モジュール（src/kabusys/data/*）
  - マーケットカレンダー管理（calendar_management.py）
    - market_calendar テーブルを使った営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録ありの場合は DB 値優先、未登録日は曜日ベースのフォールバック（土日非営業）。
    - 夜間バッチ calendar_update_job を実装（J-Quants から差分取得、バックフィル、健全性チェック、冪等保存）。
    - 最大探索日数やバックフィル日数などの安全パラメータを設定。
  - ETL パイプライン（pipeline.py, etl.py）
    - ETLResult データクラスを公開（etl.py 経由で ETLResult をエクスポート）。
    - 差分取得・保存・品質チェックのための基盤を実装（jquants_client 経由で API を呼び、quality モジュールでチェック）。
    - ETL の戻り値に品質問題やエラー概要を含める仕組みを提供。
    - 初期ロードの開始日、バックフィル既定値、DuckDB テーブルの最大日取得ユーティリティ等を実装。
  - DuckDB との互換性考慮（executemany における空リスト禁止への対処など）。

- テスト・開発補助
  - OpenAI 呼び出し部分に対してテスト時に差し替え可能なフックを用意（各モジュールの _call_openai_api は patch 可能とドキュメント化）。

### Changed
- 初回リリースのため履歴上の変更はありません。

### Fixed
- 初回リリースのため既知のバグ修正履歴はありません。

### Security
- OpenAI API キーや各種トークンは環境変数経由で取り扱う設計。
- 必須環境変数が未設定の場合は明示的に ValueError を送出することで、安全性を確保。

### Notes / Implementation details（重要な設計選択）
- ルックアヘッドバイアス回避:
  - AI/スコアリング・研究系処理では datetime.today()/date.today() を直接参照せず、外部から target_date を与える方式。
  - DB クエリは target_date より前のデータのみ参照する（半開区間等を明示）。
- フェイルセーフ:
  - OpenAI 呼び出しの失敗は致命的例外にせず、該当スコアを 0.0 にフォールバックまたは該当チャンクをスキップして処理を継続する設計。
- 冪等書き込み:
  - market_regime / ai_scores 等への書き込みは既存行を削除してから INSERT することで冪等性を担保。
- DuckDB 互換性:
  - executemany に空リストを与えないチェックや、日付型の取り扱い変換ユーティリティを用意（複数 DuckDB バージョンの差異を吸収）。

---

参考: 各モジュールの詳細はソース内の docstring に設計方針や処理フローを記載しています。今後のリリースでは API 互換の変更や機能追加（例: PBR/配当利回りの実装、追加の品質チェックルール、発注・実行モジュールの統合など）を記録します。