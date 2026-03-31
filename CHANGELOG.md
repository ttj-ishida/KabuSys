# Changelog

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の方針に従います。  

なお、本CHANGELOGはコードベースから仕様・実装を推測して作成しています。

## [0.1.0] - 2026-03-31

Added
- 初回リリース: KabuSys 日本株自動売買システムのコア機能を実装・公開。
- パッケージ公開
  - パッケージルート: `kabusys`（__version__ = "0.1.0"）。主要サブパッケージを `__all__` で公開: data, strategy, execution, monitoring。
- 設定管理
  - `kabusys.config.Settings` を追加。環境変数からアプリケーション設定を取得（必須設定は取得失敗で ValueError）。
  - 自動 .env ロード機能を追加（プロジェクトルートを .git または pyproject.toml で探索）。読み込み順序は OS 環境変数 > .env.local > .env。
  - `.env` のパースは export prefix、クォート内のエスケープ、インラインコメントの取り扱いなどに対応。`KABUSYS_DISABLE_AUTO_ENV_LOAD` で自動ロードを無効化可能。
  - 保護された OS 環境変数（既存の os.environ）は `.env` の上書きを防ぐ仕組みを実装（.env.local は override=True だが protected を考慮）。
  - 設定項目: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルトあり）、SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV（development/paper_trading/live 検証）、LOG_LEVEL（検証）。
- データ処理（data）
  - ETL パイプラインインターフェース (`kabusys.data.pipeline.ETLResult`) を公開（`kabusys.data.etl` 経由で再エクスポート）。
  - DuckDB を用いた差分取得・保存処理の基盤を実装（差分開始日の検出、バックフィル、品質チェックフック想定）。
  - マーケットカレンダー管理 (`kabusys.data.calendar_management`) を実装。
    - 営業日判定 API: is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days。
    - カレンダーが未取得の場合は曜日ベース（土日非営業日）でフォールバック。
    - calendar_update_job により J-Quants から差分取得し `market_calendar` テーブルへ冪等保存（バックフィル・健全性チェックあり）。
- 研究モジュール（research）
  - ファクター計算 (`kabusys.research.factor_research`) を実装:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（データ不足時は None）、DuckDB SQL ベース。
    - calc_volatility: 20日 ATR、ATR 比率、20日平均出来高/売買代金、出来高比率。
    - calc_value: PER（EPS が 0/欠損時は None）、ROE（raw_financials から直近データを取得）。
  - 特徴量探索 (`kabusys.research.feature_exploration`):
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン算出（LEAD を利用）。
    - calc_ic: スピアマン（ランク）での IC 計算（rank 関数を内部実装）。
    - factor_summary: 各ファクターの count/mean/std/min/max/median を算出。
    - rank: 同順位は平均ランクにするランク付け実装（丸めで ties の検出漏れを防止）。
  - `zscore_normalize` を `kabusys.data.stats` から再エクスポート。
- AI（自然言語処理）モジュール（kabusys.ai）
  - ニュースセンチメント (`kabusys.ai.news_nlp.score_news`) を実装。
    - 前日15:00 JST〜当日08:30 JST の記事ウィンドウ計算（UTC 換算）を提供（calc_news_window）。
    - 銘柄ごとに記事を集約し、1銘柄あたり最大 10 記事・3000 文字にトリムして LLM へ送信。
    - バッチ処理: 最大 20 銘柄ずつ送信。OpenAI の JSON Mode（gpt-4o-mini）を使用し、results リストを期待。
    - リトライ: 429・ネットワーク・タイムアウト・5xx を対象に指数バックオフでリトライ。API エラー非5xx はスキップ。
    - レスポンス検証: JSON パース復元（余計なテキストを包む {} の抽出）、results の型チェック、未知コード無視、スコア数値化・有限値判定。スコアは ±1.0 にクリップ。
    - 書込みは冪等: 対象コードのみ DELETE → INSERT（部分失敗時に他コードを保護）。DuckDB executemany の空リスト制約に配慮。
    - API 呼び出しモック用 hook: `_call_openai_api` をテスト時に差し替え可能。
  - 市場レジーム判定 (`kabusys.ai.regime_detector.score_regime`) を実装。
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次のレジーム（bull/neutral/bear）を算出。
    - マクロニュースは `news_nlp.calc_news_window` を用いてタイトルを抽出（マクロキーワードでフィルタ、最大 20 件）。
    - OpenAI 呼び出しは独立実装で、API 失敗時は macro_sentiment = 0.0 のフェイルセーフ。リトライとログを実装。
    - 結果は `market_regime` テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書込失敗時は ROLLBACK を試行し例外を伝播。
- 設計方針/運用上の配慮
  - ルックアヘッドバイアス防止: 各スコアリング・判定処理は内部で datetime.today()/date.today() を直接参照せず、必ず外部から target_date を受け取る設計。
  - DB 操作は冪等性を重視（DELETE→INSERT、ON CONFLICT DO UPDATE 想定）。
  - 失敗時は例外を投げる箇所とフォールバックで継続する箇所を明確に分離（LLM/外部APIの一時失敗はスコア0やスキップでフェイルセーフ）。
  - テスト性: OpenAI 呼び出し用の内部関数を patch で差し替え可能にしユニットテストを容易化。
  - DuckDB を集中的に利用（prices_daily, raw_news, ai_scores, market_regime, raw_financials, market_calendar 等の操作を想定）。

Changed
- 初版のため該当なし。

Fixed
- 初版のため該当なし。

Deprecated
- 初版のため該当なし。

Removed
- 初版のため該当なし。

Security
- 初版のため該当なし。

Notes / 必要な環境変数
- 動作には以下の環境変数が必要（未設定時は Settings のプロパティで ValueError を送出するものあり）。
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - OpenAI API 呼び出しを行う機能利用時は OPENAI_API_KEY が必要（score_news / score_regime は明示的に api_key 引数を受け取れる）。
- デフォルトの DB パス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"（expanduser 対応）。

Known limitations / 今後の改善候補（推奨）
- ai モジュール: モデル名やリトライポリシーの外部設定化、リクエストメトリクスの収集。
- ETL, calendar: jquants client のエラー細分化とリトライ戦略、UI/監視フックの追加。
- research: PBR・配当利回り等バリューファクターの追加、並列処理やキャッシュの最適化。
- テストカバレッジ: DuckDB のモックを用いた単体テスト・統合テストの整備。

--- 

このリリースはコードベースからの推測に基づいて作成しています。実際のリリースノート作成時は変更差分やコミットログ・リリースマネージャの確認を行ってください。