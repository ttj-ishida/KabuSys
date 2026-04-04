# Keep a Changelog — kabusys

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]

## [0.1.0] - 2026-04-04
初回公開リリース。以下の主要機能とモジュールを実装しています。

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報を実装（src/kabusys/__init__.py、__version__ = "0.1.0"）。
  - 公開サブパッケージ: data, strategy, execution, monitoring を __all__ に定義。

- 環境設定 / ロード (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダを実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索（CWD 非依存）。
    - 自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサは export プレフィックス、クォート（シングル/ダブル）内のバックスラッシュエスケープ、インラインコメント処理、コメント判定などに対応。
  - Settings クラスでアプリ設定をプロパティとして提供（例: JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、OPENAI 用のトークン参照ロジックなど）。
  - 設定値検証:
    - KABUSYS_ENV は "development" / "paper_trading" / "live" に限定。
    - LOG_LEVEL は標準的なログレベル (DEBUG/INFO/WARNING/ERROR/CRITICAL) のみ許容。
  - デフォルトのファイルパス設定（DuckDB/SQLite/PID/kill flag など）を Path 型で提供。

- AI（自然言語処理）機能 (src/kabusys/ai/)
  - news_nlp モジュール（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を基に銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini, JSON Mode）でセンチメントを評価。
    - バッチ処理（最大 20 銘柄 / コール）、記事数・文字数のトリム、リトライ（429・ネットワーク・5xx に対する指数バックオフ）を実装。
    - レスポンスの厳密なバリデーション（JSON 抽出、results 配列、コード照合、スコア数値検証、±1.0 クリップ）。
    - 成功スコアを ai_scores テーブルへ冪等的に書き込む（該当 code の DELETE → INSERT）。部分失敗時に他銘柄スコアを保持する設計。
    - calc_news_window 関数でニュース収集ウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）を UTC naive datetime として計算。
    - 単体テスト容易性のため OpenAI 呼び出しを差し替え可能（_call_openai_api を patch）。
  - regime_detector モジュール（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）およびマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - prices_daily からの MA 計算は target_date 未満のデータのみ使用（ルックアヘッド防止）。
    - マクロ記事抽出（キーワードリスト）、OpenAI 呼び出し（gpt-4o-mini）、リトライ処理、フェイルセーフ（API 失敗時は macro_sentiment = 0.0）を実装。
    - 結果は regime_score を -1.0〜1.0 にクリップし閾値でラベル付け。
    - OpenAI API キーは引数または環境変数 OPENAI_API_KEY から取得し、未設定時は ValueError を送出。

- データプラットフォーム（DuckDB ベース） (src/kabusys/data/)
  - calendar_management（src/kabusys/data/calendar_management.py）
    - JPX カレンダー管理ロジックを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - market_calendar が未登録時は曜日ベースでフォールバック（週末を休場とみなす）。
    - calendar_update_job により J-Quants から差分取得 → 保存（バックフィル、健全性チェック、例外ハンドリング）を実装。
  - ETL パイプライン（src/kabusys/data/pipeline.py / etl.py）
    - ETLResult データクラスを公開（etl.py 経由）。
    - 差分取得、保存（jquants_client の save_* を想定）、品質チェック integration（quality モジュール想定）を行う設計。
    - デフォルトのバックフィル、カレンダー先読み等により堅牢な取得を実現。
    - DuckDB 存在確認・最大日付取得等のユーティリティ実装。

- リサーチ（src/kabusys/research/）
  - factor_research（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Value（PER, ROE）、Volatility（20 日 ATR）および流動性指標を計算する関数を実装（calc_momentum / calc_value / calc_volatility）。
    - すべて DuckDB の prices_daily / raw_financials を参照する設計で、外部 API へのアクセスは行わない。
    - データ不足時の戻り値は None を用いる設計。
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns、ホライズンはデフォルト [1,5,21]）、IC（Spearman の ρ）を計算する calc_ic、ランク変換ユーティリティ rank、統計サマリ factor_summary を実装。
    - pandas 等の外部依存を持たない純粋 Python + DuckDB 実装。
  - research パッケージの __all__ に主要関数をエクスポート。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 非推奨 (Deprecated)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- OpenAI API キーは明示的に引数で渡すか環境変数 OPENAI_API_KEY を使用する設計。未設定の場合は処理を中断して明確なエラーを出力（誤ったキーの黙殺を防止）。
- .env 読み込みはデフォルトで有効だが、CI/テスト用に KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。

### マイグレーション / 注意事項 (Migration / Notes)
- 環境変数名の一覧（主なもの）
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - OPENAI_API_KEY（AI 機能実行時必須）
  - KABUSYS_ENV（development / paper_trading / live）
  - LOG_LEVEL（DEBUG/INFO/...）
  - DUCKDB_PATH / SQLITE_PATH / PID_FILE_PATH / KILL_FLAG_PATH 等のパス関連
  - KABUSYS_DISABLE_AUTO_ENV_LOAD（自動 .env ロードを無効化）
- DuckDB を使用するため、ローカルにデータベースファイル（デフォルト data/kabusys.duckdb）を用意するか環境変数でパスを設定してください。
- research モジュールは外部 API を呼ばないため、本番注文等と分離して安全に単体テスト可能です。
- AI 関連は外部 API（OpenAI）へ依存するため、テスト時は _call_openai_api 関数を patch してモック化することを推奨します。
- データ書き込みは多くの箇所で冪等性（DELETE→INSERT / ON CONFLICT を想定）を考慮した実装になっていますが、本番環境に導入前にバックアップと検証を行ってください。

---

記録対象外の内部実装メモや将来的に想定される拡張（例: strategy / execution / monitoring の具体的な注文ロジック、jquants_client 実装、quality モジュール詳細など）はドキュメントや別の CHANGELOG エントリで追記予定です。