# Changelog

すべての注記は Keep a Changelog の形式に準拠します。  
このファイルはコードベースから推測して作成した初回リリース向けの変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-04-03

### Added
- パッケージ初回リリース "KabuSys"（__version__ = 0.1.0）。
  - パッケージの公開インターフェースとして data, strategy, execution, monitoring モジュールをエクスポート。

- 環境設定 / ロード機能（kabusys.config）
  - .env / .env.local 自動読み込み機能を実装（プロジェクトルート判定: .git または pyproject.toml を探索）。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で抑止可能。
  - .env パーサは `export KEY=val` 形式、シングル/ダブルクォート内のエスケープ、インラインコメント扱い等に対応。
  - OS 環境変数を保護する仕組み（.env の上書き時に保護されたキーを除外）。
  - Settings クラスを提供し、アプリケーション設定値をプロパティ経由で取得可能：
    - J-Quants / kabuステーション / LINE / DB パス / 監視関連（PID、kill flag、閾値） / システム設定（KABUSYS_ENV, LOG_LEVEL）など。
  - 必須環境変数未設定時は明示的に ValueError を送出（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
  - KABUSYS_ENV と LOG_LEVEL は許容値チェックを行い、不正値は ValueError。

- AI モジュール（kabusys.ai）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - raw_news と news_symbols から前日 15:00 JST ～ 当日 08:30 JST のニュースを集計。
    - 銘柄毎に記事を集約し、1 銘柄あたり最大記事数・文字数でトリムして OpenAI（gpt-4o-mini）へバッチ送信。
    - バッチ処理（デフォルト最大 20 銘柄/コール）、429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ。
    - レスポンス検証（JSON 抽出、results キー、code と score の検査）とスコア ±1.0 クリップ。
    - DuckDB への書き込みは部分失敗で既存データを守る方針（該当コードのみ DELETE → INSERT）。
    - テスト容易性: API 呼び出し部 `_call_openai_api` をモック可能。
    - API キーは引数で注入可能（api_key）、未指定時は環境変数 OPENAI_API_KEY を参照。未設定時は ValueError。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（Nikkei225 ETF）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news を参照し、calc_news_window 等のルールに基づくウィンドウで記事を抽出。
    - LLM 呼び出し（gpt-4o-mini、JSON mode）に対する retry/backoff と 5xx 判定の扱いを実装。API 失敗時は macro_sentiment=0.0 でフォールバック（フェイルセーフ）。
    - 計算結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時は ROLLBACK を試みて例外を伝播。

- 研究（Research）モジュール（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を DuckDB SQL で計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。NULL 伝播制御あり。
    - calc_value: raw_financials から直近財務データを取得して PER / ROE を計算（EPS が 0/欠損の場合は None）。
    - いずれも外部 API に依存せず、prices_daily / raw_financials のみ参照。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズンに対する将来リターンを一括 SQL で取得（ホライズン検証あり）。
    - calc_ic: スピアマンランク相関による IC を計算（同順位は平均ランク）。
    - factor_summary: count/mean/std/min/max/median を計算（None は除外）。
    - rank: 値をランクに変換（同順位は平均ランク、丸めで ties の判定を安定化）。
  - zscore_normalize を data.stats から再エクスポート。

- データ基盤（kabusys.data）
  - calendar_management:
    - market_calendar を基に営業日判定とユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を提供。
    - DB にデータがない場合は曜日ベース（土日）でフォールバック。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等保存（バックフィル、先読み、健全性チェックを実装）。
  - pipeline / ETL:
    - ETLResult データクラスを導入（取得件数、保存件数、品質問題、エラー一覧等を格納）。
    - ETL 実行の差分取得・保存・品質チェックの設計（backfill、部分失敗保護、DuckDB 互換性への配慮）。
  - etl API（kabusys.data.etl）で ETLResult を再エクスポート。

### Changed
- 初回リリースにつき変更履歴はなし（新規導入）。

### Fixed
- 初回リリースにつき修正履歴はなし。

### Notes / 設計上の重要なポイント
- ルックアヘッドバイアス回避:
  - 日付参照は datetime.today() / date.today() に依存しない設計（関数呼び出し時に target_date を明示的に渡す）。
  - DB クエリは target_date 未満 / 排他条件を用いる等で未来データ混入を防止。
- OpenAI 呼び出し:
  - gpt-4o-mini を JSON mode（response_format={"type":"json_object"}）で利用。API レスポンスのパース失敗や想定外形式に対する堅牢な処理あり。
  - テストのため API 呼び出し関数をモック差替え可能（ユニットテスト用のフック）。
- DB 操作:
  - DuckDB 互換性（executemany の空リスト回避等）や冪等書き込み（DELETE→INSERT）を重視。
  - トランザクション（BEGIN/COMMIT/ROLLBACK）で失敗時の一貫性確保。ROLLBACK 失敗は警告ログ。
- フェイルセーフ:
  - LLM/API 部分の失敗は基本的に例外を投げずにスコア 0.0（news/regime）やスキップ動作で継続する設計（ただし API キー未設定は ValueError）。
- 設定の優先順位:
  - OS 環境変数 > .env.local > .env。.env.local は .env を上書き可能。
  - .env 読み込みに失敗した場合は警告ログを出力して継続。

### Breaking Changes
- なし（初回リリース）。

---

要約すると、本リリース（0.1.0）はデータ収集・カレンダー管理・ETL 基盤、研究用ファクター計算、OpenAI を用いたニュース NLP と市場レジーム判定、環境設定管理など、株式自動売買プラットフォームのコア機能群を一通り実装した初期版です。必要な環境変数（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を設定してご利用ください。