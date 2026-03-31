# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
このプロジェクトはセマンティックバージョニングを使用します。

- リリース日付の形式: YYYY-MM-DD
- 参照: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-03-31
初回リリース

### Added
- パッケージ基盤
  - パッケージ名: kabusys (バージョン 0.1.0)
  - パッケージの公開 API を __all__ で定義: data, strategy, execution, monitoring （src/kabusys/__init__.py）。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能（テスト用途）。
    - プロジェクトルート検出: .git または pyproject.toml を基準に探す（__file__ を起点に探索して CWD に依存しない）。
  - .env パーサを実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理をサポート）。
  - 環境変数の読み込み時に既存 OS 環境変数を保護する protected 機能を実装（上書き制御）。
  - Settings クラスを追加し、アプリケーションで利用する主要設定値をプロパティで提供。
    - J-Quants / kabuステーション / Slack / DB パス / 環境種別（development/paper_trading/live）/ログレベル 等を収集。
    - 必須 env は未設定時に ValueError を送出する _require 実装。
    - env / log_level のバリデーション（許容値チェック）と利便性プロパティ is_live / is_paper / is_dev を提供。

- AI（ニュース NLP / レジーム判定） (src/kabusys/ai/)
  - ニュース NLP スコアリングモジュール (src/kabusys/ai/news_nlp.py)
    - raw_news / news_symbols テーブルを元に銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメントを算出。
    - タイムウィンドウ: JST 前日 15:00 ～ 当日 08:30（内部は UTC naive で計算）を calc_news_window で提供。
    - バッチ処理: 1 API コールで最大 20 銘柄（_BATCH_SIZE）。
    - 1 銘柄あたりの最大記事数・文字数制限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）を実装してトークン肥大化に対応。
    - リトライ戦略: 429/ネットワーク断/タイムアウト/5xx を対象に指数バックオフでリトライ。
    - レスポンスバリデーション: JSON 抽出、"results" フォーマット検証、未知コード無視、スコアを ±1.0 にクリップ。
    - DB 書き込みは冪等的に DELETE → INSERT を実行し、部分失敗時に既存データを保護。
    - テスト容易性: OpenAI 呼び出し部分を _call_openai_api で抽象化し unittest.mock.patch で差し替え可能。
  - 市場レジーム判定モジュール (src/kabusys/ai/regime_detector.py)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とニュースマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - ma200_ratio 計算（200 日分の終値を使用、データ不足時は中立扱い）。
    - マクロキーワードで raw_news をフィルタしてタイトルを取得し、OpenAI（gpt-4o-mini）で macro_sentiment を算出（記事がない場合は LLM 呼び出しをスキップして 0.0 を採用）。
    - API 呼び出しはリトライ（429/ネットワーク断/タイムアウト/5xx）し、失敗時は macro_sentiment=0.0 としてフォールバック（例外にせず継続）。
    - 判定結果は market_regime テーブルへ冪等（BEGIN/DELETE/INSERT/COMMIT）で書き込み。
    - テスト容易性・モジュール分離のため OpenAI 呼び出しは内部で独立実装。

- Research（ファクター計算・特徴量探索） (src/kabusys/research/)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を calc_momentum で実装（営業日ベースのラグ）。
    - Volatility & Liquidity: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比（volume_ratio）を calc_volatility で実装。true_range の NULL 伝播制御あり。
    - Value: raw_financials から最新財務を取得して PER/ROE を calc_value で実装（EPS が 0/欠損時は None）。
    - DuckDB を用いた SQL 集約実装。関数は prices_daily / raw_financials のみ参照し、実行環境の取引・発注 API には影響しない設計。
  - 特徴量探索ユーティリティ (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算: calc_forward_returns で指定ホライズン（デフォルト [1,5,21]）の fwd_*d を算出。horizons の検証あり。
    - IC（Information Coefficient）計算: calc_ic で Spearman の ρ（ランク相関）を実装。十分なサンプルがない場合は None を返す。
    - ランク関数: rank は同順位の平均ランクを扱い、浮動小数点丸めで ties を安定化。
    - 統計サマリー: factor_summary で count/mean/std/min/max/median を計算。
  - research パッケージは zscore_normalize（kabusys.data.stats から）を再輸出。

- Data プラットフォーム (src/kabusys/data/)
  - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスを実装し、ETL 実行結果（取得数・保存数・品質問題・エラー）を集約。
    - 差分更新、backfill、品質チェック（quality モジュール）を想定した設計。_get_max_date 等のユーティリティ実装。
    - etl モジュールは ETLResult を再エクスポート。
  - マーケットカレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar テーブルを利用した営業日判定ユーティリティを提供:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB に値がない場合は曜日ベースのフォールバック（週末を非営業日）を採用して一貫性を保つ設計。
    - calendar_update_job を実装し、J-Quants API から差分取得 → market_calendar へ冪等保存（バックフィル・健全性チェック付き）。
    - 最大探索日数・ルックアヘッド日数等の安全制約を導入（_MAX_SEARCH_DAYS, _CALENDAR_LOOKAHEAD_DAYS, _BACKFILL_DAYS, _SANITY_MAX_FUTURE_DAYS）。
    - jquants_client を利用して外部 API 呼び出しを抽象化（fetch/save 関数を想定）。
  - DuckDB を中心とした内部クエリ実装を採用（全体で DuckDBPyConnection を受け渡す設計）。

- 共通設計ポリシー（各所での共通点）
  - ルックアヘッドバイアス対策: どのモジュールも内部で datetime.today()/date.today() を参照しない設計（target_date を明示的に受け取る）。
  - フェイルセーフ: 外部 API（OpenAI, J-Quants 等）の失敗時は可能な限り例外を露呈させずフォールバックやスキップで継続。DB 書き込み失敗時のみ例外を伝播（ROLLBACK 対応）。
  - テスト容易性: OpenAI 呼び出し等を差し替え可能にしユニットテストを容易化。
  - ロギング: 重要な分岐・エラー・警告にログを出力する実装が多くの関数に組み込まれている。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Deprecated
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- 初回リリースのため該当なし。

---

補足:
- コード中で OpenAI SDK（OpenAI クライアント）と J-Quants クライアントを想定しており、API キーは環境変数 OPENAI_API_KEY をデフォルトで参照する実装になっています。実行時には該当環境変数や .env の整備が必要です。
- DB は DuckDB 想定。ai 系処理はレスポンス JSON の厳密なフォーマット（JSON Mode）を期待していますが、堅牢化のため前後の余計なテキスト混入への対処コードも実装済みです。