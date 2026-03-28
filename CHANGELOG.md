# Changelog

すべての重要な変更点をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

## [0.1.0] - 2026-03-28

### Added
- 基本パッケージ初期リリース (kabusys 0.1.0)
  - パッケージメタ情報:
    - src/kabusys/__init__.py にてバージョンを "0.1.0" として公開。
    - パッケージ公開 API として data, strategy, execution, monitoring を __all__ で定義。

- 環境変数・設定管理
  - src/kabusys/config.py
    - .env / .env.local ファイルの自動ロード機能（プロジェクトルートを .git または pyproject.toml で検出）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能（テスト用）。
    - .env パーサを実装（コメント、export プレフィックス、シングル／ダブルクォート、エスケープに対応）。
    - 環境変数の保護（既存 OS 環境変数を protected として上書き制御）。
    - Settings クラスを公開（J-Quants・kabu API・Slack・DB パス・環境モード・ログレベル等の取得とバリデーション）。
    - デフォルト値: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH 等。

- ニュース NLP（OpenAI ベース）
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を用いて銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode でセンチメントスコアを取得して ai_scores テーブルへ保存。
    - JST ベースのニュース収集ウィンドウ計算関数 calc_news_window を提供（前日 15:00 JST 〜 当日 08:30 JST を対象）。
    - バッチ処理（_BATCH_SIZE=20）・1銘柄あたり最大記事数／文字数制限（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）。
    - リトライ（429/ネットワーク断/タイムアウト/5xx）と指数バックオフを実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results フォーマット検証、コードの正規化、スコアの数値化および ±1.0 クリップ）。
    - 部分失敗を考慮した冪等的 DB 書き込み（対象コードのみ DELETE → INSERT、DuckDB executemany の空リスト回避）。

  - テストしやすさ:
    - _call_openai_api をモジュール内で分離しており、unittest.mock.patch による差し替えが可能。
    - api_key を引数注入可能（環境変数 OPENAI_API_KEY でも代替）。

- 市場レジーム判定
  - src/kabusys/ai/regime_detector.py
    - ETF (1321) の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロ記事抽出は news_nlp.calc_news_window を利用、OpenAI 呼び出しは独立実装（モジュール結合を避ける）。
    - マクロスコア取得時のリトライ・バックオフと、API 失敗時のフォールバック macro_sentiment=0.0。
    - 計算結果を market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT、エラー時の ROLLBACK 処理とログ）。

- 研究（Research）モジュール
  - src/kabusys/research/factor_research.py
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Value（PER, ROE）、Volatility（20 日 ATR）等のファクター計算を実装。
    - DuckDB 上の SQL ウィンドウ関数を活用し、(date, code) ベースの辞書リストを返す API。
    - データ不足時の None 扱い、ログ出力による追跡。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（複数ホライズンに対応、horizons の検証あり）。
    - IC（Spearman の ρ）計算、ランク付けユーティリティ（同順位は平均ランク）。
    - factor_summary：基本統計量（count/mean/std/min/max/median）算出。
  - src/kabusys/research/__init__.py で主要関数を再エクスポート。

- データプラットフォーム（Data）モジュール
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理（market_calendar テーブル）と営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 登録値優先、未登録日は曜日ベースでフォールバック。探索範囲上限で無限ループ回避。
    - 夜間バッチ更新 calendar_update_job を実装（J-Quants API 経由で差分取得・バックフィル・健全性チェック）。
  - src/kabusys/data/pipeline.py
    - ETL パイプラインの基礎（差分取得、保存、品質チェックのフレームワーク）。
    - ETLResult データクラスを実装（取得/保存数、品質問題、エラー集約、辞書化メソッド）。
    - 内部ユーティリティ: テーブル存在判定、最大日付取得、トレーディング日調整など。
  - src/kabusys/data/etl.py
    - pipeline.ETLResult の再エクスポート。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- 環境変数の未設定時に明確なエラーメッセージを出す（必須キー取得時に ValueError を送出）。
- .env ファイル読み込みでファイル IO エラーを warnings.warn で通知して安全に継続。

### Notes / 設計上の重要ポイント
- ルックアヘッドバイアス対策: すべてのスコア／ファクター生成ロジックやニュースウィンドウは内部で datetime.today()/date.today() を直接参照せず、target_date を明示的に受け取る設計。
- OpenAI 呼び出し周りは堅牢化（JSON 解析耐性、部分的失敗のフォールバック、再試行ロジック、テスト差し替え可能）。
- DuckDB への書き込みは冪等性を重視（DELETE→INSERT、トランザクション、ROLLBACK の取り扱い、executemany の空リスト回避）。
- テスト容易性: API キー注入、モック差し替えポイント、KABUSYS_DISABLE_AUTO_ENV_LOAD による外部依存の切り離し。

--- 

今後のリリースでは、strategy / execution / monitoring の具体実装、さらに詳細な品質チェック・監視機能、追加のファクター・バックテストユーティリティなどを予定しています。