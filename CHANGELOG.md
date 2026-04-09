Changelog
=========

すべての注目すべき変更点を記録します。
このファイルは Keep a Changelog のフォーマットに準拠しています。
リリース日はコードベースから推測して付与しています。

Unreleased
----------

- (現在のブランチでの未リリース変更はありません)

[0.1.0] - 2026-04-09
--------------------

初回公開リリース。以下の主要機能・実装を含みます。

Added
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。主要サブパッケージとして data, research, ai, （および execution, monitoring, strategy 用の名前空間エクスポート）を提供。

- 設定 / 環境変数管理（kabusys.config）
  - .env / .env.local 自動読み込み機能（プロジェクトルートは .git / pyproject.toml を基準に探索）。
  - .env パーサを実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いに対応）。
  - 読み込み順と上書き戦略: OS 環境変数 > .env.local（override）> .env（非 override）。OS 環境変数は protected として上書き不可。
  - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB パス / PaperTrading / 監視しきい値 / ログ設定 等のプロパティを環境変数から取得・バリデーション（例: PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL）。
  - 必須変数未設定時は ValueError を発生させる _require ユーティリティ。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - score_news(conn, target_date, api_key=None): raw_news と news_symbols を集約し OpenAI（gpt-4o-mini）の JSON モードで銘柄ごとのセンチメントを算出、ai_scores テーブルへ冪等的に書き込む。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供。
    - バッチ処理（最大 20 銘柄/リクエスト）、1 銘柄あたりの記事数／文字数上限（トリミング）、リトライ（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）。
    - レスポンスの厳格なバリデーション（JSON 抽出、results リスト、code と score の検証）、スコアは ±1.0 にクリップ。
    - API 呼び出し箇所はテストで差し替え可能（_call_openai_api のモック）。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - score_regime(conn, target_date, api_key=None): ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して daily レジーム（bull/neutral/bear）を market_regime テーブルへ冪等的に保存。
    - MA 計算は target_date 未満のデータのみ使用（ルックアヘッド防止）、データ不足時は中立（1.0）をフェイルセーフで採用。
    - マクロニュース抽出はキーワードベースで最大件数を制限し、OpenAI 呼び出しはリトライ/フォールバック（失敗時 macro_sentiment = 0.0）。
    - OpenAI クライアント初期化時に api_key を引数から注入可能（テスト容易性）。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。market_calendar テーブルが存在する場合は DB 値優先、未登録日は曜日ベースでフォールバック。
    - カレンダー更新夜間ジョブ calendar_update_job を実装（J-Quants から差分取得、バックフィル、健全性チェック、冪等保存）。探索範囲上限・バックフィル日数等の保護ロジックを実装。
    - DuckDB 互換の型変換ユーティリティ、テーブル存在チェックを実装。

  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを公開（取得件数・保存件数・品質問題・エラー収集・ユーティリティ to_dict）。
    - 差分更新・バックフィル・品質チェック（quality モジュール連携）を行う設計に準拠した骨組み。

- リサーチ / ファクター（kabusys.research）
  - factor_research:
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility(conn, target_date): 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率等を計算。欠測制御あり。
    - calc_value(conn, target_date): raw_financials から最新の財務データ（report_date <= target_date）を取得し PER/ROE を計算。
  - feature_exploration:
    - calc_forward_returns(conn, target_date, horizons=None): 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括クエリで取得。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンランク相関（IC）を計算。有効なレコード数が少ない場合は None。
    - rank(values)、factor_summary(records, columns) 等の統計ユーティリティ。
  - kabusys.research パッケージは一部関数を再エクスポート（zscore_normalize 等）。

- 実装上の注意点 / 設計方針（コードベースに明記）
  - ルックアヘッドバイアス防止のため、datetime.today()/date.today() を直接参照しない実装方針（入力として target_date を受ける）。
  - DB 書き込みは基本的に冪等性を担保（BEGIN / DELETE / INSERT / COMMIT、失敗時の ROLLBACK 試行）。
  - OpenAI 等外部 API 呼び出しはリトライ/エクスポネンシャルバックオフ・フェイルセーフ（API 失敗時はスキップ or neutral にフォールバック）を採用。
  - DuckDB 互換性に配慮した実装（executemany の空リスト回避、list 型バインドの回避等）。
  - ログ出力と警告（データ不足・パース失敗・ROLLBACK 失敗などを詳細にログ化）。
  - テスト容易性を考慮し、外部 API 呼び出し箇所を差し替えられる設計（モジュール内部関数の patch を想定）。

Changed
- 初回リリースのため、過去リリースからの変更は無し。

Fixed
- .env パーサの堅牢化（クォート内のエスケープ、export プレフィックス、インラインコメントの扱いなどを実装）により実運用での環境変数読み込みの信頼性を向上。

Security
- 自動 .env 読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能（テストや CI 向け）。
- .env の上書き時に OS 環境変数を protected として上書き不可にする仕組みを実装（誤って OS の値を .env で上書かない）。

Deprecated
- なし

Removed
- なし

Breaking Changes
- 初回リリースのため互換性の破壊変更はありません。ただし、AI モジュールを利用するには OpenAI API キー（api_key 引数または環境変数 OPENAI_API_KEY）の提供が必須です。api_key 未設定時は ValueError が発生します。

Notes / Migration
- DuckDB のバージョン差異（executemany の空リストやリストバインドの挙動）に注意してください。既存 DB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials, market_regime 等）が必要です。
- Paper Trading の挙動は PAPER_FILL_MODE で制御されます（instant/partial/never/reject のいずれか）。

（以上）