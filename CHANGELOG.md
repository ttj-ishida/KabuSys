# Changelog

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは「Keep a Changelog」ガイドラインに準拠します。  

※この CHANGELOG はリポジトリ内のコードを解析して機能・設計方針・公開 API を推測して作成した初期リリース向けの記録です。

## [Unreleased]

（未リリースの変更はここに記載します）

---

## [0.1.0] - 2026-04-03

初期公開リリース。日本株自動売買プラットフォームの基礎モジュール群を実装しました。
主にデータ ETL、カレンダー管理、ファクター研究、AI を使ったニュース NLP / レジーム判定、環境設定ユーティリティを含みます。

### Added
- パッケージ基盤
  - パッケージメタ情報: kabusys バージョン `0.1.0` を定義。
  - パッケージ公開サブモジュール: data, strategy, execution, monitoring を __all__ で宣言（将来的な拡張ポイント）。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイル自動読み込み機能を追加（プロジェクトルートを .git または pyproject.toml で探索）。
  - .env/.env.local の読み込み順序と override/保護（OS 環境変数保護）を実装。
  - .env 行パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ処理、インラインコメントの扱いに対応）。
  - Settings クラスを追加し、アプリケーション設定をプロパティ経由で取得可能に：
    - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（_require により未設定時は ValueError）
    - 任意/既定値: KABU_API_BASE_URL, LINE_CHANNEL_ACCESS_TOKEN, DUCKDB_PATH, SQLITE_PATH, PID/KILL フラグパス、各種閾値、KABUSYS_ENV, LOG_LEVEL 等
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - JPX マーケットカレンダー管理関数群を実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB による優先判定と「データがない場合は曜日ベースのフォールバック」ロジックを実装。
    - calendar_update_job: J-Quants から差分取得して market_calendar を idempotent に更新する夜間バッチ処理（バックフィル・健全性チェック付き）。
  - pipeline / etl:
    - ETLResult データクラスを公開（ETL の実行統計・品質問題・エラーを収集）。
    - ETL パイプラインの基盤実装（差分取得、保存、品質チェックの方針を実装するためのユーティリティを追加）。
    - jquants_client を経由したデータ取得/保存を想定（jq.fetch_* / jq.save_* の呼び出しを行う設計を反映）。

- AI（kabusys.ai）
  - news_nlp:
    - score_news(conn, target_date, api_key=None) を実装。raw_news + news_symbols から銘柄毎に記事を集約し、OpenAI（gpt-4o-mini）でセンチメントスコア（-1.0〜1.0）を取得して ai_scores に書き込む。
    - バッチ処理（最大 20 銘柄/コール）、トークン肥大化対策（記事数・文字数トリム）、レスポンス検証・クリッピング、エクスポネンシャルバックオフによるリトライを実装。
    - テスト容易性: OpenAI 呼び出しを差し替え可能（_call_openai_api を unittest.mock.patch で置き換え可能）。
    - 時間ウィンドウ計算 calc_news_window を実装（JST 基準の前日 15:00 ～ 当日 08:30 を UTC naive datetime に変換）。
  - regime_detector:
    - score_regime(conn, target_date, api_key=None) を実装。ETF 1321 の 200 日移動平均乖離（70%）とニュースベースの LLM マクロセンチメント（30%）を合成して daily market_regime を書き込む。
    - ma200 計算、マクロ記事抽出（キーワードベース）、OpenAI 呼び出し、スコア合成、冪等 DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - API 呼び出しの失敗やパースエラー時はマクロセンチメントを 0.0 にフォールバックするフェイルセーフを採用。

- 研究用ユーティリティ（kabusys.research）
  - factor_research:
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、200 日 MA 乖離を計算。
    - calc_volatility(conn, target_date): 20 日 ATR（単純平均）、ATR 比率、平均売買代金、出来高比率を計算。
    - calc_value(conn, target_date): PER、ROE を raw_financials と prices_daily から計算（最新報告期の取得ロジック含む）。
    - 実行は DuckDB SQL を主に使用し、ローカル DB のみ参照する安全設計（発注 API などには触れない）。
  - feature_exploration:
    - calc_forward_returns(conn, target_date, horizons): 指定ホライズンの将来リターンをまとめて取得する効率的なクエリ。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンランク相関（IC）の計算（欠損・同順位処理を考慮）。
    - rank(values) と factor_summary(records, columns) を提供（標準ライブラリのみで統計量を算出）。

- 互換性・運用上の配慮
  - DuckDB を前提とした実装（DuckDB 0.10 の executemany 空リスト制約を考慮した実装を適用）。
  - DB 書き込みは冪等性を重視（DELETE → INSERT の置換戦略、ON CONFLICT 想定の保存フロー）。
  - ルックアヘッドバイアス回避のため、内部実装では datetime.today()/date.today() を直接参照しない設計（target_date を明示的に受け取る）。

### Changed
- 初期リリースのため該当なし。

### Fixed
- API 呼び出し周りの堅牢化:
  - OpenAI 呼び出しに対して 429 / ネットワーク断 / タイムアウト / 5xx に対するリトライ（指数バックオフ）を実装。
  - API レスポンスの JSON パース失敗時、期待キー欠落時はログ出力してスキップ（プロセス全体を停止させない設計）。
- 環境変数読み込み時の安全処理:
  - .env ファイルの読み込み失敗を warnings.warn で扱い例外を握りつぶす（起動停止を防止）。
  - auto load を無効化（KABUSYS_DISABLE_AUTO_ENV_LOAD）できるようにしてテスト性を向上。

### Security
- 環境変数の上書きルール:
  - 自動ロード時に OS 環境変数を保護する protected set を導入し、.env の上書きを防止（.env.local は override=True だが protected を尊重）。
- 機密情報の扱い:
  - API キー（OPENAI_API_KEY）やトークン類が未設定の場合は明示的に例外を出す箇所があるため、運用時は .env または環境変数で設定が必要。

### Notes / 必要な環境・依存
- 必要な外部ライブラリ:
  - duckdb
  - openai (OpenAI Python SDK)
- 必須環境変数（最低限）:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - OPENAI_API_KEY（score_news / score_regime を呼ぶ場合）
- 推奨設定項目（デフォルト値あり）:
  - KABUSYS_ENV (development|paper_trading|live) — デフォルト: development
  - LOG_LEVEL — デフォルト: INFO
  - DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH
  - 各種監視閾値: CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- テスト支援ポイント:
  - OpenAI 呼び出し箇所（news_nlp._call_openai_api, regime_detector._call_openai_api）を patch して実行をモック可能。
  - 環境変数自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化し単体テスト時の副作用を防げる。

---

## 未定義 / 今後の課題（メモ）
- strategy / execution / monitoring サブパッケージの実装（現在は名前空間として宣言）。
- ai モジュールのレスポンス検証強化（スキーマ検証、より細かいエラー分類）。
- ETL の具体的な差分ロジック・品質チェックルールの追加（quality モジュールとの連携強化）。
- 単体テスト・統合テストの追加（DuckDB のテストフィクスチャ、OpenAI 呼び出しのモック等）。

---

以上。必要であれば個別モジュールごとの変更点（関数一覧・公開 API サマリ）や、運用手順（環境変数の具体例、cron ジョブ例）を追記します。どの情報を優先して追加しますか？