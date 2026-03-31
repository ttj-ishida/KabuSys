# Changelog

すべての重要な変更点をこのファイルに記録します。フォーマットは Keep a Changelog に準拠しています。

現在のリリース方針: 0.1.0 が初期公開版です。

## [Unreleased]
（無し）

## [0.1.0] - 2026-03-31
初回リリース。日本株自動売買システム「KabuSys」のコア機能群を実装しました。

### Added
- パッケージ基礎
  - パッケージ初期化: version = 0.1.0、公開モジュール（data, research, ai, execution, strategy, monitoring 等）のエントリポイントを定義（src/kabusys/__init__.py）。
- 設定管理 (src/kabusys/config.py)
  - 環境変数/.env ファイル読み込み機能を実装。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）。
    - .env/.env.local の読み込み優先度制御（OS環境変数 > .env.local > .env）。
    - 自動読み込みを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env パーサは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理などをサポート。
    - 上書き制御（override）と保護キーセット（protected）により OS 環境変数を保持。
  - Settings クラスを提供し、必要な環境変数をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等を必須としてバリデーションを行う。
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の検証ロジックを実装。
    - DB パス（DUCKDB_PATH, SQLITE_PATH）や kabu API のベース URL のデフォルト値を提供。
- AI / 自然言語処理 (src/kabusys/ai)
  - ニュース NLP スコアリング (news_nlp.py)
    - raw_news / news_symbols を集約して銘柄毎に記事を結合し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（-1.0〜1.0）を算出。
    - 処理はチャンク単位（デフォルト 20 銘柄/チャンク）、1 銘柄あたり記事数/文字数上限でトリム。
    - OpenAI JSON Mode を利用して厳密 JSON 出力を期待し、レスポンスの堅牢なパース／バリデーション処理を実装。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライを実装。その他エラーはフェイルセーフ（スキップ）で継続。
    - DuckDB への書き込みは部分失敗時に既存スコアを保護するため、取得済みコードのみ置換（DELETE → INSERT）する冪等化処理を採用。
    - テスト用に _call_openai_api を patch 可能にしている。
  - 市場レジーム判定 (regime_detector.py)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロセンチメントはマクロキーワードでフィルタした記事タイトルを OpenAI（gpt-4o-mini）へ送り JSON レスポンスを取得してスコア化。
    - API 失敗時のフォールバック（macro_sentiment=0.0）、及び API 呼び出しリトライ／バックオフを実装。
    - 計算結果は market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）で保存。
    - ルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照せず、target_date ベースで処理。
- データ基盤 (src/kabusys/data)
  - カレンダー管理 (calendar_management.py)
    - JPX カレンダーの夜間更新ジョブ（calendar_update_job）を実装。J-Quants から差分取得して market_calendar テーブルへ冪等保存。
    - 営業日判定ユーティリティを提供: is_trading_day、next_trading_day、prev_trading_day、get_trading_days、is_sq_day。
    - DB 未取得日のフォールバックは曜日ベース（土日を非営業日扱い）。最大検索上限で無限ループ防止。
    - バックフィル、先読み日数、健全性チェック（future date の閾値）を実装。
  - ETL パイプライン（pipeline.py / etl.py）
    - ETLResult データクラスを公開（etl.py 経由で再エクスポート）。
    - 差分取得、保存（jquants_client の save_* を想定した冪等保存）と品質チェックの流れを設計。
    - テーブル存在チェックや最大日付取得などのヘルパー実装。
    - ETL 処理中のエラー・品質問題を収集して呼び出し元で判断できる設計（Fail-Fast しない）。
- 研究/リサーチ (src/kabusys/research)
  - ファクター計算 (research/factor_research.py)
    - Momentum（1M/3M/6M リターン、ma200 乖離）、Volatility（20日 ATR など）、Value（PER, ROE）等の計算関数を実装。
    - DuckDB SQL を中心とした実装で prices_daily / raw_financials のみ参照し、安全な欠測処理を行う。
  - 特徴量探索 (research/feature_exploration.py)
    - 将来リターン計算（任意ホライズン）、IC（Spearman の ρ）計算、ランク付けユーティリティ、ファクター統計サマリー（count/mean/std/min/max/median）を実装。
    - pandas 等に依存せず標準ライブラリのみで実装。
  - data.stats モジュールから zscore_normalize を再利用可能にエクスポート。
- 互換性・実装上の配慮
  - DuckDB のバージョン差異（executemany に空配列を渡せない等）を考慮した実装（空リストチェック）。
  - OpenAI SDK の挙動差（APIError に status_code がある場合など）を考慮した堅牢なエラーハンドリング記述。
  - モジュール結合を低くする設計（regime_detector と news_nlp の内部 API 呼び出し関数は別実装にしている等）。
  - ルックアヘッドバイアス回避をコード設計方針として明示・遵守。

### Changed
- 初回リリースにつき該当なし。

### Fixed
- 初回リリースにつき該当なし。

### Deprecated
- 初回リリースにつき該当なし。

### Removed
- 初回リリースにつき該当なし。

### Security
- 環境変数の必須チェックを多数実装。未設定（例: OPENAI_API_KEY, SLACK_BOT_TOKEN 等）の場合は ValueError を投げて早期検出する。
- .env 自動読み込みはデフォルトで有効だが、テスト用途に KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。

### Notes / 注意事項
- 実行には以下が前提:
  - DuckDB（および期待するテーブルスキーマ: prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等）。
  - J-Quants 関連の API トークン（JQUANTS_REFRESH_TOKEN）や OpenAI API キー（OPENAI_API_KEY）、kabu ステーション API 設定、Slack トークン等の環境変数。
- OpenAI への呼び出し箇所はテストのため patch / mock しやすく実装されています（_call_openai_api をモック可能）。
- news_nlp と regime_detector は gpt-4o-mini + JSON mode を利用する想定でプロンプト・レスポンスパースを行っています。API の挙動やモデルの応答形式が変わるとパースロジックの調整が必要になる可能性があります。
- DuckDB を利用するため、並列実行時やファイルロックに関する運用上の配慮が必要です（運用ガイド参照を推奨）。

---
このファイルはコードベースから推測して作成した CHANGELOG です。実際の変更履歴やリリースノートにはリリース担当者による確認・補正を行ってください。