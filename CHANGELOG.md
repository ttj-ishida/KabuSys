# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  
公開日付はリリース時に更新してください。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-31
初回公開リリース。

### 追加
- パッケージの基本構成
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - 公開 API: kabusys.data, kabusys.strategy, kabusys.execution, kabusys.monitoring を __all__ でエクスポート

- 設定 / 環境変数管理 (kabusys.config)
  - .env / .env.local 自動ロード機能を実装。読み込み順は OS 環境変数 > .env.local > .env。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を基準）。
  - .env パーサーは export 形式、クォート（シングル・ダブル）、エスケープ、インラインコメントに対応。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応（テスト用途）。
  - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得可能：
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live のみ有効）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL のみ有効）
    - 環境判定ヘルパー: is_live / is_paper / is_dev

- AI モジュール (kabusys.ai)
  - ニュース NLP (kabusys.ai.news_nlp)
    - score_news(conn, target_date, api_key=None)
      - raw_news / news_symbols から指定ウィンドウ（前日15:00 JST 〜 当日08:30 JST）分を集約して銘柄ごとに OpenAI（gpt-4o-mini）へ送信。
      - バッチ処理（最大 20 銘柄/回）、1 銘柄あたり最大 10 記事、最大文字数トリム機能あり。
      - レート制限(429)、ネットワーク断、タイムアウト、5xx に対して指数バックオフでリトライ。
      - レスポンスバリデーション（JSON 抽出、results 配列、code/score チェック、スコアのクリップ ±1.0）。
      - 成功分のみ ai_scores テーブルへ冪等的に書込（DELETE → INSERT）、部分失敗時も既存スコアを保護。
      - テスト容易性のため OpenAI 呼び出し関数は差し替え可能（patch 対応）。
    - calc_news_window(target_date) ユーティリティを提供（UTC naive datetime を返す）。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - score_regime(conn, target_date, api_key=None)
      - ETF 1321 の過去 200 日終値から MA200 乖離（最新 / MA200）を計算（ルックアヘッド防止: date < target_date）。
      - マクロキーワードで raw_news をフィルタしてタイトルを取得（最大 20 件）。
      - OpenAI（gpt-4o-mini）でマクロセンチメントを JSON で取得（API 失敗時は macro_sentiment=0.0 として継続）。
      - MA（重み70%）とマクロセンチメント（重み30%）を合成してレジームスコアを算出し、label を決定（bull/neutral/bear）。
      - market_regime テーブルへ冪等的に書込（BEGIN/DELETE/INSERT/COMMIT）、DB 書込失敗時は ROLLBACK を試行して例外を上位に伝播。
      - API 呼び出しは独立実装（news_nlp の内部関数を再利用しない設計）。

- データ / ETL / カレンダー (kabusys.data)
  - calendar_management
    - 市場カレンダー操作と判定ヘルパーを提供:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - market_calendar が未取得の場合は曜日ベースでフォールバック（土日を非営業日扱い）。
    - DB が部分的に存在する場合でも一貫した判定ができるよう DB 値優先＋未登録日は曜日フォールバックの設計。
    - calendar_update_job(conn, lookahead_days=90)
      - J-Quants API から差分取得して market_calendar を冪等保存。
      - バックフィル（直近数日再取得）、健全性チェック（将来日付の異常検出）などを実装。
    - jquants_client を利用するための fetch/save の呼出に対応。API エラー時は安全に 0 を返す。
  - pipeline / ETL
    - ETLResult データクラスを公開（kabusys.data.etl から再エクスポート）。
      - ETL の取得数/保存数、品質チェック結果、エラー一覧などを格納。
      - has_errors / has_quality_errors / to_dict ヘルパーを提供。
    - ETL 実行のための内部ユーティリティ（テーブル存在チェック、最大日付取得、トレーディング日調整など）を実装。
    - 設計上、差分更新・バックフィル、品質チェックは Fail-Fast とせず結果収集型。

- リサーチ / ファクター (kabusys.research)
  - factor_research
    - calc_momentum(conn, target_date)
      - mom_1m / mom_3m / mom_6m と ma200_dev を計算。データ不足時は None を返す。
    - calc_volatility(conn, target_date)
      - 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比率（volume_ratio）を計算。
    - calc_value(conn, target_date)
      - raw_financials から最新財務データを取得し PER / ROE を計算（EPS が 0/欠損時は None）。
    - 設計方針: DuckDB 上で SQL＋Python により計算。外部 API へはアクセスしない。
  - feature_exploration
    - calc_forward_returns(conn, target_date, horizons=None)
      - 翌日/翌週/翌月 等の将来リターンを一度のクエリで取得できるよう実装。
    - calc_ic(factor_records, forward_records, factor_col, return_col)
      - スピアマンのランク相関（IC）を計算。データ不足（<3）で None を返す。
    - rank(values) / factor_summary(records, columns)
      - ランク化ユーティリティ、基本統計量（count/mean/std/min/max/median）を提供。
    - pandas 等外部依存を使わない実装。

### 仕様上の重要な挙動（注意）
- OpenAI API
  - デフォルトモデル: gpt-4o-mini（JSON Mode を使用）。
  - API キーは関数引数で注入可能（api_key）、未指定時は環境変数 OPENAI_API_KEY を参照。未設定時は ValueError。
  - 大多数の OpenAI API エラー（429、ネットワーク断、タイムアウト、5xx）はリトライでフェイルセーフ的に扱い、最終的に失敗した場合は空スコアあるいは 0.0 を使って処理を継続する設計。
  - テストのために OpenAI 呼び出し関数をパッチで差し替えられるようにしている（unittest.mock.patch を想定）。
- DB 書き込み
  - ai_scores / market_regime 等への書き込みは冪等性を意識（DELETE → INSERT または ON CONFLICT 相当）してあるため、再実行で上書き可能。
  - DuckDB の executemany が空リストを受け付けない点に配慮してガードを入れている。
- 日付扱い
  - すべての処理でルックアヘッドバイアスを避けるため datetime.today()/date.today() を直接参照しない設計（target_date を明示的に渡す）。
  - news ウィンドウ等は JST ベースの定義を内部で UTC naive datetime に変換して使用。

### 既知の制約 / 前提
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN（J-Quants API 用）
  - KABU_API_PASSWORD（kabuステーション API 用）
  - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（通知用）
  - OPENAI_API_KEY（score_news / score_regime を実行する場合は必要。メソッド引数でも注入可）
- デフォルトの DB パス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- KABUSYS_ENV は development / paper_trading / live のいずれかである必要がある（不正な値は ValueError）。
- .env の自動読み込みはプロジェクトルートを特定できない場合はスキップされる。

### セキュリティ
- 各 API キー・パスワードは環境変数で管理することを想定。`.env` を使う場合はリポジトリにコミットしないよう注意してください。

---

今後のリリース案（例）
- Unreleased: エラーハンドリング強化、メトリクス収集、Kabu API との発注周りの実装（strategy / execution）、CI による DuckDB 用テストフィクスチャ追加、ドキュメント強化。