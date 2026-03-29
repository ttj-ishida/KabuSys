# Changelog

すべての注目すべき変更はここに記録します。  
このファイルは Keep a Changelog のフォーマットに準拠します。  

※ 日付・内容はリポジトリ内のコードから推測して作成しています。

フォーマット: [Unreleased] および各リリースは日付付きで記載します。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-29
初回リリース。日本株のデータ取得・ETL、研究（リサーチ）ツール群、AI を用いたニュースセンチメント/市場レジーム判定、マーケットカレンダー等を含むパッケージの初期実装。

### Added
- パッケージ基本情報
  - パッケージ初期バージョンを `kabusys.__version__ = "0.1.0"` として公開。
  - パッケージの公開 API: data, strategy, execution, monitoring を __all__ に定義。

- 環境設定 / 設定管理（src/kabusys/config.py）
  - .env ファイル（.env, .env.local）や OS 環境変数から設定を自動読み込みする機能を追加。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）を実装し、CWD に依存しない自動ロードを実現。
  - .env のパースは export 形式やクォート、エスケープ、インラインコメントを適切に扱う。
  - 自動ロードを無効化するためのフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - 必須設定取得用 _require() と Settings クラスを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
  - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）のバリデーション（許可値セット）実装。
  - デフォルトの DB パス設定（DuckDB/SQLite）を提供。

- AI モジュール（src/kabusys/ai）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）に対し JSON Mode でバッチ送信し、銘柄ごとのセンチメント（ai_score）を ai_scores テーブルへ保存する処理を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ（calc_news_window）。
    - バッチサイズ、記事文字数・件数上限、JSON レスポンスの検証・パース、スコアの ±1.0 クリップなどの実装。
    - レート制限・接続断・タイムアウト・5xx に対する再試行（指数バックオフ）実装。
    - テスト用に _call_openai_api の差し替えが可能（unittest.mock.patch）。
    - DuckDB 0.10 における executemany の空リスト制約に配慮した DB 書き込みロジック。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を組み合わせて日次でレジーム（bull / neutral / bear）を判定し market_regime テーブルへ冪等書き込みする処理を実装。
    - prices_daily / raw_news を参照して ma200_ratio を算出。データ不足時は中立（1.0）へフォールバックして安全動作。
    - マクロニュースはキーワードベースで抽出し、OpenAI に JSON レスポンスを要求。API エラー時は macro_sentiment を 0.0 として処理を継続。
    - OpenAI 呼び出しは独立実装として用意（news_nlp と内部関数を共有しない設計）。
    - 冪等な DB 更新（BEGIN/DELETE/INSERT/COMMIT）を実装。

- データプラットフォーム（src/kabusys/data）
  - ETL パイプラインの結果型 ETLResult を公開（src/kabusys/data/pipeline.py / etl.py）。
    - 差分更新、バックフィル、品質チェックを行う ETL の設計に合わせたデータクラスを実装。
    - DuckDB 接続を前提とした最大日付取得などのユーティリティを提供。
    - 品質チェック結果を含めた監査用辞書変換機能（to_dict）。
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを用いた営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - DB データ存在時は DB 値優先、未登録日は曜日ベースのフォールバック（週末除外）で一貫して判定。
    - カレンダー差分取得ジョブ（calendar_update_job）を実装（J-Quants クライアント経由の取得 → jq.save_market_calendar による冪等保存）。
    - 最大探索日数やバックフィル、健全性チェックなどの安全策を実装。

- リサーチ / ファクター計算（src/kabusys/research）
  - factor_research.py
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Value（PER, ROE）、Volatility（20日 ATR）、Liquidity（20日平均売買代金、出来高比）などの計算ロジックを実装。prices_daily / raw_financials のみ参照する純粋な計算関数。
    - データ不足時の None 処理、返却フォーマットは (date, code) ベースの dict リスト。
  - feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（Spearman の ρ）計算（calc_ic）、ランク付けユーティリティ（rank）、ファクター統計サマリ（factor_summary）を実装。
    - 外部ライブラリに依存せず標準ライブラリ（および DuckDB）のみで実装。

- その他ユーティリティ
  - data/etl の ETLResult をトップレベルで再エクスポート。
  - research パッケージのエクスポート整理（zscore_normalize などのユーティリティを公開）。

### Changed
- （初期リリースのため過去の変更はなし。設計注記として以下を明示）
  - 日時の扱いについてルックアヘッドバイアス防止方針を徹底（datetime.today()/date.today() を直接参照しない設計を一部モジュールで採用）。
  - OpenAI 呼び出し時は JSON Mode を利用し、厳密な JSON を期待することで後続処理のバリデーションを容易に。

### Fixed
- （初期実装。コード内に安全フェイルセーフやログを多数追加して想定エラーに対処）

### Security
- 環境変数経由で API キー等を扱うことを想定（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY, KABU_API_PASSWORD, SLACK_BOT_TOKEN 等）。
- .env 自動ロードは無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）で制御可能。機密情報の扱いに関する注意点を README 等で明記することを推奨。

### Notes / 実装上の重要な挙動（利用者向け）
- OpenAI API
  - デフォルトモデルは gpt-4o-mini。API 呼び出しは JSON Mode（response_format={"type": "json_object"}）で行う想定。
  - API キーは引数で注入可能（テスト容易性）または環境変数 OPENAI_API_KEY を利用。未設定時は ValueError を送出する関数あり（score_news/score_regime）。
  - API の一時的失敗（429/接続断/タイムアウト/5xx）はリトライの後フォールバック（例: macro_sentiment=0.0 や該当チャンクスキップ）して処理を継続する設計。
  - テスト時の差し替えポイントとして内部の _call_openai_api を patch 可能。
- DuckDB
  - executemany に空リストを渡せないバージョン（DuckDB 0.10）への対策を実装（空時は実行をスキップ）。
- データ不足時のフォールバック
  - ma200_ratio などで過去データ不足時は中立値（1.0）にフォールバックして安全に動作。
- DB 書き込みは冪等性を重視（DELETE → INSERT、ON CONFLICT など）。

### Migration / 使い始めるためのチェックリスト
- 必須環境変数を設定:
  - OPENAI_API_KEY（または score_* の api_key 引数で注入）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- .env 自動読み込みを無効にしたいテスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- DuckDB / SQLite のデフォルトパス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- DuckDB のバージョン差異（executemany の挙動など）に注意。

---

今後の予定（推測）
- strategy / execution / monitoring の実装拡張（現時点でパッケージ参照はあるが実装は別途）。
- 追加の品質チェックルール、ETL スケジューリング、監視アラート（Slack 連携など）の強化。

もし CHANGELOG の表現や注目すべき差分に追加してほしい点（より詳細なファイル別の履歴、開発履歴の分割など）があれば教えてください。コードからさらに細かく推測して反映します。