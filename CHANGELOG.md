# Changelog

すべての注記は Keep a Changelog 準拠で記載しています。  
このファイルは、コードベースから推測される機能追加・修正・設計方針等を基に作成した推定の変更履歴です。

フォーマット:
- Added: 新規追加機能
- Changed: 既存機能の変更（互換性あり）
- Fixed: バグ修正（互換性あり）
- Deprecated / Removed / Security: 該当なしの場合は記載しません

---

## [Unreleased]

（なし）

---

## [0.1.0] - 2026-03-29

### Added
- パッケージ初期リリース。
  - パッケージ名: kabusys、バージョン: 0.1.0（src/kabusys/__init__.py）
  - エクスポート: data, strategy, execution, monitoring をトップレベルで公開。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数からの設定読み込みを実装。
  - プロジェクトルートを .git または pyproject.toml を起点に探索して自動で .env / .env.local を読み込む自動ローダーを実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロードの無効化をサポート。
  - .env パーサーは export 構文、シングル/ダブルクォートとバックスラッシュエスケープ、行末コメントの扱い等に対応。
  - Settings クラスを提供し、J-Quants / kabuAPI / Slack / DBパス（DuckDB/SQLite） / 実行環境（development/paper_trading/live） / ログレベルの取得とバリデーションを実装。
  - 必須環境変数未設定時に ValueError を投げる _require() を提供。
  - デフォルトで DUCKDB_PATH / SQLITE_PATH の既定値を設定。

- AI モジュール（src/kabusys/ai）
  - news_nlp.score_news
    - raw_news と news_symbols から銘柄ごとに記事を集約して OpenAI（gpt-4o-mini）の JSON Mode で一括センチメント評価。
    - チャンク処理（1チャンク最大20銘柄）、各銘柄の入力長トリム、最大記事数制限をサポート。
    - 再試行（429/ネットワーク/タイムアウト/5xx）を指数バックオフで実装。
    - レスポンスバリデーション（JSON パース、results フォーマット、スコア数値化、既知コード照合）と ±1.0 クリップ。
    - 成果は ai_scores テーブルへ冪等的に置換（DELETE → INSERT）。部分失敗時に他銘柄の既存スコアを保護する設計。
    - calc_news_window ユーティリティ（前日 15:00 JST ～ 当日 08:30 JST のウィンドウ計算）を提供。
  - regime_detector.score_regime
    - ETF 1321（日経225連動型）200日移動平均乖離（重み70%）とマクロセンチメント（重み30%）を合成して日次市場レジーム（bull/neutral/bear）を判定。
    - マクロ記事は raw_news からキーワードフィルタリングして取得し、OpenAI による JSON 出力をパースしてスコア化。
    - API 呼出しのリトライ/フォールバック、結果のクリップ、レジームテーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - API キー注入（引数または環境変数 OPENAI_API_KEY）をサポート。

- Research モジュール（src/kabusys/research）
  - factor_research: calc_momentum, calc_volatility, calc_value を実装。
    - モメンタム（1M/3M/6M リターン、200日MA乖離）、ボラティリティ（20日ATR、相対ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER, ROE）等を DuckDB の prices_daily / raw_financials から計算。
    - データ不足時の None 処理やウィンドウバッファ等の扱いを明示。
  - feature_exploration: calc_forward_returns, calc_ic, rank, factor_summary を実装。
    - 将来リターン（任意ホライズン）、IC（Spearman のρ）計算、ランク付け（同順位は平均ランク）、基本統計量サマリーを提供。
    - pandas 等外部ライブラリに依存しない純標準実装。

- Data モジュール（src/kabusys/data）
  - calendar_management: JPX カレンダー管理（market_calendar）と営業日ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。
    - DB 登録値優先、未登録日は曜日ベースのフォールバック、最大探索日数制限などの健全性対策を実装。
    - calendar_update_job による J-Quants からの差分取得、バックフィル、健全性チェック、保存呼び出し（jquants_client 経由）を提供。
  - pipeline / etl: ETLResult データクラスの導入、ETL パイプライン設計方針の実装（差分更新・保存・品質チェックを想定）。
  - jquants_client 経由の差分取得・保存の呼び出しポイントを想定（実際の jquants_client は別モジュール）。

- テスト容易化と安全性のための設計
  - AI API 呼び出しは内部の _call_openai_api を使用し、テスト時にパッチしやすく設計。
  - ルックアヘッドバイアスを回避するため date.today() / datetime.today() を直接参照しない（関数引数で target_date を受ける設計）。
  - DuckDB の executemany の制約（空リスト不可）に配慮した実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- フェイルセーフな挙動を各所に実装（OpenAI API 失敗時のフォールバックや部分失敗時の DB 保護など）。
- .env 読み込みに失敗した際に警告を出力して処理を継続するハンドリングを追加。

### Notes / Usage
- 必須環境変数（例）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - OpenAI API を利用する機能は OPENAI_API_KEY が必要（score_news / score_regime は引数での注入も可能）。
- デフォルト DB パス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml）を基準とする。自動ロードを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定する。

---

今後のリリースで期待される項目（推測）
- strategy / execution / monitoring 周りの具体的な売買ロジックや注文実行モジュールの実装・公開。
- jquants_client の具体実装と ETL パイプラインの統合テスト。
- 単体テスト・統合テストの追加と CI 設定。
- ドキュメント（Usage / API / Data schema）の充実。

---

作成者注:
この CHANGELOG は提示されたソースコードから機能・設計・動作を推測して作成したものであり、実際のコミット履歴や開発履歴に基づくものではありません。必要であれば実際の git 履歴やリリースノートに基づく精査版を作成します。