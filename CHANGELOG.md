# Changelog

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の形式に従っています。  

## [0.1.0] - 2026-03-28

### Added
- 初回リリース。KabuSys：日本株自動売買システムの基盤機能を追加。
- パッケージエントリポイント
  - src/kabusys/__init__.py にてバージョン (0.1.0) と公開サブパッケージ（data, strategy, execution, monitoring）を定義。
- 環境変数・設定管理（src/kabusys/config.py）
  - .env / .env.local の自動読み込み（プロジェクトルートの自動検出：.git または pyproject.toml を基準）。
  - .env パーサーは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント等に対応。
  - 自動読み込み無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスでアプリ設定をプロパティとして提供（必須変数チェックを含む）。
    - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - デフォルト値: KABU_API_BASE_URL（http://localhost:18080/kabusapi）、DUCKDB_PATH（data/kabusys.duckdb）、SQLITE_PATH（data/monitoring.db）
    - env / log_level の値検証（許容値のみ許可）と is_live / is_paper / is_dev のユーティリティプロパティ。
- AI モジュール（src/kabusys/ai）
  - news_nlp モジュール（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約して銘柄ごとに OpenAI（gpt-4o-mini、JSON mode）へバッチ送信してセンチメント（ai_score）を算出。
    - 時間ウィンドウ定義（前日 15:00 JST ～ 当日 08:30 JST = UTC で前日 06:00 ～ 23:30）を calc_news_window で提供。
    - チャンクバッチ処理（デフォルト _BATCH_SIZE=20）、1 銘柄当たりの記事数・文字数上限、レスポンス検証、スコアの ±1.0 クリップ。
    - レート制限／ネットワーク／サーバーエラーに対する指数バックオフリトライの実装。
    - DuckDB への書き込みは部分失敗を考慮した DELETE → INSERT の冪等的更新（トランザクション制御）。
    - テスト用に _call_openai_api の差し替え（patch）を想定。
  - regime_detector モジュール（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動ETF）の 200 日移動平均乖離（重み 70%）と news_nlp ベースのマクロセンチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定。
    - マクロニュース抽出用のキーワードリスト、LLM（gpt-4o-mini）を用いた JSON 出力期待、API失敗時は macro_sentiment=0.0 のフォールバック。
    - レジームスコア合成ロジック、閾値によるラベル付与、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - テスト用に _call_openai_api の差し替えを想定。
- データプラットフォーム関連（src/kabusys/data）
  - calendar_management モジュール（src/kabusys/data/calendar_management.py）
    - JPX カレンダー管理のユーティリティ（営業日判定、前後営業日の取得、期間内営業日一覧、SQ判定）。
    - market_calendar が存在しない場合の曜日ベースのフォールバック、DB 登録ありの場合は DB 値優先。
    - 夜間バッチジョブ calendar_update_job を実装（J-Quants API からの差分取得、バックフィル、健全性チェック）。
  - ETL / パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを公開（取得件数、保存件数、品質チェック結果、エラー一覧を含む）。
    - 差分取得・バックフィル・保存（jquants_client 経由で冪等保存）・品質チェックの設計を実装に反映。
    - etl.py で ETLResult を再エクスポート。
  - その他ユーティリティ：DuckDB テーブル存在チェック、最大日付取得など。
- リサーチ（src/kabusys/research）
  - factor_research（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER, ROE）といったファクター計算を提供。
    - DuckDB を用いた SQL ベースの実装。データ不足時の None 処理。
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - 将来リターン（calc_forward_returns）、IC（calc_ic）、ランキング（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等の外部依存を使わず標準ライブラリと DuckDB で実装。
  - research パッケージでの公開 API を定義（zscore_normalize の再利用など）。
- テスト性・堅牢性のための設計上の配慮
  - ルックアヘッドバイアス回避（datetime.today()/date.today() を直接参照しない設計）。
  - API 呼び出し失敗時のフェイルセーフ（ゼロスコアやスキップで継続）とログ出力。
  - DuckDB 書き込み時のトランザクション保護（ROLLBACK 処理と警告ログ）。
  - OpenAI 呼び出し関数の差し替えを想定した抽象化（テスト容易性）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは呼び出し時に引数注入または環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出して明示的にエラーを出す設計。

### Notes / Migration
- 今バージョンでは strategy、execution、monitoring パッケージの公開は __all__ に含まれるが、今回提供されたコードにはそれらの実装が含まれていません。将来的にこれらを実装/追加予定です。
- DuckDB の executemany に関する注意（空リストの扱い）を考慮した実装を行っています。DuckDB バージョン差に起因する問題を避けるため、空パラメータリストの送出を回避しています。
- テストを書く際は ai モジュール内の _call_openai_api を patch して外部 API への実際の呼び出しを防いでください。

### BREAKING CHANGES
- なし（初回リリース）

---

今後のリリースでは、strategy/execution/monitoring の本実装、J-Quants クライアント実装の公開、より詳細な品質チェック・監視機能の追加などを予定しています。