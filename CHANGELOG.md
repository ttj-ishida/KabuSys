CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

Unreleased
----------

（未リリースの変更はここに記載してください）

0.1.0 - 2026-04-03
------------------

Added
- 初回公開リリース。パッケージ名: kabusys、バージョン __version__ = "0.1.0"。
- パッケージ構成（主要サブパッケージ / モジュール）:
  - kabusys.config
    - .env ファイルおよび環境変数の自動読み込み機能を実装（プロジェクトルートは .git / pyproject.toml で探索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - .env パースロジック（export 形式、シングル/ダブルクォート、エスケープ、インラインコメント対応）。
    - Settings クラスによりアプリ設定をプロパティ経由で提供。主な環境変数:
      - JQUANTS_REFRESH_TOKEN（必須、J-Quants）
      - KABU_API_PASSWORD（必須、kabuステーション）
      - OPENAI_API_KEY（AI 機能利用時に必要）
      - 各種パス・閾値（DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH 等）
      - KABUSYS_ENV（development / paper_trading / live の検証）
      - LOG_LEVEL（検証済み）
  - kabusys.ai.news_nlp
    - raw_news / news_symbols を集約して銘柄別にニュースをまとめ、OpenAI（gpt-4o-mini）の JSON Mode で一括センチメント評価。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ calc_news_window。
    - バッチ処理（最大 20 銘柄／回）、1 銘柄あたり記事数・文字数のトリム制御。
    - リトライ（429・ネットワーク・タイムアウト・5xx に対する指数バックオフ）、レスポンス検証（JSON 抽出／results 検証／コード整合性／数値検証）、±1.0 でスコアクリップ。
    - スコア書き込みは idempotent（対象コードのみ DELETE → INSERT）で部分失敗に対する保護を実装。
  - kabusys.ai.regime_detector
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定。
    - マクロ記事抽出（指定キーワード群）→ OpenAI 呼び出し（gpt-4o-mini）→ スコア合成（clip）→ market_regime テーブルへ冪等書き込みを実装。
    - API 呼び出し失敗時はフェイルセーフで macro_sentiment=0.0 を利用し処理継続。
  - kabusys.data.calendar_management
    - JPX カレンダー管理（market_calendar）と営業日ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録値優先、未登録日は曜日ベースのフォールバック。探索の最大範囲制限（_MAX_SEARCH_DAYS）。
    - calendar_update_job により J-Quants から差分取得・バックフィル（直近 _BACKFILL_DAYS）・保存処理を実装。
  - kabusys.data.pipeline / kabusys.data.etl
    - ETLResult データクラスを公開（ETL の取得数・保存数・品質問題・エラー等の集約）。
    - ETL 設計方針に基づく差分更新・バックフィル・品質チェック連携を考慮した実装基盤。
  - kabusys.research
    - factor_research:
      - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日 MA 乖離）を DuckDB SQL で計算。
      - calc_volatility: ATR(20)、相対ATR(atr_pct)、20日平均売買代金、出来高比率。
      - calc_value: raw_financials の直近財務から PER/ROE を算出（EPS が 0/欠損の場合は None）。
    - feature_exploration:
      - calc_forward_returns: 将来リターン fwd_{hd}d（デフォルト: 1,5,21 日）。
      - calc_ic: ランク相関（Spearman 相当）による IC 計算（rank ライブラリ関数あり）。
      - factor_summary: 基本統計量（count/mean/std/min/max/median）。
  - 共通設計上の注意点（ドキュメントとして実装）
    - ルックアヘッドバイアス防止のため、各処理は datetime.today()/date.today() 参照を極力避け、target_date を明示的に引数で受け取る設計。
    - DB 書き込みは可能な限り冪等（DELETE→INSERT や ON CONFLICT 相当）で実装。
    - 外部 API 呼び出し（OpenAI / J-Quants）に対する堅牢なリトライとフェイルセーフ動作を実装。
    - DuckDB を利用する想定（テーブル名: prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar など）。

Changed
- （初版のため過去バージョンからの変更はなし）

Fixed
- OpenAI レスポンスの JSON パースに関する実務的な取り扱い（前後の余計なテキストを {} で抽出して復元する等）を実装し現場で遭遇する不整合に対処。
- .env パーサーにおいてクォート内のエスケープ処理や export プレフィックス、インラインコメント判定の改善を実装。

Security
- 機密情報は環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY 等）で管理する設計。
- 自動 .env 読み込みを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD を提供（テスト・安全運用向け）。

Known issues / Notes
- OpenAI / J-Quants クライアントは外部サービス依存のため、実行環境で該当 API キーや API エンドポイントが必要。
- 一部関数は DuckDB のバージョン依存（executemany の挙動等）に注意（コード内に互換性対策を含む）。
- research モジュールは外部口座・発注 API に接触しない設計（分析専用）。
- calendar_update_job の正常動作には kabusys.data.jquants_client の実装が必要。

Migration / Upgrade notes
- 本リリースは初期公開のため、導入時は以下を確認してください:
  - 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD。AI 機能を使う場合は OPENAI_API_KEY。
  - DuckDB ファイルパス（default: data/kabusys.duckdb）や SQLite モニタリング DB は Settings で変更可能。
  - 自動 .env 読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

その他
- 各モジュールに詳細な docstring（設計方針・処理フロー・フェイルセーフ動作等）を含めており、内部挙動の理解や拡張が容易な実装を目指しています。

--- 

この CHANGELOG はコードの docstring と実装から推測して作成しています。追加のリリース日やリリースノートの補足があれば更新してください。