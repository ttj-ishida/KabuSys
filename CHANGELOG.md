# Changelog

すべての重要な変更は Keep a Changelog 準拠で記録しています。  
現在のバージョン: 0.1.0

なお、以下は提供されたコードベースの内容から推測してまとめた初期リリースの変更履歴です。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-04
### Added
- パッケージ初期導入
  - kabusys パッケージを追加。バージョンは 0.1.0。

- 環境変数・設定管理（kabusys.config）
  - .env / .env.local 自動読み込み機能を実装。読み込み順は OS 環境変数 > .env.local > .env。
  - プロジェクトルートの自動検出: __file__ を起点に .git または pyproject.toml を探索。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能。
  - .env パーサーを実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応）。
  - OS 側既存の環境変数を保護する protected 機能（.env の上書きを制御）。
  - Settings クラスを提供し、アプリで使う設定値（J-Quants / kabuステーション / LINE / DB パス / 監視閾値 / 環境・ログレベル判定等）をプロパティ経由で取得可能。
  - 必須環境変数未設定時に明示的なエラーを投げる _require を実装（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を使い、銘柄ごとに記事を集約して OpenAI（gpt-4o-mini）でセンチメントを評価し ai_scores テーブルへ書き込む機能を実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を提供（calc_news_window）。
    - バッチ処理（最大 20 銘柄/コール）、記事数／文字数制限（銘柄ごと最大記事数/最大文字数）などトークン肥大化対策を実装。
    - JSON Mode を利用したレスポンス検証とパース補正（前後余計なテキストの補正）。
    - レート制限・ネットワーク断・タイムアウト・5xx サーバーエラーに対する指数バックオフとリトライを実装。リトライ上限超過時は該当チャンクをスキップして継続（フェイルセーフ）。
    - レスポンス検証は所望のコードのみを受け入れ、スコアは ±1.0 にクリップ。
    - 部分失敗に備え、ai_scores への書き込みは該当コードのみ DELETE→INSERT の置換方式（部分失敗時に他コードの既存スコアを保護）。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM ベースセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出・保存。
    - prices_daily から ma200_ratio を計算、raw_news をマクロキーワードでフィルタしてタイトルを取得、OpenAI で macro_sentiment を算出、重み付け合成して market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - API 呼び出しに対するリトライ・バックオフ、500 系はリトライ、非5xxは即フォールバック（macro_sentiment=0.0）。JSON 解析エラー時も 0.0 で継続（例外を投げない）。
    - レジーム判定はルックアヘッドバイアス防止の実装方針に従い、内部で datetime.today()/date.today() を使わず、target_date 未満のデータのみ参照。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダー（market_calendar）を管理するユーティリティを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day といった営業日判定 API を提供。
    - market_calendar がなければ曜日ベース（土日除外）のフォールバックを使用。DB 登録値が優先され、未登録日は一貫して曜日フォールバックで補完。
    - カレンダー夜間更新ジョブ calendar_update_job を実装（J-Quants から差分取得 -> 保存）。バックフィル・健全性チェック・例外ハンドリングを実装。

  - ETL パイプライン（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult データクラスを公開（ETL 実行結果の集約、品質チェック結果・エラーの収集）。
    - 差分更新・backfill・品質チェックのためのインターフェースを整備（jquants_client と quality モジュールとの連携を想定）。
    - テーブル存在チェック、最大日付取得などのユーティリティを実装。

- リサーチツール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER、ROE）を DuckDB 上で計算する関数を追加（calc_momentum, calc_volatility, calc_value）。
    - データ不足時は None で返す設計。DuckDB のウィンドウ関数を活用。
    - すべての関数は prices_daily / raw_financials のみ参照し、発注等の外部操作は行わない。

  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns: 複数ホライズン対応、入力検証あり）。
    - IC（Information Coefficient）計算（calc_ic: スピアマン順位相関、3 銘柄未満は None）。
    - ファクター統計サマリー（factor_summary: count/mean/std/min/max/median）。
    - ランク付けユーティリティ（rank: 同順位は平均ランクを使用）。

- パッケージエクスポート
  - 各サブモジュールの主要関数を __all__ にて公開（例: kabusys.ai.score_news, kabusys.research.*）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 環境変数から API キー等を取得する設計。OpenAI API キーを引数で注入可能にしてテスト容易性を確保（api_key 引数がない場合は環境変数 OPENAI_API_KEY を参照）。必須トークン未設定時は明示的な ValueError を発生させる。

### Notes / Migration
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は Settings のプロパティで必須（未設定時は ValueError）。
  - OpenAI を利用する関数（score_news, score_regime）は OPENAI_API_KEY 環境変数または api_key 引数が必要。
- デフォルトの DB パス:
  - DuckDB: data/kabusys.duckdb（DUCKDB_PATH で上書き可能）
  - SQLite（監視用）: data/monitoring.db（SQLITE_PATH で上書き可能）
- .env の自動読み込みを無効化したいテスト等の用途では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

--- 

今後のリリースでは、エラー集計・品質チェックの挙動改善や OpenAI のモデル差し替え、DB マイグレーションスクリプト等の追記が想定されます。必要であれば、各モジュールごとの詳細な API 使用例や注意点（例: DuckDB テーブルスキーマ想定）も追加できます。