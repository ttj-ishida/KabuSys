# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-04-09

初回リリース。日本株自動売買システム「KabuSys」の基盤機能を実装しました。主な追加点、設計方針、フェイルセーフやテストフック等を以下にまとめます。

### 追加 (Added)
- パッケージ初期化
  - パッケージ名: kabusys、バージョン `0.1.0` を定義（src/kabusys/__init__.py）。
  - 公開サブパッケージ: data, strategy, execution, monitoring を __all__ としてエクスポート。

- 環境設定管理 (src/kabusys/config.py)
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - .env パーサ実装: export プレフィックス、クォート（シングル/ダブル）とエスケープ、コメント処理に対応。
  - 環境変数取得ユーティリティ Settings を提供:
    - JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等の必須値取得（未設定時に ValueError を投げる _require）。
    - KABU_API_BASE_URL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID の既定値/空文字許容。
    - DB パス設定 (DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH) を Path 型で提供。
    - PAPER_FILL_MODE の値検証（instant/partial/never/reject）。
    - 監視用設定（PID ファイル、KILL フラグ、リソース閾値）を提供。
    - KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL の検証プロパティ。
    - is_live / is_paper / is_dev のショートハンド。

- AI (自然言語処理) モジュール (src/kabusys/ai)
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - calc_news_window(target_date) により JST ベースのニュース収集ウィンドウを計算（UTC naive datetime を返す）。
    - score_news(conn, target_date, api_key=None)
      - raw_news / news_symbols を銘柄ごとに集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメントを ai_scores テーブルへ書き込む。
      - バッチ処理: 最大 20 銘柄/コール、1 銘柄あたり最大 10 記事、最大 3000 文字でトリム。
      - 再試行戦略: 429・ネットワーク断・タイムアウト・5xx に対して指数バックオフ（最大リトライ回数設定）。
      - レスポンスの厳密バリデーション（JSON 抽出、"results" 配列、code と score の検査、スコアを ±1.0 にクリップ）。
      - DuckDB への書き込みは部分失敗に配慮して、取得できたコードのみ DELETE → INSERT を実行。
      - テスト容易性: _call_openai_api を patch 可能（unittest.mock.patch 推奨）。
      - API キーの注入は引数または環境変数 OPENAI_API_KEY。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成し、日次で 'bull'/'neutral'/'bear' を判定。
    - _calc_ma200_ratio: target_date 未満のデータのみを使用しルックアヘッドを防止、データ不足時は中立 (1.0) を返す。
    - _fetch_macro_news: raw_news からマクロキーワード（日本・米国・グローバルの主要語）でタイトルを抽出。
    - _score_macro: LLM 呼び出し（gpt-4o-mini）して macro_sentiment を算出。API 失敗時は 0.0 にフォールバックするフェイルセーフ。
    - score_regime は合成スコアを計算し market_regime テーブルへ冪等的に書き込む（BEGIN/DELETE/INSERT/COMMIT）。API キーは引数または環境変数で解決。

- データ基盤 (src/kabusys/data)
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを利用した営業日判定 API: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - DB 登録がない場合は曜日ベースのフォールバック（土日が非営業日）。
    - next/prev_trading_day は最大探索期間を設定して無限ループ防止（_MAX_SEARCH_DAYS）。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等保存、バックフィル（日数）や健全性チェックを実装。
    - jquants_client（外部モジュール）とのインタフェース利用を想定（fetch_market_calendar / save_market_calendar）。
  - ETL パイプライン（src/kabusys/data/pipeline.py）
    - ETLResult dataclass を実装（取得数/保存数/品質問題/エラー一覧を含む）。
    - 差分更新、backfill、品質チェックを行う設計方針をドキュメント化。
    - ETLResult.to_dict で品質問題を辞書化してログ等に利用可能。
  - etl モジュールは ETLResult を再エクスポート（src/kabusys/data/etl.py）。

- リサーチ（src/kabusys/research）
  - factor_research.py
    - calc_momentum: mom_1m/mom_3m/mom_6m と ma200_dev（200日移動平均乖離）を計算。
    - calc_volatility: 20日 ATR、ATR 比率（atr_pct）、20日平均売買代金、出来高比等を計算。
    - calc_value: raw_financials から最新財務を取得して PER（EPS が 0/欠損の場合は None）、ROE を計算。
    - 全関数は DuckDB の prices_daily / raw_financials のみ参照し、外部 API へはアクセスしない設計。
  - feature_exploration.py
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得する SQL 実装。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装。利用可能レコードが 3 未満の場合は None。
    - rank: 同順位は平均ランクを割り当てる実装（丸めにより ties 判定を安定化）。
    - factor_summary: count/mean/std/min/max/median の統計サマリを実装。
  - research パッケージ初期化で主要ユーティリティを公開。

### 変更 (Changed)
- 設計方針の明確化（ドキュメント文字列内で明示）
  - ルックアヘッドバイアス回避のため、datetime.today()/date.today() をスコア算出等のコアロジック内で直接参照しない方針を採用。target_date 引数ベースで処理。
  - DuckDB の互換性を考慮し、executemany に空リストを渡さないコードパスを採用（DuckDB 0.10 の挙動回避）。

### 修正 (Fixed)
- DB 書き込み時のトランザクション管理
  - calendar_update_job / score_news / score_regime などで BEGIN/COMMIT/ROLLBACK を利用し、ROLLBACK 失敗時の警告ログ出力を追加。
- API エラー処理の強化
  - OpenAI 呼び出しのエラー分類（RateLimitError / APIConnectionError / APITimeoutError / APIError）に応じたリトライ／フォールバックロジックを導入。
  - JSON パース失敗や形式不正時は例外を投げずに警告してフェイルセーフ（スコア 0.0 またはスキップ）を行う。

### 注意 (Notes)
- テストフック:
  - news_nlp._call_openai_api, regime_detector._call_openai_api を unittest.mock.patch で差し替えて API 呼び出しをモック可能。
- DB スキーマ前提:
  - コードは prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials などのテーブル存在を前提としている（スキーマは DataPlatform.md / StrategyModel.md を参照する想定）。
- フェイルセーフ方針:
  - LLM/API の失敗はシステム全体を停止させず、デフォルト値（中立スコア・スキップ）で継続する設計。
- 環境変数の自動ロードはプロジェクトルートの検出に依存するため、パッケージ配布後や特殊環境下で問題が発生する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効化してください。

### 既知の破壊的変更 (Breaking Changes)
- 初版のため該当なし。

### セキュリティ (Security)
- 初版のため公開中のセキュリティフィックスはなし。ただし、OpenAI API キーや外部トークンは環境変数で管理することを推奨。

---

タグやリリース情報は今後の開発で追加・更新してください。README や各モジュールのドキュメントにある設計方針（DataPlatform.md / StrategyModel.md 参照）に従って拡張できます。