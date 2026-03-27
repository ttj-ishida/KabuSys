# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
このプロジェクトは Semantic Versioning に従います。

## [Unreleased]

## [0.1.0] - 2026-03-27

### Added
- 初回公開リリース。
- パッケージ概要
  - kabusys: 日本株自動売買システムの基礎モジュール群を提供。
  - パッケージバージョン: `0.1.0`（src/kabusys/__init__.py）。
- 設定/環境変数管理（src/kabusys/config.py）
  - .env および .env.local からの自動読み込み機能（優先順: OS 環境 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込みの無効化。
  - .env ファイルパーサは `export KEY=val` 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行末コメント対応を実装。
  - 環境変数の必須取得ヘルパー `_require` と Settings クラスを提供（J-Quants、kabu、Slack、DB パスなどの設定プロパティ）。
  - KABUSYS_ENV と LOG_LEVEL の入力検証（許容値のチェック、無効値で ValueError を投げる）。
- AI（自然言語処理）モジュール（src/kabusys/ai）
  - ニュースセンチメント解析（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を読み、銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini）へ送信し、ai_scores テーブルへ書き込み。
    - 時間ウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST）のユーティリティ `calc_news_window` を提供。
    - バッチ処理（1APIコールあたり最大 20 銘柄）、1銘柄あたりの最大記事数/文字数のトリム、JSON Mode レスポンスの堅牢なパース・バリデーションを実装。
    - リトライ戦略（429, ネットワーク, タイムアウト, 5xx に対する指数バックオフ）と失敗時のフェイルセーフ（部分失敗時に他コードの既存スコアを保護するため DELETE→INSERT を限定的に実行）。
    - テスト容易性のため `_call_openai_api` を patch 可能に設計。
    - 公開 API: `score_news(conn, target_date, api_key=None)`（成功時は書き込み銘柄数を返す）。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース由来の LLM センチメント（重み 30%）を合成して、日次で市場レジーム（bull/neutral/bear）を算出。
    - DuckDB の prices_daily / raw_news を参照し、計算結果を market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - API 呼び出し失敗時は macro_sentiment = 0.0 で継続（フェイルセーフ）。OpenAI 呼び出しは独立実装でモジュール結合を避ける。
    - 公開 API: `score_regime(conn, target_date, api_key=None)`（成功時 1 を返す）。
- データプラットフォーム（src/kabusys/data）
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルの利用、未取得時は曜日ベースのフォールバック（土日除外）。
    - 営業日判定ユーティリティ: `is_trading_day`, `is_sq_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days` を提供。
    - 夜間バッチジョブ `calendar_update_job(conn, lookahead_days=90)`：J-Quants から差分取得し冪等に保存（バックフィル、健全性チェックを実装）。
  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - 差分取得／保存／品質チェックの設計を反映した ETLResult データクラスを公開（ETL メソッド実装のインターフェース）。
    - ETLResult は target_date, fetched/saved カウント、quality_issues, errors を保持し、辞書変換メソッドを提供。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得など。
- リサーチ（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Value（PER/ROE）、Volatility（20日 ATR）、Liquidity（平均売買代金・出来高変化率）を計算する関数群を提供: `calc_momentum`, `calc_value`, `calc_volatility`。
    - DuckDB を用いた SQL 中心の実装で、prices_daily / raw_financials のみ参照。データ不足時の None ハンドリングを実装。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算: `calc_forward_returns(conn, target_date, horizons=None)`（デフォルト horizons=[1,5,21]）。
    - IC（Information Coefficient）計算: `calc_ic(factor_records, forward_records, factor_col, return_col)`（スピアマンのランク相関）。
    - ランク変換ユーティリティ `rank(values)`（同順位は平均ランク）。
    - 統計サマリー: `factor_summary(records, columns)`（count/mean/std/min/max/median を計算）。
- その他
  - 複数モジュールにおいて「ルックアヘッドバイアス防止」の設計を徹底（datetime.today()/date.today() を参照しない、target_date 未満/以前の限定的データ使用）。
  - DuckDB をデータ処理の主ストアとして想定し、互換性を考慮した実装（executemany の空リスト制約対応など）。
  - ロギングと警告メッセージを充実させ、健全性チェック・リトライの詳細ログを出力。

### Changed
- N/A（初回リリース）

### Fixed
- N/A（初回リリース）

### Removed
- N/A（初回リリース）

### Security
- 環境変数の読み込みは OS 環境変数を保護する仕組みを用意（.env 上書き時に保護セットを考慮）。
- OpenAI API キーは引数で注入可能で、環境変数 OPENAI_API_KEY にフォールバックする設計（テスト時は空文字列扱いに注意）。

---

注意:
- 実装は DuckDB 接続オブジェクトを引数に取る設計のため、実行には適切な DB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials, market_regime など）の事前準備が必要です。
- OpenAI 呼び出し部分は実稼働で API キーと通信環境が必要です。テスト時は各モジュールの `_call_openai_api` をモックすることを推奨します。