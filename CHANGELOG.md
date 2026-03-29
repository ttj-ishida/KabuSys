# Changelog

すべての重要な変更をここに記録します。  
フォーマットは Keep a Changelog に準拠しています。  

注: リリース日や内容はコードベースから推測して記載しています。

## [Unreleased]

## [0.1.0] - 2026-03-29
初回公開リリース。日本株自動売買システムの基盤機能群を実装しました。以下の主要コンポーネントと機能を含みます。

### Added
- パッケージ初期化
  - kabusys パッケージを公開（__version__ = 0.1.0）。主要サブパッケージ: data, research, ai, monitoring, strategy, execution（__all__ に定義）。
- 設定/環境変数管理（kabusys.config）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml から探索）。
  - export KEY=val 形式やクォート付き値、行内コメント等に対応する .env パーサ実装。
  - 自動ロードの無効化用フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供し、利用しやすいプロパティで各種設定を取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL 等）。
  - env / log_level の検証（許容値チェック）と is_live / is_paper / is_dev ヘルパーを追加。
- AI（自然言語処理）モジュール（kabusys.ai）
  - news_nlp モジュール（score_news）
    - raw_news と news_symbols を元に銘柄別にニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ書き込むパイプラインを実装。
    - バッチ処理（最大 20 銘柄/コール）、トークン肥大化対策（記事数・文字数上限）、レスポンスのバリデーション、スコアの ±1.0 クリップ、部分書き換え（DELETE → INSERT）等を実装。
    - API 呼び出しのリトライ（429 / ネットワーク断 / タイムアウト / 5xx を指数バックオフでリトライ）やフェイルセーフ（失敗時は該当チャンクをスキップ）をサポート。
    - テスト容易性のため _call_openai_api を patch して差し替え可能。
    - ニュース集計ウィンドウは JST 前日 15:00 ～ 当日 08:30（内部は UTC ナイーブ日時で扱う calc_news_window を提供）。
  - regime_detector モジュール（score_regime）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を算出し、market_regime テーブルへ冪等書き込み。
    - MA 計算はルックアヘッドを防ぐため target_date 未満のデータのみ使用。
    - OpenAI 呼び出しは独立実装でリトライ／フェイルセーフ（API失敗時は macro_sentiment=0.0）。
    - 設定可能なモデル・リトライ回数等を定数で管理。
- Data（データ基盤）モジュール（kabusys.data）
  - calendar_management
    - JPX カレンダー管理、営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。
    - market_calendar がない場合は曜日（週末）ベースでフォールバックする一貫した挙動を提供。
    - calendar_update_job: J-Quants API から差分取得 → 保存（バックフィル・健全性チェック含む）を実装。
  - pipeline / etl インターフェース
    - ETLResult データクラスを公開（取得数・保存数・品質問題・エラーの集計など）。
    - ETL の補助関数（テーブル最大日付取得など）を実装。
  - jquants_client を利用する想定（fetch/save 系の外部クライアントを呼び出す設計）。
- Research（研究用）モジュール（kabusys.research）
  - factor_research
    - Momentum（1M/3M/6M リターン）、ma200 乖離、ATR（20日）などのファクター計算を実装。prices_daily のみ参照。
    - Volatility / Liquidity（avg_turnover / volume_ratio）や Value（PER / ROE を raw_financials から参照）を提供。
    - データ不足時の None 扱い等の堅牢化。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns、任意ホライズン対応、最大 252 営業日制限）。
    - スピアマン IC 計算（calc_ic）、rank（同順位の平均ランク対応）、factor_summary（count/mean/std/min/max/median）を実装。
    - pandas 等の外部依存を持たない純粋 Python + DuckDB 実装。
- DuckDB を想定した SQL 実行とデータ操作を中心に設計（各モジュールは DuckDB 接続を受け取る）。
- ロギングの利用と情報出力（処理状況やフェイルセーフ時の警告）を多数追加。

### Changed
- （初回リリースのため過去変更なし）

### Fixed
- （初回リリースのため履歴なし）

### Security
- OpenAI API キーや各種トークンは Settings 経由で環境変数から取得する実装（明示的に必須とするプロパティを用意）。
- 自動.env 読み込みで OS 環境変数を保護する仕組み（protected set）を導入し、.env.local で上書き可能だが OS 環境変数は上書かれない。

### Notes / Migration
- 必須環境変数（例）
  - OPENAI_API_KEY または score系関数に api_key を明示的に渡す必要あり（未設定時は ValueError を送出）。
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings のプロパティで必須としている。
- データベースの想定テーブル（主に以下が存在することを想定）
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar
- デフォルトファイルパス
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- 自動 .env 読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- DuckDB 実行時の executemany に空リストを渡せない制約（DuckDB 0.10 に対応）を考慮した実装になっています。

### Known issues / Limitations
- OpenAI 呼び出しに外部ネットワークが必要。API レート制限や料金等は利用者で管理してください。
- 一部機能は外部クライアント（jquants_client など）に依存します。これらの実装は別途用意する必要があります。
- 日時は多くの箇所で naive な datetime / date を使用（設計上タイムゾーンは UTC 前提や JST の換算で扱う箇所あり）。運用時は取り扱いに注意してください。
- 単体テスト用の差し替え用フック（_call_openai_api など）を用意していますが、外部 API を必要とする統合テストはモックが必要です。

---

今後の予定（例）
- strategy / execution / monitoring モジュールの詳細実装とテストカバレッジ充実
- エンドツーエンドの ETL + モデル適用パイプライン例のドキュメント追加
- OpenAI 呼び出しのコスト最適化（プロンプト最適化やローカルモデル対応検討）

もし追加で、特定ファイルごとの差分説明やリリースノートの詳細化（変更点を関数レベルで分ける等）が必要でしたらお知らせください。