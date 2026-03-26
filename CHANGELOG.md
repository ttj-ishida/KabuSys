# Changelog

すべての重要な変更を記録します。形式は "Keep a Changelog" に準拠しています。  
このファイルはコードベースから推測して作成した変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-03-26
初期リリース。日本株自動売買 / データ基盤 / 研究用ユーティリティ群を提供します。

### Added
- パッケージ基盤
  - kabusys パッケージの公開エントリポイントを追加（__version__ = 0.1.0、__all__ を定義）。
- 環境設定 / .env 管理
  - .env ファイルと OS 環境変数を統合して読み込む設定モジュールを実装（kabusys.config）。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を探索）。
  - .env の自動ロード機能を追加（KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能）。
  - export プレフィックス対応、クォート文字列とエスケープ処理、インラインコメント扱いの細かなパース実装。
  - 環境変数取得用の Settings クラスを提供（各種必須キーの検証とデフォルト値の定義）。
  - 設定のユーティリティプロパティ（is_live / is_paper / is_dev、log_level 検証など）を追加。
- データ基盤（data）
  - ETL パイプラインの結果を表す ETLResult データクラスを追加（kabusys.data.pipeline）。
  - calendar_management: JPX カレンダー管理、営業日判定、next/prev/get_trading_days、SQ判定などのユーティリティを実装。
  - calendar_update_job: J-Quants からの差分取得と market_calendar への冪等保存ジョブを実装。
  - ETL のためのユーティリティ（テーブル存在確認、最大日付取得、取得ウィンドウ調整など）を実装。
  - jquants_client へのインターフェース想定（fetch/save 系関数を利用する設計）。
- ニュース NLP / AI（kabusys.ai）
  - score_news: raw_news を集約し OpenAI（gpt-4o-mini）で銘柄毎センチメントを算出して ai_scores に書き込む機能を実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST の UTC 変換）を提供。
    - 銘柄ごとに記事を集約（最大記事数・最大文字数でトリム）。
    - バッチ送信（最大 20 銘柄 / チャンク）、レスポンスのバリデーションとスコアクリップ（±1.0）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ実装。
    - DuckDB への部分置換（DELETE→INSERT）で部分失敗時の既存データ保護。
  - regime_detector: ETF（1321）の 200 日移動平均乖離とマクロニュースの LLM センチメントを合成して日次市場レジーム（bull / neutral / bear）を判定・保存する機能を実装。
    - ma200_ratio 計算（target_date 未満のデータのみを使用、データ不足時は中立扱い）。
    - マクロニュース抽出（複数キーワードでフィルタ、最大件数制限）。
    - OpenAI 呼び出し (gpt-4o-mini) によるマクロセンチメント評価（失敗時は macro_sentiment=0.0 にフォールバック）。
    - スコア合成ロジック（重み: MA 70% / Macro 30%）と閾値判定、冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）。
- 研究用モジュール（kabusys.research）
  - factor_research: モメンタム / ボラティリティ / バリュー系ファクター計算関数を実装。
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離（データ不足時の None 処理）。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: 最新財務データから PER / ROE を計算（raw_financials と prices_daily を組合せ）。
  - feature_exploration: 将来リターン計算、IC（スピアマンρ）計算、ランク変換、ファクター統計サマリーを実装。
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターン取得。
    - calc_ic: factor と forward を code で結合してランク相関を算出（有効レコード 3 件未満は None）。
    - rank / factor_summary: 同順位の平均ランク処理、基本統計量計算。
- その他
  - OpenAI 呼び出し部分はテスト容易性のため _call_openai_api をモジュール内で定義（テストで差し替え可能）。

### Changed
- （初期リリースのため変更履歴なし）

### Fixed / Hardening
- .env 読み込みでのファイル読み取り失敗を警告出力してスキップするように安全に処理。
- .env のクォート文字列内エスケープとコメント判定の精緻化により誤パースを低減。
- DuckDB に対する executemany の空リストバインド問題を回避するガードを追加（DuckDB 0.10 互換性対応）。
- OpenAI API 呼び出し結果の JSON パース失敗時に、文字列から最外の JSON オブジェクトを抽出して復元を試みるフォールバックを追加。
- API エラーの扱いを細分化（RateLimit / Connection / Timeout はリトライ、APIError で 5xx 判定の上リトライ）して堅牢化。
- 各種日付処理でルックアヘッドバイアスを避けるため datetime.today()/date.today() 参照を最小化（target_date を明示的に受け取る設計）。
- DB 書き込み失敗時に ROLLBACK を実行し失敗した場合は警告ログを残すように安全措置を追加。

### Security
- OpenAI API キー / Slack トークンなどの機密情報は環境変数経由で取得し、Settings クラスで必須チェックを行う設計。
- .env 自動ロードは無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）で制御可能（テストや CI 環境向け）。

### Removed
- （初期リリースのため削除なし）

---

注:
- 本 CHANGELOG は提示されたコードベースからの推測に基づいています。実際のリリースノートと差異がある場合があります。