# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) 準拠で記載しています。

現在のリリース: 0.1.0

## [Unreleased]

（未リリースの変更はここに記載します）

---

## [0.1.0] - 2026-03-28

初回公開リリース。日本株自動売買プラットフォームのコア機能群を提供します。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージを作成。公開 API として data, strategy, execution, monitoring を __all__ にてエクスポート。
  - バージョン情報を __version__ = "0.1.0" として定義。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
  - .env/.env.local の優先度と override / protected ロジックを実装し、OS 環境変数の上書きを制御。
  - .env の各行を柔軟にパースするロジックを実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理）。
  - 必須環境変数取得用の _require 関数と Settings クラスを追加。J-Quants / kabu ステーション / Slack / DB パス / 実行環境・ログレベル等のプロパティを提供。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応。

- AI 関連 (src/kabusys/ai)
  - ニュースセンチメント解析モジュール news_nlp.score_news を実装。
    - 記事ウィンドウ計算（JST → UTC 変換）、銘柄ごとの記事集約、OpenAI（gpt-4o-mini）へのバッチ送信、レスポンス検証とスコアクリップ、ai_scores テーブルへの冪等的書き込みを提供。
    - リトライ（429／ネットワーク断／タイムアウト／5xx）と指数バックオフを備え、API エラー時もフェイルセーフで処理継続。
    - DuckDB の executemany 空リスト制約に対する対処を実装。
  - 市場レジーム判定モジュール regime_detector.score_regime を実装。
    - ETF(1321) の 200 日移動平均乖離とマクロニュースの LLM センチメントを重み付けして市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等的に保存。
    - OpenAI 呼び出しの独立実装、API キー注入、リトライ処理、API失敗時のフォールバック（macro_sentiment=0.0）を実装。
  - AI モジュールは OpenAI SDK（chat completions + JSON mode）を利用する設計。

- リサーチ機能 (src/kabusys/research)
  - factor_research: モメンタム・ボラティリティ・バリュー等の定量ファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - MA200乖離、1/3/6ヶ月リターン、ATR20、出来高・売買代金指標、PER/ROE 等を DuckDB 上で SQL により計算。
    - データ不足時の None 戻り挙動を明示。
  - feature_exploration: 将来リターン計算、IC（スピアマンρ）計算、統計サマリー、ランク変換ユーティリティを実装（calc_forward_returns, calc_ic, factor_summary, rank）。
    - horizons 引数のバリデーション、単一クエリでの複数ホライズン取得などパフォーマンス配慮。

- データプラットフォーム (src/kabusys/data)
  - calendar_management: JPX カレンダー管理と営業日ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。
    - market_calendar テーブルの有無に応じた DB優先ロジックと曜日ベースフォールバック、最大探索日数での無限ループ防止を実装。
    - calendar_update_job により J-Quants API からの差分取得と冪等保存、バックフィル・健全性チェックを実装。
  - pipeline: ETL（差分取得、保存、品質チェック）を表す ETLResult データクラス等を公開。
    - ETLResult に品質問題とエラー概要の収集・シリアライズ機能を追加。
    - データ取得の最小日付、バックフィル日数、カレンダー先読みなどの定数を定義。
  - etl モジュールの公開インターフェース（ETLResult の再エクスポート）を追加。

### 変更 (Changed)
- 設計方針として多数のモジュールで「datetime.today()/date.today() を直接参照しない」方針を採用し、ルックアヘッドバイアスを防止。
- DuckDB の互換性を考慮した SQL / executemany の実装パターンを採用（空リスト対策、ROW_NUMBER による最新行取得など）。

### 修正 (Fixed)
- OpenAI レスポンスの不安定さに対応するため、JSON mode のレスポンスパースで前後余分なテキストが混入するケースを復元してパースする処理を追加（news_nlp/_validate_and_extract 等）。
- API 呼び出しで発生する各種エラー（RateLimit, APIConnectionError, APITimeoutError, APIError の 5xx/非5xx 判別）に対して適切なリトライ／フォールバックを実装。最終的にフェイルセーフなデフォルト値（例: macro_sentiment=0.0）を返すことで処理全体の中断を防止。
- .env ファイル読み込みにおけるファイル読み取り失敗時に警告を出してスキップするようにし、テストや CI 環境での堅牢性を向上。

### 既知の制限 (Known issues)
- OpenAI との統合は gpt-4o-mini の JSON mode を前提としており、今後の SDK または API の変更により調整が必要になる可能性があります。
- DuckDB のバージョン差異により一部プレースホルダの振る舞い（配列バインドなど）が変わるため、互換性テストを推奨します。
- news_nlp のスコアは現段階で sentiment_score と ai_score を同値で保存しており、将来的な拡張が考えられます。

### セキュリティ (Security)
- 環境変数の取り扱いは protected set による上書き防止を行い、OS環境変数の不意な上書きを防止。
- OpenAI API キーは引数で注入可能で、環境変数に依存しないテスト容易性を考慮。

---

今後の予定（例）
- 戦略（strategy）・実行（execution）・モニタリング（monitoring）モジュールの実装拡張（注文ロジック、リスク管理、Slack 通知など）。
- テストカバレッジの強化、CI/CD での DuckDB テスト基盤整備。
- OpenAI 呼び出しのコスト最適化とキャッシュ戦略。