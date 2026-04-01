# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このファイルはリポジトリ内のコードから推測して作成した初期リリースの変更履歴です。

全般的な注意
- 本リリースはパッケージ識別子 `kabusys` の初期公開バージョンとして想定しています（__version__ = 0.1.0）。
- 多くの機能は内部で DuckDB を使用し、外部 API 呼び出し（J-Quants / OpenAI 等）と連携します。設計上、ルックアヘッドバイアスを防ぐために日付参照は外部から渡す方式を採用しています。

## [0.1.0] - 2026-04-01

### Added
- パッケージ基盤
  - パッケージメタ情報と公開モジュール定義（kabusys/__init__.py）。
  - バージョン: 0.1.0。

- 環境設定管理 (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動ロードする仕組みを実装。
  - 環境変数のパース機能を実装（コメント、export プレフィックス、クォート/エスケープ処理に対応）。
  - 自動ロードを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用途）。
  - OS 環境変数を保護する protected 上書き制御をサポート（.env.local は上書きモード）。
  - Settings クラスを提供: J-Quants / kabu ステーション / Slack / DB path / 監視閾値 / 実行環境（development/paper_trading/live）/ログレベル等のプロパティを取得可能。
  - 必須環境変数未設定時には ValueError を発生させる _require 実装。

- AI（自然言語処理）モジュール (kabusys.ai)
  - news_nlp.score_news
    - raw_news と news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini、JSON mode）でセンチメントスコアを算出。
    - バッチ処理（最大 20 銘柄/リクエスト）、リトライ（429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ）を実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results フォーマット検証、コード照合、数値変換、クリッピング）。
    - スコアは ai_scores テーブルへ冪等的に書き込む（DELETE → INSERT、部分失敗時に既存データを保護）。
    - ニュースウィンドウ計算（JST 基準: 前日 15:00 ～ 当日 08:30 を UTC に変換）を実装。
    - API キー注入可能（引数 or 環境変数 OPENAI_API_KEY）。未設定時は ValueError。

  - regime_detector.score_regime
    - ETF 1321（Nikkei225 ETF）の 200 日移動平均乖離（重み 70%）とマクロニュース（LLM によるセンチメント、重み 30%）を合成して日次市場レジーム（bull/neutral/bear）を判定。
    - MA 計算は target_date 未満のデータのみを使用することでルックアヘッドバイアスを防止。
    - マクロニュースは raw_news からマクロキーワードでフィルタし、OpenAI に渡して JSON で macro_sentiment を取得。
    - OpenAI 呼び出しはリトライ・フェイルセーフ（失敗時は macro_sentiment=0.0）を備える。
    - 結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時は ROLLBACK を試行して例外を伝播。

- Data モジュール (kabusys.data)
  - calendar_management
    - JPX（市場）カレンダー管理機能を提供。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装。
    - market_calendar がない場合は曜日ベース（土日除外）でフォールバック。
    - 最大探索日数上限を設けて無限ループを防止。
    - calendar_update_job：J-Quants API から差分取得して market_calendar を冪等更新。バックフィルや健全性チェックを実装。
  - pipeline / etl
    - ETLResult データクラスを公開（ETL 実行メトリクス、品質問題、エラー集約）。
    - ETL パイプラインで使用するユーティリティ（差分更新、backfill、品質チェック設計に準拠）。

- Research モジュール (kabusys.research)
  - factor_research
    - モメンタム: 1M/3M/6M リターン、200日 MA 乖離（データ不足時は None）。
    - ボラティリティ/流動性: 20日 ATR、相対 ATR、20日平均売買代金、出来高比等。
    - Value: PER（EPS が 0/NULL の場合は None）、ROE（raw_financials から最新報告を結合）。
    - すべて DuckDB SQL による計算（prices_daily / raw_financials）で外部発注 API にはアクセスしない。
  - feature_exploration
    - 将来リターン計算（複数ホライズン、デフォルト [1,5,21]）、LEAD を使った効率的クエリ。
    - calc_ic: スピアマン（ランク）相関計算（ties の平均ランク対応、サンプル数閾値）。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を算出。
    - 内部ユーティリティ rank を提供（同順位は平均ランク）。

- その他
  - DuckDB を前提としたデータアクセス設計。多くの機能で SQL ウィンドウ関数（OVER, LAG, LEAD 等）を活用して効率的に集約/指標算出を行う。
  - 各モジュールで詳細なログ出力を追加（INFO/WARNING/DEBUG レベルでの状態報告）。
  - OpenAI API 呼び出し部分はテスト容易性のため _call_openai_api を分離（unittest.mock.patch で差し替え可能）。

### Changed
- （初リリースのためなし）このバージョンは初期追加がメインです。

### Fixed
- （初リリースのためなし）

### Security
- 環境変数読み込みで OS 側の既存環境変数を保護する仕組みを導入（protected set）。.env/.env.local の上書き挙動を明示。

### Known limitations / Implementation notes
- OpenAI 連携は gpt-4o-mini + JSON Mode を前提に実装しているため、API SDK・モデル仕様の変更により適合が必要。
- DuckDB executemany に関する互換性対策（空リストバインド回避）を実装しているが、環境によって挙動が変わる可能性あり。
- 一部の設計は「フェイルセーフで継続する」方針（API 失敗時はスコアを 0 にフォールバック、スコア取得失敗はそのチャンクをスキップ）を採用しているため、データ欠損時の運用ポリシーは上位で検討してください。
- 日付処理はすべて timezone-naive な date/datetime を扱う設計（UTC を想定する部分あり）。運用環境での取り扱いに注意。

---

（この CHANGELOG はコードベースの内容から推測して作成しています。実運用向けリリースノートとして使用する場合は、テスト結果・実際の変更履歴・マイグレーション手順等を追記してください。）