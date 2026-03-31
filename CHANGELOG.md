Changelog
=========

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。

[0.1.0] - 2026-03-31
--------------------

初回公開リリース。日本株自動売買システム "KabuSys" のコアライブラリを提供します。以下の主要機能・モジュールを含みます。

Added
- パッケージ基礎
  - パッケージ名: kabusys、バージョン 0.1.0。
  - src/kabusys/__init__.py で公開モジュール: data, strategy, execution, monitoring（名称空間を確立）。

- 設定・環境変数管理 (kabusys.config)
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みする仕組みを実装。
  - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱い、無効行（空行・#始まり）等に対応。
  - 自動ロードを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト時に使用）。
  - OS 環境変数を保護する protected ロジック（.env.local は既存 OS 変数を上書きしないよう保護可能）。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス /監視閾値/ログレベル/環境種別（development/paper_trading/live）などのプロパティを取得・バリデート。
  - 必須環境変数未設定時は ValueError を発生させる _require ヘルパー。

- データ関連 (kabusys.data)
  - calendar_management
    - market_calendar テーブルに基づく営業日判定ロジックを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB に登録がない場合は曜日（土日）ベースのフォールバックを行う設計（DB とフォールバックで一貫性を保つ）。
    - 夜間バッチ calendar_update_job を実装し、J-Quants API から差分取得・バックフィル・健全性チェックを行って market_calendar を更新。
    - DB の存在チェック・NULL 値検知時のログ出力など健全性重視の実装。
  - pipeline / etl
    - ETLResult データクラスを追加（ETL の取得/保存件数、品質問題、エラー集約用）。
    - ETL パイプライン（差分更新、保存、品質チェック）のインターフェースとユーティリティ（_table_exists, _get_max_date 等）の基盤を実装。
    - デフォルトで DuckDB を利用する設計を想定。
  - data.etl は pipeline.ETLResult を再エクスポート。

  - 期待する DB テーブル（コード中で参照）
    - prices_daily, raw_news, ai_scores, market_regime, raw_financials, news_symbols, market_calendar など。

  - jquants_client（kabusys.data.jquants_client）に依存する箇所があり、fetch/save 関数の存在を前提。

- 研究・ファクター計算 (kabusys.research)
  - factor_research
    - モメンタム、バリュー、ボラティリティ系ファクターを計算する関数群を実装:
      - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200日MA乖離）を計算。データ不足時は None を返す。
      - calc_volatility: 20日 ATR、ATR/価格比、20日平均売買代金、出来高比率を計算。
      - calc_value: raw_financials から最新財務を取得して PER / ROE を算出（EPS が無効なら None）。
    - DuckDB + SQL ウィンドウ関数を多用し、外部 API に依存しない純粋な計算モジュール。
  - feature_exploration
    - calc_forward_returns: 指定日から複数ホライズン先の将来リターンを一括で計算（horizons のバリデーションあり）。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算。最小有効サンプル数チェック。
    - rank: 同順位は平均ランクを返す安定したランク付け実装（丸め対策含む）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
  - research.__init__ から主要関数をエクスポート。

- AI / ニュース解析 (kabusys.ai)
  - news_nlp (score_news)
    - raw_news + news_symbols を入力に、銘柄ごとに記事を集約し（ウィンドウは前日15:00 JST〜当日08:30 JST 相当）、OpenAI（gpt-4o-mini, JSON mode）でセンチメントを算出して ai_scores に保存するバッチ処理を実装。
    - バッチサイズ、記事数/文字数のトリム（トークン肥大化対策）、最大リトライ・指数バックオフ、429/ネット断/タイムアウト/5xx の取り扱いなどを実装。
    - レスポンスのバリデーション（JSON 抽出、results リスト、code と score の整合性、数値チェック）と ±1.0 のクリップを行う。
    - 部分成功時にも既存データを消さないよう、書き込みは対象コードに限定した DELETE → INSERT の冪等処理を実装。
    - テスト容易性: OpenAI 呼び出しを _call_openai_api を通す（unittest.mock.patch により差し替え可能）。
  - regime_detector (score_regime)
    - ETF 1321（日経225連動型）の 200日移動平均乖離（重み 70%）とニュースマクロセンチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定し market_regime に冪等書き込みする処理を実装。
    - マクロ記事抽出、OpenAI 呼び出し（JSONレスポンス）、リトライ戦略、API 失敗時のフォールバック（macro_sentiment=0.0）を実装。
    - ルックアヘッドバイアス防止のため、内部処理で date.today()/datetime.today() を使わない設計（target_date 引数で明示的に指定）。
    - OpenAI クライアント生成は OpenAI(api_key=...) を使用。

Changed
- （初回リリースのため「変更」はなし）

Fixed
- （初回リリースのため「修正」はなし）

Security
- 環境変数・シークレット（OpenAI API キー等）は Settings 経由で扱い、.env 自動ロードで OS 環境変数を上書きしない既定動作を採用（.env.local で上書き可能）。自動ロードは環境変数で無効化可。

Notes / ユーザー向け情報
- 必須環境変数（代表例）
  - OPENAI_API_KEY（AI モジュールを使用する場合）
  - JQUANTS_REFRESH_TOKEN（J-Quants API 利用）
  - KABU_API_PASSWORD, KABU_API_BASE_URL（kabu ステーション API）
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（通知連携）
- デフォルト DB パス
  - DuckDB: data/kabusys.duckdb（Settings.duckdb_path）
  - SQLite (監視用): data/monitoring.db（Settings.sqlite_path）
- 自動ロードされるファイル
  - プロジェクトルートの .env（既存 OS 環境を上書きしない）
  - .env.local（.env を上書き、ただし OS 環境を保護）
- テスト可能性
  - OpenAI 呼び出し周りは内部関数を差し替え可能（unittest.mock.patch によるモック化を想定）。
- DB スキーマ（簡易）
  - 本ライブラリは特定のテーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar 等）を想定しています。実行前にスキーマ準備が必要です。
- 外部依存
  - duckdb, openai (OpenAI SDK) を利用。J-Quants 連携部分は kabusys.data.jquants_client の実装に依存。

Acknowledgements
- 本リリースは初回の公開版です。今後、strategy / execution / monitoring 等のランタイムおよび運用周りの機能強化、型・ドキュメント整備、テストカバレッジ拡充を予定しています。

（以上）