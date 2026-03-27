# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
安定したリリース（セマンティックバージョニング）に合わせてエントリを追加してください。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-27

### Added
- 新しいパッケージ `kabusys` の初期実装を追加。
  - パッケージバージョン: 0.1.0
  - エクスポート: data, strategy, execution, monitoring をトップレベルで公開（__all__）。
- 環境変数 / 設定管理 (`kabusys.config`)
  - プロジェクトルート検出（.git または pyproject.toml）に基づく .env 自動読み込み機能を実装。
  - .env パーサーは:
    - コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントを正しく処理。
    - .env と .env.local の読み込み順序をサポート（OS 環境変数を保護する protected 機構を採用）。
    - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を導入（テスト用）。
  - `Settings` クラスを提供。主要設定プロパティ:
    - J-Quants / kabuステーション / Slack / データベースパス / 環境（development/paper_trading/live）/ログレベル 等
    - 必須キーは未設定時に ValueError を送出する `_require` 実装。
    - `is_live` / `is_paper` / `is_dev` のブールプロパティを提供。
- AI モジュール (`kabusys.ai`)
  - ニュース NLP (`news_nlp.score_news`)
    - 指定日（target_date）に対するニュース集計ウィンドウ計算（JST 基準）を実装（calc_news_window）。
    - raw_news と news_symbols を結合して銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントスコアを算出。
    - バッチサイズ、トリミング（記事数・文字数制限）、JSON mode のレスポンス検証、スコアの ±1.0 クリップを実装。
    - レスポンスの検証失敗や API エラーは個別にスキップし、全体処理は継続するフェイルセーフ設計。
    - 取得スコアのみを対象に DuckDB の ai_scores テーブルへ冪等的に置換（DELETE → INSERT）。
  - 市場レジーム判定 (`regime_detector.score_regime`)
    - ETF 1321 の 200 日移動平均乖離とマクロニュースの LLM センチメントを重み付き合成して日次レジーム（bull/neutral/bear）を判定。
    - MA 計算はルックアヘッド防止のため target_date 未満のデータのみ使用。
    - OpenAI 呼び出しは再試行（指数バックオフ）とフェイルセーフ（API失敗時 macro_sentiment=0.0）を実装。
    - 結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。
  - テスト容易性のため、内部の OpenAI 呼び出し関数はモジュール内で独立実装しており patch による差し替えを想定。
- データ処理 / ETL (`kabusys.data.pipeline`, `kabusys.data.etl` 再エクスポート)
  - ETLResult dataclass を導入し、ETL 実行のフェイル／品質検査結果を構造化して返却可能に。
  - 差分更新・バックフィル・品質チェックを想定したパイプライン基盤の下地を実装。
  - DuckDB を用いた最大日付取得やテーブル存在チェック等のユーティリティを実装。
- マーケットカレンダー管理 (`kabusys.data.calendar_management`)
  - market_calendar テーブルの利用による営業日判定 API を提供:
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を実装。
  - J-Quants API との差分取得を行う夜間バッチ `calendar_update_job` を追加。バックフィル／健全性チェック（将来日付の異常検出）を含む。
  - DB 未取得時の曜日ベースフォールバック（週末を非営業日）をサポートし、DB とフォールバックの一貫性を確保。
- 研究用モジュール (`kabusys.research`)
  - ファクター計算 (`research.factor_research`)
    - モメンタム (1M/3M/6M)、200日 MA乖離、ATR ベースのボラティリティ、流動性指標、PER/ROE の取得ロジックを実装。
    - DuckDB SQL を用いたウインドウ集計により、date/code ベースの結果リストを返却。
  - 特徴量探索 (`research.feature_exploration`)
    - 将来リターン calc_forward_returns（任意ホライズン対応）、IC（Spearman）calc_ic、ランク化ユーティリティ rank、統計サマリー factor_summary を実装。
    - pandas など外部依存を使わず標準ライブラリのみで実装。
- DuckDB を主要なローカルストレージとして全モジュールで採用（prices_daily / raw_news / raw_financials / ai_scores / market_regime 等の想定テーブルに対応）。
- 設計方針として、ルックアヘッドバイアス防止（datetime.today() を直接参照しない）、冪等性、フェイルセーフ、ログ出力を徹底。

### Changed
- 初期リリースのため特になし。

### Fixed
- 初期リリースにおいて次の堅牢化を実施:
  - OpenAI 呼び出しに対する再試行（429, ネットワーク断, タイムアウト, 5xx）と指数バックオフを追加。
  - OpenAI の JSON レスポンスパース失敗時に前後の余計なテキストを含めても最外の JSON オブジェクトを抽出して復元を試みるフォールバックを追加。
  - DuckDB の executemany に空リストを渡さないガード（互換性問題回避）。
  - DB 書き込みエラー時のトランザクション管理（COMMIT / ROLLBACK とログ）。

### Security
- API キーやシークレットは環境変数経由で管理。Settings は必須のシークレットを未設定時に例外を投げる設計（誤った実行を防止）。
- .env 自動読み込み時に OS 環境変数を保護する仕組みを導入（protected set）。
- OpenAI キーを引数で注入できるようにして機密情報の注入箇所を限定可能。

### Notes / Implementation details
- 多くの機能は外部 API（OpenAI, J-Quants）やローカル DuckDB に依存するため、ユニットテストは外部呼び出しをモックするよう設計されている（内部 _call_openai_api などの差し替えポイントを用意）。
- ETL / データ更新処理は idempotent に設計されており、部分失敗時にも既存データを不必要に消去しないよう配慮している（書き込み対象コードを絞る等）。
- 日付/時間はすべて naive な datetime / date で扱い、JST/UTC の変換仕様は各モジュールのコメントに明示。
- 例外や失敗は可能な限り局所化してログに記録し、長時間バッチ処理やパイプラインの停止を最小化する設計。

---

貢献・バグ報告・改善提案はリポジトリの ISSUE / PR を通じてお願いします。