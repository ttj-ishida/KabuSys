# Changelog

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の方針に従って記載しています。  

※推測に基づく記載です。コードベースの実装内容・設計意図から主要な機能と挙動をまとめています。

## [Unreleased]
- 現時点で未リリースの変更はありません。

## [0.1.0] - 2026-03-28
初回公開リリース

### 追加 (Added)
- パッケージ全体
  - パッケージ初期バージョンを 0.1.0 として公開（src/kabusys/__init__.py）。
  - モジュールレイアウトを提供: data, research, ai, execution, strategy, monitoring（__all__ による公開インターフェース）。

- 環境設定 (kabusys.config)
  - .env ファイルと環境変数の読み込み機能を実装。プロジェクトルートを .git または pyproject.toml から自動検出して .env / .env.local を読み込む。
  - 自動ロードを環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env の行パーサを実装（コメント、export プレフィクス、クォートとバックスラッシュエスケープ対応、インラインコメントの扱い等）。
  - Settings クラスを提供し、必要な設定値（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等）をプロパティ経由で取得。検証ロジック（env 値・ログレベルの妥当性チェック、デフォルト値、パスの Path 変換など）を実装。
  - DUCKDB/SQLite パスのデフォルト、環境ごとのフラグ（is_live, is_paper, is_dev）をサポート。

- AI（ニュース NLP / レジーム判定） (kabusys.ai)
  - news_nlp モジュール:
    - raw_news と news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）を用いて各銘柄のセンチメント（-1.0～1.0）を算出して ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）算出ユーティリティを提供（calc_news_window）。
    - API バッチ処理（最大20銘柄/チャンク）、記事数・文字数トリム（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）、JSON Mode のレスポンス検証、スコアのクリップ（±1.0）を実装。
    - リトライ戦略：429・ネットワーク断・タイムアウト・5xx に対する指数バックオフと上限。API失敗時はフェイルセーフで該当チャンクをスキップ。
    - レスポンスの堅牢なパース/バリデーション実装（JSON 前後の余計なテキスト抽出、未知コードの無視、数値変換チェック等）。
    - DuckDB への冪等書き込み（DELETE → INSERT）、部分失敗時に既存スコアを保護する実装。
  - regime_detector モジュール:
    - ETF 1321 の 200 日移動平均乖離（重み70%）と、news_nlp によるマクロセンチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ書き込む。
    - prices_daily からの MA200 比率算出、raw_news からのマクロキーワードフィルタ取得、OpenAI コール（gpt-4o-mini）による macro_sentiment 推定、合成スコアの閾値判定を実装。
    - API 呼び出しに対するリトライ、API失敗時のフォールバック（macro_sentiment=0.0）、DB 書き込みはトランザクション（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）で冪等性を担保。
    - ルックアヘッドバイアス防止の設計（datetime.today()/date.today() を直接参照しない、prices_daily クエリに date < target_date を適用）。

- データ (kabusys.data)
  - calendar_management:
    - JPX カレンダー管理（market_calendar）の取得・更新ジョブ（calendar_update_job）を実装。J-Quants クライアント経由で差分取得し、冪等的に保存（ON CONFLICT 相当）を想定。
    - 営業日判定ユーティリティを提供（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。market_calendar が未取得の際は曜日ベースでフォールバックするロジックを実装。
    - カレンダー更新はバックフィル、先読み、健全性チェック（将来日付の異常検知）をサポート。
  - pipeline ETL:
    - ETLResult データクラスの公開（ETL 実行結果の集計、品質チェック結果・エラーの格納、to_dict メソッド）。
    - 差分取得、backfill、品質チェック統合の方針を定義（J-Quants クライアント、quality モジュール連携）。

- リサーチ（kabusys.research）
  - factor_research:
    - モメンタム、ボラティリティ（ATR, 平均売買代金, 出来高変化率）、バリュー（PER, ROE）等のファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。DuckDB SQL を主体に実装し、prices_daily / raw_financials を参照。
    - 計算は営業日ベースの窓や行数判定によりデータ不足時は None を返す設計。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns、可変ホライズン対応、SQL による一括取得）。
    - IC（Information Coefficient）計算（sp earman ランク相関）とランク関数、統計サマリー（factor_summary）を実装。外部ライブラリに依存せず標準ライブラリのみで実装。
  - research パッケージ __all__ に主要な関数を再エクスポート。

### 変更 (Changed)
- 初回リリースのため、変更履歴はありません（新規実装中心）。

### 修正 (Fixed)
- 初回リリースのため、修正履歴はありません。

### 既知の設計/挙動（ドキュメント的注意）
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY で解決される。未設定時は ValueError を送出する設計。
- LLM 呼び出し部分はテスト容易性のため内部関数をモック可能にしてある（_unittest.mock.patch が想定されている）。
- 全体的に「ルックアヘッドバイアス防止」「DB 書き込みの冪等性」「API 呼び出しのフェイルセーフ/リトライ」が設計方針として繰り返し適用されている。
- DuckDB 0.10 系の特性（executemany に空リストを渡せない等）を考慮した実装が含まれる。
- .env パーサは複雑なクォート/エスケープ処理に対応しているが、稀なフォーマットでは差異が出る可能性あり。

### 互換性注意 (Breaks)
- 初回リリースのため、破壊的変更は無し。

---

もし CHANGELOG の粒度や日付、または特定モジュールの変更点をより詳細に記載したい場合は、対象モジュール（例: news_nlp のレスポンスバリデーションや ETL のフローなど）を指定してください。