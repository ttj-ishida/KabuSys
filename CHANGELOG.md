# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このファイルはコードベース（バージョン __version__ = 0.1.0）から推測できる機能追加・設計方針・既知の挙動をまとめたものです。

注: 日付はリリース推定日です（コードファイルの内容からの推測）。

## [Unreleased]
- （特になし）このファイルは初期リリースに合わせて作成されています。今後の変更はここに記載してください。

## [0.1.0] - 2026-03-31
初回リリース（推定）。日本株自動売買・データ基盤・研究用ユーティリティ群の基盤実装を追加。

### Added
- パッケージ公開インターフェース
  - パッケージルート: kabusys
  - __all__ で "data", "strategy", "execution", "monitoring" を公開（将来的なサブパッケージを想定）

- 環境設定管理モジュール (kabusys.config)
  - .env ファイル（.env / .env.local）と OS 環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を探索して検出）
  - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - .env パースの実装:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - インラインコメント（クォート外かつ前にスペースがある '#'）対応
  - 上書き制御:
    - .env は OS 環境変数を保護する（既存のキーは上書きしない）
    - .env.local は override=True による上書きが可能（ただし OS 環境変数で保護）
  - Settings クラスを提供（settings インスタンスで使用）
    - 必須環境変数検証: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - オプション／デフォルト値: KABU_API_BASE_URL, DUCKDB_PATH（data/kabusys.duckdb）, SQLITE_PATH（data/monitoring.db）
    - KABUSYS_ENV の検証（development / paper_trading / live）
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - プロパティ: is_live / is_paper / is_dev

- AI 関連モジュール (kabusys.ai)
  - news_nlp.py
    - raw_news / news_symbols を元に銘柄ごとにニューステキストを集約し、OpenAI（gpt-4o-mini, JSON mode）で銘柄別センチメントを評価して ai_scores テーブルへ書き込み
    - バッチ処理（_BATCH_SIZE=20）、1銘柄あたりの記事数制限・文字数トリムの実装
    - 再試行ロジック（429、タイムアウト、ネットワーク断、5xx に対し指数バックオフ）
    - レスポンス検証（JSON 抽出、results 配列、code の正規化、数値検証、スコア ±1 にクリップ）
    - テスト用フック: _call_openai_api をモック可能
    - 公開 API: score_news(conn, target_date, api_key=None) -> 書き込み銘柄数
    - calc_news_window(target_date): ニュース収集ウィンドウ（JST ベースの UTC naive datetime）を提供

  - regime_detector.py
    - ETF 1321（日経225連動型）200日移動平均乖離（70%）とマクロニュース LLM センチメント（30%）を合成して市場レジーム（bull/neutral/bear）を日次判定
    - ma200_ratio 計算（ルックアヘッド防止のため target_date 未満のデータのみ使用）
    - マクロキーワードで raw_news をフィルタして記事タイトルを抽出、そのタイトル群を LLM（gpt-4o-mini）に投げて macro_sentiment を取得
    - OpenAI 呼び出しのリトライ・フォールバック（API 失敗時は macro_sentiment = 0.0）
    - 結果は market_regime テーブルへ冪等的（BEGIN / DELETE / INSERT / COMMIT）に書き込み
    - 公開 API: score_regime(conn, target_date, api_key=None) -> 1（成功）

- データプラットフォーム関連 (kabusys.data)
  - calendar_management.py
    - JPX カレンダー管理（market_calendar テーブル）と営業日判定ユーティリティ群を実装
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供
    - DB 登録あり → DB 値優先、未登録日 → 曜日ベースのフォールバック（週末を休場扱い）
    - 夜間バッチ job: calendar_update_job(conn, lookahead_days=90) で J-Quants から差分取得し保存（バックフィル・健全性チェックあり）
    - 最大探索日数やバックフィル日数の設定による安全設計（最大探索 _MAX_SEARCH_DAYS 等）

  - pipeline.py / etl.py
    - ETLResult データクラスを定義（取得数・保存数・quality_issues・errors 等を含む）
    - ETL の補助ユーティリティ（テーブル存在チェック・最大日付取得・トレーディングデイ調整等）
    - 差分更新・バックフィル・品質チェックの方針に基づいた設計（jquants_client / quality と連携する想定）
    - etl.py では ETLResult を再エクスポート

