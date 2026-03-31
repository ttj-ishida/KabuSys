# CHANGELOG

すべての注目すべき変更を記録します。SemVer に従ってバージョンを付け、Keep a Changelog の形式を踏襲しています。

フォーマットの指針:
- 重要な追加、変更、修正を記載します。
- リリース日にはコードベースから推測される最新の日付（このファイル作成日）を使用しています。
- この CHANGELOG はコード内容から推測して作成しています。実際のコミット履歴と差がある可能性があります。

## [Unreleased]

（今後の変更をここに記載）

---

## [0.1.0] - 2026-03-31

初回リリース（コードベースから推測）。日本株自動売買・データ基盤・リサーチ用ユーティリティを含む基盤機能を実装。

### Added
- パッケージ公開
  - パッケージ名: kabusys
  - __all__ により公開 API の概念を定義（data, strategy, execution, monitoring を想定）。

- 環境設定 / 設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込みする機能を実装。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）。
    - 読み込み順序: OS 環境 > .env.local（上書き）> .env（未設定のみ）。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env のパースは高度に堅牢:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメントの取り扱い。
  - Settings クラスを提供し、よく使う設定値をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live の検証）と LOG_LEVEL（DEBUG/INFO/... の検証）
    - is_live / is_paper / is_dev のヘルパー

- AI 関連モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news / news_symbols を用い、銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini）でセンチメントを算出。
    - バッチ処理（最大 20 銘柄/コール）、1銘柄あたり記事数・文字数上限（既定値: 10 記事, 3000 文字）。
    - JSON Mode を利用した応答検証、冗長な前後テキストの復元ロジックを含む堅牢なレスポンスパース。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ実装。
    - スコアは ±1.0 にクリップ。取得後は ai_scores テーブルへ冪等的に DELETE → INSERT 書き込み（部分失敗時に他銘柄の既存スコアを保護）。
    - ルックアヘッドバイアス回避のため、target_date を明示的に与える設計（datetime.today() を直接参照しない）。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロニュースは news_nlp.calc_news_window を用いてウィンドウを算出し、raw_news からマクロキーワードでフィルタ。
    - OpenAI 呼び出しに対するリトライ、API 失敗時のフォールバック（macro_sentiment=0.0）を実装。
    - 判定結果は market_regime テーブルへトランザクション（BEGIN/DELETE/INSERT/COMMIT）で冪等的に書き込み。
    - LLM 呼び出しはモジュール内プライベート関数で独立実装（モジュール間の結合を避ける設計）。

- データ基盤 / ETL (kabusys.data)
  - ETL 結果型の公開 (kabusys.data.pipeline.ETLResult を kabusys.data.etl から再エクスポート)。
  - ETL パイプライン基礎 (kabusys.data.pipeline)
    - 差分更新、バックフィル、品質チェック（quality モジュールとの連携）などの設計を定義。
    - ETLResult dataclass を導入し、取得件数・保存件数・品質問題・エラー情報を集約。has_errors / has_quality_errors / to_dict を提供。
    - DuckDB のテーブル存在チェック・最大日付取得などのユーティリティを実装。
  - マーケットカレンダー管理 (kabusys.data.calendar_management)
    - market_calendar テーブルを用いた営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB データがまばらな場合は曜日ベース（週末）でフォールバックする一貫した動作。
    - calendar_update_job により J-Quants API からの差分取得→冪等保存（save_market_calendar呼び出し）を実装。バックフィル、健全性チェックを実装。
    - 最大探索範囲 (_MAX_SEARCH_DAYS) により無限ループを防止。

- リサーチ / ファクター計算 (kabusys.research)
  - calc_momentum / calc_volatility / calc_value（kabusys.research.factor_research）
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離など。
    - Volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率など。
    - Value: PER（EPS が 0 または欠損時は None）、ROE（raw_financials から取得）。
    - DuckDB を用いた SQL ベース実装。ルックアヘッドバイアスに配慮した日付フィルタ。
  - 特徴量探索ユーティリティ (kabusys.research.feature_exploration)
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターン算出（LEAD を使用）。
    - calc_ic: スピアマンのランク相関による IC（情報係数）計算。データ不足時の None 戻し。
    - rank / factor_summary: ランク化（同順位は平均ランク）、基本統計量（count/mean/std/min/max/median）算出。
    - 外部ライブラリに依存せず標準ライブラリと DuckDB のみで実装。

### Changed
- （初回リリースのため該当なし。将来的な変更は Unreleased に記載予定）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーの取り扱いは api_key 引数または環境変数 OPENAI_API_KEY を想定。未設定時は ValueError を投げることで誤設定を検出。
- 自動 .env ロード時に OS 環境変数を保護する仕組み（protected set）を導入。

---

備考 / 実装上の注目点（ドキュメント的メモ）
- DuckDB を主要な分析データベースとして想定（prices_daily, raw_news, raw_financials, ai_scores, market_regime, market_calendar 等のテーブルを参照）。
- AI (OpenAI) 呼び出しは gpt-4o-mini を使用する想定。JSON mode を使った厳密なレスポンスパースと、レスポンス検証ロジックを多数実装。
- ルックアヘッドバイアス回避のため、全てのバッチ処理関数は target_date を引数に持ち、内部で date.today() 等を直接参照しない設計。
- .env パーサは実用的なケース（クォート、エスケープ、export プレフィックス、コメント）に対応しており CI / ローカル双方で安定した挙動を目指している。
- jquants_client 相当のモジュール (kabusys.data.jquants_client) を参照しているが実装はこのスナップショットに含まれていないため、実際の ETL 実行には該当クライアントの実装が必要。

もし実際のコミット履歴やリリース日が既に存在する場合は、その情報を提供していただければ CHANGELOG を正確な履歴に合わせて更新します。