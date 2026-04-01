# Changelog

すべての重要な変更点をここに記録します。フォーマットは "Keep a Changelog" に準拠しています。  
バージョン番号は semantic versioning を想定しています。

## [Unreleased]

## [0.1.0] - 2026-04-01
初回公開リリース。

### Added
- パッケージ初期化
  - kabusys パッケージを公開。__version__ = 0.1.0。
  - __all__ に data, strategy, execution, monitoring を設定（将来的な公開 API を想定）。

- 環境設定 / 設定管理
  - 統合設定クラス Settings を追加。J-Quants・kabuステーション・Slack・DB・監視・システム設定をプロパティ経由で提供。
  - .env 自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
  - .env パーサを実装（export 形式、クォート、エスケープ、インラインコメントの扱いに対応）。
  - 必須環境変数未設定時は _require() が ValueError を返す。
  - 環境変数の妥当性チェック（KABUSYS_ENV / LOG_LEVEL の許容値を検証）。

- AI モジュール
  - ニュースNLP: kabusys.ai.news_nlp モジュールを追加。
    - raw_news と news_symbols を集約して銘柄ごとのニュースを作成。
    - gpt-4o-mini（JSON mode）で銘柄ごとのセンチメント（-1.0〜1.0）を評価し ai_scores テーブルへ書き込み。
    - バッチ処理（最大 20 銘柄/回）、記事数・文字数上限、429/ネットワーク/5xx のエクスポネンシャルバックオフ・リトライ実装。
    - レスポンスの堅牢なバリデーションと JSON 抽出ロジックを実装。
    - テスト用に _call_openai_api をパッチ差し替え可能（unittest.mock.patch を想定）。
  - 市場レジーム判定: kabusys.ai.regime_detector を追加。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して day-level の market_regime を算出・保存。
    - OpenAI（gpt-4o-mini）呼び出し、リトライ/バックオフ、API失敗時のフェイルセーフ（macro_sentiment=0.0）。
    - レジームスコアのクリップ・ラベリング（bull / neutral / bear）。
    - DuckDB を使った idempotent な書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。

- データプラットフォーム（data）
  - calendar_management:
    - market_calendar を管理する夜間バッチ calendar_update_job を実装（J-Quants クライアント経由で差分取得、バックフィル、健全性チェック、冪等保存）。
    - 営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装。DB登録値優先、未登録日は曜日フォールバック。
    - 最大探索範囲・バックフィル日数・ルールによる安定性設計。
  - ETL パイプライン:
    - pipeline.ETLResult を公開（ETL の fetch/save 結果、品質問題、エラー情報を格納）。
    - 差分取得・保存・品質チェック（quality モジュール連携）を想定した設計（backfill, calendar lookahead などのパラメータを導入）。
    - DuckDB を前提としたテーブル存在チェックや最大日付取得のユーティリティを実装基盤に含む。
  - データ API 用の jquants_client を用いる設計（fetch/save の呼び出し箇所を想定）。

- リサーチ（research）
  - ファクター計算: kabusys.research.factor_research を追加。
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を算出（データ不足時は None を返す）。
    - calc_volatility: 20 日 ATR（atr_20, atr_pct）、20 日平均売買代金、出来高比率を算出（データ不足時は None）。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を算出（EPS が 0/欠損の際は None）。
    - DuckDB SQL を中心に効率的に実装。
  - 特徴量探索: kabusys.research.feature_exploration を追加。
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンをまとめて計算。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算。サンプル不足時は None。
    - rank: 同順位は平均ランクを返すユーティリティ（丸めによる tie 対応）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリ。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Security
- OpenAI API キーの取り扱いについては環境変数（OPENAI_API_KEY）または関数引数で注入する方式を採用。ログ等にキーを出力しない設計を想定。

### Notes / Implementation details（設計上の重要ポイント）
- ルックアヘッドバイアス防止:
  - 各 AI / リサーチ機能は datetime.today() / date.today() を参照しない設計。target_date を明示的に指定して外部呼び出し側で日時制御する想定。
  - DB クエリは target_date 未満／以降といった排他条件で未来データ参照を防止。
- フェイルセーフ:
  - OpenAI API 呼び出しや外部 API エラー時は例外を必ず投げるわけではなく（多数のケースで）フェイルセーフ値（例: macro_sentiment=0.0）を採用して処理継続。
- テスト容易性:
  - OpenAI 呼び出し部分（_call_openai_api）はパッチ差し替えを想定して設計されており、ユニットテストでモックしやすい。
- DB（DuckDB）互換性:
  - executemany の空リストバインド回避や DuckDB の型戻り値ハンドリング等の互換性考慮を実装。

---

今後のリリースで予定している改善例:
- 実運用向けの execution / monitoring 実装（現在 __all__ に名前はあるが未実装箇所あり）。
- ai モジュールの API クライアント抽象化とコスト制御機能。
- 詳細な品質チェック（quality モジュール）の強化とダッシュボード連携。

もし CHANGELOG に反映してほしい追加情報（貢献者一覧、リリース日修正、より細かい変更分解など）があればお知らせください。