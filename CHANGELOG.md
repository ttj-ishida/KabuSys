# CHANGELOG

すべての変更は Keep a Changelog の形式に従い、セマンティックバージョニングを使用します。  
このファイルはコードベース（src/kabusys 以下）の現在の実装に基づいて推測して作成しています。

※日付は本ファイル作成時点です。

## [Unreleased]

- 今後のリリースで追加・変更予定の項目を記載してください。

## [0.1.0] - 2026-04-01

初期公開リリース（推定）。以下の主要機能と実装方針を含みます。

### 追加 (Added)
- パッケージ概要
  - kabusys パッケージの初期実装。バージョンは 0.1.0。
- 設定管理 (kabusys.config)
  - .env / .env.local ファイルおよび OS 環境変数から設定を自動読み込み（プロジェクトルート判定: .git または pyproject.toml）。
  - 自動読み込みを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数のサポート。
  - .env パーサの実装（export 形式、シングル/ダブルクォート、エスケープ、行内コメント対応）。
  - 必須設定取得用 Settings クラス（J-Quants、kabuステーション、Slack、DB パス、監視閾値、環境・ログレベル判定など）。
  - デフォルト値（例: KABUS_API_BASE_URL、DUCKDB_PATH、PID_FILE_PATH、閾値等）を提供。
  - KABUSYS_ENV 値のバリデーション（development / paper_trading / live）および LOG_LEVEL の検証。

- AI（自然言語処理）モジュール (kabusys.ai)
  - news_nlp モジュール（score_news）
    - raw_news と news_symbols を集約し、銘柄単位で OpenAI（gpt-4o-mini）にバッチ送信してセンチメントスコアを算出。
    - タイムウィンドウ定義（前日15:00 JST ～ 当日08:30 JST を UTC に変換して使用）。
    - バッチサイズ、記事トリム、文字数上限、最大リトライ、指数バックオフ等の定義。
    - レスポンスの厳密バリデーション（JSON 抽出、results 配列、コード照合、スコア数値化、クリップ）。
    - 部分成功時の DB 更新戦略（該当コードのみ DELETE → INSERT）により既存スコアを保護。
    - テスト用に API 呼び出し箇所をモック可能（内部 _call_openai_api を patch できる設計）。
  - regime_detector モジュール（score_regime）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を組み合わせて日次で市場レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news を参照し、OpenAI を用いたマクロセンチメント評価を行う（gpt-4o-mini、JSON mode）。
    - API エラー時はフォールバック（macro_sentiment = 0.0）して処理継続するフェイルセーフ。
    - レジーム結果は market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - LLM 呼び出しは独立実装でモジュール間の結合を避ける設計。
- データ（Data Platform）モジュール (kabusys.data)
  - calendar_management
    - JPX カレンダー管理ロジック（market_calendar テーブルの参照、営業日判定、next/prev/get_trading_days、is_sq_day）。
    - DB 未取得時の曜日ベースフォールバック（週末は非営業日）。
    - 夜間バッチ calendar_update_job：J-Quants から差分取得して保存（バックフィル、健全性チェック、異常時スキップ）。
  - pipeline / etl
    - ETLResult データクラスを公開（ETL 実行結果の構造化: フェッチ/保存件数、品質問題、エラー等）。
    - ETL パイプライン方針（差分更新、backfill、品質チェックの収集と継続方針、id_token 注入可能など）。
    - 内部ユーティリティ（テーブル存在チェック、最大日付取得など）。
  - jquants_client 等（参照用クライアントモジュールと連携する想定）。
- リサーチ（研究）モジュール (kabusys.research)
  - factor_research
    - モメンタム (1/3/6ヶ月)、200日MA乖離、ATR/相対ATR、20日平均出来高・出来高比率、PER/ROE を DuckDB 上で計算。
    - データ不足時の None 戻しとログ出力。
    - DuckDB のウィンドウ関数を使った効率的なクエリ実装。
  - feature_exploration
    - 将来リターン calc_forward_returns（任意ホライズン、入力検証あり）。
    - IC（スピアマンのランク相関）計算 calc_ic（None と ties を扱う安全な実装）。
    - rank（同順位は平均ランク）、factor_summary（count/mean/std/min/max/median の算出）などのユーティリティ。
- 共通設計上の注意点
  - 全ての分析処理は（ルックアヘッドバイアスを避けるため）datetime.today() / date.today() の直接参照を避け、呼び出し側から target_date を渡す設計。
  - DuckDB を主要なローカル分析用 DB として利用。executemany の空リスト問題など DuckDB の実装差分に配慮したコード。
  - ロギングを広範に使用し、警告や情報を明確に出力する設計。
  - 外部 API 呼び出しでのリトライ/バックオフ、API 5xx 判定、JSON パースの頑健化などフォールトトレランスを重視。
  - テスト容易性への配慮（内部 API 呼び出し点をモック可能に設計）。

### 変更 (Changed)
- 初版リリースにあたっての設計決定や API（例: OpenAI モデル gpt-4o-mini の採用、スコアクリップ範囲 ±1.0、バッチサイズ 20 等）を明確化。

### 修正 (Fixed)
- 実装上のフェイルセーフ挙動を追加／明文化：
  - AI API 呼び出し失敗時やレスポンスパース失敗時に例外を上位に伝播させず、安全なデフォルト（0.0 やスキップ）で継続する処理。
  - DB 書き込み失敗時は ROLLBACK を試み、ROLLBACK の失敗も警告ログで記録するロバスト化。

### 注意 (Notes)
- 必須環境変数（例）
  - OPENAI_API_KEY（AI スコアリング、レジーム判定）
  - JQUANTS_REFRESH_TOKEN（J-Quants API）
  - KABU_API_PASSWORD / KABU_API_BASE_URL（kabu ステーション連携）
  - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（通知用）
- デフォルトのローカルパスや閾値は Settings で定義されています。配布環境では .env/.env.local または OS 環境変数で上書きしてください。
- 自動 .env ロードはプロジェクトルートの検出に依存します（.git / pyproject.toml）。パッケージ化後やテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能です。
- DuckDB バインドの実装差異（executemany に空リストを渡せない等）を考慮したコードになっています。DuckDB の互換性に注意してください。

### 既知の制約 / 今後の改善候補
- OpenAI API の JSON 出力のばらつき（前後の余計なテキスト等）に対するパースの堅牢化は行っているが、将来的により厳格なフォーマットやスキーマ検証を導入する余地あり。
- 現フェーズでは sentiment_score と ai_score を同値で保存しているが、将来的に派生指標を追加する可能性あり。
- PBR・配当利回りなどのバリュー指標は未実装（calc_value で言及）。

---

参照: ソースコードのドキュメント文字列・ログメッセージ・設定・定数などから仕様を推測して作成しました。より正確な履歴を得るにはコミットログ（Git）を用いることを推奨します。