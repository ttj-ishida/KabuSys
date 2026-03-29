# Changelog

すべての注目すべき変更を管理するために Keep a Changelog の形式に準拠しています。  
このファイルはコードベース（kabusys パッケージ）から推測できる機能追加・修正・設計上の決定をまとめたものです。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更（互換性に影響する可能性のある変更）
- Fixed: バグ修正
- Internal: 実装上の注意点・内部改善（利用者向けの API 変更を伴わないもの）

## [0.1.0] - 2026-03-29
初期リリース: 基本的なデータパイプライン、研究ユーティリティ、AI ニュース解析および市場レジーム判定機能を実装。

### Added
- パッケージ構成
  - kabusys パッケージ基盤を追加。公開 API として data, strategy, execution, monitoring を __all__ に定義（将来の拡張ポイント）。
  - バージョン番号: 0.1.0

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート探索: .git または pyproject.toml を起点にプロジェクトルートを検出して .env / .env.local を読み込む。
  - .env パーサーは `export KEY=val` 形式、クォート内エスケープ、コメント処理（クォート外の # はインラインコメントとして扱う条件付き）等に対応。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供し、各種必須設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）をプロパティ経由で取得。未設定時は例外を送出。
  - 環境値検証: KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL（DEBUG/INFO/...）の検証ロジックを実装。
  - デフォルトの DB パス（DUCKDB_PATH / SQLITE_PATH）や kabu API の base URL を提供。

- データ処理（kabusys.data）
  - calendar_management モジュールを追加し、JPX カレンダーの取扱い（market_calendar テーブル参照）と営業日判定ユーティリティを実装:
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB が存在しない／未登録日のフォールバックは曜日ベース（土日を非営業日）で一貫して動作
    - 夜間バッチ calendar_update_job: J-Quants から差分取得・バックフィル・保存（fetch/save 呼び出しを jquants_client に委譲）
    - 健全性チェック（未来日付の異常検知）とバックフィルの実装

  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを公開（取得/保存件数、品質問題、エラー情報を格納）
    - 差分取得・バックフィル・品質チェック（quality モジュール経由）設計に準拠した ETL の骨組みを実装
    - DuckDB に対するテーブル存在チェックや最大日付取得ユーティリティを提供

  - etl.py: pipeline.ETLResult を再エクスポート

- 研究用ユーティリティ（kabusys.research）
  - factor_research モジュール: ファクター計算ルーチンを実装（duckdb SQL ベース）
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）
    - calc_volatility: 20日 ATR / 相対 ATR、20日平均売買代金、出来高比率等
    - calc_value: PER, ROE（raw_financials から最新レコードを取得）
    - 計算は prices_daily / raw_financials のみ参照。欠損時は None を返す
  - feature_exploration モジュール:
    - calc_forward_returns: 指定ホライズン先の将来リターン計算（複数ホライズン同時取得）
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）計算
    - rank: 平均順位（同順位は平均ランク）を返すユーティリティ
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を算出
  - 依存を標準ライブラリと DuckDB のみとする設計

- AI / NLP（kabusys.ai）
  - news_nlp モジュール:
    - score_news: raw_news と news_symbols を元に銘柄ごとのセンチメント（ai_score）を OpenAI（gpt-4o-mini）に送って算出し、ai_scores テーブルへ書き込み
    - タイムウィンドウ（JST 基準: 前日 15:00 ～ 当日 08:30）計算（calc_news_window）
    - バッチ処理（最大 20 銘柄/コール）、1銘柄あたり記事トリム（10 件・3000 文字）
    - レスポンスバリデーション（JSON 抽出、results 配列、code と score の検証）、スコアを ±1.0 にクリップ
    - API エラー（429/ネットワーク/タイムアウト/5xx）に対する指数バックオフとリトライ、失敗時は該当チャンクをスキップ（フェイルセーフ）
    - DuckDB 0.10 の executemany 周りを考慮し、DELETE / INSERT を個別実行で互換性確保
    - テスト容易性のため _call_openai_api を patch 可能に実装

  - regime_detector モジュール:
    - score_regime: ETF 1321 の 200 日移動平均乖離（70%）とマクロニュース LLM センチメント（30%）を合成して市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み
    - マクロキーワードで raw_news のタイトルを抽出し、OpenAI（gpt-4o-mini）で JSON 出力の macro_sentiment を取得
    - MA 計算は target_date 未満のデータのみ使用しルックアヘッドを防止
    - API 呼び出しのリトライ・例外ハンドリング、失敗時の macro_sentiment=0.0 フォールバック
    - DB 書き込みは BEGIN/DELETE/INSERT/COMMIT の原子操作、失敗時は ROLLBACK を試行

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Internal / Implementation notes
- 全体設計方針として、ルックアヘッドバイアス防止のため datetime.today() や date.today() をスコープ内で直接参照しない実装を採用。すべての関数は明示的な target_date を引数に取り、テストやバックテストでの再現性を確保。
- OpenAI 呼び出しやファイル読み込みでの失敗は多くの箇所で厳密に捕捉され、フェイルセーフ（0.0 やスキップ）で継続できる設計。ログ出力で詳細を記録。
- DuckDB を主要なローカル分析 DB として使用。SQL でのウィンドウ関数活用により多くの集計処理を DB 側で実行。
- jquants_client（kabusys.data.jquants_client 想定）への依存は抽象化されており、fetch/save 関数で外部 API 連携を行う設計。
- テスト容易性: OpenAI 呼び出し箇所（_call_openai_api）や API キー注入でモックが可能。

### 既知の制約 / 注意点
- OpenAI との連携は gpt-4o-mini/JSON mode を前提としている。API レスポンス形式が変わるとパース処理が失敗する可能性があるため、運用時は SDK / API バージョンの互換性に注意すること。
- DuckDB のバージョン依存（executemany の空配列挙動など）を考慮した実装をしているが、異なるバージョンでの挙動確認が必要。
- news_nlp / regime_detector は API キーの設定（OPENAI_API_KEY）を前提としている。テスト時は api_key を明示的に渡すか内部の _call_openai_api をモックすること。

---

将来のリリースでは次のような項目を追加予定:
- strategy / execution / monitoring の実装（自動売買ロジックと実際の発注フロー）
- より詳細な品質チェックとアラート（Slack 通知等）
- テストカバレッジと CI ワークフローの強化

もし特定モジュールについてさらに詳しい変更点やリリースノートを希望される場合は、対象モジュール名を指定して伝えてください。