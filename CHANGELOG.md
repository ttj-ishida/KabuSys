# Changelog

すべての注目すべき変更はここに記録します。  
このプロジェクトは Keep a Changelog の形式に従います。  

※ 初回リリースの内容はコードベースから推測して記載しています。

## [Unreleased]
- 今のところ未定義の変更はありません。

## [0.1.0] - 2026-04-03
初回リリース

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - サブパッケージ公開: data, research, ai, execution, strategy, monitoring（__all__ により意図的な公開APIを定義）。

- 設定・環境変数管理 (kabusys.config)
  - .env / .env.local 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索して特定）。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env パース機能: コメント行、export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント判定等に対応。
  - Settings クラスを提供し、主要な環境変数をプロパティで取得:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
    - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
    - KABUSYS_ENV (development / paper_trading / live)
    - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
  - 必須 env が未設定の場合は ValueError を発生させる _require() を実装。

- AI モジュール (kabusys.ai)
  - ニュース NLP (kabusys.ai.news_nlp)
    - raw_news + news_symbols を使用して銘柄ごとのニューステキストを集約し、OpenAI（gpt-4o-mini, JSON mode）へバッチ送信してセンチメントを算出。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB と比較）。
    - チャンク処理: 最大 20 銘柄/回、1銘柄あたり最大 10 記事・3000文字でトリム。
    - リトライ: 429/ネットワーク/タイムアウト/5xx に対して指数バックオフでリトライ。
    - レスポンス検証: JSON パース、"results" 配列、code/score の存在と型検査、既知コードのみ採用、スコアを ±1.0 にクリップ。
    - 書き込みは冪等処理（DELETE → INSERT）で部分失敗時に既存スコアを保護。
    - score_news(conn, target_date, api_key=None) を公開。戻り値は書き込んだ銘柄数。
    - API キーが未設定の場合は ValueError。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロ経済ニュースの LLM センチメント（重み30%）を合成して日次でレジーム（bull/neutral/bear）判定を実装。
    - マクロニュースは news_nlp.calc_news_window で定義されたウィンドウからマクロキーワードでフィルタ。
    - OpenAI 呼び出しは専用のクライアント呼び出しを使用。失敗時は macro_sentiment=0.0 にフォールバック（例外を投げず処理継続）。
    - API リトライ・バックオフ処理を実装。
    - 計算後は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - score_regime(conn, target_date, api_key=None) を公開。成功時は 1 を返す。API キー未設定で ValueError。

- データ基盤 (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - JPX カレンダーを扱うユーティリティを実装: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - market_calendar テーブルがない場合は曜日ベースのフォールバック（土日を非営業日扱い）。
    - next/prev/search の最大探索日数を上限化して無限ループを防止。
    - calendar_update_job(conn, lookahead_days=90) により J-Quants から差分取得 → 保存（fetch_market_calendar / save_market_calendar を jquants_client 経由で想定）。バックフィル／健全性チェックあり。
  - ETL パイプライン (kabusys.data.pipeline)
    - ETL 実行結果を表す ETLResult dataclass を追加（品質チェック結果、取得件数、保存件数、エラー一覧を含む）。to_dict() により品質問題を dict に変換。
    - 差分取得・保存・品質チェックの実装方針に対応（コード上ではユーティリティ関数と定数を提供）。
    - _table_exists, _get_max_date などの内部ユーティリティを実装。

- リサーチ（kabusys.research）
  - ファクター計算 (kabusys.research.factor_research)
    - モメンタム: calc_momentum(conn, target_date)（1M/3M/6M リターン、ma200_dev）
    - ボラティリティ/流動性: calc_volatility(conn, target_date)（20日 ATR、相対 ATR、20日平均売買代金、出来高比率）
    - バリュー: calc_value(conn, target_date)（PER, ROE を raw_financials から取得）
    - DuckDB SQL を活用し、結果を list[dict] で返却。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - 将来リターン: calc_forward_returns(conn, target_date, horizons=None)（デフォルト [1,5,21]）
    - IC 計算: calc_ic(factor_records, forward_records, factor_col, return_col)（スピアマンのランク相関）
    - ランク変換ユーティリティ: rank(values)
    - 統計サマリー: factor_summary(records, columns)（count/mean/std/min/max/median）
    - 外部ライブラリに依存せず標準ライブラリのみで実装（pandas 未使用）。

### 変更点 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 注意事項 / 設計上の重要ポイント (Notes)
- ルックアヘッドバイアス対策
  - AI 系処理およびファクター計算は内部で datetime.today()/date.today() を直接参照せず、明示的に渡された target_date を基準に処理するよう設計されています。これにより学習・検証時のルックアヘッドを防止します。
- LLM 呼び出しのフェイルセーフ
  - OpenAI API 呼び出しの失敗は基本的にスコアを 0.0 にフォールバックするか（regime_detector/news_nlp の場合）、該当チャンクをスキップする設計です。致命的な例外は抑制され、処理を継続します。
- 冪等性
  - データベース書き込みは可能な限り冪等になるよう実装（DELETE → INSERT、ON CONFLICT 想定）。ETL/カレンダー更新もバックフィルと上書き戦略を採用。
- OpenAI API の取扱い
  - OpenAI クライアントには環境変数 OPENAI_API_KEY を利用可能。各公開関数は api_key を引数で注入可能（テスト容易化）。
  - 使用モデルは gpt-4o-mini、JSON mode を前提にしてレスポンスをパースします。出力の堅牢化のため余計な前後テキストの除去ロジックも実装。
- DuckDB 前提
  - 多数の SQL は DuckDB を前提に書かれており、特に executemany の空リスト制約等への対策が含まれます（DuckDB 0.10 想定）。

### 既知の制約・未実装（今後の検討事項）
- raw_financials から PBR・配当利回りは未実装（calc_value 内の注記）。
- jquants_client（jquants_client.fetch_market_calendar / save_market_calendar 等）の実装はこの差分に含まれていません（別モジュールとして想定）。
- LINE / kabu ステーション周りの実際の送信・発注ロジックはこの差分では未提示（設定変数は用意済み）。

### 移行 / 導入手順 (Migration / Setup)
- 環境変数を用意:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
  - OpenAI を利用する場合: OPENAI_API_KEY（または score_* 関数へ api_key を渡す）
  - その他: KABUSYS_ENV 等（デフォルト値あり）
- .env/.env.local をプロジェクトルートに配置すると自動で読み込まれます（必要に応じ KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化可能）。
- DuckDB のデータベース（デフォルト path: data/kabusys.duckdb）に必要なテーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等）を準備してください。
- OpenAI のレスポンス形式は JSON を期待するため、レスポンス不正時は該当チャンクがスキップされます。API レート制限やネットワーク不安定性に対するリトライ実装がありますが、運用側でも適切な API クォータ管理を推奨します。

---

作成・更新に関する問い合わせやバグ報告はリポジトリの issue にお願いします。