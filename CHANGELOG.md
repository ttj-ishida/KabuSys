# CHANGELOG

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

全般:
- 本リリースはパッケージ初期実装相当の機能群を含むメジャーな初期リリースです。
- パッケージのバージョンは src/kabusys/__init__.py にて `__version__ = "0.1.0"` として定義されています。

---

## [0.1.0] - 2026-03-28

### Added
- パッケージ基盤
  - kabusys パッケージの公開インターフェースを定義（data, strategy, execution, monitoring を __all__ に含む）。
  - バージョン情報を含む初期リリース (0.1.0)。

- 環境設定管理（kabusys.config）
  - .env / .env.local からの自動読み込み機構を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化のサポート。
  - .env パーサの実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、コメント処理の細かな扱い）。
  - Settings クラスを提供し、各種必須環境変数取得プロパティを実装:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - DUCKDB_PATH / SQLITE_PATH のデフォルトパス（expanduser 対応）
    - KABUSYS_ENV（development / paper_trading / live のバリデーション）
    - LOG_LEVEL（DEBUG/INFO/... のバリデーション）
    - is_live / is_paper / is_dev ヘルパー

- AI モジュール（kabusys.ai）
  - ニュースNLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを算出。
    - バッチ処理（最大20銘柄/チャンク）、1銘柄あたりの記事数・文字数上限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - JSON Mode での応答検証と復元処理（前後の余計なテキストが混入する場合に最外の {} を抽出）。
    - エラー時のリトライ（429 / ネットワーク / タイムアウト / 5xx）と指数バックオフの実装。
    - スコアの数値バリデーションと ±1.0 でのクリップ。
    - calc_news_window による JST ベースのニュース対象ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC 換算）。
    - テスト用に _call_openai_api を patch で差し替え可能に設計。
    - ai_scores テーブルへの冪等的書き込み（DELETE → INSERT、部分失敗時に既存スコアを保護）。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次レジーム（bull / neutral / bear）を判定。
    - マクロニュース抽出（キーワードリスト _MACRO_KEYWORDS）＋ OpenAI（gpt-4o-mini）でのセンチメント評価。
    - API 呼び出しのリトライ・フォールバック（失敗時 macro_sentiment = 0.0）。
    - レジームスコア合成ロジック（スケーリング・クリッピング）と market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - lookahead バイアスを避ける設計（target_date 未満のデータのみ参照、datetime.today() を参照しない）。

- データプラットフォーム関連（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダー管理用ユーティリティ（market_calendar テーブル参照）を実装。
    - 営業日判定: is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days。
    - DB にデータがない場合は曜日ベースのフォールバック（週末除外）。
    - calendar_update_job: J-Quants からの差分取得・バックフィル・健全性チェック（未来日付過大検出）・保存処理を実装。

  - ETL パイプライン（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult データクラスを定義し、ETL 実行結果の標準的な構造を提供（取得数・保存数・品質チェック結果・エラー一覧等）。
    - テーブル存在チェック・最大日付取得ユーティリティ、差分更新のための基礎的ロジックを実装。
    - jquants_client と quality モジュールを組み合わせた差分取得・保存・品質チェックの想定設計（具体的な API 呼び出しは jquants_client 側に委譲）。

- リサーチ（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M リターン）、200日移動平均乖離、ATR（20日）、平均売買代金、出来高変化率などのファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB を用いた SQL ベースの計算（営業日ベースの窓や LAG / AVG ウィンドウ関数を活用）。
    - calc_value は raw_financials から最新財務データを取得して PER / ROE を計算（EPS がゼロ・欠損時は None）。
    - 設計上、外部 API へはアクセスしない（読み取り専用）。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns、任意ホライズン対応、引数検証）。
    - IC（Information Coefficient）計算（calc_ic）: Spearman ランク相関の算出。
    - ランク変換ユーティリティ（rank、同順位は平均ランク）。
    - 統計サマリー（factor_summary: count/mean/std/min/max/median）。
    - pandas 等に依存しない純標準ライブラリ実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Security
- （初回リリースのため該当なし）

### Notes / Design Decisions
- ルックアヘッドバイアス対策: 多くの分析/スコア算出関数は datetime.today() を参照せず、呼び出し側から target_date を受け取る設計。
- フェイルセーフ: 外部 API（OpenAI 等）失敗時は例外で全停止させず、該当スコアをデフォルト (0.0) にして継続する実装方針を採用。
- 冪等性: DB 書き込みは基本的に冪等に行う（既存行削除→挿入、ON CONFLICT による更新など）。
- DuckDB 互換性: executemany における空リストの扱いなど、DuckDB の既知の挙動を考慮した実装。
- テスト容易性: OpenAI への実際の API 呼び出しを簡単に差し替え可能に（_call_openai_api を patch できるよう設計）。

### Known limitations / TODO
- 一部ドキュメントに記載されている機能（例: PBR、配当利回り）は現バージョンでは未実装。
- 一部ソース（長いファイル末尾など）に続きや追加機能が想定される箇所があるため、将来的な拡張・リファクタリング余地がある。
- jquants_client / quality モジュールの具体的実装に依存しているため、それらの実装次第で動作に差異が出ます。

---

今後のリリースでは以下を予定しています（例）:
- strategy / execution / monitoring モジュールの実装と統合テスト
- デプロイ・運用向けの監視/アラート機構（Slack 連携等）の強化
- モデル（LLM）呼び出し回数削減のためのキャッシュやスコア再利用ロジック
- テストカバレッジ拡充、CI ワークフローの追加

もし特定の変更点（機能追加・バグ修正）をより詳しく分けて記載してほしい場合は、対象ファイルやコミットの情報を提供してください。