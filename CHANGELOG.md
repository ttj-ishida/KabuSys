CHANGELOG
=========

すべての注目すべき変更はこのファイルに記載します。
このプロジェクトは Keep a Changelog のガイドラインに準拠しています。
セマンティックバージョニングを使用します。

0.1.0 - 2026-03-29
------------------

Added
- 初回リリース: KabuSys — 日本株自動売買／リサーチ用ライブラリのベース実装を追加。
  - パッケージ構成:
    - kabusys.config: 環境変数／設定読み込みユーティリティを提供。
      - .env / .env.local の自動読み込み（プロジェクトルート検出 .git / pyproject.toml）。
      - export KEY=val 形式、シングル／ダブルクォート、エスケープ、行内コメント対応のパーサ実装。
      - OS環境変数を保護する protected キーの仕組み。
      - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数の導入。
      - Settings クラスを公開（必要な環境変数の要求、既定値、バリデーション）。
    - kabusys.ai:
      - news_nlp.score_news:
        - raw_news / news_symbols を集約して銘柄ごとにニュースを結合し、OpenAI（gpt-4o-mini）でセンチメントを評価。
        - バッチ処理（最大 20 銘柄/APIコール）、トークン肥大対策（記事・文字数トリム）。
        - レート制限・ネットワーク断・5xx に対する指数バックオフリトライ、レスポンス検証、スコアのクリップ。
        - DuckDB への冪等的な書き込み（DELETE → INSERT）と部分失敗時の既存データ保護。
      - regime_detector.score_regime:
        - ETF 1321 の 200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム判定（bull/neutral/bear）。
        - マクロキーワードによる記事抽出、OpenAI 呼び出し（JSON モード）およびフェイルセーフ（API失敗時 macro_sentiment=0.0）。
        - レジームスコア計算、DuckDB への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）とロールバック処理。
      - 共通設計:
        - datetime.today()/date.today() を直接参照しない実装方針（ルックアヘッドバイアス回避）。
        - 単体テスト用に _call_openai_api をパッチ可能に設計。
    - kabusys.data:
      - calendar_management:
        - JPX カレンダー管理（market_calendar テーブル）と営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
        - DB 登録値優先、未登録日は曜日ベースのフォールバック、最大探索日数制限による安全性確保。
        - 夜間バッチ calendar_update_job: J-Quants API から差分取得・バックフィル・健全性チェック・保存処理。
      - pipeline / etl:
        - ETLResult データクラス（ETL 実行結果の構造化、品質問題・エラー収集）。
        - 差分更新や最終取得日の判定ユーティリティ（_get_max_date 等）。
      - jquants_client を介した差分取得と保存を想定する設計（実際のクライアント実装は別モジュール）。
    - kabusys.research:
      - factor_research:
        - calc_momentum: 1M/3M/6M リターン、ma200 乖離を計算（データ不足時は None／警告）。
        - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率などを計算（欠損時の扱いあり）。
        - calc_value: raw_financials から EPS/ROE を組合せて PER/ROE を計算（EPS=0/NULL の扱い含む）。
      - feature_exploration:
        - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
        - calc_ic: スピアマンのランク相関（IC）計算（欠損／データ不足時の None 戻し）。
        - rank, factor_summary: ランキング（同順位平均ランク）と統計サマリー集計。
    - 共通:
      - DuckDB を主要なローカルデータストアとして使用するクエリ実装。
      - ロギングを広く利用し処理状況・フォールバック・警告を記録。
      - トランザクション制御とロールバック保護（DB 書き込み時の堅牢性）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- 環境変数の自動ロード時に OS 環境変数を上書きしない保護（protected set）を導入。
- 必須トークン（OpenAI / Slack / J-Quants 等）は Settings で明示的に要求。未設定時は ValueError を送出して安全に失敗。

Notes / Limitations
- OpenAI API（gpt-4o-mini）および J-Quants API に依存。実行には各 API キーの設定が必要（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN 等）。
- DuckDB 上に想定スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials など）が存在することが前提。
- news_nlp/regime_detector の LLM 呼び出しは JSON モードのレスポンスを期待しており、API 仕様変更時に影響を受ける可能性あり。
- 日付処理は UTC naive / JST を意識したウィンドウ設計（news ウィンドウの UTC 変換等）。タイムゾーン混在に注意。
- DuckDB の executemany に空リストを渡せない制約に対応した実装（空時は呼び出しをスキップ）。

Upgrade / Migration Notes
- 既存の環境でこのライブラリを導入する場合:
  - 必須環境変数を設定 (.env/.env.local または OS 環境)：OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等。
  - DuckDB に必要なテーブルスキーマを用意してください（ETL/pipeline ドキュメントを参照）。
  - 自動 .env ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

今後の予定（参考）
- ドキュメント整備（関数ごとの使用例・スキーマ定義）
- テストカバレッジ拡充（特に OpenAI 呼び出しのモックと DuckDB 周り）
- OpenAI モデルの選択肢追加とレスポンス検証強化
- ETL の並列化やパフォーマンス改善

ライセンス
- （この CHANGELOG ではライセンスの変更履歴は含めていません。実コードのライセンスを参照してください。）