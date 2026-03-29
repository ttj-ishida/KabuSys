# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このファイルにはコードベースから推測される実装内容・設計方針を基に作成したリリースノートを日本語で記載しています。

なお、バージョンはパッケージ定義 (src/kabusys/__init__.py) に基づく 0.1.0 を初回リリースとして記載しています。

## [Unreleased]
- 今後の予定や改善点のメモ（例）
  - jquants_client 等外部クライアントの実装・統合の完成
  - strategy / execution / monitoring 等の公開 API と実装の追加
  - テスト補強（各 LLM 呼び出し・DB 書き込みのモック化、単体テスト）
  - 型注釈・ドキュメントの追記

## [0.1.0] - 2026-03-29

### Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージ公開メタ情報を src/kabusys/__init__.py に追加（__version__ = "0.1.0", __all__ の定義）。

- 環境設定・ローダー
  - src/kabusys/config.py を追加。
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動ロードする仕組みを実装。
    - .env のパース機能は export プレフィックス・クォート・エスケープ・インラインコメント等に対応。
    - OS 環境変数を保護する protected 機能、override フラグ、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
    - Settings クラスを提供し、必須環境変数取得（_require）・デフォルト値・バリデーションを実装。
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須チェック。
      - KABUSYS_ENV（development/paper_trading/live）とLOG_LEVEL（DEBUG/INFO/...）のバリデーション。
      - データベースパスのデフォルト（duckdb: data/kabusys.duckdb, sqlite: data/monitoring.db）を提供。

- AI（LLM）関連
  - src/kabusys/ai/news_nlp.py を追加。
    - raw_news と news_symbols を集約して銘柄ごとのニューステキストを生成し、OpenAI（gpt-4o-mini、JSON mode）へバッチ送信してセンチメント（ai_score）を算出。
    - バッチ処理（最大20銘柄／チャンク）、1銘柄あたり記事数・文字数のトリム、レスポンス検証、スコアの ±1.0 クリップ、DuckDB へ冪等書き込み（DELETE→INSERT）を実装。
    - リトライポリシー（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）とフェイルセーフ（失敗時は該当チャンクをスキップ）を実装。
    - テスト容易性のため _call_openai_api を内部関数として分離し patch 可能に設計。
    - calc_news_window 関数でニュース集計ウィンドウ（JST基準：前日15:00〜当日08:30）を計算。

  - src/kabusys/ai/regime_detector.py を追加。
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次市場レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news / market_regime を参照し、計算結果を冪等に market_regime テーブルへ保存（BEGIN/DELETE/INSERT/COMMIT）。
    - LLM 呼び出し（gpt-4o-mini）に対するリトライ・フォールバック（失敗時 macro_sentiment=0.0）を実装。
    - API キー注入（引数または環境変数 OPENAI_API_KEY）をサポートし、テストのための差し替え設計を行っている。

- データ（Data Platform）関連
  - src/kabusys/data/calendar_management.py を追加。
    - market_calendar テーブルを前提に JPX カレンダー（祝日・半日取引・SQ日）管理ロジックを提供。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days といった営業日判定ユーティリティを実装。DB にデータがない場合は曜日ベース（週末除外）でフォールバック。
    - calendar_update_job を実装し J-Quants API（jquants_client.fetch_market_calendar）から差分取得→保存（jq.save_market_calendar）する夜間バッチを提供。バックフィルや健全性チェックを実装。

  - src/kabusys/data/pipeline.py を追加。
    - ETLResult dataclass を定義し ETL 実行の集約結果を表現（取得数・保存数・品質問題・エラー等）。
    - ETL 用ユーティリティ（テーブル存在チェック・最終日取得・市場カレンダー調整ロジックなど）を実装。差分取得・バックフィル・品質チェックを行う設計方針を文書化。
    - src/kabusys/data/etl.py で ETLResult を再エクスポート。

  - その他データユーティリティ
    - データ処理は DuckDB を想定し、executemany の空リスト回避等 DuckDB の互換性問題に配慮した実装。

- リサーチ（Research）関連
  - src/kabusys/research/factor_research.py を追加。
    - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（20日ATR、相対ATR）、流動性（20日平均売買代金・出来高比）、バリュー（PER/ROE）等のファクター計算を実装。
    - prices_daily / raw_financials を参照し、各関数は (date, code) ベースの dict リストを返す。
    - 欠損データ・データ不足時の取り扱い（None 返却）に注意している。

  - src/kabusys/research/feature_exploration.py を追加。
    - forward returns の計算（任意ホライズン／デフォルト [1,5,21]）、IC（Spearman ρ）計算、rank（平均ランクの扱い、丸め処理）、factor_summary（count/mean/std/min/max/median）などの統計ユーティリティを実装。
    - Pandas 等外部依存を避け、標準ライブラリと DuckDB の SQL を組み合わせた実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 外部 API キーは引数注入または環境変数経由で扱い、環境変数未設定時は明示的にエラーを投げることで不正な無認証通信を防止。

### テスト・設計上の注意点 / 既知の制約
- LLM / 外部 API 呼び出し部はテスト容易性を考慮して内部呼び出しを分離（patch 可能）。ただし実ネットワーク依存のためモックが必須。
- DuckDB 固有の挙動（executemany に空リストを渡せないなど）を回避するためにガードがある。環境によっては DuckDB バージョン差分に注意。
- jquants_client（jq）や外部クライアントの実装は本コードスニペットでは省略されているため、本リリースではそれらの実体を提供する必要がある。
- strategy / execution / monitoring はパッケージの __all__ に含まれているが、この差分では具体実装が提示されていない（今後追加予定）。
- 日付の取扱いは全て date/naive datetime で統一（タイムゾーンの混入を避ける設計）。ニュースウィンドウ等は JST→UTC 変換ロジックを明示。

### Migration / Upgrade notes
- 環境変数を利用する機能が多数あるため、デプロイ前に必須環境変数（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）を適切に用意してください。
- .env 自動ロードはプロジェクトルートを .git または pyproject.toml で判定するため、配布後や CI 環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使って自動ロードを無効化できます。

---

（注）本 CHANGELOG は提供されたソースコード内容からの推測に基づいて作成しています。実際のリリース履歴や追加実装がある場合は適宜更新してください。