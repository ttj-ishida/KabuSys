# CHANGELOG

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]
- 作業中の変更はここに記載します。

## [0.1.0] - 2026-03-28
最初の公開リリース。日本株自動売買 / 研究 / データ基盤を見据えたコア機能群を実装しました。

### Added
- パッケージ基盤
  - kabusys パッケージの初期公開。__version__ = 0.1.0、公開モジュールを __all__ で定義（data, strategy, execution, monitoring）。
- 環境設定管理（kabusys.config）
  - .env ファイル自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
  - .env / .env.local の読み込み優先順と、OS 環境変数保護（protected）をサポート。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト用）。
  - シンプルだが堅牢な .env パーサを実装。export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
  - 必須環境変数取得用 _require と Settings クラスを提供。J-Quants、kabuAPI、Slack、DB パス、実行環境（development/paper_trading/live）、ログレベルの設定プロパティを実装。
  - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）を実装。
- AI モジュール（kabusys.ai）
  - news_nlp: ニュース記事を統合して OpenAI（gpt-4o-mini）で銘柄別センチメントを算出し ai_scores テーブルへ保存する機能を実装。
    - 対象時間ウィンドウの計算（JST 基準の前日 15:00 ～ 当日 08:30 の記事）。
    - 銘柄ごとに最新記事を集約しトリム（記事数・文字数上限）。
    - バッチ処理（最大 20 銘柄/コール）、JSON Mode 応答パースと厳密なバリデーション実装。
    - エラー時のリトライ（429、ネットワーク、タイムアウト、5xx）と指数バックオフ、部分成功に備えた部分的な DB 置換（DELETE → INSERT）で冪等性を確保。
    - API キー注入（引数 or 環境変数 OPENAI_API_KEY）をサポート。
  - regime_detector: 日次の市場レジーム判定（bull/neutral/bear）を実装。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成。
    - マクロ記事抽出用キーワード群、OpenAI 呼び出し（JSON mode）、リトライ・エラー時は macro_sentiment=0.0 のフェイルセーフ。
    - DuckDB を用いた ma200_ratio 計算、レジームスコア合成、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
- データ基盤（kabusys.data）
  - calendar_management: JPX カレンダーの管理と営業日判定ユーティリティを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar が未取得・部分取得のケースに対する曜日ベースのフォールバック設計。
    - calendar_update_job: J-Quants API からの差分取得と market_calendar への更新（バックフィル・健全性チェック含む）。
  - pipeline / ETL: ETLResult データクラスと ETL パイプラインの土台を実装。
    - 差分取得、保存（jquants_client の save_* を利用する想定）、品質チェック（quality モジュールとの連携）の設計方針を実装。
    - ETL 実行結果の構造化（quality_issues の展開等）。
  - etl の公開インターフェース（ETLResult の再エクスポート）。
- 研究用モジュール（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER、ROE）計算を実装。
    - DuckDB を用いた SQL 主導の実装で、外部 API や取引システムにはアクセスしない設計。
    - データ不足時の None ハンドリング、戻り値は (date, code) をキーとする dict リスト。
  - feature_exploration:
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）、IC（Spearman 相関）計算、ファクターサマリー（count/mean/std/min/max/median）、ランク化ユーティリティを提供。
    - ties の扱い（平均ランク）や浮動小数点丸めによる tie 検出対策を実装。
- DuckDB を前提とした DB 操作を各所で採用（prices_daily, raw_news, raw_financials, ai_scores, market_regime, market_calendar など）。
- ロギング出力を各モジュールに追加し、操作の追跡と障害解析を容易に。

### Fixed / Robustness
- .env パーサの堅牢化
  - クォート中のエスケープ処理、export プレフィックス、インラインコメント判定（クォート有無で異なる扱い）など、多くの .env 形式に対応。
- OpenAI 呼び出し周りの堅牢性
  - JSON パース失敗、レスポンス整形不備、API の 5xx/429/接続エラーに対するリトライ・フォールバック（最終的には 0.0 を返す）の実装により LLM API 失敗が上位処理を破壊しないように設計。
- DB 書き込みの冪等性と部分失敗耐性
  - ai_scores / market_regime への書き込みで、DELETE → INSERT のパターンを採用し、部分失敗時に既存データを不必要に削除しないように配慮。
  - DuckDB の executemany に関する互換性（空リスト不可）を考慮したガード実装。

### Security
- OpenAI API キーの取り扱いを厳格化
  - 各 AI 関数は api_key 引数または環境変数 OPENAI_API_KEY のいずれかを必須とし、未設定時は ValueError を発生させることで誤運用を防止。
- OS 環境変数の上書きを防ぐ protected ロジックを .env ロードで導入。

### Internal / Notes
- ルックアヘッドバイアス防止
  - news_nlp, regime_detector など時系列処理を行うモジュールでは datetime.today() / date.today() を内部判断に用いず、呼び出し側から target_date を受け取る設計。DB クエリも target_date 未満 / 以前の条件を明示してルックアヘッドを防止。
- テストの容易性を考慮
  - OpenAI 呼び出し関数（_call_openai_api）はモジュールローカルに分離しており、unittest.mock.patch による差し替えが可能。
  - .env 自動ロードは環境変数で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
- 外部依存
  - DuckDB と OpenAI Python SDK（openai.OpenAI クライアント）を前提としている。J-Quants API クライアントは kabusys.data.jquants_client として想定。
- ドキュメント
  - 各モジュールに詳細な docstring を付与し、設計方針やアルゴリズム、エラー取り扱いについて明記。

### Removed
- なし

### Deprecated
- なし

---

今後の予定（例）
- strategy / execution モジュールの実装（発注ロジック、リスク管理、paper/live 切替）
- 単体テスト・統合テストの追加と CI ワークフロー整備
- jquants_client の具体実装および ETL の実稼働検証
- パフォーマンス最適化（大規模データセットの集計改善、並列化検討）

フィードバックや不具合報告があれば issue を作成してください。