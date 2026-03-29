# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

注: 以下はリポジトリ内のソースコードから推測して作成した初回リリース向けの変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-03-29
初回公開リリース。

### Added
- パッケージ基盤
  - パッケージ名 kabusys と初期モジュール構成を追加（data, strategy, execution, monitoring をエクスポート）。
  - バージョン情報を __version__ = "0.1.0" として定義。

- 設定 / 環境変数管理（kabusys.config）
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みする機能を追加。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
  - .env の行パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント等を考慮）。
  - 環境変数保護機構（既存 OS 環境変数の上書き抑止）をサポート。
  - Settings クラスを追加し、J-Quants / kabuステーション / Slack / DB パス / ログレベル / 環境（development/paper_trading/live）などの設定プロパティを提供。
  - 必須設定未定義時に ValueError を出す _require ユーティリティを実装。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して銘柄ごとのニューステキストを作成し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（ai_score）を算出。
    - JSON Mode を利用した厳格なレスポンス検証とパースロジックを実装。
    - バッチサイズ、記事数・文字数トリム、リトライ（429/ネットワーク/タイムアウト/5xx）を考慮した実装。
    - スコアの ±1.0 クリップおよび部分失敗時に既存スコアを保護する書き換え（DELETE→INSERT）を実装。
    - テスト時に _call_openai_api をモック差し替え可能な設計。
    - calc_news_window 関数でニュース収集ウィンドウ（JST 前日15:00〜当日08:30 相当）を計算。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロキーワードフィルタリング、OpenAI 呼び出し（gpt-4o-mini）、リトライ、フェイルセーフ（API失敗時 macro_sentiment=0.0）を実装。
    - DuckDB の prices_daily/raw_news/market_regime を参照し、冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）で結果を保存。
    - lookahead バイアスを防ぐために target_date 未満のデータのみを利用する方針を採用。

- データモジュール（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX マーケットカレンダーの取り扱いと営業日判定ユーティリティを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar が未取得のときは曜日ベース（週末除外）でフォールバックする堅牢な実装。
    - calendar_update_job を実装し、J-Quants から差分取得 → 保存の夜間バッチ処理（バックフィル、健全性チェック含む）を提供。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを公開して ETL 実行結果を構造化（取得件数、保存件数、品質問題、エラー等）。
    - 差分取得、バックフィル、品質チェック、idempotent 保存を想定した ETL の基盤を実装。
    - jquants_client 経由の保存処理と quality モジュール連携を想定。

- リサーチ / ファクター計算（kabusys.research）
  - ファクター群の実装（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER, ROE）を DuckDB の prices_daily/raw_financials から計算する関数を追加（calc_momentum, calc_volatility, calc_value）。
    - データ不足時は None を返すなど堅牢な取り扱い。
  - 特徴量探索ユーティリティ（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns、任意ホライズン対応、入力検証あり）。
    - IC（Information Coefficient）計算（calc_ic、スピアマンのランク相関）。
    - ランク変換ユーティリティ（rank）および factor_summary（基本統計量）を実装。
  - zscore_normalize は data.stats から再エクスポート。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 環境変数周りの取り扱いを明確化:
  - 必須トークン（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）は Settings 経由で厳格に取得し、未設定時はエラーを出すように設計。
  - .env ファイル読み込み時に OS 環境変数を上書きしない保護機能を持たせ、意図しない上書きを防止。

### Performance / Reliability
- OpenAI 呼び出しについて:
  - JSON Mode を利用した厳密なレスポンス受け取りとパース、リトライ（指数バックオフ）、5xx 判定、タイムアウト対策を実装。
  - API 失敗時はフェイルセーフ（スコア 0.0 を採用して処理継続）を多くの箇所で採用し、ETL / スコアリングの途中停止を回避。
- DuckDB に対する DB 書き込みは冪等化（削除→挿入、トランザクション制御）を徹底し、部分失敗時に既存データを不必要に削除しないように配慮。

### Design Decisions / Notes
- ルックアヘッドバイアス防止のため、各スコアリング・計算処理は datetime.today() や date.today() を内部で参照せず、明示的に target_date を受け取る設計。
- テスト容易性のため、OpenAI 呼び出し箇所でモック差し替え可能な内部関数を用意。
- 外部依存の最小化: research.feature_exploration は pandas 等に依存せず標準ライブラリ + duckdb のみで実装。

### Breaking Changes
- （初回リリースのため該当なし）

--- 

今後のリリースでは、ユーザー向けドキュメント（使用例、マイグレーション指示）、追加のエラーハンドリング改善、より詳細なメトリクス収集・監視機能、strategy / execution / monitoring の実装拡充を記載していくことが想定されます。