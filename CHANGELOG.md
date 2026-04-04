# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

現在のリリース履歴:

## [0.1.0] - 2026-04-04
初回公開リリース。日本株自動売買プラットフォームのコアライブラリを追加。

### Added
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。公開モジュール: data, strategy, execution, monitoring。

- 設定 / 環境変数管理（kabusys.config）
  - プロジェクトルート検出: .git または pyproject.toml を基準に自動検出する実装を追加。CWD に依存しない自動 .env ロードをサポート。
  - .env パーサ実装: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント判定などの堅牢な行パースを実装。
  - .env 読み込みロジック: 読み込み優先順位 OS 環境変数 > .env.local > .env、.env.local は override（既存 OS 環境変数は保護）に対応。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化可能。
  - Settings クラス: J-Quants / kabu ステーション / LINE / DB（duckdb/sqlite）/監視設定/システム設定 等のプロパティを提供。必須環境変数未設定時の明示的エラー (_require)。KABUSYS_ENV / LOG_LEVEL の妥当性検証、is_live/is_paper/is_dev ヘルパー。

- データ（kabusys.data）
  - calendar_management モジュール:
    - 営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装。market_calendar が存在しない場合は曜日ベースのフォールバックを行う。
    - calendar_update_job: J-Quants クライアント経由で JPX カレンダーを差分取得し、バックフィル･健全性チェック･冪等保存を行うバッチ処理を実装。
    - 内部ユーティリティ: DuckDB テーブル存在チェック、日付変換等。
  - ETL / pipeline:
    - ETLResult dataclass とその to_dict を実装（ETL 実行結果の集約用）。
    - pipeline モジュールの公開型 ETLResult を data.etl で再エクスポート。
    - ETL 実装方針・定数（バックフィル日数、最小データ日等）を定義。

- 研究 / リサーチ（kabusys.research）
  - factor_research モジュール:
    - calc_momentum: 1M/3M/6M リターンと 200 日移動平均乖離（ma200_dev）を計算。データ不足時の None 扱い。
    - calc_volatility: 20 日 ATR（true range の扱いに注意）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から直近財務データを取得し PER（EPS が 0/欠損なら None）, ROE を計算。
    - DuckDB ベースの SQL と Python 組合せでの実装、外部 API へはアクセスしない設計。
  - feature_exploration モジュール:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。ホライズン検証（1〜252）あり。
    - calc_ic: ファクター値と将来リターンの Spearman（ランク）相関を計算（レコード不足時は None）。
    - rank / factor_summary: ランク変換（同順位は平均ランク）、各カラムの基本統計量（count/mean/std/min/max/median）を提供。
    - 実装は標準ライブラリのみ（pandas 等に依存しない）。

- AI / NLP（kabusys.ai）
  - news_nlp モジュール:
    - calc_news_window: JST 時間窓（前日 15:00 JST ～ 当日 08:30 JST）を UTC naive datetime で算出。
    - score_news(conn, target_date, api_key=None): raw_news + news_symbols を集約して銘柄ごとに記事を結合し、OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信して銘柄別センチメント ai_score を ai_scores テーブルへ idempotent に書き込む。1 バッチ最大 20 銘柄、1 銘柄あたり記事数・文字数上限を設定。
    - API リトライ/バックオフ: 429、ネットワーク断、タイムアウト、5xx に対する指数バックオフリトライを実装。部分失敗時に他銘柄スコアを保護するための削除→挿入戦略（DELETE/INSERT）を採用。
    - レスポンスバリデーション: JSON パース回復処理（前後ノイズの {} 抽出）、results フォーマット検証、未知コード無視、スコア数値変換・有限性チェック、±1.0 でクリップ。
    - フェイルセーフ: API 呼び出し失敗でも例外を投げずスキップ・継続する方針（運用継続優先）。
  - regime_detector モジュール:
    - score_regime(conn, target_date, api_key=None): ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成し、市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ冪等書き込みする。
    - マクロ記事抽出: predefined マクロキーワードで raw_news をフィルタ、最大記事数制限あり。
    - OpenAI 呼び出しはニュース NLP とは別実装（モジュール結合を避ける）。
    - API エラー時のフォールバック: マクロセンチメントは 0.0 として継続。リトライ/バックオフ処理を備える。
    - ルックアヘッドバイアス対策: target_date 未満のデータのみを参照、datetime.today()/date.today() を直接参照しない実装方針。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーを直接引数で注入可能にする実装を用意（テスト容易性と鍵管理の分離を目的）。環境変数未設定時は明示的な ValueError を発生させることで誤った鍵運用の検出を容易に。

---

注記（設計方針・運用上の要点）
- ルックアヘッドバイアス防止：多くのバッチ処理（score_news, score_regime, factor 計算等）は target_date を受け取り、内部で現在時刻を参照しない設計。
- 冪等性：DB への書き込みは基本的に DELETE → INSERT または ON CONFLICT ベースで冪等操作を行う（部分失敗時のデータ保護を意識）。
- フェイルセーフ：外部 API エラーは（多くのケースで）例外を破壊的に伝播させず、ログ記録のうえ処理を継続する方針。
- 依存最小化：研究モジュール等は pandas 等の外部重い依存を避け、標準ライブラリ＋DuckDB で完結するよう実装。

今後の予定（未実装だが想定）
- Strategy / execution / monitoring モジュールの具現化（発注ロジック、実行監視、運用アラート）。
- ai モジュールのモデル選択やプロンプト改良、より詳細な応答検証ルールの追加。
- ETL の品質チェック強化（quality モジュールとの連携拡張）。