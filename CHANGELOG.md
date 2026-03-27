# Changelog

すべての変更は Keep a Changelog の形式に準拠します。  
このファイルはコードベースの内容から推測して作成した初期リリース向けの変更履歴です。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-03-27
初回公開リリース。以下の主要機能を実装・公開。

### Added
- パッケージメタ情報
  - kabusys パッケージ初期化: __version__ = "0.1.0"、主要サブパッケージを __all__ で公開（data, strategy, execution, monitoring）。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび OS 環境変数から設定を読み込む自動ローダー実装。
  - プロジェクトルート検出ロジック: .git または pyproject.toml を起点に自動検出（カレントディレクトリに依存しない）。
  - .env パース実装:
    - export KEY=val 形式対応、シングル/ダブルクォートとバックスラッシュエスケープ対応。
    - コメント扱いルール（未クォートでの # の扱い等）を考慮。
  - .env の読み込み優先順位: OS 環境 > .env.local（上書き） > .env（未設定のみ）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを公開（settings）:
    - J-Quants / kabuステーション / Slack / DB パス等のプロパティ（必須変数は未設定時に ValueError を投げる）。
    - env（development / paper_trading / live）と log_level の検証、ユーティリティプロパティ is_live/is_paper/is_dev。
    - デフォルト DB パス（DuckDB, SQLite）をサポート。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを評価し、ai_scores テーブルへ書き込み。
    - タイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST）を calc_news_window として提供。
    - バッチ処理（最大 20 銘柄 / コール）、トークン肥大への対策（記事数上限・文字数トリム）。
    - エラーハンドリング: 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライ。その他エラーはスキップしフェイルセーフを保持。
    - レスポンスバリデーション（JSON 解析、results 配列・code/score 構造、既知コードのみにスコアを適用）。
    - スコアは ±1.0 にクリップ。
    - テスト用に _call_openai_api を patch 可能に設計。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）を算出。
    - マクロ記事抽出のためのキーワードリスト（日本・米国・グローバル系）を実装。
    - OpenAI 呼び出しは独自実装でモジュール結合を避ける。
    - API エラー時のフォールバック（macro_sentiment=0.0）、リトライ/バックオフ、JSON パース失敗時のログ出力と継続処理。
    - DuckDB への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - テスト容易性のため _call_openai_api を差し替え可能。

- データ処理／ETL（kabusys.data）
  - ETL 結果型 ETLResult の定義と再エクスポート（kabusys.data.etl）。
    - ETL の取得件数・保存件数・品質チェック結果・エラー一覧などを保持する dataclass を実装。
    - to_dict() で品質問題をシリアライズ可能。
  - ETL パイプライン基盤（kabusys.data.pipeline）
    - 差分更新のためのユーティリティ（最終日取得、テーブル存在判定など）。
    - デフォルトのバックフィル日数やカレンダー先読み等の方針を実装。
    - 市場カレンダーや株価・財務データ等の差分取得・保存・品質チェックの設計に準拠した補助関数を提供。
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar を用いた営業日判定ロジックを提供（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB にデータがない場合は曜日ベース（土日除く）でフォールバックする挙動。
    - calendar_update_job を実装し、J-Quants から差分取得して market_calendar を冪等に更新（バックフィル・健全性チェック・保存数返却）。
    - 最大探索日数の上限（_MAX_SEARCH_DAYS）など安全策を実装。

- リサーチ機能（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M リターン・ma200 乖離）、ボラティリティ（20日 ATR、相対 ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER, ROE）を計算する関数群（calc_momentum, calc_volatility, calc_value）。
    - DuckDB のウィンドウ関数を活用した SQL ベース実装。データ不足時の None 戻し等を実装。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）: 指定ホライズンまでの fwd_* を一括取得。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンランク相関を実装。
    - ランク変換ユーティリティ（rank）: 同順位は平均ランク化。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を算出。
  - すべてのリサーチ関数は外部 API に依存せず DuckDB の prices_daily / raw_financials 等のテーブルのみ参照。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは関数引数で注入可能（テスト性向上）かつ環境変数 OPENAI_API_KEY を参照する実装。未設定時は ValueError で明示。

### Notes / Implementation Details / 設計上の注意
- ルックアヘッドバイアス防止のため、いずれの AI スコア算出／レジーム判定処理も datetime.today() / date.today() を内部で直接参照しない設計（target_date 引数に基づく）。
- DuckDB の一部バージョン差異（executemany に空リスト不可等）を考慮した実装が含まれる。
- API 呼び出しに対しては明示的なリトライ・バックオフ戦略を実装し、致命的失敗を避けるフェイルセーフ動作を採用。部分失敗時でも既存データを不必要に消さないための差分書き込み・コード絞り込みを行う。
- テスト容易性を考慮し、外部 API 呼び出し箇所（_call_openai_api 等）を patch して差し替え可能にしている。

---

作者注: 本 CHANGELOG は提供されたソースコードからの推測に基づいて作成されています。実際のリリースノートやリリース日付はプロジェクト運用に応じて調整してください。