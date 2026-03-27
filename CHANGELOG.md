Keep a Changelog に準拠した CHANGELOG.md（日本語）を以下に作成しました。

注意: 記載内容は提示されたコードベースのスナップショットから推測してまとめたもので、実際のコミット履歴ではありません。

-------------------------------------------------------------------
# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  
このプロジェクトはセマンティック バージョニングに従います。

## [Unreleased]
- （今後の変更をここに記載）

## [0.1.0] - 2026-03-27
初回公開リリース（機能実装のスナップショット）。主にデータ取得/処理、研究用ファクター計算、AI を用いたニュース評価、および市場レジーム判定のコア機能を提供します。

### 追加
- パッケージ基本情報
  - kabusys パッケージ初期化（__version__ = 0.1.0）。主要サブパッケージを公開: data, research, ai, monitoring, strategy, execution（__all__ に一部記述）。

- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数の読み込み機能を実装。
  - プロジェクトルートの自動検出（.git または pyproject.toml を起点）を実装し、CWD に依存しない自動 .env ロードを実現。
  - .env/.env.local の読み込み優先度（OS 環境 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - export KEY=val やクォート・コメントを考慮した .env パース実装（エスケープ処理含む）。
  - Settings クラスによる型付き設定プロパティを提供（J-Quants / kabu API / Slack / DB パス / 環境判定 / ログレベル等）。
  - 必須環境変数が未設定のときに ValueError を発生させる _require ヘルパー。

- AI 関連（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を用いて銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを算出して ai_scores テーブルへ保存する処理を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算（calc_news_window）。
    - バッチ処理（最大 20 銘柄／リクエスト）、1 銘柄あたり記事数・文字数制限（記事数: 10 件、文字: 3000 文字）。
    - OpenAI 呼び出しのリトライ（429・ネットワーク・タイムアウト・5xx に対する指数バックオフ）実装。
    - レスポンスの厳格なバリデーション（JSON 抽出、results 配列、code/score 検証、数値チェック、±1.0 クリップ）。
    - 部分失敗に備え、ai_scores の更新は該当コードのみ DELETE→INSERT で置換（冪等性・既存スコア保護）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）判定を実装。
    - prices_daily と raw_news を参照して ma200_ratio とマクロニュースタイトルを取得。
    - OpenAI（gpt-4o-mini）呼び出し（JSON 出力期待）、リトライ・フォールバック（API 失敗時は macro_sentiment = 0.0）。
    - ルックアヘッドバイアス対策（内部で date 引数を使用し datetime.today() を参照しない、prices_daily では date < target_date の排他条件等）。
    - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）と失敗時の ROLLBACK 保護。

- 研究用モジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム: 1M/3M/6M リターン、200 日移動平均乖離（ma200_dev）。データ不足時は None を返す設計。
    - ボラティリティ/流動性: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率。
    - バリュー: PER / ROE（raw_financials から直近レコードを参照）。EPS が 0 または欠損なら PER は None。
    - DuckDB 上の SQL ウィンドウ関数を活用した実装（外部 API にはアクセスせず）。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン calc_forward_returns（デフォルト horizons=[1,5,21]）: LEAD を使って複数ホライズンのリターンを一括取得。
    - IC（Information Coefficient）計算 calc_ic: スピアマン相関（ランク）に基づく IC 計算、必要レコード数が不足すると None を返す。
    - 値のランク化ユーティリティ rank（同順位は平均ランク）。
    - 統計サマリー factor_summary（count/mean/std/min/max/median）を標準ライブラリのみで実装。
  - 研究ユーティリティの再エクスポートを __init__ で提供。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを基に営業日判定ロジックを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録値優先、未登録日は曜日ベース（平日は営業日）でフォールバックする一貫した挙動。
    - 夜間バッチ calendar_update_job: J-Quants から差分取得し market_calendar を冪等に更新。バックフィル日数・先読み・健全性チェックを実装。
    - 最大探索範囲やサニティチェック等の安全装置を実装（_MAX_SEARCH_DAYS, _BACKFILL_DAYS, _SANITY_MAX_FUTURE_DAYS）。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - 差分取得 → 保存 → 品質チェックの流れを想定した ETLResult データクラスを実装（取得件数、保存件数、品質問題、エラーリスト等を含む）。
    - _get_max_date 等のヘルパー、テーブル存在確認ユーティリティを実装。
    - エラー・品質問題情報を収集し、呼び出し元が対処を決める設計（Fail-Fast ではない）。
    - kabusys.data.etl から ETLResult を再エクスポート。

- DuckDB を主要データ層として想定
  - 各モジュールは DuckDB 接続（DuckDBPyConnection）を受け取り、prices_daily/raw_news/news_symbols/raw_financials/market_calendar/ai_scores/market_regime などのテーブルを参照・更新する設計。

- OpenAI SDK の利用
  - gpt-4o-mini を想定した Chat Completions 呼び出し（response_format={"type":"json_object"}）を各所で使用。
  - API 呼び出しをラップする内部関数を備え、テスト時に差し替え可能な設計。

### 変更（設計上の重要点・注記）
- ルックアヘッドバイアス対策を徹底
  - AI スコア / レジーム判定 / ファクター計算 / ニュースウィンドウいずれも内部で date 引数（target_date）ベースで処理し、datetime.today()/date.today() を直接参照しない設計。
- フェイルセーフ設定
  - OpenAI API 失敗時は例外を上位に直接投げず、フォールバック値（例: macro_sentiment=0.0）を使用して継続する実装が多い（可用性重視）。
- 部分失敗に対する保護
  - ai_scores や market_regime の更新は対象コード / 日付を絞った削除→挿入で行い、部分失敗時に既存データを不必要に消さない設計。

### 修正（バグフィックス）
- 初回リリースのため、コードベースにおける既知のランタイム修正履歴はなし（今後のリリースで追記予定）。

### 既知の制限 / 注意点
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY に依存。未設定時は ValueError を発生。
- DuckDB の executemany に対する空リストバインドの互換性に配慮したコード（空時は実行しないガードあり）。
- calendar_update_job 等は外部 J-Quants クライアント（jquants_client）実装に依存。外部 API のエラーはログ化して 0 を返す保護あり。
- raw_financials に基づく PER 計算は EPS が 0 または NULL の場合に None を返す。

## 参考（実装上の主な公開 API）
- kabusys.config.settings: Settings 型のインスタンス（各種環境設定プロパティ）
- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None) -> 書き込んだ銘柄数
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None) -> 1（成功）
- kabusys.research.calc_momentum / calc_volatility / calc_value
- kabusys.research.calc_forward_returns / calc_ic / factor_summary / rank
- kabusys.data.calendar_management.is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day / calendar_update_job
- kabusys.data.ETLResult（kabusys.data.etl 経由で再エクスポート）

-------------------------------------------------------------------

今後のリリース案内（例）
- Unreleased:
  - モニタリング・アラート連携（Slack 通知等）の実装・強化
  - strategy / execution モジュールの発注ロジック追加（paper/live モード）
  - 単体テスト・CI 定義の整備
  - ドキュメント・使用例の追加（Quickstart）

-------------------------------------------------------------------
変更点の追加や日付の修正が必要であれば指示ください。