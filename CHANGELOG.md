# Changelog

すべての重要な変更履歴はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

なお、本リリースはコードベースから推測して作成した初期公開バージョンの変更ログです。

## [Unreleased]

## [0.1.0] - 2026-03-29
初回リリース。日本株自動売買・データ基盤・リサーチ・AI支援のためのコアライブラリ群を公開。

### Added
- パッケージの基本情報
  - kabusys パッケージ初版を追加（__version__ = 0.1.0）。
  - パッケージ公開APIとして data, strategy, execution, monitoring をエクスポート。

- 環境設定管理 (kabusys.config)
  - .env / .env.local 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml）。
  - 高度な .env パーサ実装（コメント, export 句, クォート内エスケープ対応、インラインコメント処理等）。
  - 自動読み込みを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数対応。
  - OS 環境変数を保護する protected load ロジック（.env.local は上書き可、.env は未設定時のみ設定）。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 実行環境 / ログレベル等のプロパティで安全に取得可能（必須変数未設定時は ValueError を送出）。
  - 有効値チェック（KABUSYS_ENV, LOG_LEVEL）と便捷プロパティ（is_live / is_paper / is_dev）。

- AI モジュール (kabusys.ai)
  - news_nlp: ニュースセンチメント評価機能を追加（score_news）。
    - タイムウィンドウ計算（前日15:00 JST〜当日08:30 JST を UTC に変換）。
    - raw_news と news_symbols を基に銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini, JSON mode）へバッチ送信して銘柄単位のスコアを取得。
    - バッチ処理（最大 20 銘柄/リクエスト）、記事・文字数トリム、レスポンスバリデーション、スコアの ±1.0 クリップ、DuckDB への冪等的書き込み（DELETE→INSERT）。
    - 再試行ロジック（429/ネットワーク断/タイムアウト/5xx を指数バックオフでリトライ）、API失敗時はスキップして継続するフェイルセーフ設計。
    - テスト用に _call_openai_api を差し替え可能（unittest.mock.patch 想定）。
  - regime_detector: 市場レジーム判定機能を追加（score_regime）。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を作成。
    - prices_daily / raw_news を参照し、OpenAI（gpt-4o-mini）へ問い合わせて macro_sentiment を算出。API 失敗時は 0.0 にフォールバック。
    - レジームスコアはクリップされ、market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を行う。
    - ルックアヘッドバイアス対策（date < target_date を採用、datetime.today() を参照しない）を実装。

- データモジュール (kabusys.data)
  - calendar_management: JPX カレンダー管理（market_calendar）と営業日判定ユーティリティを追加。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day といった一貫した営業日ロジック。
    - market_calendar 未取得時の曜日ベースフォールバック、DB 値優先の挙動、最大探索日数制限で無限ループ回避。
    - calendar_update_job: J-Quants API 経由で差分取得・バックフィル・保存する夜間バッチジョブ（健全性チェック、バックフィル期間、例外ハンドリング）。
  - pipeline: ETL パイプラインのコア（ETLResult）を追加。
    - ETLResult dataclass により ETL の取得件数 / 保存件数 / 品質問題 / エラー一覧を構造化して返却。
    - 差分更新方針（最終取得日の backfill を行う等）、品質チェックを継続的に収集する設計方針を明示。
  - etl: pipeline.ETLResult の再エクスポート。

- Research モジュール (kabusys.research)
  - factor_research: ファクター計算ユーティリティを追加。
    - calc_momentum: 1M/3M/6M リターンおよび 200 日 MA 乖離を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR（true range の取り扱いに注意）や相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務を取得して PER / ROE を計算（EPS が 0/欠損のときは None）。
    - DuckDB を駆使した SQL ベース実装で外部 API への依存なし、結果は辞書リストで返却。
  - feature_exploration: 特徴量の評価・統計ユーティリティを追加。
    - calc_forward_returns: 将来リターン（指定ホライズン）を一度のクエリで取得。horizons の検証（正の整数かつ <=252）。
    - calc_ic: スピアマンのランク相関（IC）を計算。十分なサンプルがなければ None を返す。
    - rank: 同順位は平均ランクで処理（丸め誤差対策あり）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー関数。
  - research パッケージの __init__ で主要関数を公開。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーの取り扱いは環境変数または引数経由で明示的に解決。未設定時には ValueError を送出して誤使用を防止。

### Notes / Design decisions（重要な設計上の注意点）
- ルックアヘッドバイアス対策として、全てのスコア計算やデータ収集で datetime.today() / date.today() を利用せず、呼び出し側から target_date を受け取る設計にしてある（テスト容易性・再現性重視）。
- OpenAI 呼び出しは JSON mode を利用し、レスポンスの堅牢なパースとバリデーションを実装。API エラーは基本的にフェイルセーフ（スコアを 0.0 にするかその銘柄をスキップ）で処理を継続する。
- DuckDB 周りの互換性（executemany の空リスト不可等）に配慮した実装を行っている。
- DB 書き込みは基本的に冪等（DELETE→INSERT、ON CONFLICT 想定）で実装し、部分失敗が他データを巻き込まないように工夫している。
- テスト容易性のため、OpenAI API 呼び出し箇所（_call_openai_api）を patch して差し替え可能な設計。

---

参照: 各モジュールの docstring と関数コメントに設計思想・処理フロー・例外処理・ログ出力が詳細に記載されています。必要であれば、各機能ごとの利用例・API 使用方法・マイグレーション注意点を追記できます。