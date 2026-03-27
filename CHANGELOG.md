# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

なお、本CHANGELOGは提供されたコードベースから機能・設計方針を推測して作成した初期リリース向けの記録です。

## [Unreleased]

- 現在未リリースの変更はありません。

## [0.1.0] - 2026-03-27

初回公開リリース。日本株自動売買・リサーチ基盤のコア機能を実装。

### Added

- パッケージ基礎
  - kabusys パッケージ初期化（__version__ = 0.1.0）と公開サブパッケージ指定（data, strategy, execution, monitoring）。

- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
  - .env パーサー実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応）。
  - 環境変数必須チェック (_require) と Settings クラスを提供。
  - デフォルト値・検証:
    - KABUSYS_ENV: development / paper_trading / live の検証
    - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL の検証
    - データベースパスのデフォルト（DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"）
  - 必須環境変数（例）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（未設定時は ValueError）

- データプラットフォーム (kabusys.data)
  - calendar_management:
    - JPX カレンダー管理ロジック（market_calendar テーブル参照、曜日フォールバック、SQ判定、next/prev/get trading day）。
    - calendar_update_job による J-Quants からの差分取得・バックフィル・健全性チェックと冪等保存。
    - DB が部分的にしかない場合でも一貫したフォールバックロジックを採用。
  - pipeline / etl:
    - ETLResult データクラスによる ETL 実行結果の集約（品質チェック結果・エラー一覧含む）。
    - 差分取得、バックフィル、品質チェックを考慮したパイプライン設計を反映（jquants_client 連携、保存は冪等）。
    - _get_max_date / _table_exists のユーティリティ関数提供。
  - etl の公開インターフェース再エクスポート（ETLResult）。

- ニュース NLP / AI (kabusys.ai)
  - news_nlp:
    - raw_news / news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）に JSON モードでバッチ送信してセンチメント（-1.0〜1.0）を取得。
    - 時間ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST を対象に UTC に変換して比較する calc_news_window 実装。
    - 1チャンクあたり最大銘柄数（_BATCH_SIZE=20）、1銘柄あたり記事数・文字数制限（_MAX_ARTICLES_PER_STOCK、_MAX_CHARS_PER_STOCK）。
    - レスポンス検証と堅牢なパース処理（余分な前後テキストから JSON を復元する処理含む）。
    - エラーハンドリング: 429・ネットワーク・タイムアウト・5xx は指数バックオフでリトライ、その他はスキップしてフェイルセーフに動作。
    - API 呼び出し箇所はテスト用にモック可能（内部関数 _call_openai_api を patch できる設計）。
    - 最終的に ai_scores テーブルへ置換的に書き込み（DELETE → INSERT、部分失敗時に既存データを保護）。
  - regime_detector:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - マクロニュースは news_nlp の calc_news_window を利用して抽出。
    - OpenAI 呼び出しのリトライ・フォールバック（API 全失敗時は macro_sentiment = 0.0）。
    - ルックアヘッドバイアス対策: datetime.today()/date.today() を参照せず、target_date 未満のデータのみを参照。
    - テスト容易性のため _call_openai_api を差し替え可能。

- リサーチ / ファクター機能 (kabusys.research)
  - factor_research:
    - モメンタム（1M/3M/6M リターン、ma200_dev）、ボラティリティ/流動性（20日 ATR, ATR/price, 20日平均売買代金, 出来高比率）、バリュー（PER, ROE）を DuckDB の prices_daily / raw_financials から計算する関数群（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の None 扱い、結果は (date, code) をキーとする dict のリストを返す。
    - DuckDB 内でウィンドウ関数を多用し効率的に算出。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）: 指定ホライズン（デフォルト [1,5,21]）の forward return を LEAD で計算。
    - IC (calc_ic: Spearman の ρ) 計算、rank ユーティリティ、ファクター統計サマリー (factor_summary) を実装。
    - 外部ライブラリに依存せず標準ライブラリと DuckDB のみで実装。
  - research パッケージは主要な計算 API を再エクスポートして外部利用を想定。

### Design / Implementation Notes

- DuckDB を主要な分析 DB として使用する設計（関数群の引数は DuckDB 接続）。
- LLM 呼び出しは JSON mode（厳密な JSON 出力想定）で安全なパースを前提にしているが、パース失敗時の復元処理を備える。
- API キーは関数引数で注入可能（api_key 引数が優先）で、環境変数 OPENAI_API_KEY もサポート。未設定時は ValueError を発生させる。
- DB への書き込みは概ね冪等性を保つ（DELETE→INSERT や ON CONFLICT を想定した保存）。
- ルックアヘッドバイアス防止を強く意識した設計（関数群はいずれも target_date を明示的に扱い、today に依存しない）。
- テストを容易にするため、内部の API 呼び出し点はモック差し替え可能に実装。

### Fixed

- 初回リリースのため該当なし。

### Security

- 初期実装: 機密情報（OpenAI API キー等）は環境変数で扱う想定。機密保護のため .env 自動読み込みでは既存 OS 環境変数を保護する仕組みを実装。

### Breaking Changes

- 初回リリースのため該当なし。

---

注:
- 上記はコードベースの実装と docstring から推測して作成した CHANGELOG です。実際のリリース日付・バージョン管理ポリシーに合わせて調整してください。