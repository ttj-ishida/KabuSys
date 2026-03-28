# Changelog

すべての変更は Keep a Changelog の方針に従って記載しています。  
慣例: 重要な変更はカテゴリ（Added / Changed / Fixed / Deprecated / Removed / Security）に分類しています。

## [0.1.0] - 2026-03-28
初回リリース。日本株のデータ収集・研究・AIスコアリング・市場レジーム判定を念頭に置いたコアライブラリを追加。

### Added
- パッケージ初期公開
  - パッケージ名: kabusys, バージョン: 0.1.0
  - top-level の __all__ に data, strategy, execution, monitoring を公開（将来の拡張を想定）。
- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
  - .env パーサ実装:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - インラインコメントの取扱い（クォートの有無で挙動を区別）
  - OS 環境変数の保護（.env の上書き制御）、.env と .env.local の優先順位制御。
  - Settings クラスでアプリの主要設定値をプロパティとして提供（J-Quants / kabu API / Slack / DB パス / 環境 / ログレベル等）。
  - env 値や LOG_LEVEL のバリデーションを実装（許容値以外は ValueError）。

- AI モジュール (kabusys.ai)
  - news_nlp.score_news:
    - raw_news と news_symbols を集約、銘柄ごとに最新記事を結合して OpenAI（gpt-4o-mini）でセンチメントを評価。
    - バッチ処理（最大 20 銘柄/呼び出し）、トークン肥大防止（記事数・文字数の上限）。
    - JSON Mode を期待しつつ、前後に余計なテキストが混ざる場合の復元ロジックを実装。
    - エラー時はフェイルセーフ（部分失敗はスキップ、他銘柄の既存スコアは保護）し、結果を ai_scores テーブルへ idempotent に書き込み（DELETE → INSERT）。
    - リトライ（429 / ネットワーク / タイムアウト / 5xx）を指数バックオフで実装。
    - テスト容易性のため _call_openai_api を patch で差し替え可能。
  - regime_detector.score_regime:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と news_nlp ベースのマクロセンチメント（重み 30%）を合成して日次レジーム判定（bull/neutral/bear）。
    - マクロ記事の抽出、OpenAI 呼び出し、スコア合成、market_regime への冪等書き込みを実装。
    - API エラー時は macro_sentiment を 0.0 にフォールバック（サービス全体が止まらないように設計）。
    - LLM 呼び出しは独立実装し、モジュール結合を避ける（テストでの差し替えを容易化）。

- データプラットフォーム関連 (kabusys.data)
  - calendar_management:
    - JPX カレンダー管理ヘルパー（market_calendar テーブル参照）。
    - 営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB にデータが無い場合は曜日ベースでフォールバック（週末を非営業日扱い）。
    - calendar_update_job: J-Quants API からの差分取得 → market_calendar へ冪等保存、バックフィルと健全性チェックを実装。
  - pipeline (ETL):
    - ETLResult dataclass を追加（ETL 結果の構造化、品質問題やエラーの集約）。
    - 差分取得・バックフィル・保存・品質チェックの設計方針とユーティリティ関数を用意（_get_max_date 等）。
  - etl モジュールで ETLResult を再公開（kabusys.data.etl）。

- Research ツール (kabusys.research)
  - factor_research:
    - calc_momentum, calc_volatility, calc_value を実装（prices_daily / raw_financials を参照、DuckDB SQL＋ウィンドウ関数で算出）。
    - ファクター設計: モメンタム（1M/3M/6M、MA200乖離）、ボラ（ATR20）、流動性（20日平均売買代金・出来高比率）、バリュー（PER, ROE）。
    - データ不足時は None を返す設計。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズンの将来リターンを一回のクエリで取得可能に実装（LEAD を使用）。
    - calc_ic: スピアマンランク相関（Information Coefficient）計算。少数レコードや分散ゼロのケースをハンドリング。
    - rank: 平均ランク（ties は平均ランク）、丸めで ties 検出の安定化。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。

- ロギングと設計方針
  - 多数の関数に詳細なログ出力を追加（INFO/DEBUG/WARNING/EXCEPTION）。
  - ルックアヘッドバイアス対策として datetime.today() / date.today() をスコア計算ロジック内で直接参照しない設計を徹底。
  - DuckDB を前提とした SQL 実装（互換性のため executemany 空リストの扱いに配慮）。

### Changed
- （初回リリースのため「Changed」相当の履歴は初期設計方針として記載）
  - 外部 API 呼び出しの失敗に対するフェイルセーフな挙動を優先（スコアに中立値 0.0 を使用し例外を上位に伝播しない箇所を明確化）。
  - OpenAI API 呼び出しは JSON Mode を期待しつつ、実運用での不整合に備えた復元・検証ロジックを導入。

### Fixed
- 安定運用のための防護策を多数実装（初期バージョンでの「修正済み」扱いの設計決定として記載）
  - .env パーサの不正入力（コメントやクォート、エスケープ）に対する耐性向上。
  - DuckDB executemany の空パラメータに起因する問題回避（実行前に空チェックを行う）。
  - OpenAI からの非標準レスポンス（前後に余計なテキストが混入する等）に対する復元ロジックを追加。

### Deprecated
- なし

### Removed
- なし

### Security
- 環境変数（API キー等）は Settings を通じて必須チェックを行うため、未設定時は明示的に ValueError を発生させ検出を容易化。
- OpenAI API キー取得は api_key 引数優先→環境変数の順で解決し、明示的な未設定チェックを実装。

---

注:
- 本 CHANGELOG はリポジトリ内のコードから設計意図・機能を抽出して作成しています。実際のリリースノート作成時は、コミット履歴や PR 説明等の運用履歴に基づいて更新してください。