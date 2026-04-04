# Changelog

すべての重要な変更履歴をここに記載します。本ファイルは「Keep a Changelog」に準拠します。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-04

### Added
- パッケージ初版リリース: kabusys (日本株自動売買システム) の基本モジュール群を追加。
  - パッケージバージョン: 0.1.0

- 環境変数 / 設定管理
  - 自動 .env ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。OS 環境変数は保護され、.env.local で上書き可能。
  - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env のパース機能を実装（export 形式、クォート、コメント処理、エスケープ対応）。
  - Settings クラスを提供し、主要な設定に対する取得・検証を行うプロパティを実装。
    - 主要な環境変数例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, OPENAI_API_KEY, LINE_CHANNEL_ACCESS_TOKEN, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL 等。
  - KABUSYS_ENV と LOG_LEVEL の許容値チェックを実装（不正値は ValueError）。

- データ関連 (duckdb を前提)
  - ETL 用インターフェース ETLResult を追加（kabusys.data.etl から再エクスポート）。
  - ETL パイプライン基盤（kabusys.data.pipeline）を実装。
    - 差分取得、バックフィル、品質チェックを想定した設計。
    - ETLResult に品質検出やエラーを収集する機能を実装。
  - マーケットカレンダー管理モジュール（kabusys.data.calendar_management）を追加。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day といった営業日判定 API を提供。
    - market_calendar が未取得の際は曜日ベースでフォールバックするロジックを実装。
    - calendar_update_job: J-Quants クライアント経由で差分取得し冪等的に保存する夜間バッチ処理を実装（バックフィル、健全性チェック含む）。

- 研究（Research）モジュール
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離などを計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率等を計算。
    - calc_value: PER / ROE を raw_financials と prices_daily から計算。
    - DuckDB ベースの SQL 実装で、外部 API へアクセスしないことを保証。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: 指定ホライズンの将来リターンを一括クエリで計算（horizons の検証あり）。
    - calc_ic: スピアマンランク相関（IC）を計算（結合と欠損値除外、少数サンプル時のハンドリング）。
    - rank: 同順位は平均ランクにするランク変換処理（丸めで ties を安定化）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー。

- AI / ニュース NLP
  - ニュースセンチメント分析モジュール（kabusys.ai.news_nlp）
    - target_date に対するニュース収集ウィンドウを calc_news_window で定義（JST -> UTC 変換を考慮）。
    - raw_news と news_symbols を基に銘柄毎に記事を集約し、OpenAI の Chat API（gpt-4o-mini, JSON Mode）へバッチ送信してセンチメントを取得。
    - バッチサイズや最大記事数・最大文字数といったトークン肥大化対策、429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。
    - レスポンス検証とスコアのクリップ（±1.0）。部分失敗時に既存スコアを保護するため、書き込みは対象コードに限定して DELETE→INSERT（トランザクション）を行う。
    - フェイルセーフ: API 失敗時は該当銘柄スキップ、例外は必要に応じて上位で扱う。
  - 市場レジーム判定モジュール（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で regime（bull/neutral/bear）を判定。
    - ma200_ratio 計算は target_date 未満のデータのみを使用してルックアヘッドバイアスを防止。
    - マクロキーワードによる記事抽出、LLM 呼出し（gpt-4o-mini）、リトライ・フェイルセーフ実装（API 失敗時 macro_sentiment=0.0）。
    - 計算結果は market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時 ROLLBACK 処理あり）。

- 実装・設計上の重要事項（明示的に実装）
  - DuckDB 接続を利用することを前提とした SQL ベースの実装。
  - ルックアヘッドバイアス対策として内部で datetime.today()/date.today() を参照しない設計（target_date を呼び出し側で指定）。
  - OpenAI 呼び出しについてはモジュール毎に private 呼出し関数を独立実装し、テスト時には patch で差し替え可能。
  - API 呼び出しは JSON Mode（response_format={"type":"json_object"}）を使用し、レスポンスの堅牢なパース処理を実装。
  - トランザクション処理は明示的に BEGIN/COMMIT で行い、失敗時は ROLLBACK を試みてログを残す。
  - 設定に関するデフォルト値と閾値（CPU/MEM/DISK 等）を Settings のプロパティとして提供。

### Changed
- 初版のため該当なし。

### Fixed
- 初版のため該当なし。

### Security
- 初版のため該当なし（ただし環境変数の取り扱いで OS 環境（protected）を上書きしない設計を採用）。

---

注記 / マイグレーション情報
- OpenAI API を利用する関数（score_news, score_regime）は api_key 引数を受け取り、未指定時は環境変数 OPENAI_API_KEY を使用します。未設定の場合は ValueError を送出します。
- .env 自動ロードはプロジェクトルートの検出に依存するため、配布後やテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して自動ロードを無効化できます。
- DuckDB 側の executemany に空リストを渡すとエラーになる古いバージョンに対する互換性考慮があり、該当箇所では空チェックを行っています。
- ニュースの時間ウィンドウは JST 基準で設計されているため、DB に保存される raw_news.datetime は UTC である前提です。
- ログ・警告は失敗時も処理継続するフェイルセーフな方針で実装されています。プロダクション運用時はログ監視と適切な再実行戦略を検討してください。

もし必要であれば、各モジュールごとの使用例（API 呼び出しサンプル）や環境変数一覧・推奨設定を別途まとめます。