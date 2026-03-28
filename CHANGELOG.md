# CHANGELOG

すべての重要な変更点をここに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

注: このリポジトリの初期リリースを表す CHANGELOG です。コードから推測できる機能・設計方針を元に記載しています。

## [Unreleased]

## [0.1.0] - 2026-03-28
初回公開リリース。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初版を追加。バージョンは 0.1.0。
  - パッケージ公開インターフェースで data, strategy, execution, monitoring をエクスポート。

- 環境設定・ロード (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダを実装。
  - プロジェクトルートの自動検出ロジックを実装（.git または pyproject.toml を探索）。
  - .env パース実装:
    - 空行・コメント行の無視、`export KEY=val` 形式のサポート。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理。
    - クォートなし値のインラインコメント扱い（直前がスペース/タブの場合に '#' をコメントと認識）。
    - 読み込み時の上書き制御（override）と「保護された」OS環境変数の扱い。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加（テストで利用可能）。
  - Settings クラスを実装してアプリケーション設定をプロパティ経由で取得可能に:
    - J-Quants / kabu API / Slack / DB パス等の設定項目を定義。
    - KABUSYS_ENV と LOG_LEVEL のバリデーションを実装（許容値チェック）。
    - デフォルト値（KABUSYS_ENV=development、LOG_LEVEL=INFO、KABU_API_BASE_URL、DB パス等）を提供。

- AI モジュール
  - kabusys.ai.news_nlp:
    - raw_news と news_symbols を用いて銘柄毎のニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ書き込む機能を実装。
    - ニュース対象ウィンドウの計算（前日 15:00 JST ～ 当日 08:30 JST の UTC 変換）。
    - 1 銘柄あたりの記事数・文字数トリム対策、バッチ（最大 20 銘柄）による API 呼び出し。
    - JSON Mode を前提としたレスポンスバリデーションとスコア ±1.0 のクリップ処理。
    - レートリミット・ネットワーク断・タイムアウト・5xx に対する指数バックオフによるリトライ。
    - API 失敗時は部分スキップして他の銘柄処理を継続（フェイルセーフ）。テーブル書き込みは対象コードのみ DELETE → INSERT することで部分失敗時の既存データ保護を行う。
    - テスト用フック: _call_openai_api 関数を patch 可能に実装。

  - kabusys.ai.regime_detector:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込みする関数を実装。
    - マクロニュース抽出（マクロキーワードリストによるタイトルフィルタ、最大記事数制限）。
    - OpenAI（gpt-4o-mini）を用いたマクロセンチメント評価（JSON 出力期待）。
    - API 呼び出しのリトライ・エラー処理、JSON パース失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - スコア合成のクリップ、閾値に基づくラベル付与、DB 書き込みのトランザクション制御（BEGIN/DELETE/INSERT/COMMIT、失敗時 ROLLBACK）。

- データプラットフォーム関連
  - kabusys.data.pipeline / etl:
    - ETLResult データクラスを公開。ETL の取得件数、保存件数、品質問題、エラー概要などを保持。has_errors / has_quality_errors / to_dict メソッドを提供。
    - ETL パイプラインの設計方針をコードに反映（差分取得、backfill、品質チェック連携、id_token 注入でテスト容易化等）。
  - kabusys.data.calendar_management:
    - JPX 市場カレンダー管理機能（market_calendar テーブルの利用）と営業日判定ユーティリティを実装:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days の提供。
      - market_calendar が未取得の場合の曜日ベースのフォールバック・挙動、DB 値優先の一貫性、最大探索日数制限を実装。
    - calendar_update_job:
      - J-Quants API から差分取得して market_calendar を冪等更新する夜間バッチ処理を実装。
      - バックフィル、健全性チェック（将来日付の異常検出）を実装。
    - 内部ユーティリティ: テーブル存在チェック、DuckDB からの date 変換、NULL 値取り扱いに関するログ出力等。

- リサーチ・ファクター群 (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離率などのモメンタム系ファクターを計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率などのボラティリティ／流動性ファクターを計算。
    - calc_value: raw_financials から直近財務データを取得して PER、ROE を計算（EPS が 0/欠損時は None）。
    - DuckDB を用いた SQL ベースの実装で、外部 API へはアクセスしない設計。
  - feature_exploration:
    - calc_forward_returns: 基準日から指定ホライズン（日数）後の将来リターンを計算。デフォルト horizons=[1,5,21]。horizons のバリデーションを実装。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算（有効レコードが 3 未満なら None を返す）。
    - rank: 同順位は平均ランクとするランク変換を実装（浮動小数の丸めで ties を検出）。
    - factor_summary: 各ファクター列の基本統計（count/mean/std/min/max/median）を計算。
    - 実装は標準ライブラリのみ（pandas 等に依存しない）。

- その他ユーティリティ
  - kabusys.data.etl: pipeline.ETLResult を再エクスポートして公開 API を簡潔にした。

### 変更 (Changed)
- 初期リリースのため該当なし（初回追加のみ）。

### 修正 (Fixed)
- 初期リリースのため該当なし。

### 非推奨 (Deprecated)
- 初期リリースのため該当なし。

### 削除 (Removed)
- 初期リリースのため該当なし。

### セキュリティ (Security)
- 初期リリースのため該当なし。

---

注記（設計上の重要点・制約）
- 多くのアルゴリズム（ニュース集約、レジーム判定、ファクター計算等）は datetime.today()/date.today() を直接参照せず、target_date を明示的引数として受け取る設計になっており、ルックアヘッドバイアスを防止する意図が反映されています。
- OpenAI の呼び出しは JSON Mode を期待しているため、レスポンスの堅牢なバリデーションとパース耐性（前後の余計なテキストの除去）を備えています。
- DuckDB を主要なローカル分析 DB として使用。executemany の空リストバインド等の実装上の互換性を考慮した処理が入っています。
- テスト容易性のため、OpenAI 呼び出し用の内部関数を patch できるように実装されています（ユニットテストでのモック化を想定）。

もし CHANGELOG に追記したい改善点やリリース日・バージョン名の変更があれば指示してください。