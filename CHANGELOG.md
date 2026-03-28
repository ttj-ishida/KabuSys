# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
バージョン管理ポリシー: SemVer 準拠。

## [Unreleased]

## [0.1.0] - 2026-03-28

### Added
- 初回リリース。パッケージ名: `kabusys`（バージョン 0.1.0）。
- パッケージ初期化: src/kabusys/__init__.py にて主要サブパッケージを公開（data, strategy, execution, monitoring）。
- 環境設定管理モジュール（src/kabusys/config.py）
  - .env/.env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml で検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
  - export キーワードやクォート、インラインコメントに対応した堅牢な .env パーサ実装。
  - 既存 OS 環境変数を保護する protected オプション、override フラグのサポート。
  - 必須環境変数取得用 _require と Settings クラス（J-Quants / kabu / Slack / DB パス / 環境判定 / ログレベル等）。
  - DUCKDB_PATH / SQLITE_PATH のデフォルトパス設定と expanduser 対応。
  - KABUSYS_ENV / LOG_LEVEL のバリデーション（許容値チェック）。
- AI モジュール（src/kabusys/ai）
  - ニュースセンチメントスコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約して銘柄ごとにテキストを作成、OpenAI（gpt-4o-mini）へバッチ送信してスコアを ai_scores テーブルへ書き込み。
    - バッチ処理サイズ、文字数・記事数トリム、JSON モードレスポンスのバリデーション実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx を対象とした指数バックオフリトライ。
    - レスポンスパースや未知コード・非数値スコア対応の安全化。
    - テスト容易性のため _call_openai_api をモック差し替え可能に設計。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news からのデータ取得、OpenAI（gpt-4o-mini）呼び出し、冪等な market_regime テーブルへの書き込みを実装。
    - API の多層的リトライとフェイルセーフ（API失敗時は macro_sentiment=0.0）実装。
    - テスト用に _call_openai_api を差し替え可能。
- Research / ファクター系（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - モメンタム（1M/3M/6M）、200日MA乖離、ATR（20日）、20日平均売買代金、出来高比率等を DuckDB の SQL と Python で計算。
    - データ不足時の None 扱い、結果は (date, code) を含む dict リストで返却。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（任意 horizon 対応）、Spearman ランク相関（IC）計算、ランク関数、ファクター統計サマリーを実装。
    - pandas 等外部依存を避け、標準ライブラリのみで実装。
  - 研究ユーティリティの再エクスポート（zscore_normalize 等）。
- Data プラットフォーム（src/kabusys/data）
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ロジック。
    - JPX カレンダーの夜間差分取得ジョブ（calendar_update_job）と J-Quants クライアント連携。
    - market_calendar が未取得の際は曜日ベースのフォールバック（土日非営業）を採用。
    - 最大探索範囲・バックフィル・健全性チェックの実装。
  - ETL パイプライン基盤（src/kabusys/data/pipeline.py / etl.py）
    - 差分更新・保存・品質チェックフローの実装方針に基づく ETLResult データクラスを提供。
    - DB 最大日付取得ユーティリティ等、ETL 実行時に利用するユーティリティを提供。
  - data パッケージの公開インターフェース整備（pipeline.ETLResult の再エクスポート）。

### Changed
- 初版のため該当なし。

### Fixed
- 各モジュールで発生しうる API・DB エラーに対してフェイルセーフ／ログ出力を充実させ、処理が致命的に停止しないよう改善。
  - OpenAI 呼び出しの多段リトライと 5xx 判定の取り扱い（APIError の status_code 互換性を考慮）。
  - DuckDB executemany に空リストを渡さないガードを追加（互換性確保）。
  - JSON モードでも余剰テキストが混入するケースへの復元処理を追加。

### Deprecated
- 初版のため該当なし。

### Removed
- 初版のため該当なし。

### Security
- 初版のため公開鍵・シークレットの取り扱いは環境変数ベース。Settings で必須キーが未設定の場合は明確なエラーを出す設計。環境変数の上書き制御（protected set）を導入。

---

注記:
- 全モジュールは「ルックアヘッドバイアス回避」を設計原則としており、datetime.today()/date.today() の直接参照を避け、呼び出し側から target_date を受け取る設計になっています。
- OpenAI 連携は gpt-4o-mini を想定し、JSON Mode を用いた厳密なパースを前提に実装されています。API キーは引数注入か環境変数 OPENAI_API_KEY を使用します。
- DuckDB を主な分析用 DB として利用する想定（デフォルトの duckdb ファイルパスは data/kabusys.duckdb）。