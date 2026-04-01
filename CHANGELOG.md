# CHANGELOG

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠します。  
各リリースは日付順（新しい順）に記載します。

URL/参照: リポジトリ内の src/kabusys 以下のコードを基に作成しています。

## [Unreleased]
- 今後のリリースに向けた未反映の変更点はありません。

## [0.1.0] - 2026-04-01
初回公開リリース。システムのコア機能一式を実装しています（データ取得・ETL・カレンダー管理・研究用ファクター計算・ニュースNLP・市場レジーム判定・設定管理など）。

### Added
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = 0.1.0）。
  - パッケージ public API を示す __all__ を定義（data, strategy, execution, monitoring）。

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env ロード機能（プロジェクトルートを .git / pyproject.toml で検出）。
  - .env の読み込みは優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能。
  - .env パーサーは export KEY=val 形式、クォーテーション・バックスラッシュエスケープ、コメント処理（空白の直前にある # をコメントとみなす）に対応。
  - 環境変数保護（override フラグと protected セット）により OS 環境変数を誤って上書きしない実装。
  - 各種必須設定をプロパティ化（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）。
  - ログレベル・環境（KABUSYS_ENV）に対する値検証を実装（不正値は ValueError）。

- データ / ETL（kabusys.data.pipeline / etl）
  - ETLResult データクラスを実装し、ETL 実行結果／品質問題／エラーメッセージの統合レポートを保持。
  - 差分更新・バックフィル方針を踏まえた設計。J-Quants クライアント経由での差分取得・保存を想定。
  - データ品質チェック（quality モジュール参照）を取り込むためのインフラを準備。
  - etl モジュールで ETLResult を公開（再エクスポート）。

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - JPX カレンダー管理：market_calendar テーブルの夜間更新処理（calendar_update_job）を実装。
  - 営業日判定ユーティリティ群を実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
  - DB 登録値を優先し、未登録日は曜日ベース（週末除外）でフォールバックする一貫したロジック。
  - バックフィル、先読み、健全性チェック（過剰に未来の日付の検出）を実装。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を基に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini、JSON mode）へバッチ送信してセンチメント（ai_scores）を算出・保存する機能を実装。
  - 時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ（calc_news_window）。
  - バッチ送信（最大 20 銘柄/チャンク）、トークン肥大化対策（1銘柄あたり記事数上限・文字数トリム）。
  - API エラー（429, 接続断, タイムアウト, 5xx）に対する指数バックオフとリトライ実装。致命的でないエラーはスキップして継続（フェイルセーフ）。
  - レスポンスの堅牢なバリデーション（JSON 抽出・results 検証・コード照合・スコアの数値検証・クリップ ±1.0）。
  - DuckDB への冪等的書き込み（DELETE→INSERT、部分失敗時に他銘柄の既存スコアを保護）。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225 連動型）200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を組み合わせて日次で市場レジーム（bull / neutral / bear）を算出。
  - マクロキーワード一覧を用いた raw_news フィルタリング、最大記事数制限、OpenAI 呼び出し（gpt-4o-mini）。
  - LLM 呼び出し失敗時は macro_sentiment = 0.0 としてフェイルセーフで継続。
  - DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。

- 研究用ユーティリティ（kabusys.research）
  - ファクター計算（factor_research）:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から財務指標（PER, ROE）を取得して計算。
  - 特徴量探索（feature_exploration）:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: スピアマンランク相関（IC）を計算（有効レコードが 3 件未満なら None）。
    - rank: 平均ランク処理（同順位は平均ランク）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
  - zscore_normalize を data.stats から再エクスポート（research パッケージで使用可能）。

- その他
  - OpenAI クライアントの呼び出しラッパーを各モジュールで定義し、テスト時に差し替え可能に設計（unittest.mock.patch を想定）。
  - DuckDB を主要なローカル分析 DB として全面的に利用。

### Changed
- なし（初回リリースのため既存機能の変更はありません）。

### Fixed
- なし（初回リリース）。

### Security
- なし（公開範囲に影響する既知のセキュリティ修正はありません）。  
  - ただし、環境変数の取り扱い・自動読み込みは慎重に扱う設計（protected セット、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）を採用しています。

### Known issues / Notes
- 一部モジュール（例: kabusys.data.__init__）は将来的にエクスポート内容を拡充する想定です。
- OpenAI API 呼び出しは gpt-4o-mini を想定して実装されています。API のバージョン/仕様変更や利用制限に対してはアダプタの調整が必要になる場合があります。
- ETL / pipeline モジュールは J-Quants クライアント（kabusys.data.jquants_client）と quality モジュールに依存します。これらクライアント実装と API キー設定（環境変数）により挙動が変わります。
- 日付やウィンドウ計算はルックアヘッドバイアス回避のため、内部で datetime.today() や date.today() を参照しない方針で実装されています。テスト・再現性のためには target_date を明示的に指定してください。

### Migration / Usage notes
- OpenAI を使用する機能（score_news, score_regime）を利用するには環境変数 OPENAI_API_KEY を設定するか、api_key 引数で明示的に渡してください。未設定の場合は ValueError が発生します。
- .env 自動読み込みはプロジェクトルートの検出に依存します。パッケージ環境下でテストする際は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを抑制できます。
- DuckDB のパスは Settings.duckdb_path（デフォルト data/kabusys.duckdb）で指定できます。既存 DB に対する操作はバックアップを推奨します。

---

今後のリリースでは、ドキュメントの充実、テストカバレッジの拡大、外部 API エラーハンドリングの詳細改善、監視・実行周りの実装拡張（execution/monitoring パッケージの具現化）を予定しています。