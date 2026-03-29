# CHANGELOG

すべての注目すべき変更履歴をここに記載します。本ファイルは "Keep a Changelog" の形式に準拠します。

- フォーマット: https://keepachangelog.com/ja/1.0.0/
- バージョニングは semver 準拠を想定しています。

## [0.1.0] - 2026-03-29
初回リリース（推定）。以下はコードベースから推測してまとめたこのリリース時点での主な追加機能・設計上の決定・実装概要です。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの公開: data, strategy, execution, monitoring を __all__ でエクスポート。
  - バージョン情報: __version__ = "0.1.0" を設定。

- 設定・環境変数管理 (kabusys.config)
  - .env 自動ロード機能を実装（プロジェクトルートの検出: .git または pyproject.toml を探索）。
  - .env / .env.local の読み込み順序と上書きルールの実装（OS 環境変数保護機能あり）。
  - .env パーサ実装: export プレフィックス、クォート文字のエスケープ、インラインコメントの取り扱いなどに対応。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化サポート。
  - Settings クラスを提供: J-Quants / kabu API / Slack / DB パス / 環境 (development/paper_trading/live) / LOG_LEVEL 判定等のプロパティを定義。
  - 必須環境変数未設定時に明示的なエラーを投げる _require ヘルパ。

- AI モジュール (kabusys.ai)
  - ニュースNLP (kabusys.ai.news_nlp)
    - calc_news_window: ニュース収集ウィンドウ（前日15:00 JST〜当日08:30 JST）を計算。
    - score_news: raw_news と news_symbols から銘柄ごとの記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（ai_scores）を書き込む機能。
    - バッチ処理（_BATCH_SIZE=20）、記事トリム（記事数上限・文字数上限）とレスポンス検証ロジックを実装。
    - JSON Mode を期待する厳格な出力パースとフォールバック (外側の {} を抽出) を実装。
    - リトライ（429/ネットワーク/タイムアウト/5xx）と指数バックオフの実装。失敗時は安全にスキップして続行する設計。
    - DuckDB 向けの冪等的な DB 書き込み（DELETE → INSERT、executemany の空リスト回避）。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離とマクロニュースの LLM センチメントを重み付け合成して市場レジーム（bull/neutral/bear）を判定。
    - ma200_ratio 計算（ルックアヘッド回避のため target_date 未満データのみ使用）、マクロ記事の抽出、OpenAI 呼び出し（gpt-4o-mini）を含む。
    - API 呼び出しのリトライ/フォールバック（API 失敗時は macro_sentiment=0.0）を実装。
    - 結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。書き込み失敗時はロールバック処理を行う。
    - 設計上の注意: datetime.today()/date.today() を参照せず、ルックアヘッドバイアスを防止。

- 研究用モジュール (kabusys.research)
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離を計算（prices_daily を参照）。
    - calc_volatility: 20日 ATR、相対 ATR、平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER/ROE を計算（最新報告日の選定を含む）。
    - いずれも DuckDB を用いた SQL ベース実装で、外部 API にはアクセスしない設計。
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算（LEAD を利用）。
    - calc_ic: スピアマンランク相関（IC）を計算する実装（欠損・同順位対応）。
    - rank: 平均ランクを計算するユーティリティ（丸めによる ties 対策あり）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
  - zscore_normalize をデータ層から再エクスポート（kabusys.research.__init__）。

- データプラットフォーム (kabusys.data)
  - calendar_management
    - JPX カレンダー管理: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。
    - market_calendar テーブルがない場合は曜日ベースのフォールバック（週末を休場扱い）。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等に更新（バックフィル、健全性チェック含む）。
    - 最大探索日数やバックフィル・先読み日数等、現実的な制約 (_MAX_SEARCH_DAYS, _BACKFILL_DAYS, _CALENDAR_LOOKAHEAD_DAYS) を設定。
  - pipeline / etl
    - ETLResult データクラスを導入（取得件数・保存件数・品質検査結果・エラー概要の保持）。
    - ETL 設計方針: 差分更新、バックフィル、品質チェック（品質問題は収集して呼び出し元判断）、id_token 注入によるテスト性の配慮。
    - 内部ユーティリティ: テーブル存在確認、最大日付取得、トレーディング日の調整等を実装。
  - jquants_client との連携を想定（fetch/save 系関数経由でのデータ取得・保存を利用）。

- 共通・実装上の設計ノート
  - DuckDB を主要なローカル分析 DB として使用。日付は明示的に date オブジェクトで扱い timezone 混入を回避。
  - ルックアヘッドバイアス対策の徹底（関数は内部で date.today() を参照しない）。
  - AI 呼び出しに対してはリトライ・バックオフ・フォールバックを実装し、安全に継続できるフェイルセーフ設計。
  - DB 書き込みは可能な限り冪等（DELETE→INSERT など）を採用し、部分失敗時に既存データを保護する。

### 変更 (Changed)
- 初回リリースのため該当なし（新規実装が主体）。

### 修正 (Fixed)
- 初回リリースのため該当なし（既知のフェイルセーフや例外処理を実装済み）。

### 削除 (Removed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- OpenAI API キーは関数引数で注入可能かつ環境変数 OPENAI_API_KEY を参照する設計。未設定時は ValueError を投げることで明示的に扱う。

---

注意:
- 本 CHANGELOG は提示されたコードからの推測に基づいて作成しています。実際のリリースノートや変更履歴はリポジトリのコミット履歴、issue、リリース文書などを参照して確定してください。