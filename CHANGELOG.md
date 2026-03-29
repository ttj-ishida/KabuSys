# Changelog

すべての注目すべき変更点をここに記録します。  
このファイルは「Keep a Changelog」仕様に準拠しています。  

- リリース方針: 破壊的変更が発生した場合はメジャー番号を上げます。  
- 日付はパッケージ初期リリース日（推定）を使用します。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-29
初期リリース — KabuSys の基本コンポーネントを実装しました。主に日本株のデータ取得／ETL、マーケットカレンダー管理、ファクター計算、ニュースのAI解析、及び市場レジーム判定の機能を提供します。

### Added
- パッケージメタ
  - パッケージバージョン管理: `src/kabusys/__init__.py` に `__version__ = "0.1.0"` を追加。
  - パッケージの公開 API (`__all__`) を定義（data, strategy, execution, monitoring）。

- 設定・環境変数管理
  - `kabusys.config` モジュールを追加。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）を実装し、CWD に依存しない .env 自動読み込みを実現。
    - `.env` / `.env.local` の読み込み優先順位（OS 環境変数 > .env.local > .env）と上書き保護機能（既存 OS 環境変数を保護）を実装。
    - `.env` パーサを独自実装：コメント行、export 先頭表記、シングル/ダブルクォート内のエスケープ、インラインコメント処理などに対応。
    - 自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - 必須設定取得ヘルパ `_require` と、アプリ設定をプロパティアクセスで提供する `Settings`（例: `settings.jquants_refresh_token`, `settings.slack_bot_token`, `settings.kabu_api_password`）。
    - `KABUSYS_ENV` と `LOG_LEVEL` のバリデーション（許容値チェック）を実装。

- AI（自然言語処理）
  - `kabusys.ai.news_nlp` を追加。
    - ニュース記事を銘柄ごとに集約し、OpenAI（gpt-4o-mini）に対してバッチでセンチメント解析を行い、結果を `ai_scores` テーブルに書き込むワークフローを実装。
    - バッチサイズ、記事数・文字数の上限、JST→UTC ウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST の記事）を実装。
    - JSON Mode を利用した厳密なレスポンス期待と、レスポンスの頑健なバリデーション実装（JSON 抽出、results 構造チェック、既知コードのみ採用、数値チェック、±1.0 のクリップ）。
    - リトライ戦略（429・ネットワーク断・タイムアウト・5xx）を指数バックオフで実装。フェイルセーフとして失敗時は対象銘柄をスキップして他銘柄を継続処理。
    - テストの容易性のため OpenAI 呼び出し箇所を差し替え可能（モジュール内プライベート関数の patch を想定）。

  - `kabusys.ai.regime_detector` を追加。
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）と、ニュース由来の LLM マクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - prices_daily と raw_news を参照し、適切な時間ウィンドウでデータを取得（ルックアヘッド回避設計）。
    - OpenAI 呼び出しは独立実装、API エラー時は macro_sentiment=0.0 にフォールバック（継続的動作保証）。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）を行う実装。

- データプラットフォーム（Data）
  - `kabusys.data.calendar_management` を追加。
    - JPX カレンダーの取得・保存ロジック、営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。
    - market_calendar が未取得の場合は曜日ベースのフォールバック（週末を非営業日）を採用し、DB 登録があれば DB 値を優先する一貫した挙動。
    - 夜間バッチ更新 job（calendar_update_job）を実装。J-Quants クライアント経由で差分取得し保存、バックフィル・健全性チェックを実装。

  - `kabusys.data.pipeline` を追加。
    - ETL の差分取得・保存・品質チェックフレームワークを実装。
    - ETL 結果を格納する dataclass `ETLResult` を提供（フェッチ数・保存数・品質問題リスト・エラーメッセージ等を含む）。
    - jquants_client と quality モジュールと連携する設計（idempotent な保存・バックフィル・品質チェックは継続収集方式）。

  - `kabusys.data.etl` で ETLResult を再エクスポート。

  - DuckDB を主な永続層として利用する設計（SQL クエリとウィンドウ関数を多用）。

- リサーチ（因子・特徴量）
  - `kabusys.research.factor_research` を追加。
    - Momentum (1M/3M/6M リターン、200 日 MA 乖離)、Volatility (20 日 ATR 等)、Value (PER / ROE) の計算関数を実装（prices_daily / raw_financials 使用）。
    - データ不足時の挙動（必要行数未満で None を返す）を明確化。
  - `kabusys.research.feature_exploration` を追加。
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク変換（rank）、統計サマリー（factor_summary）等を実装。
    - スピアマンランク相関（ランクへの変換は同順位の平均ランクを採用）と、ties を考慮した実装。

- その他ユーティリティ
  - 各モジュールで「ルックアヘッドバイアス防止」を設計方針として徹底（datetime.today()/date.today() の呼び出しを直接参照しない箇所が注記されている）。
  - OpenAI 呼び出しを直接行う箇所は（単体テストのため）差し替え可能な実装とした点を明記。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- OpenAI API キーは引数で注入可能か環境変数（OPENAI_API_KEY）を参照する仕様とし、キーの扱いに配慮した設計になっています。環境ファイル自動読み込みはプロセス環境を上書きしない（既存 OS 環境変数を保護）デフォルトになっています。

### Notes / Migration
- 必須環境変数（例）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は `settings` 経由で参照され、未設定時はエラーを送出します。`.env.example` を参考に `.env` を用意してください。
- DuckDB スキーマ（prices_daily, raw_news, ai_scores, market_calendar, raw_financials 等）が前提です。テストや初期ロード時は ETL パイプラインをご利用ください。
- OpenAI 呼び出し部分はテスト容易性のためモック可能です（各モジュール内の `_call_openai_api` を差し替えられます）。

---

今後の予定（想定）
- strategy / execution / monitoring に関連する実行系モジュールの実装強化（現状はパッケージ公開シンボルとして存在）。
- 品質チェック（quality モジュール）や jquants_client の具体実装との統合テスト強化。
- ドキュメント・運用ガイド（例: ETL スケジュール、監視アラート設定、Slack通知ワークフロー）の追加。