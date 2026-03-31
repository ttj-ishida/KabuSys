# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

※注: 内容はソースコードから推測して作成したリリースノートです。

## [Unreleased]

## [0.1.0] - 2026-03-31
初回リリース。本リポジトリは日本株自動売買システム「KabuSys」の基盤ライブラリ群を提供します。主な追加点は以下の通りです。

### Added
- パッケージ基礎
  - パッケージ名を kabusys として公開。トップレベルで data / strategy / execution / monitoring モジュールを想定してエクスポート（__all__ に登録）。
  - バージョン情報を `__version__ = "0.1.0"` として設定。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを提供。
  - 自動 .env ロード機能を実装（プロジェクトルートは .git または pyproject.toml から探索）。
  - .env パーサーは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント（条件付き）等を考慮。
  - 自動ロードを環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - 必須設定取得用の `_require`、ログレベル・実行環境（development/paper_trading/live）等の検証ロジックを提供。
  - デフォルトの API ベース URL やデータベースパス（duckdb/sqlite）のデフォルト値を設定。

- データプラットフォーム（kabusys.data）
  - ETL パイプラインインターフェース: `ETLResult` を公開（data.pipeline）。
  - market_calendar（マーケットカレンダー）管理（calendar_management）
    - 営業日判定（is_trading_day）、前後営業日取得（next_trading_day / prev_trading_day）、
      期間内営業日取得（get_trading_days）、SQ日判定（is_sq_day）等のユーティリティを実装。
    - DB 未取得時の曜日ベースのフォールバック、最大探索範囲制限 (_MAX_SEARCH_DAYS) の導入。
    - 夜間バッチジョブ `calendar_update_job` により J-Quants API からの差分取得/保存（バックフィル・健全性チェック含む）を実装。
  - ETL パイプライン（pipeline）
    - 差分更新、IDEMPOTENT な保存（jquants_client 経由）、品質チェック（quality）統合の設計。
    - ETL 実行結果を表す `ETLResult` データクラス（品質問題のシリアライズ、エラー有無判定プロパティ等）を実装。
    - DuckDB のテーブル存在チェックや最大日付取得ユーティリティを提供。

- AI（kabusys.ai）
  - ニュース NLP スコアリング（news_nlp）
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）で銘柄ごとのセンチメント（-1.0〜1.0）を算出して ai_scores テーブルへ書き込むワークフローを実装。
    - タイムウィンドウ（JST 前日15:00 ～ 当日08:30、内部は UTC naive）計算と記事トリム（記事数・文字数上限）の実装。
    - バッチ（最大20銘柄）単位での API 呼び出し、429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ実装。
    - API レスポンスの厳密なバリデーション（JSON 抽出、results 配列、コード整合、数値検査）とスコアクリップ。
    - DuckDB の executemany 制約を考慮した安全な DB 書き換え（部分失敗時は他コードを保護）。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能に設計（内部の _call_openai_api を patch で差替え可）。
  - 市場レジーム判定（regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news を参照、LLM（gpt-4o-mini）呼び出しは JSON Mode を利用。失敗時は安全に macro_sentiment=0.0 へフォールバック。
    - 計算結果を market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK を試行）。
    - ルックアヘッドバイアス防止のため内部で datetime.today() 等を参照しない設計。

- リサーチ（kabusys.research）
  - ファクター計算（factor_research）
    - Momentum（1M/3M/6M リターン、ma200 乖離）、Volatility（20日 ATR、相対 ATR、出来高指標）、Value（PER、ROE）等の計算関数を実装。
    - DuckDB 上の SQL ウィンドウ関数を利用し、各関数は prices_daily / raw_financials のみを参照。
    - データ不足時の None 処理やログ出力に対応。
  - 特徴量探索（feature_exploration）
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic：Spearman の ρ）、統計サマリー（factor_summary）、ランク変換ユーティリティ（rank）を実装。
    - Pandas 等に依存せず標準ライブラリで実装。

- 再エクスポート / ユーティリティ
  - research パッケージの __init__ で一部関数をまとめてエクスポート（zscore_normalize の再エクスポート等）。
  - data.etl モジュールから ETLResult を再エクスポート。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは引数で注入可能かつ環境変数（OPENAI_API_KEY）から読み取る設計。未設定時は ValueError を発生させて明示的に失敗。

### Design / Implementation Notes（重要な設計上の注意）
- ルックアヘッドバイアス防止: AI/リサーチ関連の関数は datetime.today() / date.today() を内部参照せず、すべて呼び出し側が target_date を明示的に渡す方式を採用。
- フェイルセーフ: 外部 API（OpenAI / J-Quants）呼び出し失敗時は部分的に 0.0 や空結果で継続する実装が多く、安全に運用できるよう配慮。
- DuckDB 互換性: executemany の空リスト禁止など DuckDB のバージョン差に対する対策を実装。
- タイムゾーン扱い: ニュース収集は UTC naive datetime を使用して比較。JST/UTC の変換ロジックを明示している。
- API 呼び出しのリトライ戦略: 429・ネットワーク断・タイムアウト・5xx 等を対象に指数バックオフでリトライし、それ以外のエラーはスキップして継続する方針。
- DB 書き込みは冪等性を重視（DELETE→INSERT パターン、ON CONFLICT 方針など）。

---

今後のリリースでは、strategy / execution / monitoring 周りの具体的な実装（売買ロジック、注文実行、監視アラート連携など）や、テストカバレッジ／CI 設定、ドキュメント追加を予定しています。