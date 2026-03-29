CHANGELOG
=========

All notable changes to this project will be documented in this file.
このプロジェクトにおけるすべての重要な変更はこのファイルに記載します。

フォーマットは「Keep a Changelog」に準拠しています。
（https://keepachangelog.com/ja/1.0.0/）

Unreleased
----------
（未リリースの変更はここに記載します）

0.1.0 - 2026-03-29
-----------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージのトップレベル定義を追加
    - __version__ = "0.1.0"
    - __all__ = ["data", "strategy", "execution", "monitoring"]

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機能を実装
    - 読み込み順: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
    - プロジェクトルートは .git または pyproject.toml を起点に探索（CWD 非依存）
  - .env パーサを独自実装（シングル/ダブルクォート、エスケープ、コメント処理を考慮）
  - Settings クラスを追加し、環境変数からアプリケーション設定を取得
    - J-Quants / kabuステーション / Slack / DB パス / 実行環境（KABUSYS_ENV） / LOG_LEVEL 等をサポート
    - KABUSYS_ENV と LOG_LEVEL の有効値検証を実装
    - Path 型で duckdb/sqlite のデフォルトパスを返すプロパティを用意

- AI モジュール（kabusys.ai）
  - news_nlp モジュール: ニュースセンチメントのバッチ評価・ai_scores 書き込み処理を実装
    - OpenAI（gpt-4o-mini）の JSON Mode を使用
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST を対象（UTC への変換済み）
    - 1 銘柄あたり最大記事数・最大文字数でトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）
    - 1 API 呼び出しで最大 _BATCH_SIZE（20）銘柄を処理するチャンク処理
    - 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライ
    - レスポンス検証ロジックを実装（JSON 抽出、results 配列、code/score の検証、±1.0 でクリップ）
    - DuckDB の executemany に空リストを渡せない点を考慮した安全な書き込み（DELETE→INSERT）

  - regime_detector モジュール: 市場レジーム（bull/neutral/bear）判定ロジックを実装
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成
    - OpenAI（gpt-4o-mini）でマクロセンチメントを JSON 出力で取得
    - API エラー時は macro_sentiment を 0.0 として継続（フェイルセーフ）
    - 計算結果を market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）
    - DuckDB を使ったデータ取得でルックアヘッドバイアスを避ける実装（date < target_date など）

- data モジュール（kabusys.data）
  - calendar_management: JPX マーケットカレンダー管理機能を実装
    - 営業日判定: is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
    - market_calendar が未取得の場合は曜日ベース（週末除外）でフォールバック
    - calendar_update_job: J-Quants API からの差分取得・保存ロジック（バックフィル、健全性チェック、冪等保存）
    - 最大探索幅・バックフィル日数・サニティチェック等の安全機構を実装
  - pipeline / etl: ETL パイプライン用ユーティリティを実装
    - ETLResult データクラスを公開（ETL 結果、品質問題、エラーの集約）
    - 差分取得・バックフィル・品質チェックの設計に対応する支援関数を実装（内部ユーティリティ）
  - etl を通じた jquants_client 連携用インタフェースを用意（jq 経由で API を呼ぶ想定）

- research モジュール（kabusys.research）
  - factor_research: ファクター計算機能を実装
    - Momentum（1M/3M/6M リターン、ma200 乖離）、Volatility（ATR20、相対ATR）、Value（PER, ROE）等
    - DuckDB SQL ベースで計算し、結果を (date, code) をキーとする dict のリストで返却
    - データ不足時は None を返す設計（下流で扱いやすく）
  - feature_exploration: 将来リターン計算・IC（Spearman）・統計サマリー等を実装
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを計算
    - calc_ic: ランク相関（Spearman）の実装（ties の平均ランク処理を含む）
    - factor_summary / rank: 基本統計量とランク処理ユーティリティ

- パッケージ公開インターフェースの整備
  - ai.__init__ で score_news を公開
  - research.__init__ で主要関数を再エクスポート
  - data.etl で ETLResult を再エクスポート

Changed
- （初回リリースにつき該当なし）

Fixed
- （初回リリースにつき該当なし）

Deprecated
- （初回リリースにつき該当なし）

Removed
- （初回リリースにつき該当なし）

Security
- OpenAI API キーは引数経由または環境変数 OPENAI_API_KEY から取得する仕様
  - api_key が未設定の場合は ValueError を発生させ明示的に要求する設計
- .env の読み込みはデフォルトで有効だが、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 によりテスト等で無効化可能

注意事項 / マイグレーション（使用上の重要ポイント）
- 必須環境変数（起動前に設定が必要）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - OpenAI を使う機能を利用する場合は OPENAI_API_KEY を設定
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を含むフォルダ）を起点に行われるため、
  配布後やインストール環境で動作させる場合は KABUSYS_DISABLE_AUTO_ENV_LOAD の利用や明示的な環境変数設定を推奨
- DuckDB の executemany は空リストを受け付けないバージョン依存の挙動に対応済み（空の書き込みをスキップ）
- LLM を利用する処理は gpt-4o-mini を想定（モデル名は定数で変更可能）
- レスポンスパース失敗や API 停止時のフォールバック動作:
  - regime_detector: macro_sentiment = 0.0（警告ログ）として処理継続
  - news_nlp: 当該チャンクはスキップし、他チャンクの処理は継続
- ルックアヘッドバイアス対策:
  - 各種処理は内部で datetime.today()/date.today() を直接参照しないよう設計（target_date を明示的に渡す）
- DuckDB スキーマ前提:
  - 多くの関数が prices_daily / raw_news / news_symbols / ai_scores / market_regime / raw_financials / market_calendar 等のテーブル存在を前提とするため、
    実行前に適切なスキーマ・テーブルを用意してください

既知の制約・今後の改善候補
- OpenAI 呼び出しの具体的な料金・レイテンシ考慮はユーザー側の運用で調整する必要がある
- response_format に JSON モードを用いているため、将来 SDK の仕様変更があった場合に互換性の確認が必要
- jquants_client（jq）モジュールの具象実装は外部依存の想定（テスト時はモック化推奨）
- DuckDB バインドの型や日付型の扱いは環境差に注意（UTC naive な datetime を使用）

貢献・サポート
- このリリースは初期機能群の提供を目的としています。バグ報告や機能リクエストは issue にて受け付けてください。

--- 

（注）本 CHANGELOG は提示されたコードベースの内容から推測して作成しています。実際のリリース手順やドキュメントとは差異がある可能性があります。