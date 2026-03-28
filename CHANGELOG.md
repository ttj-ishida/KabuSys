# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングに従います。

## [0.1.0] - 2026-03-28

初回リリース。日本株自動売買システムのコアライブラリを実装しました。主な追加点・設計方針は以下の通りです。

### Added
- パッケージ基本情報
  - パッケージバージョン `__version__ = "0.1.0"` を追加。
  - パッケージの公開インターフェース（__all__）を定義（"data", "strategy", "execution", "monitoring"）。

- 設定 / 環境変数管理 (`kabusys.config`)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機能：
    - プロジェクトルートを `.git` または `pyproject.toml` から探索して検出（CWD に依存しない）。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - OS 環境変数を保護するための protected 上書き制御。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` による自動ロード無効化。
  - .env パーサの強化:
    - 空行・コメント行（#）をスキップ。
    - `export KEY=val` 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープを正しく処理。
    - クォートなし値の行内コメント判定を空白/タブの直前 `#` のみコメントと判断する仕様。
  - 必須環境変数取得時の検証（未設定時は ValueError）。
  - 利用可能な設定項目（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL 等）と helper プロパティ（is_live/is_paper/is_dev）を提供。
  - `KABUSYS_ENV` と `LOG_LEVEL` の値検証（許容値チェック）。

- データプラットフォーム（Data）モジュール群
  - ETL パイプラインのインターフェース (`kabusys.data.pipeline.ETLResult`)
    - ETL 実行結果を保持する dataclass を実装（取得件数、保存件数、品質問題、エラー一覧など）。
    - `has_errors`, `has_quality_errors`, `to_dict` を提供。
    - 小さなユーティリティ (テーブル存在確認、最大日付取得) を実装。
  - ETL 再エクスポート用の `kabusys.data.etl`（ETLResult の公開）。
  - カレンダー管理 (`kabusys.data.calendar_management`)
    - JPX マーケットカレンダーの夜間差分フェッチ/保存ロジック（calendar_update_job）を実装。
    - カレンダーデータがない場合の曜日ベースフォールバック（週末は非営業日）。
    - 営業日判定および操作ユーティリティ:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - 最大探索日数制限（_MAX_SEARCH_DAYS）や先読み・バックフィル（日数設定）・健全性チェックを導入。
    - DB 優先で未登録日は曜日フォールバックする一貫した設計。

- 研究 (Research) モジュール群 (`kabusys.research`)
  - ファクター計算 (`factor_research`)
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
      - データ不足時の None 処理、結果は (date, code) ベースの dict リストで返す。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率等を計算。
      - true_range の NULL 伝播制御、窓内行数不足時の None 処理。
    - calc_value: raw_financials から最新財務を取得して PER, ROE を計算（EPS=0 の場合は None）。
  - 特徴量探索 (`feature_exploration`)
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括 SQL で計算。
      - horizons の検証（正の整数、最大252）と重複除去。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（有効レコードが3件未満は None）。
    - rank: 同順位を平均ランクとするランク化ユーティリティ（丸めで ties 検出を安定化）。
    - factor_summary: count/mean/std/min/max/median を計算するサマリ機能。

- AI 関連 (`kabusys.ai`)
  - ニュース NLP スコアリング (`news_nlp.score_news`)
    - raw_news と news_symbols を集約して銘柄ごとのニューステキストを作成（記事数・文字数上限でトリム）。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して比較（ルックアヘッド防止のため date.today を参照しない設計）。
    - OpenAI（gpt-4o-mini） を JSON Mode で呼び出し、銘柄単位に -1.0〜1.0 のスコアを取得。
    - バッチ処理（最大 20 銘柄/コール）、429/ネットワーク/タイムアウト/5xx に対して指数的バックオフでリトライ。
    - レスポンス検証（JSON パース回復ロジック、results 配列検査、コード照合、数値チェック）と ±1.0 クリップ。
    - DB 書き込みは冪等操作（対象コードのみ DELETE → INSERT）で部分失敗時の保護を実現。
    - API キー解決: 引数優先、なければ環境変数 OPENAI_API_KEY、未設定時は ValueError。

  - 市場レジーム判定 (`ai.regime_detector.score_regime`)
    - ETF 1321（日経225連動型）の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を組み合わせて日次レジーム（bull / neutral / bear）を判定。
    - ma200_ratio の計算は target_date 未満のデータのみを参照（ルックアヘッドバイアス防止）。
    - マクロニュースは news_nlp.calc_news_window に基づくウィンドウで抽出、最大 20 件まで。
    - OpenAI 呼び出しは専用実装（news_nlp とプライベート関数を共有しない設計）。
    - リトライ/フォールバック: API 全滅やパース失敗時は macro_sentiment = 0.0 にフォールバックして処理継続。
    - 最終的なレジームスコアはクリップされ、閾値でラベル付け。結果は market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - 使用モデル: gpt-4o-mini。マクロキーワードセットを内包。

- DuckDB を中心とした DB 操作
  - 多くのモジュールで DuckDB 接続 (duckdb.DuckDBPyConnection) を受け取り SQL と Python の組み合わせで処理。
  - DuckDB バージョンの制約（executemany の空リスト不可等）を考慮した実装。

### Design / Behavior Notes
- ルックアヘッド・バイアス対策:
  - AI・研究モジュールともに内部で datetime.today()/date.today() を参照せず、必ず呼び出し側から target_date を受け取る設計。
  - DB クエリでも target_date 未満 / 以降などの排他条件を厳格に適用。
- フェイルセーフ設計:
  - 外部 API（OpenAI / J-Quants）失敗時は極力処理を継続（デフォルト値や部分結果を用いる）し、例外は必要な箇所でのみ伝播。
  - DB 書き込みはトランザクションと ROLLBACK 処理を行い、失敗時に警告ログを出力。
- テストしやすさ:
  - OpenAI 呼び出し箇所は内部関数として抽象化され、ユニットテストでモック差し替え可能に実装。
  - API キーは引数で注入可能。

### Fixed
- （初版のため該当なし）

### Changed
- （初版のため該当なし）

### Removed
- （初版のため該当なし）

### Security
- 外部 API のキーは引数優先かつ環境変数を参照する安全な解決方法を採用。環境変数未設定時は例外で明示する実装。

---

今後の予定（例）
- strategy / execution / monitoring モジュールの実装（現行はパッケージエントリを用意済み）。
- J-Quants API クライアントの細部実装や追加品質チェックルールの拡充。
- テストカバレッジの拡張と CI 設定。