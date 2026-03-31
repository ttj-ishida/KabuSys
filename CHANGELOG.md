# CHANGELOG

すべての注目すべき変更点をこのファイルで管理します。本ファイルは「Keep a Changelog」準拠の形式で記載しています。

フォーマット:
- 変更はセクション（Added / Changed / Fixed / Security 等）ごとに分類しています。
- 各リリースにはバージョンと日付を付記しています。

<!-- NOTE: このリリースはパッケージの初回公開相当として作成されています -->

## [0.1.0] - 2026-03-31

### Added
- 基本パッケージ構成を追加（kabusys パッケージの初期公開）
  - パッケージバージョンを `0.1.0` に設定（src/kabusys/__init__.py）。
  - パッケージの公開 API: data, strategy, execution, monitoring を __all__ で定義。

- 環境設定管理モジュールを追加（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込みする仕組みを実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化サポート。
  - .env パーサは `export KEY=val` 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントに対応。
  - 環境変数の上書きルール: OS 環境変数 > .env.local > .env。OS 環境変数は protected として上書きを防止。
  - Settings クラスを提供し、各種必須設定（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等）やパス（DUCKDB_PATH / SQLITE_PATH）、環境（KABUSYS_ENV）やログレベル（LOG_LEVEL）の検証ロジックを実装。

- AI 関連モジュールを追加（kabusys.ai）
  - news_nlp:
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）の JSON モードで銘柄ごとのセンチメント（-1.0〜1.0）を計算して ai_scores テーブルへ書き込む処理を実装。
    - バッチ処理（最大 20 銘柄/リクエスト）、1銘柄あたりの記事上限（10件）、文字数トリム（3000 文字）を導入。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフによるリトライ実装。
    - レスポンスの厳格なバリデーションと JSON 復元ロジックを実装（余計な前後テキストから最外の {} を抽出）。
    - DuckDB の互換性問題を考慮し、executemany で空パラメータを渡さない保護ロジックを追加。
    - テスト用に _call_openai_api をパッチ可能にしている（unittest.mock.patch により差し替え可能）。

  - regime_detector:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を算出し market_regime テーブルへ冪等書き込みする処理を実装。
    - ma200 データ不足時は中立（ma200_ratio = 1.0）にフォールバック。マクロニュースが無い/API失敗時のフェイルセーフで macro_sentiment = 0.0。
    - OpenAI 呼び出しのリトライ（429・接続エラー・タイムアウト・5xx）実装。レスポンスパース失敗は警告ログを出して継続。
    - テスト用に _call_openai_api をパッチ可能にしている（news_nlp とは別実装でモジュール間結合を避ける設計）。

- Research モジュールを追加（kabusys.research）
  - factor_research:
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR 等）、Value（PER、ROE）等ファクター計算を実装。
    - DuckDB の SQL を活用して効率的に計算し、結果を (date, code) キーの dict リストで返す。
    - データ不足時の None 処理、ログ出力を実装。
  - feature_exploration:
    - 将来リターン計算（任意ホライズン）、Spearman ベースの IC（Information Coefficient）計算、ランク変換、ファクター統計サマリーを実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。

- Data モジュールを追加（kabusys.data）
  - calendar_management:
    - JPX カレンダーの夜間バッチ更新ジョブ（calendar_update_job）実装。J-Quants から差分取得して market_calendar テーブルへ冪等更新。
    - 営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。DB が未取得の場合の曜日フォールバック実装。
    - 安全措置として最大探索日数や健全性チェック、バックフィル期間等を導入。
  - pipeline:
    - ETLResult データクラスを公開（kabusys.data.etl 経由で再エクスポート）。ETL の実行結果、品質問題、発生エラーの集約に対応。
    - 差分更新、バックフィル、品質チェックの方針を実装するための基盤コード（関数の下地）を用意。

### Changed
- （初回リリースのため該当なし）

### Fixed
- OpenAI / JSON 処理に関する堅牢性向上:
  - JSON mode でも前後に余計なテキストが混入するケースへ対応するため、最外の {} を抽出して復元するロジックを追加（news_nlp, regime_detector）。
  - レスポンスの型・キー検証（results / macro_sentiment 等）を厳格化し、パース失敗時は例外ではなくログ出力の上フォールバックするようにして、ETL/バッチの継続性を担保。

- DuckDB 互換性対応:
  - executemany に空リストを渡すと例外となる旧バージョンの問題に対処し、空の場合は呼び出しをスキップする保護を実装（news_nlp の DB 書込み処理等）。

- DB 書込みの冪等性と安全性:
  - ai_scores / market_regime などへの書込みを BEGIN / DELETE / INSERT / COMMIT の順で行い、例外発生時に ROLLBACK を試行して安全に復旧する実装を追加。ROLLBACK に失敗した場合は警告ログを出力。

### Security
- 環境変数保護:
  - .env 上書き時に OS 環境変数を上書きしないよう protected セットで保護（config）。
  - 必須キーが未設定の場合に ValueError を送出して明示的に失敗させることで、誤った機密情報の取り扱いを防止（Settings._require）。

### Known limitations / Notes
- スキーマ依存:
  - 多くの機能は DuckDB 上の特定スキーマ（prices_daily, raw_news, news_symbols, ai_scores, raw_financials, market_calendar, market_regime 等）を前提としているため、実行前に DB スキーマとデータの準備が必要です。

- 外部 API:
  - OpenAI（gpt-4o-mini）および J-Quants API への接続が必須。環境変数 OPENAI_API_KEY / JQUANTS_REFRESH_TOKEN 等の設定を忘れないでください。

- テスト支援:
  - OpenAI 呼び出しはモジュール内の _call_openai_api を unittest.mock.patch で差し替え可能にしてあるため、ネットワークに依存しない単体テストが容易です。

- 設計方針:
  - すべての AI / 分析処理はルックアヘッドバイアスを避けるため datetime.today()/date.today() を直接参照しない実装方針を採用しています（target_date を明示的に渡す設計）。

- エラーフォールバック:
  - マクロセンチメントやニューススコアの API 障害時は 0.0 にフォールバックし、全体処理を止めないフェイルセーフ設計です。

### Migration / Usage notes
- 環境変数の準備:
  - 必須: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - 任意/デフォルト: KABUSYS_ENV (development / paper_trading / live), LOG_LEVEL (INFO など), DUCKDB_PATH, SQLITE_PATH
  - 自動ロードが不要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

- テスト:
  - OpenAI 呼び出しを差し替えることで単体テストを容易に実行できます（例: unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api")）。

---

今後の予定（例）
- strategy / execution / monitoring モジュールの実装を拡充して実運用フローに統合予定。
- より細かい品質チェックルールの追加、ETL の監査ログ強化。
- モデル・プロンプトのチューニングとキャッシュ・コスト対策（LLM 呼び出し最適化）。

もし特定の機能・ファイルについて詳細なCHANGELOG追記や、別バージョンでの差分を推測して作成してほしい場合は、該当の差分や追加情報（変更ファイル一覧やコミットメッセージなど）を提供してください。