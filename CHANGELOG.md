# Changelog

すべての重要な変更はこのファイルに記載します。フォーマットは「Keep a Changelog」に準拠しています。  
リリースはセマンティックバージョニングに従います。

## [Unreleased]

（現在未リリースの変更なし）

## [0.1.0] - 2026-04-01

初回リリース。日本株自動売買システム「KabuSys」の基盤的なモジュール群を実装しました。主な追加・仕様は以下の通りです。

### Added
- パッケージ初期化
  - kabusys パッケージの初期化（src/kabusys/__init__.py）。バージョンは 0.1.0。公開 API として data, strategy, execution, monitoring をエクスポート。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を自動読み込みする機能を実装（プロジェクトルートは .git または pyproject.toml で探索）。
  - .env ファイルのパースは export 形式、クォート（シングル/ダブル）のエスケープ、行内コメント処理等に対応。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB /監視 /システム設定等のプロパティを提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, DUCKDB_PATH など）。
  - env 値（KABUSYS_ENV）とログレベル（LOG_LEVEL）のバリデーションを追加（許容値以外は ValueError を送出）。

- AI 関連（src/kabusys/ai）
  - ニュースNLP（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を元に銘柄毎にニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメントスコアを ai_scores テーブルへ書き込む。
    - バッチ化（最大 20 銘柄 / API コール）、トークン肥大対策（記事数・文字数制限）、レスポンスバリデーション（JSON 抽出・型チェック・既知コードのみ許容）を実装。
    - 429/ネットワーク/タイムアウト/5xx に対して指数バックオフのリトライ処理を実装。失敗時は該当チャンクをスキップして他チャンクの処理を継続するフェイルセーフ設計。
    - ルックアヘッドバイアス対策として datetime.today()/date.today() を外部参照せず、target_date ベースのウィンドウで処理。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、日次で market_regime テーブルへ冪等的に書き込む。
    - マクロキーワードで raw_news をフィルタし、OpenAI（gpt-4o-mini）へ送信してマクロセンチメントを算出。API エラー時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - LLM 呼び出しは独立実装でモジュール間の結合を避ける設計。

- Data（src/kabusys/data）
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを基に営業日判定、翌/前営業日の算出、期間内営業日リスト取得、SQ判定等のユーティリティを実装。
    - DB が未取得または日付未登録のときは曜日ベース（土日を非営業日）でフォールバックする一貫したロジックを採用。
    - calendar_update_job を実装し、J-Quants から差分取得・バックフィル（直近数日）・健全性チェックを行い冪等保存する処理を提供。

  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを公開。差分取得・保存・品質チェックを想定した結果格納構造を用意。
    - 差分更新や backfill を考慮した定数・ユーティリティを実装（初回ロード用の最小日付など）。

- Research（src/kabusys/research）
  - factor_research モジュール（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M、MA200乖離）、Volatility（20日ATR、相対ATR、平均売買代金、出来高比率）、Value（PER, ROE）などのファクター計算を実装。DuckDB の SQL ウィンドウ関数を活用。
    - データ不足時の None 処理やログ出力、結果を (date, code) ベースの dict リストで返す仕様。
  - feature_exploration モジュール（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）、IC（Spearman の ρ）計算、ランク変換、ファクター統計サマリーを実装。
    - 外部依存を使わず標準ライブラリで実装。入力検証（horizons の範囲等）あり。

- 研究ユーティリティ再エクスポート（src/kabusys/research/__init__.py）
  - 主要な関数（calc_momentum, calc_value, calc_volatility, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）を公開。

### Changed
- 設計方針の明文化
  - 多くのモジュールで「ルックアヘッドバイアス禁止」の方針を明示し、target_date ベースで計算する実装に統一。
  - OpenAI API 呼び出しに対して JSON Mode を利用し、レスポンスの堅牢な検証とクリッピングを導入。

### Fixed / Robustness
- API 耐障害性の強化
  - OpenAI 呼び出しに対して 429/ネットワーク障害/タイムアウト/5xx の扱いを統一的にリトライ（指数バックオフ）する実装を追加。回復不能な場合は警告を出してフェイルセーフ（0 やスキップ）で継続する。
  - DuckDB への書き込みはトランザクション（BEGIN/DELETE/INSERT/COMMIT）で冪等に実行し、失敗時は ROLLBACK を試みる。ROLLBACK 自体が失敗した場合は警告出力。

- .env パーサーの堅牢化
  - export プレフィックス、クォート内のバックスラッシュエスケープ、行末コメントの扱い等を細かく処理し、意図しない値の読み込みを防止。

### Security / Requirements
- OpenAI API キー
  - score_news / score_regime 等の AI 関数は api_key 引数または環境変数 OPENAI_API_KEY によるキー解決を行い、未設定時は ValueError を送出する（明示的なエラー設計）。
- 環境変数の保護
  - .env ロード時は既存 OS 環境変数を保護（上書き防止）しつつ、.env.local により上書き可能な仕組みを採用。

### Notes / Migration
- 初期化時に .env を自動ロードする挙動があるため、テストや CI 環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを抑止してください。
- OpenAI を利用する機能を使う場合は事前に OPENAI_API_KEY を環境変数に設定するか、各関数に api_key を明示的に渡してください。
- DuckDB を使用した設計のため、本コードを動かすには DuckDB と対応するテーブルスキーマ（prices_daily, raw_news, ai_scores, market_regime, raw_financials, news_symbols, market_calendar 等）が必要です。
- ai モジュールは外部 API 呼び出しを伴うため、API コール回数やバッチサイズ（デフォルト 20）などは運用に応じて調整してください。

---

開発・運用中に追加の変更やバグ修正が発生したら、本CHANGELOGに逐次追記してください。