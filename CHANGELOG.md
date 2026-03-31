# Changelog

すべての変更は Keep a Changelog のガイドラインに従って記載しています。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [Unreleased]

## [0.1.0] - 2026-03-31
初回公開リリース。

### Added
- パッケージの基本構成
  - kabusys パッケージのエントリポイントを定義（バージョン: 0.1.0）。__all__ に data, strategy, execution, monitoring を公開。

- 環境変数 / 設定管理 (kabusys.config)
  - .env ファイル（および .env.local）または環境変数から設定を自動読み込みする仕組みを実装。
  - 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に検出。テスト等で無効化可能なフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサーは次の機能をサポート:
    - export KEY=val 形式の対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - インラインコメントの扱い（クォート有無での処理差異）
  - OS 環境変数を保護するための protected キー概念を導入し、.env.local による上書き制御を可能に。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 環境モード（development/paper_trading/live）/ログレベル等の取得とバリデーションを行う。
  - 必須環境変数の未設定時に ValueError を送出（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。

- AI モジュール（kabusys.ai）
  - news_nlp モジュール: raw_news を OpenAI（gpt-4o-mini）でバッチセンチメント評価し、銘柄ごとの ai_scores テーブルへ書き込む機能を実装。
    - ニュース収集ウィンドウ計算（JST を UTC に変換した明確なウィンドウ）。
    - 1銘柄あたりの記事数・文字数上限（トークン肥大化対策）。
    - 最大バッチサイズ、リトライ（429/ネットワーク/タイムアウト/5xx）・指数バックオフ。
    - レスポンスの厳密なバリデーション（JSON 抽出、results 配列、code/score の検証）。
    - スコアは ±1.0 にクリップ。
    - DuckDB（ai_scores/news_symbols/raw_news）への冪等書き込み（DELETE → INSERT）、部分失敗時に既存スコアを保護する実装。
    - テスト容易性のため _call_openai_api の差し替えが可能（unittest.mock.patch を想定）。
    - 空記事や API キー未設定時の安全措置（例外送出やスキップ論理を明示）。
  - regime_detector モジュール: 市場レジーム判定（bull / neutral / bear）を日次で算出して market_regime テーブルへ保存する機能を実装。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成。
    - ma200 計算は target_date 未満のデータのみ使用しルックアヘッドバイアスを回避。
    - マクロニュースはマクロキーワードでフィルタし、LLM（gpt-4o-mini）により -1.0〜1.0 を算出、レスポンスの JSON パースとリトライ処理を実装。
    - API 失敗時は macro_sentiment = 0.0 でのフォールバック（フェイルセーフ）。
    - 計算結果は冪等に market_regime テーブルへ書き込む（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。

- Research（因子計算 / 特徴量探索）モジュール（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR 等）、バリュー（PER, ROE）などのファクター計算関数を提供。
    - DuckDB の SQL とウィンドウ関数を活用し、prices_daily / raw_financials を参照。
    - データ不足時（例: MA200 に必要な行数未満）には None を返す設計。
  - feature_exploration:
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）を1クエリで取得。
    - IC（Spearman の rank 相関）計算、ランク化ユーティリティ（同順位は平均ランク）、ファクター統計サマリー（count/mean/std/min/max/median）を提供。
    - pandas 等に依存せず標準ライブラリ + duckdb で実装。

- Data プラットフォーム（kabusys.data）
  - calendar_management:
    - JPX カレンダー（market_calendar）の夜間バッチ更新ロジック（calendar_update_job）を実装：J-Quants クライアント経由で差分取得 → 冪等保存。
    - 営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を提供。DB にデータがある場合は DB 優先、未登録日は曜日ベースでフォールバック。
    - 探索上限やバックフィル、健全性チェック（極端に将来の last_date を検出した場合のスキップ）を実装。
  - pipeline / etl:
    - ETLResult データクラスと ETL パイプラインの骨格を実装。差分取得、保存、品質チェック（quality モジュールとの連携）を想定。
    - デフォルトの backfill_days、calendar lookahead などの設定を提供。
    - DuckDB のテーブル存在チェック・最大日付取得ユーティリティ等を実装。
  - jquants_client との連携ポイントを想定（fetch/save 関数を利用）。

- テスト性・堅牢性
  - LLM 呼び出し部はテスト用に差し替え可能（_call_openai_api を patch）。
  - API 呼び出しのリトライ・バックオフ処理、5xx とそれ以外の扱いの分離、JSON パース失敗時のフォールバックを実装。
  - ルックアヘッドバイアス防止のため、各モジュールは datetime.today() / date.today() を直接参照しない設計（target_date を明示受け取り）。

### Notes / Usage 注意点
- OpenAI API
  - AI 機能（score_news, score_regime）は OpenAI API キー（OPENAI_API_KEY）を要求。api_key を引数で注入可能。
  - デフォルトモデルは gpt-4o-mini。JSON Mode を期待する設計。
- データベース
  - DuckDB を利用する前提（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar 等のスキーマが必要）。
  - 一部実装は DuckDB のバージョン固有挙動（例: executemany に空リスト不可）を考慮している。
- 環境変数自動読み込み
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - 自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- 安全策
  - API 失敗時は例外を上位に投げるよりも「安全なデフォルト」で継続する設計（例: macro_sentiment=0.0、スコア未取得はスキップ等）。DB 書き込みはトランザクションで保護（失敗時に ROLLBACK）。

### Breaking Changes
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

---

開発・運用における詳細（テーブルスキーマ、J-Quants / OpenAI の具体的な利用制限や課金など）は README や各モジュールの docstring を参照してください。