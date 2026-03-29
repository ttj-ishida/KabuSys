# Keep a Changelog

すべての互換性のある変更は、セマンティックバージョニングに従って記録します。  
このファイルは主に人間向けであり、将来のリリースでの差分確認に用います。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-03-29

初回リリース。日本株自動売買プラットフォームの基盤機能を実装しました。  
主にデータ取得・ETL・マーケットカレンダー管理・ファクター計算・ニュースNLP・市場レジーム判定・設定管理を含みます。

### Added
- パッケージ基本情報
  - `kabusys` パッケージを追加。バージョン: `0.1.0`。
  - パッケージ公開 API: `data`, `strategy`, `execution`, `monitoring` を `__all__` で定義。

- 環境設定 / 設定管理
  - `kabusys.config` モジュールを追加。
    - .env 自動ロード機能（プロジェクトルートを .git または pyproject.toml で探索）。
    - .env / .env.local の読み込み順序と上書きルール（OS 環境変数を保護）。
    - エントリ行の詳細なパース（コメント、export プレフィックス、クォート/エスケープ処理対応）。
    - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` に対応。
    - `Settings` クラスを提供し、主要設定をプロパティ経由で取得:
      - J-Quants: `jquants_refresh_token` (`JQUANTS_REFRESH_TOKEN` 必須)
      - kabuステーション: `kabu_api_password`, `kabu_api_base_url`（デフォルト値あり）
      - Slack: `slack_bot_token`, `slack_channel_id`（必須）
      - DB パス: `duckdb_path`, `sqlite_path`（デフォルトパスあり）
      - 環境種別検証: `env`（development/paper_trading/live の検証）
      - ログレベル検証: `log_level`（DEBUG/INFO/WARNING/ERROR/CRITICAL）
      - 簡易判定ヘルパ: `is_live` / `is_paper` / `is_dev`

- データ取得 / ETL
  - `kabusys.data.pipeline` モジュールを追加。
    - ETL のための `ETLResult` データクラス（target_date、取得/保存件数、品質問題、エラー集約など）。
    - 差分取得・バックフィル・カレンダー先読み等の設計に対応する定数とヘルパ関数。
    - DuckDB テーブルの最終日取得ユーティリティ等を実装。
    - DuckDB バインド互換性に関する注意（executemany の空リスト制約）を考慮。
  - `kabusys.data.etl` から `ETLResult` を再エクスポート。

- マーケットカレンダー管理
  - `kabusys.data.calendar_management` を追加。
    - 営業日判定・前後営業日取得・期間の営業日リスト取得:
      - `is_trading_day(conn, d)`
      - `next_trading_day(conn, d)`
      - `prev_trading_day(conn, d)`
      - `get_trading_days(conn, start, end)`
      - `is_sq_day(conn, d)`
    - JPX カレンダーの夜間差分更新ジョブ `calendar_update_job(conn, lookahead_days=90)` を実装。
    - DB にデータがない場合は曜日ベース（土日非営業）でフォールバックする堅牢な設計。
    - バックフィル、先読み、健全性チェック（将来日付の異常検知）に対応。

- ニュース NLP（AI）
  - `kabusys.ai.news_nlp` を追加。
    - ニュース収集ウィンドウ計算: `calc_news_window(target_date)`（JST基準のウィンドウを UTC naive datetime で返す）。
    - `score_news(conn, target_date, api_key=None)`:
      - `raw_news` と `news_symbols` を用いて記事を銘柄毎に集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出。
      - バッチ処理（最大 20 銘柄 / チャンク）、1 銘柄あたりの記事数/文字数上限（トリム）あり。
      - API の 429/ネットワーク/タイムアウト/5xx に対して指数バックオフでリトライ。
      - レスポンスの JSON バリデーションとスコアの ±1.0 クリッピング。
      - 成功した銘柄のみ `ai_scores` テーブルへ（DELETE→INSERT の冪等更新）。
      - API キー未設定時は `ValueError` を送出。
    - テスト容易性のため、内部の OpenAI 呼び出しを差し替え可能に設計（ユニットテストで patch 可能）。

- 市場レジーム判定（AI + 指標合成）
  - `kabusys.ai.regime_detector` を追加。
    - ETF 1321（日経225連動型）を用いた 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）の合成により日次でレジーム（bull/neutral/bear）を判定。
    - 主な公開 API: `score_regime(conn, target_date, api_key=None)`。market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - マクロキーワードで `raw_news` をフィルタしてタイトルリストを作成、OpenAI（gpt-4o-mini）へ投げて -1.0〜1.0 のスコアを取得。
    - API 失敗時はマクロスコアを 0.0 とするフェイルセーフ（例外を上げず処理継続）。
    - OpenAI 呼び出しは独立実装でモジュール間結合を低減。再試行ロジックあり。

- リサーチ / ファクター計算
  - `kabusys.research.factor_research` を追加。
    - モメンタム: `calc_momentum(conn, target_date)`（1M/3M/6M リターン、ma200 乖離）。
    - ボラティリティ/流動性: `calc_volatility(conn, target_date)`（ATR20, ATR比率, 平均売買代金, 出来高比率）。
    - バリュー: `calc_value(conn, target_date)`（PER, ROE。raw_financials から最新財務を参照）。
    - いずれも DuckDB の SQL ウィンドウ関数を活用して高速集計。
  - `kabusys.research.feature_exploration` を追加。
    - 将来リターン算出: `calc_forward_returns(conn, target_date, horizons=None)`（デフォルト：[1,5,21]）。
    - IC 計算（Spearman の ρ）: `calc_ic(factor_records, forward_records, factor_col, return_col)`.
    - ランク変換ユーティリティ: `rank(values)`（同順位は平均ランク）。
    - 統計サマリー: `factor_summary(records, columns)`（count, mean, std, min, max, median）。
  - `kabusys.research.__init__` で主要関数を再エクスポート。`kabusys.data.stats.zscore_normalize` を再エクスポート。

- DB / トランザクション
  - DuckDB を用いる設計で、各種書き込み処理は冪等性（DELETE→INSERT）やトランザクション BEGIN/COMMIT/ROLLBACK を明示的に扱う。
  - ROLLBACK 失敗時のログ出力など堅牢性を確保。

### Changed
- 初版のため該当なし。

### Fixed
- 初版のため該当なし。

### Security
- OpenAI API キーや各種トークンは環境変数経由で管理する設計（ex: `OPENAI_API_KEY`, `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`）。  
- .env 自動ロードで OS 環境変数を保護する挙動を実装。

### Notes / 既知の注意点
- AI 機能（news_nlp, regime_detector）は OpenAI SDK（gpt-4o-mini）を利用。API 呼び出しの実行には適切な API キーと料金設定が必要です。
- AI 関連関数は API 失敗時にフォールバックする設計だが、外部 API の長期不調時は結果欠損を招きます。
- `ETLResult` 等で品質チェック（quality モジュール）は呼び出し側での評価を前提とします（Fail-Fast しない設計）。
- DuckDB のバージョン依存:
  - `executemany` に空リストを渡すとエラーとなるバージョン（例: DuckDB 0.10）の互換性を考慮して、空チェックを行っています。
- ルックアヘッドバイアス防止:
  - 全体的に `datetime.today()` / `date.today()` をスコア計算ロジック中で直接参照しない方針。関数は明示的な `target_date` を引数に取り、過去データのみを参照します。
- テスト設計:
  - OpenAI 呼び出しは内部関数を patch してモック可能（ユニットテストを容易にするため）。

### Migration / Setup
- 初期利用時は以下テーブル/データの準備が必要:
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials など。
- 環境変数例:
  - OPENAI_API_KEY（AI機能使用時必須）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - DUCKDB_PATH, SQLITE_PATH（任意。デフォルト: data/kabusys.duckdb / data/monitoring.db）
- 自動 .env ロードはプロジェクトルート（.git or pyproject.toml）を起点に行われます。CI 等で無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

今後のリリースでは、戦略エンジン（strategy モジュール）・実行（execution）・監視（monitoring）・より細かな品質チェックと UI/CLI ツールの追加、並びにモデル・プロンプト改善やパフォーマンス最適化を予定しています。