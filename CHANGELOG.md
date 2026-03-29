# Keep a Changelog

すべての公開変更履歴はこのファイルに記録します。  
本プロジェクトは "Keep a Changelog" の形式に準拠しています。  
日付はリリース日を示します。

## [Unreleased]

- （なし）

## [0.1.0] - 2026-03-29

### Added
- 初期公開: kabusys パッケージ（日本株自動売買・データ基盤・リサーチ支援ライブラリ）。
  - パッケージバージョン: 0.1.0
  - パッケージ公開モジュール: data, research, ai, など（__all__ に基づく）

- 環境設定管理
  - 自動 .env ロード機能を実装（プロジェクトルートを .git または pyproject.toml で探索）。
  - .env ファイルパーサを実装:
    - `export KEY=val` 形式に対応。
    - シングル/ダブルクォートとバックスラッシュエスケープを適切に扱う。
    - インラインコメント判定の細かいルール（クォート有無で挙動が異なる）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロード無効化可能。
  - Settings クラスを導入（環境変数からのプロパティ取得）:
    - J-Quants、kabuステーション、Slack、DB パス、実行環境（development/paper_trading/live）等のプロパティ。
    - 不正な env 値や未設定の必須変数は ValueError を送出する。

- AI（ニュース NLP / レジーム判定）
  - news_nlp モジュール:
    - score_news(conn, target_date, api_key=None): raw_news / news_symbols から銘柄ごとの記事を集約し、OpenAI（gpt-4o-mini の JSON mode）でセンチメントを評価。
    - バッチ処理（最大 20 銘柄/回）・記事・文字数トリミング・レスポンス検証・±1.0 クリップを実装。
    - リトライ（429/ネットワーク/タイムアウト/5xx）＋指数バックオフ。API 失敗時は個別チャンクをスキップして継続（フェイルセーフ）。
    - DuckDB 互換性考慮（executemany の空リスト回避ロジック）。
  - regime_detector モジュール:
    - score_regime(conn, target_date, api_key=None): ETF 1321 の 200 日 MA 乖離（加重 70%）とマクロニュース LLM センチメント（加重 30%）を合成して市場レジーム（bull/neutral/bear）を判定。
    - マクロ記事フィルタリング（キーワードリスト）・OpenAI 呼び出し・スコア合成・冪等な market_regime テーブル書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - API 呼び出し失敗時は macro_sentiment=0.0 へフォールバックし処理継続（フェイルセーフ）。
  - 設計上の特徴:
    - OpenAI クライアント呼び出しはテスト用にモック差し替え可能（内部の _call_openai_api を patch 可能）。
    - GPT モデル: gpt-4o-mini を利用する想定。
    - レスポンスは厳密な JSON を期待、パース失敗時の救済ロジックも実装。

- Data（データ基盤）
  - calendar_management:
    - JPX カレンダー管理（market_calendar）機能を提供。
    - 営業日判定（is_trading_day）、SQ 判定（is_sq_day）、前後営業日検索（next_trading_day/prev_trading_day）、期間内営業日取得（get_trading_days）、夜間バッチ（calendar_update_job）を実装。
    - 市場カレンダー未取得時は曜日ベースのフォールバック（週末除外）で一貫した動作を提供。
    - calendar_update_job は J-Quants クライアント経由で差分取得・バックフィル・健全性チェックを行い、idempotent に保存。
  - pipeline / ETL:
    - ETLResult データクラスを追加（ETL のメタ情報、品質問題、エラー一覧を保持）。
    - ETL パイプライン設計に関するユーティリティ（最終取得日の取得・差分算出・テーブル存在チェックなど）。
    - jquants_client と quality モジュールとの連携を想定した設計。
  - etl モジュールは ETLResult を再エクスポート。

- Research（リサーチ用ユーティリティ）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率を計算。
    - calc_value: 最新の raw_financials を参照して PER/ROE を計算（EPS が 0 / 欠損の場合は None）。
    - 全関数は DuckDB の prices_daily / raw_financials のみ参照し外部 API に依存しない設計。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。
    - calc_ic: factor_records と forward_records を結合して Spearman（ランク相関）で IC を計算。
    - rank: 同順位は平均ランクで扱うランク変換ユーティリティ（丸め処理で ties の誤検出を低減）。
    - factor_summary: count/mean/std/min/max/median の統計サマリーを計算。
  - 設計方針:
    - datetime.today()/date.today() を参照しない（ルックアヘッドバイアス防止）。
    - pandas 等の外部ライブラリに依存しない純 Python 実装。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- OpenAI API キーや各種トークン（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN 等）は必須設定とし、未設定時は ValueError を投げて明示的に通知する実装。
- .env 自動ロード時に OS 環境変数は "protected" と扱い、.env/.env.local により上書きされないよう配慮。

### Notes / Implementation details and compatibility
- DuckDB 特有の挙動（executemany に空リストを渡せない等）に配慮した実装を含む。
- DB 書き込みは基本的に冪等性を保つ（DELETE → INSERT や ON CONFLICT を想定）。
- LLM 呼び出しのリトライとログ出力は運用時の観測性を重視して実装。
- 日時はすべて timezone-naive な datetime / date を使用し、UTC/ JST の変換は明示的に制御している（ニュースウィンドウ等で採用）。

---

著者注: 本 CHANGELOG はコードベースからの挙動・設計記述を基に推測して作成しています。実際のリリースノートに含めるべき追加情報（既知の制限、互換性ノート、マイグレーション手順、既知のバグ等）がある場合は追記してください。