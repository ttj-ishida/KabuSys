# Changelog

すべての変更は Keep a Changelog のフォーマットに従い、セマンティックバージョニングを使用します。  

リリース日: 2026-03-28

## [Unreleased]
特になし。

## [0.1.0] - 2026-03-28
初回リリース。

### Added
- 基本パッケージ初期化
  - src/kabusys/__init__.py にてパッケージ名と公開サブパッケージを定義（data, strategy, execution, monitoring）。
  - パッケージバージョンを `0.1.0` として設定。

- 環境変数 / 設定管理
  - src/kabusys/config.py
    - .env / .env.local の自動読み込み機能（OS環境変数優先）。プロジェクトルートは `.git` または `pyproject.toml` を基準に探索。
    - .env パーサの実装（コメント行、export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理対応）。
    - 自動読み込みを環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - 設定ラッパー `Settings` を提供。J-Quants / kabuステーション / Slack / DB パス / 環境種別（development/paper_trading/live）等のプロパティと入力検証を実装。
    - DB デフォルトパス（DuckDB: `data/kabusys.duckdb`, SQLite: `data/monitoring.db`）。

- AI モジュール（OpenAI を用いたニュース解析・レジーム判定）
  - src/kabusys/ai/news_nlp.py
    - ニュース記事の銘柄別センチメントスコアリング機能 `score_news(conn, target_date, api_key=None)` を実装。
    - スコア算出のためのニュース時間ウィンドウ計算 `calc_news_window`（JST ベース → UTC 変換）を実装。
    - OpenAI (gpt-4o-mini) 向けプロンプト（JSON Mode）を使用したバッチ送信（最大20銘柄/チャンク）、トークン肥大化対策（記事数・文字数制限）。
    - リトライ（429・ネットワーク断・タイムアウト・5xx）に対する指数バックオフ、レスポンスバリデーション（JSON 抽出、results 構造、コード照合、数値チェック）、スコア ±1.0 でクリップ。
    - テスト容易性のため OpenAI 呼び出し部分は差し替え可能（_call_openai_api を patch 可能）。
    - DuckDB への冪等書き込み（DELETE → INSERT）とトランザクション制御。部分失敗時に既存スコアを保護する実装。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動型）200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定する `score_regime(conn, target_date, api_key=None)` を実装。
    - ma200_ratio 計算（_calc_ma200_ratio）ではルックアヘッド防止のため target_date 未満のみ使用、データ不足時は中立(1.0)でフォールバック。
    - マクロキーワードによる raw_news フィルタリング、OpenAI による JSON 出力パース、リトライ/フェイルセーフ（失敗時 macro_sentiment=0.0）。
    - 判定結果を market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）、エラー時はロールバックを試行し失敗ログ。

- データプラットフォーム機能（DuckDB ベース）
  - src/kabusys/data/pipeline.py
    - ETL パイプライン基盤（差分取得、保存、品質チェック）に基づく処理ユーティリティを実装。
    - ETL 実行結果を表すデータクラス `ETLResult` を提供（フェッチ/保存件数、品質問題、エラー集約、ヘルパーメソッド）。
    - テーブル存在チェック、最大日付取得などのユーティリティを実装。

  - src/kabusys/data/etl.py
    - pipeline の `ETLResult` を再エクスポート。

  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理（market_calendar）と夜間バッチ `calendar_update_job(conn, lookahead_days=...)` を実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ロジックを提供。DB データがない場合は曜日（週末）に基づくフォールバックを使用。
    - 更新時は J-Quants クライアント経由で差分取得 → 冪等保存。バックフィル、健全性チェック（将来日付の異常検知）を実装。

- Research（因子・特徴量探索）
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M リターン、MA200 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER、ROE）などの因子計算関数を実装（calc_momentum / calc_volatility / calc_value）。
    - DuckDB SQL を主体とした実装で、prices_daily / raw_financials のみ参照。欠損時の挙動を明示。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns、複数ホライズン対応）、IC（Information Coefficient）計算（calc_ic）、ランキング変換（rank）、ファクター統計サマリー（factor_summary）を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。ランクの同順位は平均ランク処理。

- テストや運用面の配慮
  - 各種モジュールで API 呼び出しを差し替え可能（unit test 用 patch）に設計。
  - ルックアヘッドバイアス防止のため、各スコアリング/判定関数は内部で datetime.today()/date.today() を参照しない。target_date を明示的に受け取る設計。
  - ロギングを広く導入し、失敗時のフォールバックや警告を記録。

### Changed
- 該当なし（初回リリースのため）。

### Fixed
- 該当なし（初回リリースのため）。

### Security
- 該当なし（初回リリースのため）。

---

注記:
- OpenAI API 呼び出しには環境変数 `OPENAI_API_KEY` または関数引数でのキー指定が必要。未指定時は ValueError を送出する設計。
- .env パーサや DB 書き込みの挙動、リトライ戦略、フェイルセーフの動作は各モジュールのドキュメント文字列に詳述されています。必要に応じて個別関数のドキュメントを参照してください。