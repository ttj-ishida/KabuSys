# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトのバージョンは src/kabusys/__init__.py の __version__ に合わせています。

## [Unreleased]

- （なし）

## [0.1.0] - 2026-03-31

Added
- パッケージ基本構成を追加
  - kabusys パッケージエントリ（__all__ に data, strategy, execution, monitoring を公開）。
- 設定管理モジュールを追加（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを提供。
  - 自動ロード順序: OS 環境変数 > .env.local > .env。プロジェクトルートは .git または pyproject.toml により探索。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト向け）。
  - .env のパース機能を実装（export 形式対応、シングル/ダブルクォート内のエスケープ対応、インラインコメント処理等）。
  - 必須設定取得用の _require と各種プロパティを定義（J-Quants / kabu API / Slack / DB パス / 監視閾値 / 環境判定など）。
  - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL 等）。

- AI 関連モジュールを追加（kabusys.ai）
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI の gpt-4o-mini（JSON Mode）で銘柄ごとのセンチメントを計算。
    - バッチ処理（最大 20 銘柄/コール）、1銘柄あたりの記事数/文字数の上限トリム、レスポンス検証・スコアクリップ（±1.0）。
    - 再試行（429/ネットワーク/タイムアウト/5xx）を指数バックオフで実施。失敗時はフォールバックしてスキップ（例外を上げず継続）。
    - スコア保存処理は部分失敗時に既存スコアを保護するため、対象コードのみ DELETE→INSERT する冪等実装。
    - テストしやすさのため _call_openai_api をモック差替え可能。
    - calc_news_window により JST ベースの収集ウィンドウ（前日 15:00 ～ 当日 08:30 JST / UTC で前日 06:00 ～ 23:30）を計算（ルックアヘッドバイアス対策として datetime.today() を参照しない設計）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して market_regime テーブルへ書き込み。
    - LLM は gpt-4o-mini を利用（JSON 出力を期待）。API 呼び出しはリトライ・バックオフを行い、失敗時は macro_sentiment=0.0 として継続するフェイルセーフを実装。
    - prices_daily / raw_news のクエリは target_date 未満のデータのみを使用してルックアヘッドを防ぐ。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等操作。失敗時は ROLLBACK を試行して例外を上位へ伝播。

- データプラットフォーム関連（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX マーケットカレンダーの夜間バッチ更新ジョブ（calendar_update_job）と営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を提供。
    - market_calendar 未取得時は曜日ベース（土日休）でフォールバック。DB 登録値優先で一貫した挙動を実現。
    - バックフィル、健全性チェック、最大探索日数制限を導入し無限ループや異常値を防止。
  - ETL / パイプライン基盤（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult データクラスを公開（ETL 実行結果・品質問題・エラー等を格納）。
    - 差分更新・バックフィル・品質チェックの設計方針を実装（J-Quants クライアント経由で差分取得し冪等保存）。
    - DuckDB を用いたテーブル存在チェックや最大日付取得ユーティリティ等を提供。
  - jquants_client との連携を想定した設計（fetch/save 関数を利用）。

- リサーチ / ファクター群（kabusys.research）
  - factor_research
    - Momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日MA乖離）を計算。データ不足時は None を返す。
    - Volatility: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
    - Value: raw_financials から EPS/ROE を組み合わせて PER/ROE を計算（EPS 0 や欠損時は None）。
    - DuckDB 上で SQL+ウィンドウ関数を使い効率的に計算。すべて prices_daily / raw_financials のみ参照。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns: 指定ホライズンまでのリターンを一度のクエリで取得）。
    - IC（Information Coefficient）計算（スピアマンのランク相関）、ランク化ユーティリティ（ties は平均ランク）、統計サマリー（count/mean/std/min/max/median）。
    - pandas 等に依存せず標準ライブラリのみで実装。

- その他
  - DuckDB ベースのクエリ実行を前提とした設計／ロギング（各モジュールで適切な情報ログ・警告ログを出力）。
  - テスト容易性のため一部内部 API（_call_openai_api 等）をモック差替え可能に実装。

Fixed
- 初版リリース（0.1.0）として上記機能を実装。

Security
- OpenAI API キーは明示的に引数で渡すか OPENAI_API_KEY 環境変数で設定する必要がある旨をドキュメント化（未設定時は ValueError を発生）。
- .env の読み込みでは OS 環境変数を保護するため読み込み順や上書き制御（protected set）を実装。

Known issues / Notes
- AI モジュールは外部 API（OpenAI）に依存するため、利用には適切な API キーとネットワーク環境が必要。API 失敗時は安全側のフォールバック（スコア 0.0 / スキップ）を行う設計。
- news_nlp の応答を厳密に JSON として期待するが、稀に前後に余計なテキストが入る場合があり、その場合は文字列から最外の {} を抽出して再パースする処理を実装している。
- ETL / pipeline の一部ユーティリティは DuckDB のバージョン差分（executemany の空配列許容など）に配慮した実装になっている。
- ルックアヘッドバイアス防止のため、各モジュールは内部で date.today()/datetime.today() を直接参照しない設計になっている（target_date を引数で与える必要がある）。

移行・利用メモ
- 初期設定は .env.example を参照して .env/.env.local をプロジェクトルートに配置してください。
- 自動 .env ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しをテスト環境でモックする場合は各モジュール内の _call_openai_api を patch してください（コメントにモック方法を記載）。
- DuckDB 接続オブジェクトを各関数に渡して利用してください（関数は DuckDB 接続上のテーブルを前提としています）。

参考
- バージョンは src/kabusys/__init__.py の __version__ = "0.1.0" に合わせています。