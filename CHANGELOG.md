# Changelog

すべての重要な変更は Keep a Changelog のガイドラインに従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

注意: 本 CHANGELOG は与えられたコードベースの内容から実装意図・機能を推測して作成した初期リリース記録です。

## [unreleased]

## [0.1.0] - 2026-04-09
初回公開リリース。

### Added
- パッケージ基盤
  - kabusys パッケージを追加。__version__="0.1.0" としてリリース。
  - パッケージ外部公開 API を __all__ で整理 (data, strategy, execution, monitoring)。

- 環境設定/ロード機能 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - 自動ロード順序: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - プロジェクトルート検出は .git または pyproject.toml を起点に行い、CWD に依存しない実装。
  - .env パーサを実装:
    - 空行やコメント行を無視。
    - export KEY=val 形式をサポート。
    - シングル/ダブルクォート内のバックスラッシュエスケープを考慮した値抽出。
    - クォートなしの場合はインラインコメント（#）処理の取り扱いを改善。
  - _load_env_file にて protected（既存の OS 環境変数）を保護しつつ override の挙動を制御。
  - Settings クラスを追加し、アプリケーション設定値をプロパティとして提供:
    - J-Quants / kabuステーション / LINE / DB パス / 監視閾値 / システム設定等を取得するプロパティを実装。
    - 必須環境変数未設定時は _require が ValueError を投げて明確化。
    - PAPER_FILL_MODE のバリデーション（instant|partial|never|reject）を追加。
    - KABUSYS_ENV と LOG_LEVEL の許容値検証を実装（不正値は ValueError）。

- AI モジュール (kabusys.ai)
  - news_nlp モジュール:
    - raw_news と news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode を使ってセンチメントを計算。
    - 時間ウィンドウの計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window として実装。
    - バッチ処理（最大 20 銘柄/コール）、1銘柄あたり記事数・文字数の上限（トリム）付き。
    - 再試行ポリシー: 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ。
    - レスポンスの厳密バリデーションと JSON 復元処理（前後余計なテキストが混じった場合の最外 {} 抽出）。
    - スコアを ±1.0 にクリップ。部分失敗時に既存スコアを保護するため、取得できたコードのみ DELETE→INSERT で置換する実装。
    - テスト容易性のため _call_openai_api を差し替え可能に実装。
  - regime_detector モジュール:
    - ETF 1321 の 200 日移動平均乖離 (ma200_ratio) と macro ニュースの LLM センチメントを重み付き合成（MA 70% / Macro 30%）して市場レジーム（bull/neutral/bear）判定を行う。
    - LLM 呼び出し（gpt-4o-mini / JSON Mode）の再試行とフェイルセーフを実装。API 失敗時は macro_sentiment=0.0 にフォールバック。
    - ルックアヘッドバイアス防止のため、prices_daily クエリは target_date 未満のデータのみ使用。datetime.today()/date.today() を直接参照しない設計。
    - 結果は market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）する。
    - テスト用に _call_openai_api を差し替え可能に実装。

- Research モジュール (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から EPS/ROE を取得し PER/ROE を算出（EPS が 0/欠損なら None）。
    - 計算は DuckDB( prices_daily / raw_financials) の SQL ウィンドウ関数中心で実装。データ不足時は None を返す。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一回のクエリで取得。horizons のバリデーションあり。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。十分なサンプルがない場合は None。
    - rank: 同順位は平均ランクになるよう実装（丸め処理で ties の検出精度向上）。
    - factor_summary: count/mean/std/min/max/median を算出するユーティリティ。
  - research パッケージはデータ処理ユーティリティ（zscore_normalize 等）を再公開。

- Data モジュール (kabusys.data)
  - calendar_management:
    - JPX カレンダー管理機能を実装（market_calendar テーブルを前提）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - DB にカレンダーが存在しない場合は曜日ベースのフォールバック（平日を営業日）を使用。
    - next/prev/get の実装は DB 登録を優先しつつ未登録日は曜日フォールバックで一貫した挙動を示す。
    - calendar_update_job: J-Quants API（jquants_client）から差分取得し、バックフィルや健全性チェックを行って market_calendar を更新。
  - pipeline / etl:
    - ETLResult dataclass を追加し、ETL 実行結果（取得数・保存数・品質問題・エラー）を構造化。
    - ETL の設計方針（差分更新、バックフィル、品質チェックの扱い、id_token 注入可能性等）をコメントで明示。
  - etl モジュールは pipeline.ETLResult を公開して再利用可能にした。

### Changed
- （初回リリースのため変更履歴なし）

### Fixed
- （初回リリースのため修正履歴なし）

### Deprecated
- （初回リリースのためなし）

### Removed
- （初回リリースのためなし）

### Security
- OpenAI API キーの取り扱い:
  - 各 AI モジュールは api_key 引数を受け取り、未指定時は環境変数 OPENAI_API_KEY を参照する。未設定時は ValueError を投げて明確化。
  - .env 自動ロード時に OS 環境変数は protected として保持する実装により、テストや運用における意図しない上書きを防止。

---

今後の更新で想定される改善点（例）
- strategy / execution / monitoring の具体実装（本リリースではパッケージ構成のみ）。
- 単体テスト・統合テストの追加（特に OpenAI 呼び出し周りのモック）。
- jquants_client / kabusys.data.jquants_client の詳細実装とテスト。
- ドキュメント（README、API リファレンス、設計ドキュメント）の拡充。