CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。本プロジェクトは Keep a Changelog の形式に準拠し、セマンティックバージョニングを採用しています。

[Unreleased]
------------

- 現在未リリースの変更はありません。

[0.1.0] - 2026-03-31
-------------------

初回公開リリース。以下の機能群・モジュールを実装しています。

Added
- パッケージ初期化
  - kabusys パッケージの __version__ を "0.1.0" として定義。
  - 公開モジュール一覧を __all__ で宣言（data, strategy, execution, monitoring）。

- 設定管理 (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動検出して読み込む自動ロード機能を実装。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサーは export 形式・クォート・エスケープ・インラインコメントに対応。
  - Settings クラスを提供し、アプリケーション設定（J-Quants トークン、kabuステーション API、Slack、DB パス、監視閾値、環境 / ログレベル判定等）をプロパティ経由で取得できる。未設定の必須値は ValueError を発生させる。
  - 環境変数値のバリデーション（KABUSYS_ENV, LOG_LEVEL）を実装。

- AI モジュール (kabusys.ai)
  - news_nlp:
    - raw_news / news_symbols を元にニュースを銘柄ごとに集約し、OpenAI（gpt-4o-mini + JSON mode）へバッチ送信して銘柄ごとのセンチメント（ai_score）を算出。
    - バッチ処理（同時最大銘柄数 20）・1銘柄あたりの記事数/文字数制限・JSON レスポンスバリデーションを実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフのリトライを実装。レスポンスパース失敗等はログ出力のうえスキップ（フェイルセーフ）。
    - calc_news_window 関数でニュース集計ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST を UTC で表現）を計算。
    - AI 呼び出し箇所はテスト容易性のため差し替え可能（_call_openai_api をモック可能）。
    - DuckDB への書き込みは冪等性を保つ（対象コードのみ DELETE → INSERT）。DuckDB の executemany の制約を考慮。

  - regime_detector:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を算出し market_regime テーブルへ書き込む処理を実装。
    - LLM 呼び出しは gpt-4o-mini を使用、応答は JSON として期待。API エラーやパースエラー時は macro_sentiment=0.0 にフォールバック。
    - retry ポリシー・ログ、DB 側の BEGIN / DELETE / INSERT / COMMIT による冪等書き込みを実装。
    - テスト容易性のため _call_openai_api は独自実装で差し替え可能（news_nlp と共有しない設計）。

- 研究用 (kabusys.research)
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高変化率）、バリュー（PER・ROE）の計算関数を実装。
    - DuckDB の SQL ウィンドウ関数を活用し、prices_daily / raw_financials から直接計算。データ不足時は None を返す挙動。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns：任意ホライズンのリードを使用）、IC（calc_ic：スピアマンランク相関）、ランク変換ユーティリティ（rank）、および統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリのみで実装。
  - kabusys.research パッケージとして主要ユーティリティを再エクスポート。

- データ層 (kabusys.data)
  - calendar_management:
    - market_calendar を用いた営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。DB が未取得の場合は曜日ベースのフォールバック（平日を営業日）を使用。
    - calendar_update_job により J-Quants API からの差分取得と冪等保存を行うジョブを実装。バックフィルや健全性チェックを含む。
  - pipeline / etl:
    - ETLResult データクラスを実装し ETL 実行結果を構造化して返す。品質チェック結果・エラーを格納可能。
    - ETL パイプラインの設計に沿ったユーティリティ（差分取得、保存、品質チェック呼び出し）を実装するための下地を用意。
  - etl.py で ETLResult を再エクスポート。

- 他
  - モジュール設計上の共通方針として、処理内で datetime.today() / date.today() を直接参照しない（ルックアヘッドバイアス回避）点を明記・実装。
  - ロギングを多用し、失敗時には例外を破棄せず上位に伝播する/フェイルセーフで続行する箇所を適切に使い分け。

Changed
- 初回リリースのため「追加（Added）」中心で変更履歴はありません。

Fixed
- 初回リリースのため「修正（Fixed）」の履歴はありません。

Known limitations / 注意事項
- OpenAI API のキー（OPENAI_API_KEY）や各種必須環境変数（JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD 等）は Settings を通じて必須チェックされます。未設定時は ValueError が発生します。
- DuckDB と OpenAI Python SDK（および必要な依存）が環境に必要です。
- 一部の DB バインド（DuckDB executemany の空リスト問題等）に配慮した実装になっていますが、利用する DuckDB のバージョンによって挙動が差異を示す可能性があります。
- AI 呼び出し部分は API 利用料・レイテンシを伴います。ローカルテストでは _call_openai_api をモックすることを推奨します。

Migrating
- 初回リリースのためマイグレーションはありません。

Contributing
- バグ報告・改善提案は Issue を立ててください。テスト可能性を重視した実装が行われているため、ユニットテストやモックを用いたテストを歓迎します。

ライセンスやその他のメタ情報はリポジトリのルート（pyproject.toml / LICENSE 等）を参照してください。