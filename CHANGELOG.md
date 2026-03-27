# CHANGELOG

すべての注目すべき変更を記録します。フォーマットは Keep a Changelog に準拠します。

全般方針:
- Breaking change があれば明示します（現時点ではなし）。
- 日付はリリース日を示します。

## [0.1.0] - 2026-03-27

初回リリース（ベース機能実装）。日本株自動売買プラットフォームのコア機能群を提供します。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージを追加。公開 API: data, strategy, execution, monitoring を __all__ で定義。
  - パッケージバージョンを `__version__ = "0.1.0"` に設定。

- 設定管理
  - 環境変数 / .env 読み込みユーティリティを実装（kabusys.config）。
  - プロジェクトルート自動検出機能を実装（.git または pyproject.toml を基準）。カレントワーキングディレクトリに依存しない動作。
  - .env/.env.local を読み込み（優先順: OS環境 > .env.local > .env）、`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動読み込みを無効化可能。
  - .env パーサはコメント行、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント等に対応。
  - Settings クラスを提供し、アプリケーション向けプロパティを型付けして公開：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - is_live / is_paper / is_dev のユーティリティプロパティ

- データプラットフォーム（kabusys.data）
  - マーケットカレンダー管理（calendar_management）
    - market_calendar テーブルを用いた営業日判定 API（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を追加。
    - カレンダー未取得時のフォールバック（曜日ベース：土日は非営業日）を実装。
    - 最大探索範囲（_MAX_SEARCH_DAYS）で無限ループを防止。
    - calendar_update_job により J-Quants からの差分取得と冪等保存を実装（バックフィル・健全性チェックを含む）。
  - ETL パイプライン（pipeline）
    - ETLResult データクラスを追加（取得件数、保存件数、品質問題、エラーの収集）。
    - 差分更新、バックフィル、品質チェックの設計を反映。
  - etl モジュールで ETLResult を公開再エクスポート。

- AI（自然言語処理 / レジーム検知） (kabusys.ai)
  - ニュース NLP（news_nlp）
    - raw_news / news_symbols を集約し、銘柄ごとに記事をまとめて OpenAI（gpt-4o-mini）へ送信しセンチメントを算出。
    - バッチ処理（1 API コールにつき最大 20 銘柄）、各銘柄の最大記事数・最大文字数でトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - JSON mode を用いたレスポンス期待値と、レスポンスのバリデーション（results 配列、code と score の検証、数値チェック、既知コードのみ採用）。
    - リトライ戦略（429・ネットワーク断・タイムアウト・5xx は指数バックオフでリトライ）、失敗時はフェイルセーフでスキップ。
    - ai_scores テーブルへトランザクション（DELETE → INSERT）で置換保存。部分失敗時に他コードの既存スコアを保護する実装。
    - テスト容易性のため _call_openai_api を patch 可能に設計。
  - 市場レジーム判定（regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定。
    - マクロセンチメントは news_nlp の calc_news_window を利用して抽出したマクロキーワード記事を gpt-4o-mini へ渡し評価（JSON 出力想定）。
    - レジームスコア合成と閾値判定、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - API 呼び出し失敗時は macro_sentiment=0.0 とするフェイルセーフ。
    - テスト容易性のため _call_openai_api を独立実装（モジュール間のプライベート関数共有を回避）。

- リサーチ（kabusys.research）
  - factor_research
    - モメンタム（1M/3M/6M リターン）、200日 MA 乖離、ATR（20日）、平均売買代金・出来高比率等を計算する関数を追加（calc_momentum, calc_volatility, calc_value）。
    - DuckDB を用いた SQL ベースの計算で、prices_daily / raw_financials テーブルのみ参照。
    - データ不足時には None を返す等の安全処理を実装。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns）: 複数ホライズンを統合クエリで取得。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンのランク相関を実装（ランクは同順位平均ランク）。
    - ランク変換ユーティリティ（rank）。
    - ファクター統計サマリー（factor_summary）。
    - 外部依存を避け、標準ライブラリと DuckDB のみで実装。

- その他ユーティリティ
  - DuckDB 接続を前提とした多くの関数は、データ欠損時のロギングとフォールバックを備える。
  - ロギングを多用して処理の追跡性を確保。

### 修正 (Fixed)
- トランザクション失敗時の後始末として ROLLBACK を試み、ROLLBACK の失敗も警告ログに記録する実装を多数の保存処理に適用（score_regime, score_news, pipeline 等）。
- OpenAI API 呼び出しでのエラー判定とリトライロジックを明確化（APIError の status_code 有無に配慮）。

### 既知の制約 / 注意点 (Known issues / Notes)
- OpenAI API キーが未設定の場合、score_news / score_regime は ValueError を送出する。利用時は api_key 引数または環境変数 OPENAI_API_KEY を設定する必要あり。
- DuckDB executemany は空リストバインドに注意（実装側で空チェックを行っている）。
- datetime.today() / date.today() を参照しない設計方針により、対象日付は明示的に引数で与えることを期待する（ルックアヘッドバイアス回避）。
- 外部 API（J-Quants, OpenAI）への依存があるため、API 側の仕様変更やレート制限により動作影響が生じる可能性あり。
- 現バージョンでは PBR・配当利回り等は未実装（calc_value に注記あり）。

---

今後の予定（例）:
- strategy / execution / monitoring モジュールの実装拡充（実際の発注ロジック・モニタリング／アラート）。
- テストカバレッジ拡充と CI 統合。
- より高度な品質チェック（quality モジュール拡張）やメタデータ管理の追加。