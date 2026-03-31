KEEP A CHANGELOG
All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

Unreleased
----------

- なし

0.1.0 - 2026-03-31
------------------

追加 (Added)
- パッケージ初期リリースを追加
  - パッケージ名: kabusys、バージョン 0.1.0
  - package export: kabusys の __all__ に data, strategy, execution, monitoring を公開

- 環境設定/読み込み機能を追加（kabusys.config）
  - .env ファイルと環境変数の自動ロード機能を実装
    - プロジェクトルート検出: カレントファイル位置から .git または pyproject.toml を辿って判定
    - 読み込み順序: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロード無効化可能（テスト向け）
    - OS 環境変数を protected として上書きを防止
  - .env パーサ実装（export KEY=val、クォート／エスケープ、行末コメント対応）
  - 必須環境変数取得ヘルパー _require と Settings クラスを提供
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID などのプロパティ
    - duckdb/sqlite のデフォルトパス設定
    - KABUSYS_ENV / LOG_LEVEL の値検証（許容値チェック）
    - is_live / is_paper / is_dev のユーティリティプロパティ

- ニュース NLP・AI 関連モジュールを追加（kabusys.ai）
  - news_nlp.score_news
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメントをスコア化
    - バッチ処理（最大 20 銘柄）、記事数／文字数のトリム、429/タイムアウト/5xx に対する指数バックオフリトライ
    - レスポンスの堅牢なバリデーション（JSON 抽出、結果キー検証、未知コード無視、数値チェック）
    - DuckDB への冪等書き込み（DELETE → INSERT、部分失敗時に既存スコアを保護）
    - calc_news_window ヘルパー（タイムウィンドウ: 前日15:00 JST ～ 当日08:30 JST の変換処理）
  - regime_detector.score_regime
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次市場レジーム（bull/neutral/bear）を算出
    - マクロ記事抽出（キーワードリスト）、OpenAI 呼び出し（gpt-4o-mini、JSON Mode）、リトライ／フォールバック（API 失敗時 macro_sentiment=0.0）
    - レジームスコアを market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）
    - 設計上、ルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない実装

- データプラットフォーム関連（kabusys.data）
  - calendar_management
    - JPX カレンダー管理（market_calendar テーブル）
    - 営業日判定、前後営業日取得、期間内営業日列挙、SQ判定、夜間バッチ更新 job（calendar_update_job）
    - DB 未取得時の曜日ベースフォールバック、最大探索日数制限、バックフィルと健全性チェック
  - pipeline / etl
    - ETLResult データクラスを公開（ETL の取得数・保存数・品質チェック結果・エラーの集約）
    - ETL 実行設計: 差分更新、バックフィル、品質チェック（quality モジュールと連携）に対応
    - DuckDB テーブルの最大日付取得やテーブル存在チェック等のユーティリティを実装
  - jquants_client を利用したカレンダー等の取得・保存フローを想定（calendar_update_job で利用）

- リサーチ / ファクター計算機能（kabusys.research）
  - ファクター計算モジュール (factor_research)
    - calc_momentum: 1M/3M/6M リターンと ma200_dev を計算（営業日ベース、データ不足時の挙動明確化）
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算（true_range の NULL 伝播制御）
    - calc_value: raw_financials から最新の財務データを参照して PER / ROE を計算
    - 全関数は prices_daily / raw_financials のみ参照し、本番口座や発注 API へはアクセスしない
  - 特徴量探索 (feature_exploration)
    - calc_forward_returns: 指定ホライズンの将来リターン算出（horizons のバリデーション、単一クエリ実行）
    - calc_ic: スピアマンのランク相関（Information Coefficient）算出（None/不足レコードを除外）
    - rank: 同順位は平均ランクを返すランク関数（丸めにより ties の扱いを安定化）
    - factor_summary: 各ファクター列の基本統計量（count, mean, std, min, max, median）

変更 (Changed)
- 設計方針の明示化
  - ルックアヘッドバイアス防止のため、日付参照は外部引数（target_date）を必須とする実装を徹底
  - OpenAI 呼び出しは JSON Mode を想定し、JSON パース失敗時の救済処理（文字列から最外の {} を抽出）を実装
  - DuckDB 互換性考慮: executemany に空リストを渡さない実装（DuckDB 0.10 の制約回避）

修正 (Fixed)
- エラー耐性の改善
  - OpenAI API 呼び出しでの RateLimit/接続/タイムアウト/5xx を識別して再試行ロジックを追加（指数バックオフ）
  - API レスポンスのパース失敗や検証エラー時は例外を上位へ伝播させずフェイルセーフ（0.0 やスキップ）で継続する挙動を明確化
  - DB 書き込み失敗時に ROLLBACK を試み、ROLLBACK 自体が失敗した場合は警告ログ出力

既知の制約 (Known limitations)
- OpenAI への依存:
  - API キーが未設定だと ValueError を送出する（score_news / score_regime）
  - JSON Mode の応答品質に依存するため稀に LLM 応答パースに失敗する可能性がある（フォールバックで空スコア扱い）
- 一部のモジュール（strategy, execution, monitoring）はパッケージエクスポートに含まれるが、本リリースでの実装はコードベースの他ファイルに依存する可能性がある（本 CHANGELOG は提供されたコードに基づく）

セキュリティ (Security)
- 特になし

注記 (Notes)
- 本リリースでは「挙動の堅牢化」「ルックアヘッドバイアス対策」「DuckDB 互換性確保」「OpenAI 呼び出しのリトライ・検証」の実装に重点を置いています。
- ドキュメント文字列に多数の設計意図を含めており、テスト時は OpenAI 呼び出し部分をパッチして差し替えることを想定しています。