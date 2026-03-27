CHANGELOG
=========

フォーマット: Keep a Changelog 準拠  
初版作成日: 2026-03-27

[Unreleased]
-------------

- （なし）

0.1.0 - 2026-03-27
-----------------

Added
- パッケージ初期リリース。
- 基本情報
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - 目的: 日本株向けのデータプラットフォーム・リサーチ・AI補助スコアリング・市場レジーム判定・ETL およびカレンダ管理を含む自動売買支援ライブラリ群の提供。

- 環境設定 (kabusys.config)
  - .env ファイルおよび環境変数からの設定自動読み込み機能を実装。
    - 優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - プロジェクトルート判定は .git または pyproject.toml を起点に行い、CWD に依存しない実装。
  - .env パーサ実装: export 形式、クォートやエスケープ、インラインコメントの取り扱いに対応。
  - Settings クラスを提供（settings インスタンス経由で利用）。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
    - デフォルト値・検証: KABUSYS_ENV (development|paper_trading|live)、LOG_LEVEL (DEBUG|INFO|...)、DB パス（DUCKDB_PATH / SQLITE_PATH）など。
    - ヘルパープロパティ: is_live / is_paper / is_dev。

- AI モジュール (kabusys.ai)
  - ニュースセンチメントスコアリング (news_nlp.score_news)
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）に JSON モードで問い合わせて銘柄毎のセンチメントを算出。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して定義（calc_news_window）。
    - 入力制限・バッチ化: 1 API コールあたり最大 20 銘柄 (_BATCH_SIZE)、1 銘柄あたり最大 10 記事・3000 文字にトリム。
    - 再試行・バックオフ: 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフと最大リトライ。
    - レスポンス検証: JSON パース、"results" 構造検証、スコア数値チェック、±1.0 でクリップ。
    - DB 書き込みは冪等処理（対象コードのみ DELETE → INSERT）で部分失敗時に既存スコアを保護。
    - テストしやすさ: _call_openai_api をパッチ可能。APIキー注入可能（api_key 引数 or OPENAI_API_KEY 環境変数）。
  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - マクロニュース抽出はマクロキーワードリストを使用して raw_news からタイトルを取得。
    - LLM 呼び出しは gpt-4o-mini（JSON 出力）を使用。API 障害時は macro_sentiment=0.0 でフェイルセーフに継続。
    - 計算結果（regime_score, regime_label, ma200_ratio, macro_sentiment）を market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - ルックアヘッドバイアス対策: datetime.today()/date.today() を参照せず、target_date ベースで処理。
    - 再試行/エラー処理: OpenAI API の一般的な例外ハンドリング（RateLimitError 等）とリトライ実装。

- データモジュール (kabusys.data)
  - カレンダー管理 (calendar_management)
    - JPX カレンダーの夜間バッチ更新ロジック（calendar_update_job）を実装。
      - J-Quants API から差分取得→ market_calendar に冪等保存（ON CONFLICT / upsert 想定）。
      - バックフィル・健全性チェック（最大未来日チェック）を実装。
    - 営業日判定ユーティリティを提供:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
      - DB にデータがない場合は曜日ベース（土日除外）でフォールバック。
      - 探索上限（_MAX_SEARCH_DAYS）で無限ループを防止。
  - ETL パイプライン (pipeline.ETLResult と etl の公開)
    - ETLResult データクラスを公開（取得件数、保存件数、品質問題、エラー情報などを保持）。
    - ETL 設計方針: 差分取得、backfill による再取得、品質チェックの収集（Fail-Fast ではなく呼び出し元が判断）をサポート。
  - jquants_client ラッパー経由の差分フェッチ / 保存ワークフローと quality モジュール連携を想定（実際の jquants_client 実装は別モジュール）。

- Research モジュール (kabusys.research)
  - ファクター計算 (research.factor_research)
    - calc_momentum:
      - mom_1m / mom_3m / mom_6m、ma200_dev（200 日 MA に対する乖離）を prices_daily から計算。
      - データ不足時の None ハンドリング。
    - calc_volatility:
      - 20 日 ATR（true range の単純平均）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比率（volume_ratio）を計算。
      - true_range の NULL 伝播制御により欠損の扱いを慎重に実装。
    - calc_value:
      - raw_financials から target_date 以前の最新財務データを取り、PER（price / EPS）と ROE を計算。
  - 特徴量探索 (research.feature_exploration)
    - calc_forward_returns:
      - target_date 終値から指定ホライズン（デフォルト [1,5,21] 営業日）の将来リターンを計算。ホライズンの妥当性チェックあり。
    - calc_ic:
      - ファクター値と将来リターンのスピアマンランク相関（IC）を計算。サンプル不足時は None を返す。
    - rank:
      - 同順位は平均ランク扱いのランク化ユーティリティ（丸めを用いた ties 対応）。
    - factor_summary:
      - count/mean/std/min/max/median を算出する統計サマリー実装。
  - すべて DuckDB 接続を受け取り、prices_daily / raw_financials などの DB テーブルのみ参照する設計（実環境の取引 API へはアクセスしない）。

Security / Reliability / Testing
- OpenAI API 呼び出しは JSON モードを利用し、レスポンスの堅牢なパースとバリデーションを実装。
- API 呼び出し部はパッチで置き換え可能（ユニットテスト容易化）。
- ルックアヘッドバイアス防止のため date の扱いに注意（datetime.today() 等は使用しない）。
- DB 書き込みは冪等性を重視（DELETE → INSERT パターンや ON CONFLICT 想定）。
- 各種フォールバック（カレンダー未取得時、API 異常時の既定値）により処理継続性を確保。

Known limitations / Notes
- 実際の外部クライアント（J-Quants、kabuステーション、Slack、OpenAI）の具体的な実装やネットワーク設定は本コードベース外。環境変数（トークン/キー等）の設定が必要。
- ai モジュールは gpt-4o-mini を想定しており、OpenAI SDK のバージョン差分（status_code 等）への互換処理を導入しているが、将来の SDK 変更に注意。
- 一部 SQL の挙動（DuckDB のバージョン差）に配慮した実装（executemany の空リスト制約や配列バインドの互換性回避）が含まれる。
- 日付の扱いはすべて naive な date / datetime（UTC 想定での比較が多いため運用時の timezone に注意）。

効能
- 日本株向けのデータ収集／品質チェック／ファクター算出／ニュース由来の AI スコアリング／市場レジーム判定を一貫して実行するための基盤を提供します。

----- 

注: 本 CHANGELOG は提供されたソースコードから推測して作成しています。実際のリリースノート作成時はリリース日付、コミットハッシュ、追加の破壊的変更や移行手順、既知のバグ等をプロジェクト実態に合わせて追記してください。