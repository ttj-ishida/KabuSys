# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

注: この CHANGELOG は与えられたコードベースの内容から機能・設計方針を推測して作成しています。

## [Unreleased]
- 今後のリリースでの予定や検討中の改善点を記載します（現時点では特になし）。

## [0.1.0] - 2026-04-04
初回公開リリース。本バージョンは日本株自動売買システムのコアライブラリ群の初期実装を含みます。

### Added
- 基本パッケージ構成
  - kabusys パッケージ初期化（__version__ = 0.1.0）。公開モジュールの __all__ に data, strategy, execution, monitoring を定義。

- 環境設定 / 設定管理
  - 自動 .env 読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
  - .env / .env.local の読み込み順序と上書き動作を実装（OS 環境変数を保護可能）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化する仕組みを追加。
  - 複雑な .env パース処理を実装（export プレフィックス対応、クォート内エスケープ、コメントルール）。
  - Settings クラスを実装し、J-Quants / kabu API / LINE / データベース / 監視 / システム設定などの環境変数を型付きプロパティで提供。必須変数は _require による明確なエラーを返す。
  - 環境チェック（KABUSYS_ENV の許容値、LOG_LEVEL の許容値）を導入。

- AI（自然言語処理）モジュール
  - kabusys.ai.news_nlp
    - raw_news と news_symbols からニュースを銘柄ごとに集約し、OpenAI（gpt-4o-mini）の JSON Mode を使って銘柄別センチメント（-1.0〜1.0）を算出する機能を実装。
    - バッチ処理（最大 20 銘柄/チャンク）、1 銘柄あたり最大記事数・文字数制限、応答バリデーション、スコアクリップ（±1.0）、リトライ（指数バックオフ）等を実装。
    - タイムウィンドウ（JST 前日 15:00 ～ 当日 08:30）計算ユーティリティを提供（calc_news_window）。
    - API キー注入対応（api_key 引数または OPENAI_API_KEY 環境変数）。
    - スコア書き込みは idempotent な DELETE → INSERT（部分失敗時に他銘柄の既存データを保護）。

  - kabusys.ai.regime_detector
    - 日次で市場レジーム（bull / neutral / bear）を判定する機能を実装。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成。
    - マクロニュース抽出用キーワードリスト、最大取得記事数制限、OpenAI 呼び出しの再試行・フォールバック（API 失敗時は macro_sentiment = 0.0）を実装。
    - 判定結果を market_regime テーブルへ冪等に書き込む（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。
    - LLM 呼び出しは専用の内部実装によりモジュール結合を避ける設計。

- データ処理・ETL
  - kabusys.data.pipeline
    - ETLResult データクラスを実装（ETL 実行結果・品質チェック結果・エラー集約を含む）。
    - 差分取得・バックフィル・品質チェック等の設計方針を反映した実装（_MIN_DATA_DATE、デフォルト backfill、品質問題は収集して呼び出し元で判断する方針）。
  - kabusys.data.etl
    - pipeline.ETLResult の再エクスポートインターフェースを追加。

- カレンダー管理
  - kabusys.data.calendar_management
    - JPX マーケットカレンダー管理（market_calendar）用ユーティリティを実装。
    - 営業日判定（is_trading_day）、前後営業日取得（next_trading_day / prev_trading_day）、期間内営業日列挙（get_trading_days）、SQ 日判定（is_sq_day）を提供。
    - DB 登録データを優先し、登録がない日については曜日ベースでフォールバックする一貫したロジックを実装。
    - 夜間バッチ更新ジョブ（calendar_update_job）：J-Quants から差分取得→保存（バックフィル処理、健全性チェック）を実装。
    - 最大探索日数 (_MAX_SEARCH_DAYS) による無限ループ防止設計。

- 研究（Research）モジュール
  - kabusys.research.factor_research
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER、ROE）計算を実装。
    - DuckDB を利用した SQL ベースの実装で、prices_daily / raw_financials のみ参照（本番発注等に影響しない）。
    - データ不足時の None 処理やログ出力を備える。
  - kabusys.research.feature_exploration
    - 将来リターン計算（calc_forward_returns）と IC（calc_ic、Spearman ランク相関）計算、ランク変換ユーティリティ、ファクター統計サマリー（factor_summary）を実装。
    - 外部ライブラリに依存せずに標準ライブラリと DuckDB で実装。

### Changed
- （初回リリースに伴い過去変更なし）

### Fixed
- （初回リリースに伴い過去修正なし）

### Security
- 環境変数の自動読み込みで OS 環境変数を保護する設計（.env を上書きしない、.env.local の override 挙動を明示）。
- OpenAI API キーは引数注入か OPENAI_API_KEY 環境変数から取得。未設定時は明示的な ValueError を送出して誤操作を防止。

### Design / Implementation Notes
- ルックアヘッドバイアス防止のため、各処理は datetime.today() / date.today() を直接参照しない設計（target_date を外部から渡す）。
- DuckDB をデータ基盤として使用。DuckDB の executemany の制約（空リスト不可）を回避するための防御コードを含む。
- OpenAI 呼び出しは JSON Mode を利用し、応答の頑健なバリデーションとフォールバックを実装（JSON 解析失敗や API エラー時はスキップまたは中立値を使用）。
- DB 書き込みは可能な限り冪等に行う（DELETE→INSERT、ON CONFLICT 想定の保存呼び出し等）。

### Breaking Changes
- なし（初回リリース）

---

将来的なリリースでは、strategy / execution / monitoring モジュールの公開実装、より細かいモニタリング機能や発注ロジックの実装、テストカバレッジ・型注釈強化などが予定されます。