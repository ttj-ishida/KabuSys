# Keep a Changelog

すべての可視的な変更はこのファイルに記録します。  
このプロジェクトは [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) の方針に従います。

## [Unreleased]

## [0.1.0] - 2026-03-29
初回公開リリース。パッケージの骨格と主要機能を実装しました。

### Added
- パッケージ基盤
  - kabusys パッケージ初版を追加。公開 API の __all__ に data, strategy, execution, monitoring を含む（将来モジュールの公開を想定）。
  - パッケージバージョンを `__version__ = "0.1.0"` に設定。

- 設定・環境変数管理（kabusys.config）
  - .env/.env.local ファイルと OS 環境変数から設定を自動読み込みする仕組みを実装（プロジェクトルートの検出は .git または pyproject.toml を基準に行う）。
  - .env パーサーを実装（コメント、export プレフィックス、シングル／ダブルクォート、エスケープ対応、インラインコメント処理）。
  - 自動ロードを環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - OS 環境変数を保護するため `.env` 読み込み時に既存キーを上書きしない挙動をデフォルトとし、`.env.local` は上書きを許容（ただし OS 環境変数は保護）。
  - Settings クラスを実装して型安全に設定を取得するプロパティを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV/LOG_LEVEL バリデーションなど）。
  - 必須環境変数未設定時は ValueError を送出する `_require` を提供。

- AI / ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を用いて銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いてセンチメントスコアを算出する score_news 関数を実装。
  - ニュース収集ウィンドウ（JST 前日 15:00 ～ 当日 08:30 = UTC 前日 06:00 ～ 23:30）を計算する calc_news_window を実装。
  - バッチ処理（1 API コール当たり最大 20 銘柄）・記事文字数上限・記事数上限の制限実装によるトークン肥大化対策。
  - API の一時エラー（429/ネットワーク断/タイムアウト/5xx）に対する指数バックオフリトライを実装。
  - OpenAI レスポンスのバリデーション（JSON パース、"results" 配列と要素構造、未知コードの無視、数値変換、有限性チェック）と ±1.0 クリップを実装。
  - 部分成功時の DB 書き込み戦略（対象コードのみ DELETE → INSERT を行い、部分失敗で既存スコアを消去しない）を採用。
  - テスト向けフックとして _call_openai_api を patch 可能に実装。

- AI / 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とニュースによるマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
  - 移動平均乖離の計算（ルックアヘッドバイアス回避のため target_date 未満のデータのみ利用）とデータ不足時のフォールバック（中立値 1.0）を実装。
  - マクロキーワード抽出、OpenAI 呼び出し、レスポンス JSON パース、リトライ・フォールバック（API 失敗時は macro_sentiment=0.0）を実装。
  - レジーム結果を market_regime テーブルへ冪等（BEGIN/DELETE/INSERT/COMMIT）で保存。

- データ基盤（kabusys.data）
  - calendar_management モジュールを実装し、JPX カレンダー管理・営業日判定機能を提供。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days の一式を実装。
    - market_calendar がない場合は曜日（土日）ベースのフォールバックを使用。
    - calendar_update_job を実装し J-Quants API から差分取得→保存（バックフィルと健全性チェックを含む）。
  - ETL パイプラインの型と結果（pipeline.ETLResult）を実装。
  - data.etl モジュールで ETLResult を再エクスポート。

- リサーチ（kabusys.research）
  - factor_research モジュール:
    - calc_momentum：1M/3M/6M リターンと 200 日 MA 乖離（ma200_dev）計算。
    - calc_volatility：20 日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
    - calc_value：raw_financials から最新財務を取得して PER、ROE を計算（EPS が 0/欠損は None）。
  - feature_exploration モジュール:
    - calc_forward_returns：将来リターン（複数ホライズン）を一度のクエリで取得する汎用実装。
    - calc_ic：ファクター値と将来リターンのスピアマンランク相関（IC）を計算。
    - rank：値を平均ランクに変換するユーティリティ（丸めで ties の検出漏れ対策）。
    - factor_summary：count/mean/std/min/max/median を計算する統計サマリー。

- 互換性・運用周り
  - DuckDB を利用した SQL 実装。DuckDB の executemany に関する既知挙動（空リスト不可）を考慮した安全な DB 書き込み実装。
  - ログ出力（info/warning/debug）を適所に追加し、フェイルセーフ時の情報を出力。
  - OpenAI モデルとして gpt-4o-mini を想定。

### Changed
- （初版なので変更はなし）

### Fixed
- （初版なので修正はなし）

### Deprecated
- （初版なのでなし）

### Removed
- （初版なのでなし）

### Security
- 環境変数管理で OS 環境変数を保護する仕組みを導入（.env 読み込み時に既存 OS 環境変数を上書きしない）。
- 必須トークン未設定時は明示的に例外を投げることで安全性を確保（OpenAI キーや Slack トークン等）。

### Notes / 実装上の設計方針（重要）
- ルックアヘッドバイアス対策として、いかなる箇所も datetime.today()/date.today() を直接参照せず、外部から与えた target_date を基準に処理を行う方針を徹底。
- OpenAI 呼び出しは各モジュールで独立実装し、モジュール間でプライベート関数を共有しないことで結合度を下げ、テストしやすくしている（ユニットテストでのモック差し替えを想定）。
- API エラー時はフォールバック（スコア 0.0）やスキップで継続する「フェイルセーフ」な設計を採用。致命的な DB 書き込み失敗時のみ例外を伝播。
- DuckDB の互換性に関する注記（executemany の空リスト回避など）をコーディングに反映。

もしリリース日や追加してほしい変更項目（例: リリースノートの細分化、既知の制約、マイグレーション手順など）があればお知らせください。必要に応じて Unreleased セクションや将来のリリース候補を追加します。