# Changelog

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
このプロジェクトはセマンティックバージョニングに従います。

## [Unreleased]

## [0.1.0] - 2026-03-29
初回リリース。日本株自動売買システムのコアライブラリを実装しました。

### Added
- パッケージ基盤
  - kabusys パッケージ初期化（バージョン情報: 0.1.0）。__all__ に data, strategy, execution, monitoring を公開。
- 設定/環境変数管理（kabusys.config）
  - .env / .env.local ファイルと OS 環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を起点）によりカレントディレクトリに依存しない自動ロード。
  - .env パーサを実装（export 構文、シングル/ダブルクォート、エスケープ、行内コメントの取り扱いをサポート）。
  - 自動読み込みを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 必須環境変数チェック（_require）。未設定時は ValueError を発生。
  - 設定値の公開: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）、SLACK_BOT_TOKEN, SLACK_CHANNEL_ID、DUCKDB_PATH（デフォルト: data/kabusys.duckdb）、SQLITE_PATH（デフォルト: data/monitoring.db）、KABUSYS_ENV（development/paper_trading/live のバリデーション）、LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL のバリデーション）、ユーティリティプロパティ is_live / is_paper / is_dev。
- AI モジュール（kabusys.ai）
  - news_nlp モジュール（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）でセンチメント評価を行い ai_scores テーブルへ保存。
    - タイムウィンドウの計算（JST 前日 15:00 ～ 当日 08:30 を UTC に変換）。
    - バッチ処理（最大 20 銘柄/リクエスト）、1 銘柄あたり記事数上限・文字数上限でトークン肥大を抑制。
    - JSON Mode での応答受信・検証ロジック（レスポンス復元、スキーマ検証、未知コードの無視、スコアのクリップ）。
    - 再試行ロジック（429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ）とフェイルセーフ（失敗時はスキップして継続）。
    - テスト支援: _call_openai_api を patch して置換可能。
    - レコード書き込みは部分失敗に備え、取得したコード群のみ DELETE → INSERT することで既存データ保護。
  - regime_detector モジュール（kabusys.ai.regime_detector）
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定。
    - prices_daily, raw_news, market_regime を参照し、計算結果を冪等に market_regime テーブルへ書き込み。
    - OpenAI 呼び出しの再試行・例外ハンドリング、API 失敗時は macro_sentiment = 0.0 にフォールバック。
    - ルックアヘッドバイアス対策（date 比較は厳密に target_date 未満条件を使用、datetime.today() を直接参照しない）。
- データ処理・ETL（kabusys.data）
  - pipeline モジュール（kabusys.data.pipeline）
    - 差分取得・保存・品質チェックの基本インターフェース（ETLResult データクラス）を実装。
    - ETLResult に品質問題一覧・エラーメッセージを保持し、辞書化（to_dict）可能。
    - DB テーブルの最大日付取得ユーティリティ等を実装。
  - etl の再エクスポート（kabusys.data.etl）で ETLResult を公開。
  - calendar_management モジュール（kabusys.data.calendar_management）
    - JPX マーケットカレンダー管理（market_calendar）と営業日判定ユーティリティを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar がない場合は曜日ベース（土日除外）でフォールバック。DB 登録値があれば優先。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等更新。バックフィルや健全性チェックを導入。
- Research モジュール（kabusys.research）
  - factor_research: calc_momentum, calc_value, calc_volatility を実装（prices_daily / raw_financials のみ参照）。
    - Momentum: 1M/3M/6M リターン、200日移動平均乖離（データ不足時は None）。
    - Volatility: 20日 ATR、相対 ATR、20日平均売買代金、当日出来高比率。
    - Value: PER/ROE（raw_financials から target_date 以前の最新を取得）。
  - feature_exploration: calc_forward_returns（任意ホライズンの将来リターン取得）、calc_ic（スピアマンのランク相関）、rank（同順位は平均ランク）、factor_summary（基本統計量）。
  - 研究向けユーティリティの公開（kabusys.research.__init__ でまとめてエクスポート）。
- 実装上の設計方針（共通）
  - ルックアヘッドバイアス回避のため datetime.today() / date.today() の直接参照を避ける設計（関数に target_date を注入）。
  - DuckDB を主要なローカルストレージとして想定。書き込みは冪等性を重視（DELETE→INSERT、ON CONFLICT を想定）。
  - OpenAI 呼び出しに対して堅牢な再試行・フェイルセーフを実装。
  - 外部発注・本番 API への接続は含まず、分析・調査・データ基盤に焦点を当てる。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Deprecated
- （初版のため該当なし）

### Security
- API キーやトークン（OPENAI_API_KEY 等）は環境変数から取得する設計。必須項目が未設定の場合は実行前に例外で明示することで誤動作を防止。

### Notes / 注意事項
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（各 AI API 呼び出しを行う機能を使う場合）
- 環境変数の自動読み込み:
  - パッケージロード時にプロジェクトルートから .env / .env.local を自動読み込みします。テストや特殊用途で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI との連携:
  - モデル gpt-4o-mini を前提に JSON Mode を利用したレスポンス解析を行います。API の変更により挙動が変わる可能性があります。
  - テスト時は _call_openai_api をモックすることで外部呼び出しを避けられます（news_nlp と regime_detector で独立して実装済み）。
- データ欠損時のフォールバック:
  - MA 計算に必要なデータが不足する場合やニュースが存在しない場合、明示的なフォールバック値（例: ma200_ratio = 1.0、macro_sentiment = 0.0）を使って処理を継続します。
- DuckDB バージョン差異:
  - executemany に空リストを渡せないなどの互換性考慮がコード内にあり、DuckDB のバージョンによっては挙動差が生じる点に注意してください。
- ルックアヘッド回避:
  - 全てのバッチ処理・スコアリング関数は target_date を外部から与える設計です。実運用では必ず適切な target_date を渡してください。

今後の予定（参考）
- strategy / execution / monitoring パッケージの実装（取引モデル、発注ラッパー、監視アラート等）
- ETL の詳細な品質チェックルールの実装（quality モジュールの充実）
- テストカバレッジ向上（API モック、DuckDB テストフィクスチャ）

-----