# CHANGELOG

すべての注目すべき変更点を記録します。本ファイルは Keep a Changelog に準拠しています。

## [0.1.0] - 2026-03-29

Initial release — 日本株自動売買支援ライブラリ "KabuSys" の最初の公開版。

### Added
- パッケージ構成
  - src/kabusys パッケージを追加。主要サブパッケージとして data, research, ai, monitoring, strategy, execution（公開 API 用のエントリポイントを __all__ に定義）を用意。

- 環境設定管理（kabusys.config）
  - .env/.env.local ファイルおよび OS 環境変数から設定を自動読み込みする実装を追加。
  - プロジェクトルート特定ロジック（.git or pyproject.toml を基準）により CWD に依存しない自動ロードを実現。
  - 行パーサは export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いなどを考慮する堅牢な実装。
  - 自動ロードの無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）をサポート。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 実行環境・ログレベルなどの取得・検証（必須環境変数の必須チェック、許容値検証）を実装。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols を元に銘柄別にニュースを集約し、OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメント（ai_score）を算出・ai_scores テーブルへ書き込む処理を実装。
  - 時間ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST に対応）を提供（calc_news_window）。
  - バッチ処理（最大 20 銘柄/チャンク）、1 銘柄あたりの記事数・文字数制限（トークン肥大化対策）を実装。
  - API リトライ（429 / ネットワーク断 / タイムアウト / 5xx）を指数バックオフで実装。非再試行エラーはスキップして継続するフェイルセーフ設計。
  - レスポンスの厳密なバリデーションと JSON 前後余分テキストの復元処理、スコアの ±1.0 クリップ、部分失敗時に既存データを保護する idempotent な DB 書き換え（DELETE → INSERT）を実装。
  - 公開 API: score_news(conn, target_date, api_key=None) — 書き込んだ銘柄数を返す。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定・market_regime テーブルへ冪等書き込みする機能を実装。
  - マクロニュース抽出、OpenAI 呼び出し、再試行ロジック、API 失敗時のフォールバック（macro_sentiment = 0.0）などを含む堅牢な実装。
  - ルックアヘッドバイアス対策（datetime.today()/date.today() 非参照、DB クエリで date < target_date とする等）。
  - 公開 API: score_regime(conn, target_date, api_key=None) — 成功時に 1 を返す。

- Data / ETL（kabusys.data.pipeline / etl）
  - ETL パイプラインのインターフェースと結果を表す ETLResult データクラスを実装・公開（kabusys.data.ETLResult を再エクスポート）。
  - 差分更新、バックフィル、品質チェックの枠組みを考慮した設計（設計方針をドキュメントとして明示）。

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - market_calendar テーブルを用いた営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
  - DB にデータがない場合の曜日ベースのフォールバック、カレンダー更新バッチ（calendar_update_job）を実装。
  - カレンダー取得時のバックフィル、健全性チェック（極端な将来日付の保護）を実装。

- リサーチ・ファクター計算（kabusys.research）
  - ファクター計算群を実装:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と価格を組み合わせて PER / ROE を計算。
  - 特徴量探索ユーティリティ:
    - calc_forward_returns: 指定ホライズンの将来リターンを一括取得（複数 horizon をサポート、入力検証あり）。
    - calc_ic: スピアマンランク相関（IC）を計算（欠損値・同順位の扱いを考慮）。
    - factor_summary: count/mean/std/min/max/median を計算。
    - rank: タイ付き（平均ランク）でのランク変換（丸めを用いて浮動小数点の ties 検出漏れ対策）。
  - 結果は (date, code) ベースの辞書リストで返す設計。

- DuckDB 周りの互換性・堅牢化
  - DuckDB の executemany に空リストを渡せない制約への対応（空チェックを行ってから executemany 実行）。
  - DuckDB 日付型の取り扱い補助（_to_date など）。

- ロギング・設計方針の明示
  - 各モジュールで設計上の注意点（ルックアヘッドバイアス回避、フェイルセーフ、idempotency）をドキュメント文字列として明記。

### Changed
- （初期リリースのため該当なし）

### Fixed
- .env 読み込みのエラー発生時に warnings.warn でユーザーに通知するようにし、I/O エラーを無理に上げない堅牢な動作に変更。
- OpenAI API 呼び出し周りでの多種エラー（RateLimitError, APIConnectionError, APITimeoutError, APIError）のハンドリングを明確化し、5xx は再試行、それ以外はフォールバック／スキップするように整備。
- news_nlp の JSON パースで周辺文字列が混入したケースに対する復元処理（最外の {} を抽出して再パース）を実装し、現実の LLM 出力の揺らぎに耐えるようにした。

### Security
- （初期リリースのため該当なし）

---

注記:
- 本リリースは「設計方針」を重視しており、実行環境（特に OpenAI API キー、kabu API パスワード、Slack トークン等）は Settings 経由で適切に設定する必要があります。必須環境変数が未設定の場合は ValueError を送出します。
- 各 AI 関連処理は外部 API に依存するため、API 失敗時は可能な限りフェイルセーフ（スコア＝0 や処理スキップ）で継続する設計です。運用時はログとメトリクス監視を推奨します。