# Changelog

すべての重要な変更履歴を記録します。本ファイルは Keep a Changelog の形式に準拠しています。  

- 仕様: https://keepachangelog.com/ja/1.0.0/
- バージョン番号は Semantic Versioning を想定しています。

## [Unreleased]

## [0.1.0] - 2026-03-28
初回公開リリース。パッケージは日本株自動売買基盤（KabuSys）のコア機能群を含みます。主にデータ取得・ETL・マーケットカレンダー管理・因子計算・ニュースNLP／市場レジーム判定・環境設定まわりの実装が含まれます。

### Added
- 基本パッケージと公開 API
  - パッケージルート: kabusys (バージョン 0.1.0) を導入。
  - __all__ に data, strategy, execution, monitoring を準備。

- 環境設定と .env 自動読み込み（src/kabusys/config.py）
  - Settings クラスにより各種設定値を環境変数から取得（必須項目は取得失敗時に ValueError を投げる）。
  - 自動 .env ロード機能:
    - プロジェクトルートを .git または pyproject.toml を基準に探索して特定。
    - OS 環境変数 > .env.local > .env の優先度で読み込み。
    - .env のパースは export 形式、シングル/ダブルクォート、エスケープ、インラインコメント等に対応。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能（テスト用）。
    - OS 環境変数は protected として上書きを防止する仕組みを実装。
  - 設定項目のバリデーション（KABUSYS_ENV, LOG_LEVEL 等の有効値チェック）。
  - デフォルト値: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH など。

- ニュースNLP（src/kabusys/ai/news_nlp.py）
  - raw_news と news_symbols を元に銘柄別にニュースを集約し、OpenAI（gpt-4o-mini）の JSON モードでセンチメント評価を行う処理を実装。
  - バッチ処理（最大 20 銘柄/リクエスト）、1 銘柄あたりの最大記事数・文字数制限、スコア ±1 にクリップ。
  - 再試行ポリシー: 429（RateLimit）・ネットワーク断・タイムアウト・5xx に対する指数バックオフとリトライ。
  - レスポンスの厳密なバリデーション（JSON 抽出、results 配列の検証、数値チェック、未知コードは無視）。
  - DuckDB へは冪等的に書き込む（対象コードのみ DELETE → INSERT）し、部分失敗時に既存スコアを保護。
  - テストフック: OpenAI 呼び出しをパッチ差し替え可能（_call_openai_api のモック化を想定）。
  - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC で扱う calc_news_window）。

- 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュースセンチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等書き込み。
  - DuckDB からの価格取得は target_date 未満のデータのみを使用してルックアヘッドを防止。
  - OpenAI 呼び出しは独自実装（news_nlp と共有しない）で、API エラー時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
  - 再試行ポリシー（RateLimit・接続エラー・タイムアウト・5xx）と最大リトライ回数を実装。

- データプラットフォーム（src/kabusys/data）
  - ETL / Pipeline（src/kabusys/data/pipeline.py）
    - 差分更新のための最終取得日チェック、バックフィル（日数指定）による再取得、品質チェックのフレームワークを用意。
    - ETLResult dataclass を公開（src/kabusys/data/etl.py で再エクスポート）。
    - DuckDB のテーブル存在チェック、最大日付取得等のユーティリティを実装。
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダーの夜間バッチ更新 calendar_update_job を実装（J-Quants クライアント経由で差分取得して保存）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定 API を提供。
    - market_calendar が未取得のときは曜日ベースでフォールバック（土日を非営業日とする）。
    - 検索上限日数やバックフィル、健全性チェック（異常に未来の last_date の検出）を実装。
  - jquants_client 連携ポイント（モジュール間で呼び出す設計を想定）。

- Research（src/kabusys/research）
  - factor_research モジュール
    - モメンタム（1M/3M/6M）や ma200 乖離、ATR（20日）、20日平均売買代金・出来高比率等の計算を実装。
    - DuckDB の SQL ウィンドウ関数を多用して効率的に計算。
    - データ不足時は None を返す設計。
  - feature_exploration モジュール
    - 将来リターン calc_forward_returns（任意ホライズン対応）、IC（スピアマンランク相関）計算、ランク付け、ファクター統計サマリーを実装。
    - pandas 等に依存せず純粋 Python + DuckDB による実装。
  - zscore_normalize は data.stats から再利用可能にエクスポート。

### Fixed
- API 呼び出しや DB 書き込み失敗時のフォールバック・ロールバック処理を整備。
  - DB 書込みは BEGIN / DELETE / INSERT / COMMIT の冪等シーケンスを採用し、例外時は ROLLBACK を試行してから例外を再送出。
  - OpenAI レスポンスのパース失敗や API エラーは例外を投げずにログ出力してスキップする形に統一（システムのロバスト性向上）。

### Security
- 環境変数に関する配慮:
  - 必須 API キー（OPENAI_API_KEY, SLACK_BOT_TOKEN など）は未設定時に ValueError を送出して明示的に失敗させる。
  - .env の自動ロード時に OS 環境変数を保護する protected 機能を実装。
- OpenAI API 呼び出しはタイムアウトとリトライを設定して DoS/ハングを防止。

### Notes / Known limitations
- Value ファクター: PBR・配当利回りは現バージョンで未実装（calc_value は PER と ROE のみを提供）。
- ニュース・レジーム周りは OpenAI（gpt-4o-mini）に依存。API コストや利用制限に注意。
- ETL の品質チェックモジュール（quality）は存在する前提で参照しているが、詳細実装は別モジュールに依存。
- DuckDB 特有の executemany の空リスト制約への対処を盛り込んでいる（互換性対策）。
- 日付処理はすべて date / naive datetime を使用し、タイムゾーン混入を避ける設計。

---

（今後のリリースでは、バグ修正・API 互換性改善・追加ファクター・運用監視機能の強化などを記載予定）