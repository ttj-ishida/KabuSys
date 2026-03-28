# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
このプロジェクトの初期リリース（0.1.0）に含まれる主要な機能・設計決定をコードベースから推測して記載しています。

## [0.1.0] - 2026-03-28

### Added
- パッケージ基盤
  - パッケージメタ情報を追加（src/kabusys/__init__.py: __version__ = "0.1.0"）。
  - 公開 API 想定モジュール（data, strategy, execution, monitoring）を __all__ に定義。

- 環境設定 / 設定管理（src/kabusys/config.py）
  - .env ファイルと環境変数から設定を読み込む Settings クラスを実装。
  - 自動読み込みロジック: プロジェクトルート（.git または pyproject.toml）を基準に .env, .env.local を優先順で読み込み。テスト用に KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - .env パーサ実装: export 形式のサポート、シングル/ダブルクォートのエスケープ処理、インラインコメント取り扱い、無効行スキップ等の堅牢なパース処理。
  - 必須環境変数チェック（_require）と各種プロパティ:
    - JQUANTS_REFRESH_TOKEN（J-Quants）
    - KABU_API_PASSWORD / KABU_API_BASE_URL（kabuステーション）
    - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（Slack通知）
    - DUCKDB_PATH / SQLITE_PATH（データベースパス）
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL（ログレベル検証）
  - OS側の既存環境変数を保護する protected 上書き制御。

- AI (自然言語処理) 機能（src/kabusys/ai/**）
  - ニュースセンチメント解析（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON モードでバッチ評価して ai_scores テーブルへ書き込み。
    - タイムウィンドウ定義（JST 前日 15:00 ～ 当日 08:30 相当の UTC 範囲）を calc_news_window で提供。
    - チャンク（最大 20 銘柄）単位での API 呼び出し、1銘柄あたりの記事数・文字数（トリム）制御。
    - リトライ（429 / ネットワーク断 / タイムアウト / 5xx）と指数バックオフ実装。
    - レスポンスの厳密バリデーション（JSON 抽出、results 配列、code/score の検証、スコアのクリッピング）。
    - DuckDB への冪等的な書き込み（DELETE→INSERT、トランザクション、ROLLBACK 対応）。部分失敗時に既存スコアを保護する実装。
    - テスト容易性のため _call_openai_api をモック差し替え可能に設計。
    - 公開関数: score_news(conn, target_date, api_key=None)
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（Nikkei 225 連動ETF）の 200 日移動平均乖離（重み 70%）とニュース由来の LLM マクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を算出し market_regime テーブルに冪等書き込み。
    - マクロニュース抽出用キーワードリストと最大記事数制限を実装。
    - OpenAI（gpt-4o-mini）呼び出し、レスポンス JSON パース、リトライ（エクスポネンシャルバックオフ）とフェイルセーフ（API 失敗時は macro_sentiment=0.0）。
    - ルックアヘッドバイアス回避の設計（date < target_date の排他条件、datetime.today() を使わない）。
    - 公開関数: score_regime(conn, target_date, api_key=None)

- データ処理 / ETL（src/kabusys/data/**）
  - ETL パイプライン（src/kabusys/data/pipeline.py）
    - ETLResult データクラス（取得数・保存数・品質問題・エラーを集約）を実装し、結果の to_dict メソッドを提供。
    - 差分更新、バックフィル（デフォルト 3 日）、品質チェックの概念や J-Quants クライアント統合を想定した設計。
    - DuckDB を前提とした最大日付取得ユーティリティ等を提供。
  - ETL 公開インターフェースのエイリアス（src/kabusys/data/etl.py）で ETLResult を再エクスポート。
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルに基づく営業日判定ユーティリティ（is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days）を実装。
    - データ未取得時の曜日ベースフォールバック（週末を非営業日扱い）。
    - calendar_update_job により J-Quants API からカレンダーデータの差分取得・保存（バックフィル・健全性チェックを含む）を実装。
    - DB の存在チェックや日付変換ユーティリティを実装。
  - その他のデータユーティリティ（jquants_client 経由の fetch/save を想定する呼び出し箇所とエラーハンドリングを実装）。

- リサーチ / 特徴量探索（src/kabusys/research/**）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、MA200 乖離）、Volatility（20 日 ATR、相対 ATR、平均売買代金、出来高比率）、Value（PER、ROE）など複数のファクター計算関数を実装。
    - DuckDB 上の SQL を用いて、ルックバック・ウィンドウ設計（営業日バッファ等）を考慮。
    - 結果は (date, code) をキーとする辞書リストとして返す。
  - 特徴量探索ツール（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）: 任意ホライズンの LEAD によるリターン計算、入力検証（horizons 範囲）。
    - IC（Information Coefficient）計算（calc_ic）: スピアマン（ランク相関）を独自実装。
    - ランク変換ユーティリティ（rank）: 同順位処理は平均ランク、丸め対策あり。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を算出。
  - research パッケージの __all__ で主要関数を公開。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Deprecated
- （初期リリースのため該当なし）

### Removed
- （初期リリースのため該当なし）

### Security
- OpenAI API キーの扱いに関する注意
  - API キーは関数引数で注入可能（テスト容易性）であり、環境変数 OPENAI_API_KEY からも取得する。ログや例外にキーを出力しない実装方針が読み取れる。

### Notes / 設計上の重要ポイント（実装からの推測）
- ルックアヘッドバイアス防止:
  - AI スコアリングやレジーム判定で datetime.today() / date.today() を直接参照せず、target_date を明示的に受け取る設計。
  - prices_daily 等のクエリは target_date 未満を明確に使いルックアヘッドを回避。
- フェイルセーフ指向:
  - 外部 API（OpenAI / J-Quants）失敗時は例外で停止させず、代替値（例: macro_sentiment=0.0）で継続する箇所がある。
  - DuckDB への書き込みはトランザクション＋ROLLBACK 保護を行い、部分失敗時に他のデータを守る設計。
- テスト容易性:
  - _call_openai_api 等の内部呼び出しをモック差し替え可能にしてユニットテストを容易にする工夫がある。
- DuckDB を中心とした設計:
  - 大部分の処理は DuckDB 接続を受け取り SQL で完結する（外部ネットワーク依存を最小化）。
- ロギング:
  - 各処理に INFO / WARNING / DEBUG ログが適切に配置され、運用時のトラブルシュートを考慮。

---

今後のリリース案（例）
- 0.2.0: 発注実行（execution）やストラテジー（strategy）実装、Slack 通知連携の実装・改善。
- 0.1.x: バグ修正、OpenAI レスポンスパースの堅牢化、J-Quants クライアント周りのエラーハンドリング強化。

（この CHANGELOG はコード内容から推測して作成しています。実際の変更履歴やリリースノート作成時はコミットログやリリース差分を基に更新してください。）