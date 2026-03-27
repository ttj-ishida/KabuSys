# CHANGELOG

すべての変更は Keep a Changelog の形式に従っています。  
このプロジェクトの初期リリース（v0.1.0）は、データ取得・ETL、カレンダー管理、ファクター計算、ニュースNLP とレジーム判定、設定管理など日本株自動売買システムの基盤機能を実装しています。以下はコードベースから推測した主な追加点・設計方針・既知制約です。

## [Unreleased]
- （なし）

## [0.1.0] - YYYY-MM-DD
初回リリース

### 追加（Added）
- パッケージ基本情報
  - kabusys パッケージの基本バージョンを `0.1.0` として公開（src/kabusys/__init__.py）。
  - パッケージ外部 API として data, strategy, execution, monitoring をエクスポート。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env/.env.local の自動読み込み（プロジェクトルート検出: .git / pyproject.toml を基準）。
  - 読み込み時の優先順位: OS 環境 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能（テスト等で利用）。
  - .env 行パーサーは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、コメント処理等に対応。
  - Settings クラスを導入し、J-Quants / kabu ステーション / Slack / DB パス / 実行環境（development/paper_trading/live）・ログレベル等の取得とバリデーションを提供。
  - 必須環境変数未設定時は明示的なエラーを返す（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。

- AI（ニュースNLP / レジーム判定）（src/kabusys/ai/*）
  - news_nlp モジュール（score_news）:
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）でバッチ解析して ai_scores テーブルへ書込。
    - 時間ウィンドウ (前日15:00 JST ～ 当日08:30 JST 相当) を calc_news_window で計算。
    - バッチサイズ、記事数・文字数上限（トークン肥大対策）、JSON Mode 利用、レスポンス検証、スコアクリップ（±1.0）を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフでのリトライとフェイルセーフ（失敗時はスキップ、例外は投げない）を実装。
    - DuckDB への書き込みは冪等性を考慮（該当コードのみ DELETE → INSERT）。
  - regime_detector モジュール（score_regime）:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し日次で市場レジーム（bull / neutral / bear）を判定し market_regime テーブルへ冪等書込。
    - マクロニュースは news_nlp のウィンドウ計算を再利用して抽出、OpenAI を呼び出して JSON レスポンスをパース。
    - API キーは引数または環境変数 OPENAI_API_KEY を使用。API 呼び出し失敗時は macro_sentiment=0.0 のフォールバック。

- データプラットフォーム（src/kabusys/data/*）
  - calendar_management モジュール:
    - market_calendar を用いた営業日/前後営業日/期間取得/is_sq_day 判定ロジックを実装。
    - DB にカレンダーが無い場合は曜日ベースのフォールバック（土日を非営業日として扱う）。
    - calendar_update_job により J-Quants API から差分取得して market_calendar を冪等更新（バックフィル・健全性チェックを含む）。
  - pipeline / etl モジュール:
    - ETLResult データクラスを公開（ETL の取得数・保存数、品質問題リスト、エラーの集約など）。
    - ETL パイプラインの概念設計を実装（差分取得、保存、品質チェックのフックなど）。
    - _get_max_date 等のヘルパーによる最終取得日判定など。

- 研究モジュール（src/kabusys/research/*）
  - factor_research モジュール:
    - モメンタム（1M/3M/6M）、200 日 MA 乖離、ATR（20 日）、平均売買代金・出来高比、EPS/ROE ベースの PER/ROE など主要ファクターを DuckDB の SQL と組合せて計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の None 扱い、営業日バッファや窓幅の設計を実施。
  - feature_exploration モジュール:
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク関数（rank）、ファクター統計サマリー（factor_summary）を実装。
    - 外部依存を避け、標準ライブラリと DuckDB のみで実装。

- 共通ユーティリティ
  - DuckDB を主要なローカル分析 DB として利用する前提の実装（duckdb.DuckDBPyConnection 型注釈多数）。
  - ロギングを各モジュールで積極的に使用。設計上、ルックアヘッドバイアス防止のために datetime.today()/date.today() をスコアリング関数内部で直接参照しない方針を採用（target_date を明示的に受け取る）。

### 変更（Changed）
- 初版（ベースライン）リリースのため、既存ライブラリや公開 API の大幅な変更はなし（初回追加のみ）。

### 修正（Fixed）
- 初版リリース時点の実装に対する安全措置・バリデーションを多数導入:
  - .env のパース強化（クォート内エスケープ、inline コメントの取り扱い）により誤読を低減。
  - OpenAI API 呼び出しに対する例外分岐とリトライロジック、JSON パース時の復元ロジック（前後余計テキストの補正）を実装。
  - DuckDB に対する executemany の空リスト扱いの注意（空の場合の分岐）を導入。

### 既知の制約（Known issues）
- 外部依存:
  - OpenAI クライアント（OpenAI SDK）と DuckDB が必須。API キーやトークンは環境変数で供給する必要あり（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN）。
  - jquants_client への依存部分（calendar_update_job などの外部 API 呼出し）はモジュール内で使用されるが、外部側の実装・接続状況に依存。
- フェイルセーフ設計により、AI API の失敗時は失敗を吸収して処理を続行する（スコア欠落や 0.0 フォールバック）。運用上は失敗ログの監視が必要。
- news_nlp / regime_detector は JSON モードを前提とするが、LLM の応答がフォーマットされない場合は空スコアを返すなどの保守的挙動となる。
- 単体テスト用のフック（_call_openai_api の差し替えなど）が用意されているが、統合テストでは OpenAI / J-Quants 呼び出しのモックが必要。

### セキュリティ（Security）
- 環境変数保護:
  - 自動読み込み時に OS 環境変数は保護（protected set）され、.env ファイルでの上書きを意図的に制御。
- パスワード・トークンは Settings を通して必須チェックを行い、未設定時に ValueError を発生させることで誤動作を防止。

---

開発者向け注記:
- 多くの処理（スコアリング、ETL、calendar update）は target_date を明示的に受け取る設計になっています。これは未来情報の混入（ルックアヘッド）を防ぐためで、バッチ実行やバックフィル時に deterministic な挙動を確保します。
- テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を使って自動 .env ロードをオフにし、環境変数を制御してください。
- 将来的な改善候補:
  - OpenAI 呼び出し部分の共通化（現在はモジュール毎に独立実装）と共通リトライ/ロギングラッパーの導入。
  - ETL の具体的な pipeline 実装の追加（現在は ETLResult と補助ユーティリティが中心）。
  - strategy / execution / monitoring パッケージの実装（__all__ に宣言ありが未実装の場合は今後追加予定）。

もしリリース日や追加で強調したい変更点（日付、特定のバグ修正やセキュリティ対応など）があれば教えてください。CHANGELOG をその情報に合わせて更新します。