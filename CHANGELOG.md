Keep a Changelog フォーマットに従い、コードベースから推測した変更履歴（初回リリース）を日本語で作成しました。

CHANGELOG.md
=============
すべての変更はセマンティック バージョニングに従います。  
詳しくは https://keepachangelog.com/ja/1.0.0/ を参照してください。

Unreleased
----------
（なし）

0.1.0 - 2026-03-27
-----------------
初回公開リリース。以下の主要機能と実装詳細を含みます。

Added
- パッケージ初期化
  - kabusys パッケージの基本（__version__ = 0.1.0、公開モジュール一覧）を追加。

- 環境変数 / 設定管理（kabusys.config）
  - .env / .env.local を自動ロードする機能を実装（プロジェクトルートは .git / pyproject.toml を基準に探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - 強化された .env パーサー:
    - export プレフィックス対応、クォート（シングル／ダブル）とバックスラッシュエスケープ対応、インラインコメント処理、無効行スキップ。
  - Settings クラスを提供し、J-Quants / kabu ステーション / Slack / DB パス / 実行環境（development/paper_trading/live）/ログレベルなどをプロパティ経由で取得。
  - 必須環境変数未設定時は適切な例外（ValueError）を発生。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメントスコアを算出して ai_scores テーブルへ保存する score_news を実装。
  - タイムウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST を対象（内部では UTC naive datetime を利用）。
  - バッチ処理（最大 20 銘柄/チャンク）、1 銘柄あたり記事数・文字数上限を設定（過大入力をトリム）。
  - API 再試行戦略（429/ネットワーク断/タイムアウト/5xx に対して指数バックオフ）やレスポンス検証ロジックを実装。
  - レスポンスの堅牢なバリデーション（JSON 抽出、results フォーマット検証、スコア数値化、既知コードのみ採用、±1.0 にクリップ）。
  - DuckDB への冪等書き込み（DELETE → INSERT、部分失敗時に既存スコアを保護）。
  - テスト容易性のため API 呼び出し箇所を差し替え可能に実装（_call_openai_api をモック可能）。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（Nikkei 225 連動）200 日移動平均乖離（70%）とマクロニュース LLM センチメント（30%）を組み合わせて日次の市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
  - ma200_ratio 計算、マクロキーワードによる記事抽出、OpenAI 呼び出し（gpt-4o-mini）による macro_sentiment 評価、再試行ポリシー、最終スコアのクリッピングとラベリング。
  - DB への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）と例外時の ROLLBACK 処理。
  - API 失敗やパース失敗時はフェイルセーフとして macro_sentiment=0.0 を使用。

- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER・ROE を計算（EPS が 0 または欠損の扱いは明記）。
  - feature_exploration:
    - calc_forward_returns: 指定 horizon（デフォルト [1,5,21]）で将来リターンを計算（LEAD を利用）。
    - calc_ic: ファクターと将来リターン間のスピアマンランク相関（IC）を計算。
    - rank: 同順位は平均ランクにするランク関数（浮動小数の丸め処理あり）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
  - 設計上、DuckDB 接続を受け取り、prices_daily / raw_financials のみを参照。外部 API や pandas などに依存しない実装。

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days といった市場カレンダー判定ユーティリティを提供。
    - market_calendar が未取得の場合は曜日ベース（土日非営業日）でフォールバックする一貫した挙動。
    - calendar_update_job：J-Quants API から差分でカレンダーを取得し market_calendar を冪等保存（バックフィル、健全性チェックを含む）。
  - ETL パイプライン（pipeline）:
    - ETLResult データクラスを公開（取得件数・保存件数・品質問題・エラー一覧などを報告）。
    - 差分更新・バックフィル・品質チェック等に関するユーティリティを実装（内部で jquants_client や quality モジュールを参照）。
  - jquants_client の呼び出しと save_* による冪等保存を前提とした設計。

Changed
- （初回リリースのため変更履歴は無し）

Fixed
- （初回リリースのため修正履歴は無し）

Security
- （初回リリースのためセキュリティ関連の既知問題なし）

Notes / 実装上の重要ポイント
- ルックアヘッドバイアス回避: いずれのモジュールも内部で datetime.today() / date.today() を参照せず、target_date 引数ベースで処理を行う設計。
- DuckDB を主要なデータストアとして使用。SQL ウィンドウ関数（OVER / LAG / LEAD / ROW_NUMBER 等）を多用。
- OpenAI（gpt-4o-mini）を JSON Mode で利用し、API レスポンスの堅牢な検証とエラー時のフォールバックを実装。
- トランザクション管理: DB 書き込みは BEGIN/COMMIT/ROLLBACK を使用し、例外時に ROLLBACK を試みる。ROLLBACK に失敗した場合はログ出力。
- テスト容易性: OpenAI 呼び出し箇所は内部関数で分離されており、unittest.mock.patch による差し替えが可能。
- .env 読み込みでは OS 環境変数を保護する仕組み（.env.local が override=True でも OS 環境変数が優先される）。

今後の予定（想定）
- Strategy / Execution / Monitoring モジュールの実装拡充（パッケージの __all__ に存在はするが本リリースでは限定的）。
- より詳細な品質チェック・監査ログ・運用監視（Slack 通知連携等）の実装強化。

-----------------------------------------------------------------------------
以上。追加で各モジュールごとの細かな変更やリリース日付の調整が必要であれば教えてください。