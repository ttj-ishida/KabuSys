# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。  
このファイルはコードベースの内容から推測して作成した初期の変更履歴です。

全般的な注意
- 本リリースはパッケージの初期公開（v0.1.0）を想定した記述です。
- 日付は本回答日時（2026-03-31）を記載しています。
- 設計上の振る舞いやフォールバック、エラーハンドリング、外部依存（OpenAI / J-Quants / DuckDB 等）に関する挙動はコード内の実装から記載しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-31
### Added
- パッケージ初期公開
  - パッケージ名: kabusys
  - バージョン: 0.1.0（src/kabusys/__init__.py）

- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数から自動読み込みを行う機能を追加
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - プロジェクトルートの検出は .git または pyproject.toml を基準に行う（cwd に依存しない）
    - 自動ロードを抑止するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート
  - .env パーサーの実装（export 形式やクォート、エスケープ、インラインコメント対応）
  - 環境変数取得ユーティリティ（Settings クラス）を提供
    - 必須項目の検証（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）
    - デフォルト値と検証（KABUSYS_ENV の有効値: development / paper_trading / live、LOG_LEVEL の有効値: DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - データベースパスのデフォルト（DUCKDB_PATH, SQLITE_PATH）
    - is_live / is_paper / is_dev のブールプロパティ

- AI 関連（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を元に銘柄ごとのニュースを集約し OpenAI（gpt-4o-mini）でセンチメント評価
    - 処理ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB クエリ）
    - バッチ処理: 1 回の API 呼び出しで最大 20 銘柄を処理（_BATCH_SIZE）
    - 1 銘柄あたりの最大記事数および文字数制限（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）
    - レスポンスは JSON Mode を期待し、堅牢なパースとバリデーションを実施（結果キー・型・スコア検証）
    - 失敗時のフェイルセーフ: API エラーやパースエラー時は該当チャンクをスキップし継続
    - リトライ戦略: 429 / ネットワーク断 / タイムアウト / 5xx を指数バックオフでリトライ
    - 結果を書き込む際は対象コードのみを DELETE → INSERT で置換し部分失敗時に既存データを保護
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を統合して daily レジームを判定
    - マクロニュースは predefined マクロキーワードでフィルタして LLM に投げる
    - LLM 呼び出しは専用の呼び出し実装を持ち、内部でリトライ・フォールバック（失敗時 macro_sentiment=0.0）を行う
    - レジームスコアの閾値により "bull" / "neutral" / "bear" を決定し、market_regime テーブルへ冪等書き込みを行う（BEGIN/DELETE/INSERT/COMMIT）

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを参照した営業日判定および前後営業日の取得ユーティリティを提供
    - DB にカレンダーがない場合は曜日（平日）ベースでフォールバック
    - next_trading_day / prev_trading_day / get_trading_days / is_trading_day / is_sq_day 等の API を実装
    - 夜間バッチ calendar_update_job を実装（J-Quants API から差分取得して保存、バックフィル・健全性チェックあり）
    - 探索上限日数やバックフィル日数等の安全パラメータを設定（例: _MAX_SEARCH_DAYS, _BACKFILL_DAYS, _SANITY_MAX_FUTURE_DAYS）
  - ETL パイプライン（kabusys.data.pipeline / kabusys.data.etl）
    - ETLResult dataclass を公開（パイプラインの実行結果を集約して返却）
    - 差分フェッチ、idempotent 保存（jquants_client を利用）、品質チェック（quality モジュールを想定）を設計方針として定義
    - テーブルの最大日付取得やテーブル存在確認などのユーティリティを実装

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum: 1M/3M/6M リターン、200 日移動平均乖離の計算
    - Volatility / Liquidity: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率
    - Value: PER（株価 / EPS）および ROE（raw_financials から最新報告値を参照）
    - すべて DuckDB の prices_daily / raw_financials を参照して SQL ベースで計算
    - データ不足時は None を返すなど堅牢に扱う
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns: デフォルト horizons = [1,5,21]）
    - IC（Information Coefficient）計算（スピアマンランク相関）
    - ランク変換（ties は平均ランクで処理）
    - ファクター統計サマリー（count/mean/std/min/max/median）を提供
    - 外部ライブラリに依存せず標準ライブラリ + DuckDB で実装

- API・設計上の留意点（全体）
  - ルックアヘッドバイアス防止のため、各モジュールで datetime.today()/date.today() を直接参照しない実装方針を採用（target_date を引数で受ける）
  - OpenAI の呼び出しは gpt-4o-mini を指定し、JSON モードで厳密な JSON を期待するプロンプトを使用
  - DuckDB を利用したクエリ実装が中心
  - 各種書き込み処理は冪等性を考慮（DELETE → INSERT、ON CONFLICT に相当する扱い）
  - テスト容易性を考慮し、OpenAI 呼び出し関数はモジュール単位で差し替え可能（unit test 用に patch しやすい実装）

### Changed
- なし（初期リリース）

### Fixed
- なし（初期リリース）

### Deprecated
- なし

### Removed
- なし

### Security
- なし（初期リリース）
  - ただし環境変数に API キーを期待している箇所があるため、運用時は環境変数管理に注意が必要（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN 等）

Notes（実装上の補足・運用メモ）
- OpenAI API に依存する機能（news_nlp / regime_detector）は APIキーの未設定時に ValueError を送出する設計。CI/テスト実行時はモック化が必要。
- news_nlp と regime_detector はそれぞれ独立した _call_openai_api 実装を持つことでモジュール結合を避けている（テスト時の差し替えが容易）。
- DuckDB の executemany に空リストを渡すと問題となるバージョンを考慮して、空チェックを行ってから executemany を呼んでいる。
- calendar_update_job / ETL 処理は外部 API（J-Quants）からの取得に依存するため、API エラー時は例外を捕捉して安全に 0 を返す等のフェイルセーフを備えている。

もし CHANGELOG の粒度（個別ファイルごとの細かい変更点や将来のリリースノートテンプレート等）をさらに詳しく分けたい場合は、コードの差分やコミット履歴をもとに改めてより詳細な項目を作成できます。どのレベルの詳細を希望するか教えてください。