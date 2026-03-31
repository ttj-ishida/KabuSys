CHANGELOG
=========
All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and is maintained under
Semantic Versioning.

フォーマット:
- 変更はカテゴリ（Added, Changed, Fixed, Deprecated, Removed, Security）に分類します。
- 日付は YYYY-MM-DD 形式で記載します。

Unreleased
----------
（現在なし）

0.1.0 - 2026-03-31
-----------------
Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージトップレベルを公開（kabusys.__version__ = "0.1.0"）。
  - 公開モジュール: data, strategy, execution, monitoring（__all__ で宣言）。
- 設定/環境変数管理モジュール (kabusys.config)
  - .env ファイルおよび環境変数の自動読み込み機能を実装。
    - プロジェクトルート判定は __file__ を起点に .git または pyproject.toml を探索して行うため CWD に依存しない。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env の行パーサ実装: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント処理に対応。
  - override/protected 指定で OS 環境変数を保護しつつ .env を上書き可能。
  - Settings クラスを提供し、必要な環境変数の取得（必須チェック）や既定値、型変換、バリデーションを行うプロパティを実装。
    - J-Quants / kabu ステーション / Slack / DB パス / 監視閾値 / 環境（development/paper_trading/live）/ログレベルなどをサポート。
    - 不正な KABUSYS_ENV / LOG_LEVEL は ValueError を投げる。
- AI（OpenAI）連携モジュール (kabusys.ai)
  - news_nlp モジュール (kabusys.ai.news_nlp)
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）へ送信。
    - JSON Mode を用いてレスポンスを厳密にパース・バリデーションし、ai_scores テーブルへ idempotent に書き込み（DELETE → INSERT）。
    - バッチ送信（最大 20 銘柄/チャンク）、トークン肥大対策（記事数上限・文字数トリム）を実装。
    - リトライポリシー（429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ）を実装し、フェイルセーフとして失敗時は該当チャンクをスキップして継続。
    - テスト容易性のため _call_openai_api はパッチ差し替え可能。
    - ルックアヘッドバイアスを避けるため datetime.today()/date.today() を参照しない設計。
  - regime_detector モジュール (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）判定を実装。
    - prices_daily / raw_news からデータを取得し、OpenAI（gpt-4o-mini）でマクロセンチメントを取得。API失敗時は macro_sentiment=0.0 で継続。
    - レジームスコア算出後、market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK を試行）。
    - LLM 呼び出しのリトライ/エラー分類や JSON パース失敗のフォールバックを実装。
- データプラットフォーム / ETL (kabusys.data)
  - ETLResult データクラス (kabusys.data.pipeline.ETLResult)
    - ETL 実行結果の集約（取得数/保存数/品質問題/エラー等）と to_dict() による辞書化機能。
  - pipeline モジュール (kabusys.data.pipeline)
    - 差分取得、バックフィル、品質チェックの大枠（設計・ユーティリティ）を実装（jquants_client と quality モジュールとの連携想定）。
    - DuckDB テーブル存在チェック、最大日付取得等のユーティリティを提供。
  - ETL の設計方針として id_token 注入・部分失敗に対する既存データ保護（部分書き換え）等を明確化。
  - calendar_management モジュール (kabusys.data.calendar_management)
    - JPX マーケットカレンダー管理機能を実装。
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days 等の営業日判定ユーティリティ。
      - market_calendar がない場合の曜日ベースフォールバック（週末は非営業日）。
      - calendar_update_job にて J-Quants API から差分取得し冪等保存。バックフィル・先読み・健全性チェックを含む。
    - DB の登録値優先・未登録日は曜日フォールバックという一貫した挙動。
- リサーチ/ファクターモジュール (kabusys.research)
  - factor_research モジュール
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高変化率）、バリュー（PER, ROE）を DuckDB の prices_daily / raw_financials から計算する関数を実装。
    - 欠損データやデータ不足時の扱い（None を返す）を明確化。
    - 関数は外部 API にアクセスしない設計（分析環境向け）。
  - feature_exploration モジュール
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク関数（rank）、ファクター統計サマリ（factor_summary）を実装。
    - calc_forward_returns はホライズンのバリデーション（正の整数かつ <=252）と単一クエリでの効率的取得を実装。
    - calc_ic はスピアマンのランク相関を計算し、データ不足時は None を返す。
  - research パッケージの __init__ で主要関数をエクスポート。
- 共通実装上の注意・品質
  - DuckDB を主要なストレージ層として利用する SQL 実装（DuckDB の互換性配慮あり）。
  - ルックアヘッドバイアス対策: 主要な関数（AI スコアリング、レジーム判定、ETL、リサーチ計算）は内部で現在時刻を参照しない（target_date ベース）。
  - トランザクション処理（BEGIN/COMMIT/ROLLBACK）を行い、ROLLBACK 失敗時はログ出力するなど堅牢性に配慮。
  - OpenAI 呼び出しはモジュール内で独立実装（テスト時に差し替え可能）し、JSON Mode のレスポンス解析と堅牢なバリデーションを実装。
  - エラーハンドリングは「フェイルセーフで継続」が基本（API 失敗時は該当チャンクのスキップやデフォルト値適用）。

Changed
- 初版のため過去バージョンからの変更履歴はなし。

Fixed
- 初版のため修正履歴はなし。

Deprecated
- なし。

Removed
- なし。

Security
- OpenAI API キーは関数引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を発生させ処理を停止（誤用を抑止）。

Notes / 今後の着目点
- strategy / execution / monitoring パッケージの具体実装は本リリースのコードでは限定的または未実装の箇所が見られます。実運用に移す際は発注ロジック・モニタリングループ・安全ガード（rate limiting、注文確認等）を追加してください。
- DuckDB のバインドや executemany の挙動はバージョン差異により影響を受けるため、本番環境では使う DuckDB バージョンでの検証を推奨します。
- OpenAI 呼び出し部分は使用する SDK バージョンやモデル（gpt-4o-mini）に依存するため、SDK の更新に伴う挙動変化に注意してください（status_code の有無などに配慮した実装を行っていますが、将来の互換性確認が必要）。

--- END ---