# CHANGELOG

すべての注目すべき変更を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。  
バージョン番号はセマンティックバージョニングに従います。

## [Unreleased]
- （なし）

---

## [0.1.0] - 2026-03-29
初回公開リリース。

### Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョン: 0.1.0 を導入。パッケージの公開インターフェースを __all__ で定義（data, strategy, execution, monitoring）。

- 設定 / 環境変数管理（kabusys.config）
  - .env ファイルと環境変数から設定を自動読み込みする機構を実装。
  - プロジェクトルート探索ロジックを追加（.git または pyproject.toml を基準）。これによりカレントワーキングディレクトリに依存しない自動ロードを実現。
  - .env のパース機能を強化:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理を考慮して値を正しく抽出。
    - クォートなしの値についてはインラインコメント（#）を適切に扱う。
  - .env 読み込みの優先順位を OS 環境変数 > .env.local > .env とし、既存 OS 環境変数は保護（protected）されるよう実装。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加（テストなどで利用可能）。
  - Settings クラスを追加し、アプリケーション設定をプロパティ経由で取得可能に：
    - J-Quants, kabuステーション API, Slack, DB（duckdb/sqlite）パス、環境（development/paper_trading/live）、ログレベル等。
    - 必須設定未指定時は明示的な ValueError を投げる。

- AI（自然言語処理）モジュール（kabusys.ai）
  - news_nlp モジュール:
    - raw_news と news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ書き込み。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ（calc_news_window）を提供。
    - バッチ処理（最大 20 銘柄／リクエスト）、1 銘柄あたり記事数・文字数上限（肥大化対策）を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフによるリトライを実装。
    - レスポンスの厳密バリデーション（JSON 抽出、構造チェック、スコア数値検証、±1.0 でのクリップ）を実装。
    - API 呼び出しはテスト用に差し替え可能（_call_openai_api をパッチ可能）。
    - エラー耐性（API失敗時は該当チャンクをスキップして他は継続）を確保。
  - regime_detector モジュール:
    - 日次で市場レジーム（bull/neutral/bear）を判定する機能を追加。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース由来の LLM センチメント（重み 30%）を合成してスコアリング。
    - マクロ記事抽出（タイトルベース、キーワードリスト）と OpenAI によるセンチメント評価を実装。
    - API エラー時は macro_sentiment = 0.0 としてフェイルセーフに継続。
    - レジーム判定結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時はロールバック処理を行う。
    - OpenAI 呼び出しは独立実装によりモジュール結合を低減。

- データプラットフォーム（kabusys.data）
  - calendar_management モジュール:
    - JPX カレンダー（market_calendar）を管理するロジックを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day といった営業日判定ユーティリティを提供。
    - DB 登録値を優先し、未登録日は曜日ベースのフォールバック（週末除外）で一貫した判定を行う設計。
    - カレンダー夜間バッチ（calendar_update_job）を実装し、J-Quants クライアントから差分を取得して保存（バックフィル・健全性チェックを含む）。
    - 探索範囲上限 (_MAX_SEARCH_DAYS) を設けて無限ループを防止。
  - pipeline / etl モジュール:
    - ETL パイプラインのための ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。
    - 差分更新・バックフィル・保存（idempotent）・品質チェックの設計に対応するユーティリティを実装。
    - DuckDB に対するテーブル存在チェックや最大日付取得ロジックを追加。
    - ETL の結果を辞書化する to_dict() を提供（品質問題は簡易タプルに変換して出力）。

- Research（kabusys.research）
  - factor_research モジュール:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER, ROE）といったファクター計算を実装。
    - DuckDB の SQL ウィンドウ関数を活用して効率的に計算を行う。
    - データ不足時（必要行数未満）は None を返す方針で、安全に扱える設計。
  - feature_exploration モジュール:
    - 将来リターン計算（任意ホライズン）、IC（Spearman ランク相関）計算、ファクター統計サマリー、ランク変換ユーティリティを実装。
    - 外部依存（pandas など）を持たず標準ライブラリのみで実装。

- その他
  - OpenAI クライアント呼び出しは各モジュールで独立して実装（テスト時に差し替え可能）。
  - DuckDB を前提とした SQL ベースの計算／更新ロジックを採用。部分失敗時にも既存スコアを保護するために対象コードを絞って DELETE → INSERT を実施する実装方針を採用。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Deprecated
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- OpenAI API キーや各種トークンは環境変数から取得する設計。必須キー未設定時は ValueError を出すことで誤動作を防止。

---

注: 本 CHANGELOG はソースコードの内容に基づいて推測・要約したものです。実際のリリースノートやドキュメントは用途に応じて補完してください。