- 研究（Research）モジュール (kabusys.research)
  - factor_research.py
    - モメンタム（1M/3M/6M）・200日 MA 乖離・ATR（20日）・流動性（20日平均売買代金・出来高比）・Value（PER/ROE）等のファクター計算関数を実装
    - DuckDB の SQL を活用した実装で prices_daily / raw_financials のみ参照
    - 出力は日付・コード単位の dict リスト（例: {"date": ..., "code": "XXXX", "mom_1m": ...}）
    - 公開関数: calc_momentum, calc_volatility, calc_value

  - feature_exploration.py
    - 将来リターン計算（calc_forward_returns）: 複数ホライズン（デフォルト [1,5,21]）に対応
    - IC（Information Coefficient）計算（calc_ic）: スピアマンランク相関の実装（ties 平均ランク対応）
    - ランク変換ユーティリティ rank(values)
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を算出
    - 設計方針: pandas 等に依存せず標準ライブラリのみで実装

- テスト・開発向け配慮
  - OpenAI 呼び出し部分にモック差し替えを想定した箇所を用意（_call_openai_api を patch 可能）
  - DuckDB 0.10 の制約（executemany に空リスト不可）への対処がある箇所を注記・対応

### Changed
- （初期リリースのため変更履歴なし）

### Fixed
- （初期リリースのため修正履歴なし）

### Security
- （初期リリースのため特記事項なし）

---

## 既知の挙動・設計上の注意（重要）
- ルックアヘッドバイアス回避
  - ほとんどの処理（score_news, score_regime, factor計算等）は datetime.today()/date.today() を内部で参照せず、関数引数の target_date に依存する設計。
  - DB クエリでは target_date 未満 / 対象日のみ等の排他条件を意識しているため、本番使用時も target_date の指定に注意すること。

- フォールバックとフェイルセーフ
  - OpenAI API 呼び出しの失敗（タイムアウト・5xx・レート制限等）はリトライ／フォールバック（ゼロスコアやスキップ）で安全に継続する実装。
  - カレンダーデータがない場合は曜日ベースで営業日判定するフォールバックを行う。

- DB 書き込みの冪等性
  - market_regime / ai_scores 等への書き込みは冪等（DELETE → INSERT、トランザクション）で実装。エラー時は ROLLBACK を試みるが、ROLLBACK 自体が失敗する場合は警告ログを出力して上位へ例外を伝播。

- 環境変数必須項目
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings で必須とされる（未設定時は ValueError を送出）。
  - OpenAI API キーは score_news / score_regime の api_key 引数または OPENAI_API_KEY 環境変数で供給すること。未設定だと ValueError を送出。

- 依存・実行に必要なもの（推定）
  - duckdb、openai パッケージが必要
  - jquants_client、quality モジュールへの依存（data.jquants_client や data.quality を利用するコードが想定されるが、ここでは参照のみ）

## 開発者向けメモ
- テスト容易性:
  - OpenAI 呼び出しは内部関数をモックすることで外部 API を叩かずにテスト可能（例: unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api")）。
- DuckDB バインドの互換性:
  - executemany に空パラメータを渡さないようにする対策がいくつかの箇所にある（DuckDB 0.10 の挙動回避）。
- プロジェクトルート検出:
  - config の自動 .env 読み込みは __file__ を基点に親ディレクトリを探索するため、CWD に依存しない（パッケージ配布後でも動作を想定）。

---

この CHANGELOG は現状のコードベースから推測して作成しています。実際の変更履歴・リリースノートはプロジェクト管理の履歴（Git タグやコミットメッセージ）に基づいて更新してください。必要であれば、各関数やモジュールの公開 API を抜粋した「API 互換性」や「移行ガイド」を追加で作成します。