# Changelog

すべての重要な変更をここに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

最新: [Unreleased] セクションを確認してください。

※ 日付はリリース日を示します。

## [Unreleased]

- なし（次回リリースに向けた未公開変更はここに記載します）。

---

## [0.1.0] - 2026-03-29

初回公開リリース。日本株自動売買システムのコアライブラリを提供します。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ基礎
  - kabusys パッケージの初期公開（src/kabusys/__init__.py, version 0.1.0）。
  - モジュール群を public API として整理（data, strategy, execution, monitoring を __all__ に追加）。

- 設定管理
  - 環境変数・.env ファイル自動読み込み機能を実装（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml から自動検出して .env / .env.local を読み込む。
    - OS 環境変数を保護するための protected 上書き制御、override オプションをサポート。
    - 自動読み込みを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - .env のパースは export 形式やクォート、インラインコメント等に対応。
  - Settings クラスを提供し、アプリケーション設定（J-Quants、kabuステーション、Slack、DB パス、環境種別、ログレベル等）をプロパティ経由で取得可能に。
    - env / log_level のバリデーション（許容値チェック）を実装。
    - duckdb/sqlite パスは既定値を持ち expanduser による展開を行う。

- データ取得・ETL
  - ETL パイプラインの結果を表す ETLResult データクラスをエクスポート（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）。
    - 取得件数、保存件数、品質問題（quality_issues）、エラー概要、ユーティリティ (to_dict, has_errors, has_quality_errors) を提供。
  - market calendar（カレンダー）管理モジュールを追加（src/kabusys/data/calendar_management.py）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティ。
    - DB（market_calendar）を優先し、未登録日は曜日ベースでフォールバックする一貫したロジックを提供。
    - calendar_update_job により J-Quants からの差分取得と冪等保存をサポート（バックフィル・健全性チェックを含む）。
  - ETL パイプライン基盤（差分取得・保存・品質チェックの指針）を実装（pipeline.py）。
    - _get_max_date 等の DB ヘルパー、差分取得に関する定数・方針を定義。

- AI（自然言語処理）機能
  - ニュースセンチメントスコアリング（news_nlp）モジュールを追加（src/kabusys/ai/news_nlp.py）。
    - 指定タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）内の記事を銘柄ごとに集約し、OpenAI（gpt-4o-mini）へバッチ送信してスコアを ai_scores テーブルへ書込む。
    - バッチ処理（最大 20 銘柄/コール）、1 銘柄あたりの最大記事数/文字数制限、429/ネットワーク/5xx に対する指数バックオフリトライを実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results キー・型検証、未知コード無視、数値チェック、スコアの ±1.0 クリップ）を実装。
    - API キー注入可（引数または OPENAI_API_KEY 環境変数）。
    - テスト容易性のため _call_openai_api をモック置換可能に設計。
  - 市場レジーム判定（regime_detector）モジュールを追加（src/kabusys/ai/regime_detector.py）。
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロ経済ニュースの LLM センチメント（重み30%）を合成し、日次で市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ冪等書込む。
    - prices_daily, raw_news を参照、LLM 呼び出しは OpenAI 経由（gpt-4o-mini）で実行。API エラー時は macro_sentiment=0.0 でフォールバックする設計（フェイルセーフ）。
    - リトライ・バックオフ、JSON レスポンス検証、ロギングを実装。
    - ルックアヘッドバイアス防止設計（datetime.today() を参照しない、クエリに date < target_date の排他条件）。

- 研究（Research）ユーティリティ
  - research パッケージを追加（src/kabusys/research）。
    - factor_research: モメンタム、ボラティリティ、バリュー等のファクター計算（calc_momentum, calc_volatility, calc_value）。
      - DuckDB を使った SQL ベースの計算、MA200, ATR20, 各種モメンタムの算出、raw_financials 参照による PER/ROE など。
      - データ不足時の None ハンドリングを明示。
    - feature_exploration: 将来リターン計算（calc_forward_returns）、IC 計算（calc_ic）、ランク化ユーティリティ（rank）、統計サマリー（factor_summary）。
      - 外部ライブラリに依存せず標準ライブラリで実装。
    - data.stats の zscore_normalize を再エクスポートすることで研究ワークフローと統合。

- データベース・互換性
  - DuckDB を主要な分析 DB として全面的に利用（関数は DuckDB 接続を引数に取る設計）。
  - DB 書き込みは冪等操作（DELETE → INSERT、BEGIN/COMMIT/ROLLBACK 管理）を基本とする。

### 変更 (Changed)
- なし（初回リリース）。

### 修正 (Fixed)
- なし（初回リリース）。

### 破壊的変更 (Removed / Breaking Changes)
- なし（初回リリース）。

### セキュリティ (Security)
- OpenAI API キーを引数で注入可能にして直接的な環境変数依存を回避できるように設計。  
- .env 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD で明示的に無効化可能。

---

開発上の注意点・設計上の特徴（要約）
- ルックアヘッドバイアス防止: 日時の参照はすべて外部から与えられる target_date に依存し、内部で date.today()/datetime.today() を使わない設計。
- フェイルセーフ: 外部 API（OpenAI, J-Quants 等）失敗時は例外で即停止させず、デフォルト値で継続する箇所を用意（ログ出力で可観測性確保）。
- テストしやすさ: OpenAI 呼び出しの内部ラッパー関数は unittest.mock.patch により差し替え可能に設計。
- DuckDB バージョン互換性: executemany の空リスト禁止など、既知の制約を考慮した実装。

---

参考:
- Keep a Changelog: https://keepachangelog.com/en/1.0.0/