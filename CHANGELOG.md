# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

履歴は降順（新しいものが上）です。

## [Unreleased]

（今後の変更をここに記載）

## [0.1.0] - 初期リリース
初期リリース。以下の主要機能・API を実装しています。

### 追加
- パッケージ基礎
  - パッケージ初期化を実装（kabusys.__init__）。公開サブパッケージ: data, research, ai, execution, monitoring, strategy（__all__ に含む）。
  - パッケージバージョン: 0.1.0（kabusys.__version__）。

- 設定 / 環境変数管理（kabusys.config）
  - .env ファイルや環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env 読込機能:
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して特定（CWD 非依存）。
    - 読込順序: OS 環境変数 > .env.local > .env。OS 環境変数は保護され、.env で上書きされない。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化可能。
  - .env パーサーは export 句、クォート文字列、エスケープ、インラインコメント（条件付き）などに対応。
  - 必須変数未設定時は _require() により ValueError を発生させる（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）。
  - 一部設定値に対するバリデーション（KABUSYS_ENV の有効値、LOG_LEVEL の有効値）を実装。
  - デフォルトパスの提供（DUCKDB_PATH, SQLITE_PATH 等）。

- AI 関連（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して、銘柄ごとにニュースを結合し OpenAI（gpt-4o-mini）へ送信してセンチメントを取得。
    - タイムウィンドウ計算（JST 基準の前日 15:00 ～ 当日 08:30 を UTC に変換）を calc_news_window で提供。
    - バッチ処理（最大 20 銘柄/chunk）、1 銘柄あたりの記事数・文字数制限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - リトライ方針: 429（RateLimit）・ネットワーク断・タイムアウト・5xx は指数バックオフでリトライ。その他エラーはスキップ。
    - レスポンスの厳密なバリデーション: JSON 抽出、results 配列の存在、各要素に code と score、既知コードとの照合、数値チェック、スコアを ±1.0 にクリップ。
    - 対象スコアの DB 書き込みは冪等（DELETE → INSERT）で行い、部分失敗時に既存スコアを消さない工夫。
    - OpenAI 呼び出しを差し替え可能にしてテストを容易化するフックを用意（_call_openai_api を unittest.mock.patch で差し替え可）。
    - Public API: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。OpenAI API キーがない場合は ValueError。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、日次でレジーム（bull / neutral / bear）を判定。
    - マクロニュースは news_nlp.calc_news_window で決定されるウィンドウから取得し、マクロキーワードでフィルタ。
    - OpenAI 呼び出しは専用実装（news_nlp とプライベート関数を共有しない設計）。
    - API エラー時やパース失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - 計算結果は market_regime テーブルに冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。エラー時は ROLLBACK を試み、失敗ログ出力。
    - Public API: score_regime(conn, target_date, api_key=None) → 1（成功）を返す。OpenAI API キー未設定時は ValueError。

- Research（kabusys.research）
  - factor_research
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR、相対 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER、ROE）を計算する関数を実装。
    - 関数:
      - calc_momentum(conn, target_date) → 各銘柄の mom_1m, mom_3m, mom_6m, ma200_dev を返す。
      - calc_volatility(conn, target_date) → atr_20, atr_pct, avg_turnover, volume_ratio を返す。
      - calc_value(conn, target_date) → per, roe を返す（raw_financials を参照）。
    - データ不足時の挙動: 十分な履歴が不足している場合は None を返す設計。
    - DuckDB のウィンドウ関数を活用して効率的に計算。

  - feature_exploration
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic: Spearman ランク相関）、ランク変換ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - calc_forward_returns は複数ホライズンを一括で取得する効率的なクエリを実装（horizons の検証あり）。
    - calc_ic は None 値や無効なケースを除外し、有効レコードが少なければ None を返す。
    - すべて標準ライブラリと DuckDB のみで実装。

- Data（kabusys.data）
  - calendar_management
    - JPX カレンダー（market_calendar）を管理するユーティリティを実装。
    - 営業日判定関数群: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - DB にカレンダーデータがない場合は曜日ベース（平日を営業日）でフォールバック。DB 値が優先され、未登録日はフォールバックで一貫して扱う。
    - 夜間バッチ更新 job: calendar_update_job(conn, lookahead_days=90) を実装。J-Quants クライアントを通じて差分取得し保存（バックフィル、健全性チェックあり）。
    - 最大探索日数・バックフィル・サニティチェック等の安全策を備える。
    - jquants_client への依存注入設計（データ取得・保存は jquants_client 経由）。

  - ETL / pipeline
    - ETLResult データクラス（kabusys.data.pipeline.ETLResult）を実装し、ETL の実行結果（取得数・保存数・品質問題・エラー等）を表現。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得、トレーディングデイ調整等を実装。
    - kabusys.data.etl は ETLResult を再エクスポート。

### 変更（設計方針・重要実装ノート）
- ルックアヘッドバイアス防止:
  - score_news / score_regime / 各種 Research 関数は datetime.today() / date.today() を内部で参照せず、必ず呼び出し側から target_date を受け取る設計。
  - DB クエリは target_date 未満や target_date 固定などでルックアヘッドを防止。
- DB 書き込みは可能な限り冪等化（DELETE→INSERT や ON CONFLICT 相当）し、部分失敗で他データを消さない工夫を実装。
- OpenAI 呼び出しの堅牢化:
  - 429・ネットワーク・タイムアウト・5xx をリトライ対象にし指数バックオフを実装。
  - パース失敗や non-5xx エラーはフェイルセーフでスコア 0.0（もしくは処理スキップ）にフォールバック。
  - テスト用に _call_openai_api を差し替え可能な実装。
- DuckDB 互換性対応:
  - executemany に空リストを渡さない等の互換性配慮（DuckDB 0.10 の制約回避）。

### 既知の注意点 / 制限
- OpenAI（gpt-4o-mini） と DuckDB に依存。実行には OPENAI_API_KEY や DuckDB 環境が必要。
- news_nlp と regime_detector は別実装の _call_openai_api を持つため、テストでそれぞれ差し替える必要がある。
- 一部の機能（PBR・配当利回り等）は現バージョンでは未実装（calc_value の注記参照）。
- calendar_update_job は jquants_client の実装に依存し、API エラー時は 0 を返してスキップする（エラーはログ出力）。

### セキュリティ
- 環境変数で機密情報（API キー等）を管理。自動読み込み時に OS 環境変数は保護される。

---

必要があれば、各モジュールの公開 API（関数一覧と簡単な使用例）を CHANGELOG に追記できます。どのレベルの詳細が必要か教えてください。