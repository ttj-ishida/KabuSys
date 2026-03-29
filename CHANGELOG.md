CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
このファイルは「Keep a Changelog」の形式に準拠しています。  

フォーマット:
- 変更はセマンティックバージョニングに従って記載しています。
- 各リリースには日付を付与しています。

履歴
----

## [Unreleased]
（現在リリース済みのベース実装のみ。次バージョンでの追加予定機能や修正点はここに記載します。）

## [0.1.0] - 2026-03-29
初回公開リリース。以下の主要機能・モジュールを追加しました。

### 追加 (Added)
- パッケージ構成
  - パッケージ kabusys を導入。公開サブパッケージ: data, research, ai, execution, monitoring（__all__ 設定）。
  - バージョン情報: __version__ = "0.1.0"。

- 設定管理（kabusys.config）
  - Settings クラスを実装し、環境変数から設定を取得する統一インターフェースを提供。
  - .env 自動ロード機能を実装（プロジェクトルートの判定に .git / pyproject.toml を使用）。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサーは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントなどに対応。
  - 必須環境変数チェック（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。デフォルト値を持つ項目（KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH）を定義。
  - KABUSYS_ENV と LOG_LEVEL の値検証ロジック（許容値チェック）を追加。開発/ペーパー/本番判定用のユーティリティプロパティ（is_dev / is_paper / is_live）を提供。

- データ基盤（kabusys.data）
  - calendar_management:
    - JPX マーケットカレンダー管理ロジックを実装。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day といった営業日判定ユーティリティを提供。
    - calendar_update_job を実装し、J-Quants からの差分取得と market_calendar テーブルへの冪等保存（バックフィル・健全性チェック付き）を行う。
    - market_calendar 非整備時は曜日ベースのフォールバックを採用。
  - pipeline / etl:
    - ETLResult データクラスを定義し、ETL の実行結果（取得数、保存数、品質問題、エラー等）を集約。
    - ETL に必要なユーティリティ（最終取得日の取得、テーブル存在チェックなど）を提供。
    - kabusys.data.etl で ETLResult を再エクスポート。

- 研究モジュール（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER, ROE）などの定量ファクター計算関数を実装。
    - calc_momentum, calc_volatility, calc_value を実装し、prices_daily / raw_financials テーブルを参照して結果を (date, code) ベースの dict リストで返す。
  - feature_exploration:
    - 将来リターン算出（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク変換ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas など外部ライブラリに依存しない純粋 Python + SQL 実装。

- AI モジュール（kabusys.ai）
  - ニュースセンチメント（kabusys.ai.news_nlp）
    - score_news(conn, target_date, api_key=None) を実装。raw_news と news_symbols から記事を集約し、OpenAI（gpt-4o-mini）の JSON モードで銘柄ごとのセンチメントを取得して ai_scores テーブルへ保存する。
    - バッチ処理（1回あたり最大 _BATCH_SIZE=20 銘柄）、1銘柄あたりの記事数・文字数上限（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）を実装。
    - 再試行（429、ネットワーク断、タイムアウト、5xx）に対する指数バックオフ実装。レスポンスは厳密な JSON を期待し、パース・バリデーション検証済みのスコアのみを採用（不正レスポンスはスキップ）。
    - 部分失敗時にも既存スコアを残すため、書込みはコードを絞って DELETE→INSERT を行う（DuckDB の executemany 空リスト制約に配慮）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - score_regime(conn, target_date, api_key=None) を実装。ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込みする。
    - マクロニュースはニュース NLP の calc_news_window を利用して対象ウィンドウを決定。OpenAI 呼び出しは専用実装を持ち、リトライ/フォールバック（失敗時 macro_sentiment=0.0）を行う。
    - ルックアヘッドバイアスを防ぐ設計（date 未満 / target_date 依存のクエリ、datetime.today() を参照しない等）。

- 共通設計上の注意点
  - DuckDB を主要なローカル DB として利用。各種関数は DuckDB 接続を引数に取り SQL を中心に処理。
  - DB 書込みは明示的に BEGIN / COMMIT / ROLLBACK を使用して冪等性と失敗時のロールバックを確保。ROLLBACK 失敗時の警告ログ出力にも対応。
  - テスト容易性: OpenAI 呼び出し部分は関数単位で差し替え（unittest.mock.patch）できるように設計。
  - ルックアヘッドバイアス防止のため、内部処理で現在日時（datetime.today()/date.today()）を直接参照しない設計方針を採用している箇所がある。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 削除 (Removed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- 初回リリースのため該当なし。

重要な注意事項 / マイグレーション
--------------------------------
- AI 機能（score_news / score_regime）を利用するには OpenAI API キー（環境変数 OPENAI_API_KEY または api_key 引数）が必須です。未設定時は ValueError を送出します。
- 環境変数の自動ロードはプロジェクトルート検出に依存します。パッケージ配布後にテストや CI から .env を読み込ませたくない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- デフォルトのデータベースパス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  必要に応じて環境変数で上書きしてください。
- DuckDB の executemany は空リストバインドで問題を起こすバージョンがあるため、コード内で空配列時の分岐を入れています。DuckDB のバージョンアップ時は注意してください。

既知の挙動・実装上の留意点
------------------------
- OpenAI 呼び出しは gpt-4o-mini を想定し、JSON モードで厳密な JSON を期待します。LLM の挙動により前後に余計なテキストが混ざる場合に備えパース回復処理を実装していますが、完全な互換性は保証しません。
- API 呼び出し失敗時のフェイルセーフとして、ニュース系はスコアを取得できない銘柄をスキップ、レジーム判定は macro_sentiment を 0.0 として処理を継続します。
- calendar_update_job は J-Quants クライアント（jquants_client）を利用します。外部 API 側の仕様変更や認証方法の変化に注意してください。

貢献
----
初回リリースにつき、今後のバグ修正・機能追加の PR を歓迎します。README / CONTRIBUTING で開発フローを整備する予定です。