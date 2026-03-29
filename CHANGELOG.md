# CHANGELOG

すべての変更は Keep a Changelog の形式に従い、慣例に従って分類しています。  
初期リリースに相当する内容を、ソースコードから推測して日本語でまとめています。

全般:
- パッケージ名: kabusys
- 現行バージョン: 0.1.0
- リリース日: 2026-03-29（コードベース作成日として推定）

## [Unreleased]
（次回以降の変更履歴をここに記載します）

## [0.1.0] - 2026-03-29

Added
- 初期実装の公開（モジュール群を含む）
  - パッケージ公開インターフェース: kabusys.__init__ (version=0.1.0, __all__ に data/strategy/execution/monitoring を定義)
- 環境設定管理
  - kabusys.config
    - .env / .env.local の自動読み込み機能（プロジェクトルートを .git または pyproject.toml から探索）
    - export KEY=VALUE 形式やクォート・コメント処理に対応した .env パーサ実装
    - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート
    - Settings クラスを提供（J-Quants、kabu API、Slack、DBパス、環境種別、ログレベル等のプロパティ）
    - 必須環境変数未設定時に明示的な例外を投げる _require 実装
    - デフォルト DB パス: DUCKDB_PATH= data/kabusys.duckdb, SQLITE_PATH= data/monitoring.db
    - 有効な KABUSYS_ENV 値: development / paper_trading / live
- AI（NLP）機能
  - kabusys.ai.news_nlp
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信して銘柄ごとのセンチメントを算出
    - タイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST 相当）を行う calc_news_window 関数
    - バッチサイズ、文字数上限、記事数上限などハイパーパラメータを採用（バッチ20銘柄、1銘柄3000文字/10記事など）
    - レスポンスの厳格なバリデーションと数値クリップ（±1.0）
    - ネットワークエラー・429・5xx を対象とした指数バックオフリトライ
    - 書き込み: ai_scores テーブルへ (DELETE → INSERT) の冪等更新
    - テスト容易性のため _call_openai_api を差し替え可能
    - score_news(conn, target_date, api_key=None) を公開（戻り値: 書き込んだ銘柄数）
  - kabusys.ai.regime_detector
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）と、ニュース NLP によるマクロセンチメント（重み30%）を合成して日次市場レジーム（bull/neutral/bear）を判定
    - マクロニュース抽出（キーワードベース）と OpenAI への JSON 出力期待によるセンチメント算定
    - API 失敗時はフォールバック macro_sentiment=0.0（フェイルセーフ）
    - DB への書き込みは market_regime テーブルへ冪等（BEGIN/DELETE/INSERT/COMMIT）で実行
    - score_regime(conn, target_date, api_key=None) を公開（戻り値: 1=成功）
- Research（ファクター計算・特徴探索）
  - kabusys.research.factor_research
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）等を計算（prices_daily 参照）
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率等を計算
    - calc_value: raw_financials から最新財務を取得し PER/ROE を算出（prices_daily と結合）
    - 全て DuckDB SQL を用いた実装で外部 API にはアクセスしない
  - kabusys.research.feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）に対する将来リターンを一括で計算
    - calc_ic: スピアマンランク相関（IC）を計算（要するに factor と forward returns の rank 相関）
    - rank: 同順位は平均ランクの実装（丸めで ties 対応）
    - factor_summary: count/mean/std/min/max/median を計算
    - すべて標準ライブラリのみで依存を抑制
- Data（データ基盤ユーティリティ）
  - kabusys.data.calendar_management
    - JPX カレンダー管理（market_calendar テーブル参照）
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供
    - DB データが不十分な場合は曜日ベースでフォールバック（週末は非営業日）
    - calendar_update_job: J-Quants API から差分取得して market_calendar を更新（バックフィル・健全性チェックを実装）
  - kabusys.data.pipeline / etl
    - ETLResult データクラスを公開（ETL 実行結果の構造化）
    - ETL 実行方針: 差分取得、idempotent 保存（ON CONFLICT DO UPDATE）、品質チェック（quality モジュール）などを想定
    - 内部ユーティリティ: テーブル有無チェック、最大日付取得など
  - いくつかの jquants_client / quality など別モジュールに依存しており、それらを通じて外部 API へアクセスする想定
- 実装上の安全策・細かな設計配慮
  - 全モジュールでルックアヘッドバイアスを避ける設計（datetime.today()/date.today() を内部ロジックで直接使わない／明示的に target_date を受け取る）
  - OpenAI 呼び出しは個別モジュール内で独立実装（モジュール間でプライベート関数を共有しない）でテスト差し替え可能
  - DB 書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で安全に行い、ROLLBACK 失敗時もログを出す
  - LLM の応答パース失敗や API 異常時は例外を投げずフォールバック（0.0 やスキップ）して処理を継続する方針
  - DuckDB の executemany に空リストを渡せない問題を回避するためのガード実装あり

Changed
- 初期リリースのため変更履歴なし（新規追加のみ）

Fixed
- 初期リリースのため修正履歴なし

Removed
- 該当なし

Security
- 環境変数の自動読み込み時、OS 環境変数を保護する設計（.env の上書きを制御）
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY により注入。未指定時は ValueError を投げる（明示的な失敗）

Notes / Usage / 要注意点
- 必須環境変数（少なくとも以下をプロジェクト設定または環境に設定しておく必要があります）
  - JQUANTS_REFRESH_TOKEN（J-Quants API 用）
  - KABU_API_PASSWORD（kabu API 用）
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（通知用）
  - OPENAI_API_KEY（AI モジュールを使用する場合）
- .env 自動読み込み
  - プロジェクトルートを .git または pyproject.toml により検出し、.env → .env.local の順で読み込む（.env.local は上書き）
  - テスト等で自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定する
- DB（DuckDB）テーブル前提
  - AI / Research / Data モジュールは内部で以下のテーブルを参照します（存在しない場合は機能しない/フォールバックあり）
    - prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar 等
- OpenAI 呼び出し
  - gpt-4o-mini を利用、JSON Mode を期待してレスポンスを厳密 JSON として処理するが、パース不能時の復元ロジック（最外の {} 抽出）も実装
  - バックオフ・リトライ戦略あり（最大リトライ回数・指数バックオフ）
- フェイルセーフ
  - AI API の失敗時は例外を上位に伝播させず、スコアを 0.0 にフォールバックするなどしてパイプライン全体の停止を防ぐ設計
- テストのしやすさ
  - OpenAI 呼び出し用の内部関数（_call_openai_api）をパッチしてモック化できるためユニットテストが容易

Breaking Changes
- 初回リリースのため breaking changes はありません。

今後の方向性（想定）
- api キー管理の改善、より厳密な型チェック、より詳細な品質チェックルール（quality モジュールの充実）
- モデルやバッチサイズの調整、より堅牢なエラーハンドリング・監視（監視モジュールの実装）
- ETL のスケジューリング/監査ログの強化

Contributors
- コードベースから明示的な著者情報は推測できないため省略

---

この CHANGELOG はソースコードの内容に基づき自動推測して作成しています。実際のリリースノートとして使用する際は、リリース日や変更の優先度・具体的な責任者等をチームポリシーに合わせて編集してください。