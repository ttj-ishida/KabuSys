# Changelog

すべての注目すべき変更点を記録します。  
このファイルは「Keep a Changelog」形式に準拠しています。

- リリース方針: 互換性はセマンティックバージョニングに従います（MAJOR.MINOR.PATCH）。
- 日付はリリース日を表します。

## [Unreleased]
（現在のコードベースは初回リリース相当の状態のため、Unreleased エントリは空です）

---

## [0.1.0] - 2026-03-27

初回リリース。日本株自動売買プラットフォームの基礎機能群をまとめて提供します。以下はコードベースから推測してまとめた主要な追加点・設計方針・注意点です。

### Added
- パッケージ基盤
  - kabusys パッケージ初期実装（__version__ = 0.1.0）。
  - 公開サブパッケージ: data, research, ai, monitoring, strategy, execution（__all__ により表明）。

- 設定管理
  - 環境変数／.env の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml から探索）。
  - .env/.env.local の読み込み順序と上書きルールを定義（OS環境変数保護、.env.local が上書き）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを提供。
  - .env 行パーサは `export KEY=val`、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
  - Settings クラスを提供し、必須環境変数取得（_require）や検証を行うプロパティを定義。
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須項目。
    - 環境 (development/paper_trading/live) と LOG_LEVEL の検証。
    - データベースパス（DuckDB/SQLite）のパス取得ユーティリティ。

- AI（NLP / レジーム判定）
  - news_nlp モジュール: raw_news と news_symbols を元に OpenAI（gpt-4o-mini）でニュースごとのセンチメントスコアを算出し、ai_scores テーブルへ書き込む。
    - ニュース時間ウィンドウ（JST 前日15:00〜当日08:30、DBはUTCで扱う）計算ユーティリティを提供。
    - バッチ処理（銘柄ごとに最大 _BATCH_SIZE=20）・トリミング（記事数・文字数制限）を実装。
    - JSON mode を想定したレスポンス検証、スコアの ±1.0 クリップ。
    - 429/接続断/タイムアウト/5xx に対する指数バックオフとリトライ。
    - 部分成功を考慮した DB の置換（DELETE → INSERT）戦略により既存スコアの不意な消失を防止。
  - regime_detector モジュール: ETF 1321 の 200 日移動平均乖離とマクロニュースの LLM センチメントを重み合成して日次の市場レジーム（bull/neutral/bear）を算出・保存。
    - MA 計算（lookahead バイアス防止のため target_date 未満のデータのみ使用）。
    - マクロキーワードによるニュース抽出、LLM 呼び出し、リトライ/フォールバック（API 失敗時 macro_sentiment=0.0）。
    - レジーム合成式、閾値判定、冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）。

- データ（ETL / カレンダー / pipeline）
  - data.pipeline: ETLResult データクラス（ETL の取得数・保存数・品質問題・エラー集約）を公開。
  - calendar_management: JPX カレンダー管理と営業日判定ユーティリティ。
    - market_calendar の有無に応じたフォールバック（未登録日は曜日ベース判定）を一貫して実装。
    - next_trading_day / prev_trading_day / get_trading_days / is_trading_day / is_sq_day を提供。
    - calendar_update_job: J-Quants から差分取得、バックフィル数日分の再取得、健全性チェック（未来日異常検出）を実装。
  - pipeline (ETL) の設計方針:
    - 差分更新、idempotent な保存（jquants_client の save_* を使用）、品質チェックの実行（quality モジュールと連携）を想定。
    - デフォルトの backfill を設定し、部分的な品質問題があっても処理を継続して全問題を収集する方針。

- Research（因子計算・特徴量探索）
  - factor_research:
    - Momentum（1M/3M/6M リターン、200日MA乖離）、Value（PER、ROE）、Volatility（20日ATR）、Liquidity（20日平均売買代金、出来高比率）の計算関数を実装。
    - DuckDB のウィンドウ関数等を利用して効率的に計算。データ不足時は None を返す。
  - feature_exploration:
    - 将来リターン calc_forward_returns（複数ホライズン対応、入力検証あり）。
    - IC（Information Coefficient: Spearman ρ）計算、rank ユーティリティ（同順位は平均ランク）。
    - factor_summary による統計量集計（count/mean/std/min/max/median）。
  - これらは外部 API に依存せず、prices_daily / raw_financials のみを参照する設計。

- 公開 API の整理
  - 複数モジュールでの内部 OpenAI 呼び出しはテスト置換しやすいように専用関数を定義（_call_openai_api）。
  - 全体的に lookahead バイアス対策（datetime.today()/date.today() を直接参照しない）を守る設計。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 環境変数の自動ロード時に OS 環境変数を保護する仕組みを導入（読み込み時 protected set を利用）。
- API キーの必須チェックを実装し、未設定時は明示的に ValueError を発生させる。

### Notes / Implementation details / フェイルセーフ挙動
- DuckDB を主要なローカル分析 DB として使用。DuckDB のバージョン差異（executemany の空配列等）に配慮した実装あり。
- LLM（OpenAI）呼び出しは JSON mode を想定。レスポンスのパース失敗や非致命的 API エラーはログ警告を出してフォールバックする（処理を継続）。
- DB 書き込みは可能な限り冪等（既存行の削除→挿入や ON CONFLICT を想定）にして部分失敗の影響を最小化。
- calendar_update_job など外部 API 呼び出し部分は例外捕捉とログ出力により失敗時は 0 を返すフェイルセーフを採用。

### Breaking Changes
- （初回リリースのため該当なし）

---

追記・補足:
- README やリリースノートはコードの公開範囲・運用フローに合わせて別途整備すると良いです（API キーの取り扱い、必須環境変数一覧、DuckDB スキーマ定義、J-Quants / kabu API のクレデンシャル設定方法など）。
- 実運用前に OpenAI 呼び出しのレートやコスト、J-Quants API の利用制限を確認してください。