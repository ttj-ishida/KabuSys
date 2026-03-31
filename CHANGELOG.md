# Changelog

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。

次のタグ付けルールに従います:
- 変更はカテゴリ（Added, Changed, Fixed, Deprecated, Removed, Security）ごとに記載します。
- 日付はリリース日です。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-31
初回リリース — 日本株自動売買／リサーチ基盤のコア機能を実装。

### Added
- 基本パッケージ
  - パッケージ名: kabusys、バージョン 0.1.0。パッケージ公開用の __init__ を追加。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルート（.git または pyproject.toml）を起点に .env/.env.local を探索して読み込む。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env のパースは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント処理等をサポート。
    - OS 環境変数は protected として .env.local の上書きから保護。
  - Settings クラスを提供（J-Quants/OpenAI/Slack/DB パス/ログレベル 等のプロパティを取得）。
    - 必須変数未設定時は ValueError を送出。
    - KABUSYS_ENV と LOG_LEVEL に対する値検証（許容値のチェック）。
    - デフォルトの DB パス（duckdb/sqlite）を設定。

- データ基盤（kabusys.data）
  - calendar_management: 市場カレンダー管理と営業日判定ユーティリティを追加。
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を実装。
    - DB に calendar がない場合は曜日ベース（土日除外）でフォールバック。
    - calendar_update_job による夜間差分取得・バックフィル・健全性チェックを実装（J-Quants クライアント経由）。
  - pipeline / etl:
    - ETLResult dataclass を実装（取得/保存件数、品質問題、エラー収集等）。
    - テーブル存在チェック・最大日付取得など ETL 用のユーティリティを実装。
    - data.etl で ETLResult を再エクスポート。

- AI（自然言語処理）機能（kabusys.ai）
  - news_nlp: ニュース記事を OpenAI（gpt-4o-mini）でセンチメントスコア化し ai_scores に書き込む処理を実装。
    - ニュース収集ウィンドウ（前日15:00 JST ～ 当日08:30 JST）の計算（calc_news_window）。
    - 銘柄ごとに記事を集約し（件数・文字数制限）、最大 20 銘柄/チャンクでバッチ送信。
    - レート制限・ネットワーク断・タイムアウト・5xx を対象に指数バックオフで再試行。
    - レスポンスの厳密な JSON パース・バリデーションを行いスコアを ±1 にクリップ。
    - スコア取得済み銘柄のみを対象に DELETE → INSERT の冪等的な DB 書き込み（トランザクション）。
    - テスト容易化のため OpenAI 呼び出し部分は差し替え可能（ユニットテスト用 patch を想定）。
  - regime_detector: ETF（1321）の 200 日 MA 乖離とマクロニュースの LLM センチメントを合成して日次市場レジーム（bull/neutral/bear）を判定。
    - ma200_ratio と LLM による macro_sentiment を 0.7 / 0.3 の重みで合成。
    - LLM 呼び出しに対してリトライ/フォールバック（失敗時 macro_sentiment=0.0）。
    - market_regime テーブルに冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）、エラー時は ROLLBACK（ROLLBACK 失敗は警告ログ）。

- リサーチ機能（kabusys.research）
  - factor_research: モメンタム（1M/3M/6M）、MA200乖離、ATR（20日）、流動性（20日平均売買代金・出来高比）などのファクター計算を実装。
    - calc_momentum, calc_volatility, calc_value を提供。
    - DuckDB 上の SQL + Python で完結（外部 API へはアクセスしない）。
  - feature_exploration: 将来リターン計算、IC（Spearman）の計算、統計サマリー、ランク変換を実装。
    - calc_forward_returns（任意ホライズン）、calc_ic、rank、factor_summary を提供。
  - research パッケージで主要関数をエクスポート。

- 共通・実装上の工夫
  - DuckDB を主要な分析 DB として利用する想定（接続を引数で受け取る）。
  - すべての日付・時間扱いはルックアヘッドバイアス回避のため date/UTC naive datetime を使用（datetime.today() を参照しない設計）。
  - ロギング（logger）を広く使用し、警告・情報を出力。
  - API 呼び出しはタイムアウト設定を行いフェイルセーフなフォールバックを実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI / J-Quants / Slack の API キーは環境変数または .env で管理。必須変数未設定時は明示的に例外を発生させることで安全性を確保。

### Notes / Known limitations
- OpenAI（gpt-4o-mini）を利用するため API コストとレート制限が発生します。API の不可用時は一部スコアが中立/スキップされる設計です（失敗時はスコアを 0.0 にフォールバック、もしくは銘柄単位でスキップ）。
- DB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar 等）に依存します。適切なスキーマが前提です。
- DuckDB のバージョンによる制約（executemany に空リスト不可）を考慮した実装になっていますが、運用環境の DuckDB バージョンに注意してください。
- ETL の運用スケジューラやジョブキューは含まれていません。calendar_update_job / ETL utilities は呼び出し元から定期実行する前提です。
- JSON Mode でも LLM の応答に余分な前後テキストが混入することを想定してパースの救済処理を入れていますが、完全な安全性は保証しません。

### Migration / Setup
- 必須環境変数（例）
  - OPENAI_API_KEY (news_nlp / regime_detector 実行時)
  - JQUANTS_REFRESH_TOKEN（J-Quants クライアント使用時）
  - KABU_API_PASSWORD（kabu API 利用時）
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（通知利用時）
- .env.example を参照して .env を作成してください。自動読み込みはプロジェクトルートに依存します。

---

今後の予定（例）
- モデルのバージョン管理・カスタムプロンプト調整インターフェースの追加
- より細かなエラー分類と再試行ポリシーのチューニング
- ETL 実行の CLI / サービス化（ジョブ制御）