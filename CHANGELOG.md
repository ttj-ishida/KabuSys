# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
このプロジェクトの現行バージョンは 0.1.0 です。

※日付はパッケージの初期リリース日として 2026-03-29 を付与しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-29

### Added
- 初回リリース。日本株自動売買システム「KabuSys」のコアモジュールを導入。
  - パッケージエントリポイント `kabusys`（src/kabusys/__init__.py）を追加し、サブパッケージを公開（data, research, ai, monitoring, strategy, execution などを想定）。
- 環境設定管理モジュール（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルート検出は .git または pyproject.toml を基準）。
  - export 形式 / クォート / インラインコメント等に対応した .env パーサー実装。
  - OS 環境変数を保護する仕組み（.env.local は既存変数上書き、ただし OS 環境変数は protected）。
  - 設定値を取得する `Settings` クラスを提供（J-Quants / kabu API / Slack / DBパス / 環境モード / ログレベル等）。
  - 必須環境変数未設定時は明確な例外メッセージを返す `_require` 関数を実装。
  - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。
- AI モジュール（src/kabusys/ai）
  - ニュースNLP（news_nlp.py）
    - raw_news と news_symbols を元に銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを算出して `ai_scores` テーブルへ書き込む `score_news` を実装。
    - タイムウィンドウ計算（JST 前日 15:00 ～ 当日 08:30）を行う `calc_news_window` を実装。
    - バッチ（銘柄最大 20 件）での API 呼び出し、トークン肥大化対策（記事数・文字数制限）、レスポンス検証とスコアクリップを実装。
    - リトライ（429 / ネットワーク断 / タイムアウト / 5xx）向け指数バックオフ、フェイルセーフ動作（API 失敗時はスキップし処理継続）。
    - テスト容易性のため OpenAI 呼び出し箇所を差し替え可能（内部 `_call_openai_api` をモック可能）。
  - 市場レジーム判定（regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成し、日次で市場レジーム（bull/neutral/bear）を算出する `score_regime` を実装。
    - prices_daily / raw_news を参照し、計算後に `market_regime` テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を行う。
    - API キー解決、OpenAI 呼び出し、リトライ、JSON パースエラー時のフォールバック（macro_sentiment=0.0）等に対応。
- Data モジュール（src/kabusys/data）
  - カレンダー管理（calendar_management.py）
    - JPX カレンダーの管理ロジックを提供：営業日判定、next/prev_trading_day、get_trading_days、is_sq_day、および夜間バッチ更新 `calendar_update_job`。
    - market_calendar 未取得時は曜日ベースのフォールバック（土日を休場と扱う）。
    - 最大探索日数の上限、バックフィル、健全性チェックを実装。
    - J-Quants クライアント経由で差分フェッチ→冪等保存する仕組みを想定。
  - ETL パイプライン（pipeline.py / etl.py）
    - ETL 結果を表す `ETLResult` データクラスを実装（取得件数、保存件数、品質チェック結果、エラー一覧などを保持）。
    - 差分更新・バックフィル方針、品質チェックの扱い（重大度に応じた判定）を設計に組み込んだインターフェースを提供。
    - etl モジュールで `ETLResult` を再エクスポート。
- Research モジュール（src/kabusys/research）
  - ファクター計算（factor_research.py）
    - Momentum（1M/3M/6M、ma200乖離）、Volatility（20日ATR、相対ATR、出来高比等）、Value（PER、ROE）を DuckDB の SQL と Python で計算する関数（calc_momentum, calc_volatility, calc_value）。
    - DuckDB のウィンドウ関数を多用し、データ不足時は None を返す扱いで実装。
  - 特徴量探索（feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic: スピアマンランク相関）計算、ランク変換ユーティリティ（rank）、および統計サマリー（factor_summary）を実装。
    - Pandas 等に依存せず、標準ライブラリと DuckDB で完結する設計。
  - research パッケージ初期化で主要関数を公開（zscore_normalize を kabusys.data.stats から再利用）。
- 監視・ロギング設計
  - 各モジュールで詳細な logger 呼び出しを追加。失敗時の警告/例外ログ、処理完了ログを明示。
- ドキュメント化（各モジュールに処理フロー・設計方針の docstring を充実）
  - ルックアヘッドバイアス回避の設計、DB 書き込みの冪等性、テストしやすさ（モックポイント）の意図が明記されている。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- OpenAI API キーは引数または環境変数（OPENAI_API_KEY）で注入する設計。APIキー未設定時は ValueError を発生させ、誤った動作を防止。

### Notes / Usage hints
- 必須環境変数（例）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings 経由で必須チェックが入ります。
- DB デフォルトパス
  - DuckDB: data/kabusys.duckdb（環境変数 DUCKDB_PATH で変更可）
  - SQLite（監視用）: data/monitoring.db（環境変数 SQLITE_PATH で変更可）
- 自動 .env 読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- OpenAI 呼び出しは内部で共通の wrapper を使っているが、ユニットテスト時は該当関数を patch して通信を差し替えられます（_call_openai_api の差し替えポイントあり）。

---

今後のリリースでは以下を想定しています:
- モジュール単位のユニットテスト・統合テストの追加（現状は設計でテストしやすさを配慮）
- 追加のファクター（PBR・配当利回り等）や発注・実行ロジックの実装（strategy / execution）
- ドキュメント（API 仕様書・運用手順書）の更なる整備

--- 
Keep a Changelog: https://keepachangelog.com/en/1.0.0/