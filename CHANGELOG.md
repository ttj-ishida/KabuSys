Keep a Changelog
=================

すべての変更は https://keepachangelog.com/ja/ の慣例に従って記載しています。

[Unreleased]

[0.1.0] - 2026-04-04
-------------------

Added
- パッケージ基本構成
  - kabusys パッケージ初期バージョンを追加。
  - __version__ = "0.1.0" を設定し、主要サブパッケージ（data, research, ai, ...）を公開。

- 設定 / 環境変数読み込み（kabusys.config）
  - .env / .env.local 自動読み込み機能を追加（プロジェクトルートを .git または pyproject.toml から探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
  - .env パーサ実装（export プレフィックス対応、クォート／エスケープ処理、行内コメント処理）。
  - .env の読み込み時に OS 環境変数の保護（protected）を実装し、.env.local は上書き（override=True）を許可。
  - Settings クラスを実装し、環境変数から設定値をプロパティで取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
    - DUCKDB_PATH, SQLITE_PATH
    - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
    - CPU/MEMORY/DISK 閾値
    - KABUSYS_ENV（development/paper_trading/live の検証）および LOG_LEVEL 検証
    - is_live / is_paper / is_dev ユーティリティプロパティ
  - 必須変数未設定時には ValueError を送出する _require 実装。

- データプラットフォーム（kabusys.data）
  - ETL パイプラインの公開インターフェース（ETLResult の再エクスポート）。
  - pipeline モジュール:
    - ETLResult データクラスを導入。ETL 実行の集計（取得数・保存数・品質問題・エラー等）を保持。
    - 差分更新・バックフィル・品質チェック設計を反映した骨組みを実装。
    - DuckDB 上のテーブル存在チェック等ユーティリティ実装。
  - calendar_management モジュール:
    - JPX 市場カレンダー管理機能を実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days の営業日判定 API を提供。
    - calendar_update_job により J-Quants API から差分取得して market_calendar を冪等更新する処理を実装。
    - DB 登録の有無に応じた曜日ベースのフォールバックや健全性チェック、バックフィル振る舞いをサポート。
    - 最大探索範囲（_MAX_SEARCH_DAYS）などを導入して無限ループを防止。

- 研究用モジュール（kabusys.research）
  - factor_research:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を計算（prices_daily を使用）。
    - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio を計算。
    - calc_value: PER / ROE を raw_financials と prices_daily から計算。
    - 欠損・データ不足時の None 処理、ログ出力を実装。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズンの将来リターンを一括取得する汎用実装（horizons バリデーション含む）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を実装（必要なサンプル数チェック）。
    - rank: 平均ランク（同順位は平均）を計算するユーティリティ。
    - factor_summary: count/mean/std/min/max/median の統計サマリーを算出する実装。
  - すべて DuckDB 接続を受け取り、外部 API を呼ばない設計（研究環境向け）。

- AI 系処理（kabusys.ai）
  - news_nlp モジュール:
    - score_news(conn, target_date, api_key=None): raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）で銘柄ごとニュースセンチメントを算出して ai_scores に書き込む。
    - ニュースウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）を calc_news_window として実装。
    - バッチ送信（最大 _BATCH_SIZE=20 銘柄）と 1 銘柄あたりの上限記事数・文字数制限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - JSON Mode を前提としたレスポンスバリデーション（結果抽出や余分な前後テキストからの復元処理を含む）。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ・リトライ処理。部分失敗時に他銘柄スコアを保護するため DELETE → INSERT の置換戦略を採用。
    - スコアは ±1.0 にクリップ。API キー未設定時は ValueError を送出。
    - テスト用に _call_openai_api を patch できる設計。
  - regime_detector モジュール:
    - score_regime(conn, target_date, api_key=None): ETF 1321 の 200 日 MA 乖離（重み70%）とマクロセンチメント（重み30%）を合成して market_regime に書き込む。
    - マクロニュース取得（マクロキーワードによるタイトル抽出）と LLM（gpt-4o-mini）呼び出しによる macro_sentiment 評価（JSON 出力想定）。
    - LLM 呼び出しは堅牢なリトライとフェイルセーフ（API 失敗時 macro_sentiment=0.0）を備える。
    - スコア合成ロジックと閾値に基づくラベル付け（bull / neutral / bear）。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等処理、失敗時は ROLLBACK を行う。

- 再エクスポート / 公開 API
  - kabusys.data.etl: ETLResult を再エクスポート。
  - kabusys.research.__init__, kabusys.ai.__init__ 等で主要関数を __all__ により公開。

Security / Safety / Design decisions
- ルックアヘッドバイアス防止:
  - date/datetime の現在時刻参照（datetime.today() / date.today()）をファクション内部で行わず、必ず target_date を入力として扱う設計。
  - DB クエリは target_date より過去のデータを明示することでルックアヘッドを防止。
- トランザクション:
  - DB 書き込みは冪等・トランザクション（BEGIN/COMMIT/ROLLBACK）で保護。
- フェイルセーフ:
  - LLM / API の一時エラーやパース失敗時は例外を破壊的に投げず、警告ログ出力の上で安全側のデフォルト（例: macro_sentiment=0.0）にフォールバック。
- テスト容易性:
  - OpenAI 呼び出しを行う内部関数を patch できるように分離（ユニットテストで差し替え可能）。

Notes / Upgrade / Migration
- 動作に必要な主要環境変数:
  - OPENAI_API_KEY（AI モジュール利用時）、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD など。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われるため、パッケージ配置方法に注意。
- .env.local は .env を上書きする用途で想定。OS 環境変数は保護（上書き不可）。
- DuckDB の executemany に対する空リストの制約（0.10 系）を考慮した実装で互換性を確保。
- OpenAI SDK の例外の取り扱いは将来の SDK 変更に対する互換性を考慮して実装（status_code を getattr で安全に取得等）。

Fixed
- 初期リリースのため該当なし。

Breaking Changes
- 初期リリースのため該当なし。

署名
- 初回リリース (0.1.0): コアデータ処理・研究用指標・AI スコアリング・カレンダー管理・設定読み込みの基礎を実装しました。