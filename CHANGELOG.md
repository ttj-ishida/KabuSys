# CHANGELOG

全ての重要な変更は Keep a Changelog のガイドラインに従って記載しています。  
リリース日はコード内容と本日の日付に基づいて推測しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-09
初期リリース

### Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョン: 0.1.0
  - 公開モジュール: data, strategy, execution, monitoring を __all__ で公開（参照インターフェース）

- 設定 / 環境変数管理 (kabusys.config)
  - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用途）。
  - .env パーサーは export KEY=val 形式、クォート内のバックスラッシュエスケープ、行内コメント扱い等に対応。
  - protected（OS 環境変数）を考慮した override ロジック。
  - Settings クラスを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等の必須/任意項目をプロパティで取得。
    - DB パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）、PID / kill flag 関連、リソース閾値（CPU/MEM/DISK）など多数の設定をプロパティ化。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
    - KABUSYS_ENV のバリデーション（development, paper_trading, live）。
    - LOG_LEVEL のバリデーション（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- ニュース NLP & 市場レジーム判定（kabusys.ai）
  - news_nlp.score_news:
    - raw_news と news_symbols を集約し、銘柄毎のニュースを OpenAI（gpt-4o-mini, JSON mode）へ送信してセンチメントを算出。
    - バッチ処理（最大 20 銘柄/チャンク）、記事トリム（最大記事数・最大文字数）を実装。
    - 429 / 接続断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。
    - レスポンスの厳密なバリデーションとスコアの ±1.0 クリップ。
    - DuckDB への冪等書き込み（DELETE→INSERT、executemany を使用）。DuckDB 互換性のため空パラメータ回避。
    - タイムウィンドウ: JST 基準で「前日 15:00 〜 当日 08:30」を UTC に変換して比較（ルックアヘッドバイアス対策）。
    - API キー注入（引数または環境変数 OPENAI_API_KEY）。未設定時は ValueError。
    - フェイルセーフ: API エラー時は該当チャンクをスキップして処理継続。
  - regime_detector.score_regime:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、news_nlp ベースのマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出。
    - ma200_ratio の計算は target_date 未満のデータのみを使用（ルックアヘッド排除）。
    - マクロ記事はキーワードフィルタで抽出（日本・米国などの主要キーワード集合）。
    - OpenAI 呼び出しは専用ラッパーを使用、JSON パース失敗や API 障害時は macro_sentiment=0.0 にフォールバック。
    - スコア合成後、market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。DB 書き込み失敗時はロールバックし例外を伝播。

- Research（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日 MA 乖離）を DuckDB SQL で計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR（true range を考慮） / atr_pct / avg_turnover / volume_ratio を計算。窓内データ不足を考慮。
    - calc_value: raw_financials から最新財務を取得し PER / ROE を計算（EPS が 0/欠損のときは None）。
    - 全関数は prices_daily / raw_financials のみを参照し、外部 API にはアクセスしない設計。
  - 特徴量探索（kabusys.research.feature_exploration）:
    - calc_forward_returns: リード関数で複数ホライズン（デフォルト [1,5,21]）の将来リターンをまとめて算出。ホライズン検証あり（1〜252）。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算。データ不足（<3）時は None。
    - rank: 同順位は平均ランクで処理（浮動小数誤差対処のため round を使用）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリ。
  - research パッケージは主要関数を __all__ で再公開。

- Data プラットフォーム（kabusys.data）
  - calendar_management:
    - JPX マーケットカレンダーを管理。is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day のユーティリティを提供。
    - market_calendar が未取得の場合は曜日ベースで土日を非営業日扱いするフォールバックを採用。
    - next/prev/get_trading_days は DB 登録値を優先し、未登録日は曜日フォールバックで一貫性を保つ。
    - calendar_update_job: J-Quants API から差分取得・バックフィル（直近日数）を行い、save_market_calendar を使って冪等保存。健全性チェック（将来日付の異常検出）を実装。
  - ETL パイプライン（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult データクラスを公開（取得件数・保存件数・品質問題・エラーメッセージ等を含む）。
    - 差分更新、バックフィル、品質チェック（quality モジュールとの統合）に基づく設計方針を採用。
    - jquants_client を介した取得/保存で冪等性を考慮。
    - デフォルトのバックフィル / カレンダー先読み等の定数を定義。

### Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY から取得。README 等に API キー管理方法の明示を推奨。

### Notes / Implementation Details
- ルックアヘッドバイアス防止: 各種処理で datetime.today()/date.today() を直接参照しない方針（target_date ベース）。
- DuckDB 互換性: executemany に空リストを渡さない等の実装上の配慮。
- ロギング: 各主要処理で INFO/DEBUG/WARNING/EXCEPTION ログを出力。
- フェイルセーフ設計: 外部 API (OpenAI / J-Quants) の失敗時は例外を無闇に上げず一部フォールバック・スキップして全体処理を継続する箇所が多い（運用上の可用性優先）。

---

（注）上記はリポジトリに含まれるコードの内容から推測して作成した初期リリースの CHANGELOG です。実際のリリース日・追加機能・既知の問題についてはリポジトリのリリース履歴やリリースノートを参照してください。