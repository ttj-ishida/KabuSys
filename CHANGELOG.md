# Changelog

すべての注目すべき変更を記録します。これは Keep a Changelog の形式に従っています。  
なお、本ファイルはリポジトリ内のコードから推測して作成した初期リリース向けの要約です。実際のリリース履歴や日付は必要に応じて調整してください。

注: ここに記載の「追加」「修正」等は、提供されたコードベースの機能・設計意図を元に推測してまとめたものです。

## [Unreleased]
- 今後の変更履歴をここに記載します。

## [0.1.0] - 2026-04-01
初回公開リリース。主要サブシステム（データ収集/ETL、マーケットカレンダー、リサーチ/ファクター計算、AI ベースのニュース解析・市場レジーム判定、設定管理など）を実装。

### Added
- パッケージ初期エントリ
  - kabusys パッケージを追加。バージョン: 0.1.0
  - パッケージ公開 API（__all__）に data, strategy, execution, monitoring を定義。

- 設定管理 (kabusys.config)
  - .env / .env.local 自動読み込み機能（プロジェクトルートを .git または pyproject.toml で検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env のパースはクォート、エスケープ、コメント（'#'）に対応。
  - Settings クラスを実装し、主要環境変数をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須項目を検査。
    - KABUSYS_ENV の検証（development / paper_trading / live のみ有効）。
    - LOG_LEVEL 検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - デフォルトの DB パス (DUCKDB_PATH, SQLITE_PATH) や監視設定（PID ファイル、CPU/メモリ/ディスク閾値）を提供。

- AI モジュール (kabusys.ai)
  - news_nlp.score_news:
    - raw_news と news_symbols を元にニュースを銘柄別に集約し、OpenAI（gpt-4o-mini）の JSON モードでセンチメントを取得。
    - バッチ処理（1 回につき最大 20 銘柄）・記事数/文字数のトリム・リトライ（429/ネットワーク/タイムアウト/5xx の指数バックオフ）に対応。
    - レスポンスの検証（JSON 抽出、results リスト、code/score 検証）を実施し、スコアを ±1.0 にクリップして ai_scores テーブルへ冪等的に保存（DELETE → INSERT）。
    - API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出。
    - テスト容易性のため OpenAI 呼び出し部分を patch で差し替え可能。
  - regime_detector.score_regime:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等書き込み。
    - prices_daily と raw_news を参照し、calc_news_window を使ってニュースウィンドウを算出。
    - LLM 呼び出しは個別の内部関数を持ち、API エラー時は macro_sentiment=0.0 にフォールバック。
    - レジーム合成スコアはクリップされ、閾値に基づいてラベル付け。
    - API キーは引数または環境変数 OPENAI_API_KEY から解決。

- データプラットフォーム (kabusys.data)
  - calendar_management:
    - JPX カレンダー管理（market_calendar）を提供。is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。
    - DB にデータが無い場合は曜日ベースのフォールバック（週末は非営業日）。
    - 夜間バッチ用 calendar_update_job を実装（J-Quants から差分取得、バックフィル、健全性チェック、冪等保存）。
  - pipeline / etl:
    - ETLResult データクラスを追加（ETL の取得件数、保存件数、品質問題、エラー一覧などを保持）。
    - ETL の設計方針に従い差分取得／バックフィル／品質チェックのための基盤コードを実装（jquants_client と quality モジュールを利用する想定）。
  - jquants_client との連携を想定した保存／取得フロー（実装ファイルは別途存在すると推定）。

- リサーチ（kabusys.research）
  - factor_research:
    - モメンタム (1M/3M/6M)、200 日移動平均乖離、ATR（20 日）、流動性指標（20 日平均出来高・売買代金）等の計算機能を実装。
    - raw_financials を用いた PER / ROE の取得（calc_value）。
    - DuckDB の SQL ウィンドウ関数を活用した実装で、データ欠損時の振る舞い（None 返却）を定義。
  - feature_exploration:
    - 将来リターン calc_forward_returns（任意ホライズン対応）、IC（calc_ic）計算、rank、factor_summary（count/mean/std/min/max/median）などを実装。
    - 外部依存を極力使わない純粋 Python 実装。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Notes / 実装上の重要点（利用・運用時の注意）
- OpenAI 関連
  - news_nlp と regime_detector は gpt-4o-mini を利用する想定で JSON Mode を期待するプロンプト設計。
  - API 失敗時はフェイルセーフとしてスコアを 0.0 にフォールバックし、処理継続を優先。
  - テスト時は内部の _call_openai_api を unittest.mock.patch で差し替え可能（ユニットテスト容易性）。

- ルックアヘッドバイアス対策
  - AI・リサーチ関連モジュールは内部で datetime.today()/date.today() を参照せず、必ず target_date を明示的に受け取り、対象データは target_date 未満/前日の範囲で抽出するよう設計。

- DB（DuckDB）設計
  - 多くの機能は DuckDB 接続を前提。以下のテーブル構造（想定）が必要:
    - prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar など。
  - ai_scores / market_regime 等への書き込みは冪等設計（DELETE→INSERT や ON CONFLICT 相当）を採用。
  - DuckDB の executemany 空リスト制約への対処が実装されている（空の場合は実行せず）。

- 環境変数（必須/推奨）
  - 必須と思われる環境変数:
    - JQUANTS_REFRESH_TOKEN（J-Quants API）
    - KABU_API_PASSWORD（kabu API）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（通知）
    - OPENAI_API_KEY（AI モジュール利用時）
  - 自動 .env 読み込みはプロジェクトルート検出に依存。CWD に依存しない実装。

- ロギング／検証
  - 設定値（KABUSYS_ENV, LOG_LEVEL）はバリデーションされ、不正値は ValueError を投げる。
  - 各種処理は情報ログ・警告ログを出す設計（運用で監視可能）。

### Known limitations / 今後の改善候補（推測）
- news_nlp のレスポンス検証は強化済みだが、LLM の出力多様性に対する追加の堅牢化（例: より高度な JSON 復元ロジックやリトライ条件の細分化）は検討の余地あり。
- バッチ／並列化戦略（API 呼び出しのスループット最適化）やコスト管理（API 呼び出しコスト抑制）は運用フェーズでのチューニングが必要。
- monitoring モジュールが __all__ に含まれているが、今回提供コード内に詳細実装が見えないため、監視 / アラートの統合は別途実装想定。

### Breaking Changes
- 初回公開のため該当なし。

### Security
- 特別なセキュリティ修正は含まれていません。API キーやパスワードは環境変数で管理することを想定しています。

---

補足:
- 本 CHANGELOG は提供されたソースコードの機能とコメント（docstring）から推測して作成しました。実際のリリースノートとして採用する場合は、実際の履歴（コミット / リリース日 / 変更差分）に基づき調整してください。