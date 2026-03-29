CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを使用します。
リリース日にはこのコードベースの現時点（2026-03-29）の日付を使用しています。

[Unreleased]
------------

- （現状なし）

[0.1.0] - 2026-03-29
-------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージエントリポイント: src/kabusys/__init__.py
    - __version__ = "0.1.0"
    - パブリックサブパッケージとして data, strategy, execution, monitoring を宣言（将来の拡張点）
- 設定/環境変数管理モジュール（src/kabusys/config.py）
  - .env / .env.local ファイルおよび環境変数からの設定自動読み込みを実装
    - プロジェクトルートの検出は .git または pyproject.toml を基準に実施（CWD 非依存）
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能
    - .env パースは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントなどに対応
    - .env.local は既存 OS 環境変数（protected）を上書きしないが override=True の挙動で読み込まれる
  - Settings クラスを公開（settings = Settings()）
    - J-Quants、kabuステーション、Slack、DBパス、環境フラグ（development/paper_trading/live）、ログレベル等のプロパティを提供
    - 必須項目未設定時は ValueError を送出（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）
    - env/log_level の値検証を実装（有効な列挙値でない場合は ValueError）
- AI モジュール（src/kabusys/ai）
  - ニュースNLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いてセンチメントを算出
    - バッチ処理（最大 20 銘柄/コール）、1 銘柄あたりの記事数・文字数制限を導入（トークン肥大化対策）
    - 429・ネットワーク・タイムアウト・5xx に対する指数バックオフでのリトライ実装
    - レスポンスの厳密バリデーション／部分書き込み（成功した銘柄のみ ai_scores テーブルへ DELETE→INSERT）により冪等性と部分失敗耐性を確保
    - calc_news_window(target_date) により JST ベースのニュースウィンドウを計算（ルックアヘッド回避設計）
    - API キー未設定時は明確な ValueError を返す
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して market_regime に書き込み
    - ma200_ratio 計算、マクロ記事抽出、OpenAI 呼び出し、スコア合成、ラベル判定（bull/neutral/bear）
    - LLM の失敗時は macro_sentiment=0.0 で継続するフェイルセーフ
    - OpenAI 呼び出しはリトライ・エラー別処理（RateLimit, Timeout, 5xx 等）
    - DB 書き込みはトランザクション（BEGIN/DELETE/INSERT/COMMIT）で冪等性を保証
- Data モジュール（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを用いた営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装
    - DB データがない場合は曜日ベース（土日除外）でフォールバック
    - calendar_update_job により J-Quants API から差分取得→save（バックフィル・健全性チェック付き）
    - 最大探索日数やバックフィル日数、先読み日数などの安全パラメータを導入して無限ループや異常データを防止
  - ETL / パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを導入（取得件数、保存件数、品質チェック結果、エラー一覧などを保持）
    - _get_max_date 等のユーティリティにより差分取得の基準日を計算
    - DataPlatform 設計方針に沿った差分更新・バックフィル・品質チェックの骨子を実装
    - etl.py で ETLResult を再エクスポート
- Research モジュール（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER, ROE）の計算関数を実装
    - DuckDB SQL を活用し prices_daily / raw_financials に依存（外部 API にはアクセスしない）
    - 行不足時の None ハンドリング、結果は list[dict] 形式を返す設計
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、IC 計算（calc_ic）、ランク付けユーティル（rank）、統計サマリー（factor_summary）を実装
    - 外部ライブラリ不使用（標準ライブラリと duckdb を利用）で研究用途に適した API を提供
  - パッケージレベル再エクスポート（src/kabusys/research/__init__.py）で主要関数を公開
- 内部ユーティリティ・設計上の共通方針
  - ルックアヘッドバイアス回避: 各モジュールで datetime.today() / date.today() を直接参照しない実装方針を順守（target_date 引数駆動）
  - DuckDB を主要なストレージバックエンドとして利用（関数は DuckDB 接続を受け取る）
  - DB 書き込みにおける冪等性・部分失敗耐性を重視（DELETE→INSERT、個別 executemany）
  - OpenAI 呼び出し部はテスト容易性のため差し替え可能（_call_openai_api の patch を想定）
  - ロギングと細かい警告で動作状態を可視化

Changed
- 初期リリースにつき該当なし

Fixed
- 初期リリースにつき該当なし

Deprecated
- 初期リリースにつき該当なし

Removed
- 初期リリースにつき該当なし

Security
- 環境変数の自動ロード時、OS 環境変数（既存キー）を保護する仕組み（protected set）を導入
- OpenAI/API キー等の必須値は明確にエラーを返すため、キー設定漏れに早期に気づける

Notes / Requirements / 既知の注意点
- Python バージョン: 型ヒント（X | Y など）を使っているため Python 3.10+ が必要です。
- 依存: DuckDB、OpenAI Python SDK（新しい JSON Mode / response_format をサポートするバージョンが必要）等。
- 環境変数:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（Settings が要求する値）
  - OpenAI の利用には OPENAI_API_KEY が必要。news_nlp.score_news / regime_detector.score_regime は引数で API キー注入可。
- DB パスのデフォルト:
  - DuckDB: data/kabusys.duckdb
  - SQLite (monitoring 用): data/monitoring.db
- いくつかのパッケージ公開名（strategy, execution, monitoring）は __all__ にリストアップされていますが、このリリースのコードスナップショットではそれらの実体が未提供の可能性があります（将来の拡張点）。
- OpenAI 呼び出しはネットワーク/レートエラーに対して堅牢に設計されていますが、API 仕様や SDK バージョン変更により動作が変わる可能性があります。特に response_format と JSON Mode の利用は SDK の互換性要件があります。

貢献・フィードバック
- 不具合や改善提案があれば issue/PR を通じてお願いします。README やドキュメントは今後追記予定です。