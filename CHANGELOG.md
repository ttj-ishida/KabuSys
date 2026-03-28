# CHANGELOG

すべての重要な変更をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

## [Unreleased]

## [0.1.0] - 2026-03-28
初回リリース (initial public commit 相当)。日本株自動売買・データ基盤・リサーチ用の基盤機能を実装。

### Added
- パッケージ骨格
  - kabusys パッケージ初期構成を追加。バージョンは 0.1.0。
  - __all__ に data/strategy/execution/monitoring を想定して公開。

- 環境設定管理 (kabusys.config)
  - .env / .env.local を自動読み込みする仕組みを追加（プロジェクトルートは .git または pyproject.toml を探索して決定）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env 解析の強化:
    - `export KEY=val` 形式のサポート。
    - シングル/ダブルクォート内でのバックスラッシュエスケープ処理対応。
    - クォートなし行でのインラインコメント判定（直前が空白/タブの場合のみ '#' をコメントとして扱う）。
  - _load_env_file の override / protected 挙動により OS 環境変数を保護しつつ .env.local で上書き可能。
  - Settings クラスを追加し、アプリ設定をプロパティ経由で取得可能に:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID の必須チェック（未設定時は ValueError）。
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH のデフォルト値。
    - KABUSYS_ENV の検証（development / paper_trading / live のみ許可）。
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - is_live / is_paper / is_dev ヘルパー。

- AI モジュール (kabusys.ai)
  - ニュースセンチメント解析モジュール news_nlp を追加:
    - raw_news と news_symbols を用い、銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini）へバッチ送信。
    - バッチ処理: 最大 20 銘柄/コール、1銘柄あたり最大 10 記事・3000 文字でトリム。
    - JSON Mode の利用、レスポンス検証、スコアを ±1.0 にクリップ。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ。
    - エラー時はフェイルセーフでスキップ（例外を上げずに処理継続）。
    - スコア取得後は ai_scores テーブルへトランザクションで置換（DELETE → INSERT）。部分失敗時に他銘柄の既存スコアを保護する実装。
    - 単体テスト容易化のため _call_openai_api を patch 可能に実装。
    - 公開 API: score_news(conn, target_date, api_key=None) を提供（書き込んだ銘柄数を返す）。
  - 市場レジーム判定モジュール regime_detector を追加:
    - ETF 1321（Nikkei 日経225 ETF）200日移動平均乖離（重み70%）とニュースLLMセンチメント（重み30%）を合成して日次でレジーム（bull/neutral/bear）判定。
    - マクロキーワードによる raw_news フィルタリング、OpenAI 呼び出し（gpt-4o-mini）によるマクロセンチメント算出、スコア合成。
    - API エラー時は macro_sentiment=0.0 にフォールバックするフェイルセーフ。
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。ROLLBACK の失敗ログも考慮。
    - 公開 API: score_regime(conn, target_date, api_key=None) を提供（成功時は 1 を返す）。

- データ基盤モジュール (kabusys.data)
  - カレンダー管理 calendar_management を追加:
    - market_calendar テーブルを基にした営業日判定ユーティリティ（is_trading_day、next_trading_day、prev_trading_day、get_trading_days、is_sq_day）。
    - DB にカレンダーがない／不完全な場合は曜日ベースのフォールバック (土日非営業)。
    - next/prev/get_trading_days は DB 登録値優先で未登録日は曜日フォールバックにより一貫性を維持。
    - calendar_update_job により J-Quants API から差分取得し冪等保存（バックフィルや健全性チェックを実装）。
  - ETL / パイプライン pipeline と ETLResult を追加:
    - 差分更新、API 取得→保存→品質チェックの枠組みを想定（jquants_client, quality と連携）。
    - ETLResult dataclass を導入（target_date、各種 fetched/saved カウント、quality_issues、errors、to_dict()）。
    - ETLResult で品質チェックの重大度検出（has_quality_errors）・エラー有無（has_errors）を提供。
  - etl モジュールで ETLResult を再エクスポート。

- 研究（Research）モジュール (kabusys.research)
  - factor_research を追加:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離を計算（データ不足時は None）。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算（データ不足は None）。
    - calc_value: raw_financials から最新財務を取得し PER / ROE を計算（EPS が 0/NULL の場合は None）。
    - DuckDB を用いた SQL 中心の実装で、外部 API にはアクセスしない安全設計。
  - feature_exploration を追加:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算（複数ホライズンをまとめて1クエリで取得）。
    - calc_ic: Spearman ランク相関（IC）を計算（有効サンプル <3 の場合は None）。
    - rank: 同順位は平均ランクにするランク化ユーティリティ（丸めによる tie 検出向けの配慮あり）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
  - research パッケージの __init__ で主要関数群をエクスポート（calc_momentum, calc_value, calc_volatility, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- トランザクション処理の安全性を考慮:
  - DB 書き込み処理で例外発生時に ROLLBACK を試み、さらに ROLLBACK 自体の失敗を警告ログに記録するように実装（score_regime, score_news 等）。
  - DuckDB の executemany 空リスト禁止に対応するガード実装（ai.score_news の DELETE/INSERT 前チェック）。

### Security
- セキュリティに関する注意点:
  - OpenAI API キーは引数で注入可能（テスト容易化）かつ環境変数 OPENAI_API_KEY を参照する設計。未設定の場合は ValueError を送出して明示的に失敗させる。
  - OS 環境変数を .env により上書きされないよう protected set を導入。

### Notes / Design decisions
- ルックアヘッドバイアス防止:
  - 多くの処理（news ウィンドウ計算、レジーム判定、ファクター計算など）は datetime.today()/date.today() を直接参照せず、target_date を明示的に受け取る API 設計になっています。
- テスト性:
  - OpenAI 呼び出し用のプライベート関数（_call_openai_api）を patch しやすく実装しており、API モックによる単体テストが可能。
- 外部依存:
  - リサーチ系関数は pandas 等に依存せず標準ライブラリ＋duckdb のみで実装。

---

（この CHANGELOG はコード内容から推測して作成しています。実際のリリースノートはコミット履歴やリリース日付に合わせて更新してください。）