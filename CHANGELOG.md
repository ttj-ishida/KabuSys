# CHANGELOG

すべての注目すべき変更を記録します。SemVer と Keep a Changelog の慣例に準拠します。

## [Unreleased]

## [0.1.0] - 2026-03-31

初回リリース。日本株自動売買システム「KabuSys」の基盤機能を実装しました。主要な追加点と設計上の重要な決定を以下にまとめます。

### 追加
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = 0.1.0、主要サブパッケージを公開）。

- 環境設定
  - 環境変数/.env ロード機能（kabusys.config）。
    - プロジェクトルート検出（.git または pyproject.toml を起点に探索）。
    - .env と .env.local の自動読み込み（OS 環境変数を保護する protected 機構、.env.local は .env を上書き）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート。
    - .env パースは export 句、クォートやエスケープ、インラインコメントの取り扱いに対応。
  - Settings クラス（settings）を提供し、主要設定値をプロパティで取得。
    - J-Quants / kabuステーション / Slack / DB パス / 実行環境フラグ（development/paper_trading/live） / ログレベルなど。
    - env と log_level の検証（許可値チェック）を実装。

- AI（自然言語処理）
  - kabusys.ai.news_nlp
    - score_news(conn, target_date, api_key=None)：ニュース記事の銘柄別センチメントを OpenAI（gpt-4o-mini）で評価し、ai_scores テーブルへ書き込む。
    - calc_news_window(target_date)：JST ベースのニュース収集ウィンドウ計算（UTC での DB 比較用）。
    - バッチ処理（1 API コールあたり最大 20 銘柄）、1 銘柄当たりの記事数/文字数上限、JSON mode を期待するプロンプト設計。
    - API 呼び出しでのリトライ（429/ネットワーク断/タイムアウト/5xx）と指数バックオフ。
    - レスポンスの厳密なバリデーション（JSON 解析、results 配列、コードの照合、数値検証）、スコアを ±1.0 でクリップ。
    - テスト容易性のため、内部の _call_openai_api を patch で差し替え可能。
    - DB 書き込みは部分置換（対象コードのみ DELETE → INSERT）で部分失敗時に既存データを保護。
  - kabusys.ai.regime_detector
    - score_regime(conn, target_date, api_key=None)：ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して market_regime テーブルに書き込む。
    - MA 計算は target_date 未満のデータのみを使用してルックアヘッドバイアスを排除。
    - マクロキーワードに基づく raw_news の抽出と LLM による macro_sentiment 評価（gpt-4o-mini、JSON 出力期待）。
    - API エラー時は macro_sentiment=0.0 のフェイルセーフ、リトライ実装、ログ出力。
    - DB 書き込みは冪等（BEGIN/DELETE/INSERT/COMMIT）で ROLLBACK ハンドリングを実装。
    - レジームの閾値（bull/neutral/bear）と合成ロジックを実装。

- データ層（DuckDB ベース）
  - kabusys.data.calendar_management
    - market_calendar を用いた営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB にデータがない場合は曜日ベースでフォールバック（週末を非営業日とする）。
    - calendar_update_job：J-Quants API からの差分取得と market_calendar テーブルへの冪等保存（バックフィル、先読み、健全性チェックを備える）。
    - 最大探索範囲やバックフィル、先読み日数等の定数化。
  - kabusys.data.pipeline / etl
    - ETLResult データクラスを公開（ETL 実行結果の構造化、品質チェックの集約、エラー/品質フラグ）。
    - pipeline モジュール（差分取得/保存/品質チェック方針の下地）を実装（内部ユーティリティ、最大日付取得等）。
    - etl モジュールから ETLResult を再エクスポート。
    - DuckDB テーブル存在チェック、最大日付取得ユーティリティを実装。

- リサーチ / ファクター
  - kabusys.research.factor_research
    - calc_momentum(conn, target_date)：1M/3M/6M リターン、ma200 乖離（ma200_dev）を計算。
    - calc_volatility(conn, target_date)：20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。
    - calc_value(conn, target_date)：最新財務データと株価から PER / ROE を計算（raw_financials 参照）。
    - 各関数は prices_daily / raw_financials のみ参照し、本番 API 等へアクセスしない設計。
  - kabusys.research.feature_exploration
    - calc_forward_returns(conn, target_date, horizons=None)：指定ホライズンの将来リターンを一括で取得（LEAD を利用）。
    - calc_ic(factor_records, forward_records, factor_col, return_col)：スピアマンのランク相関（IC）を計算（ランク処理と ties の平均ランク処理を実装）。
    - rank(values)：同順位は平均ランクを返す実装。
    - factor_summary(records, columns)：count/mean/std/min/max/median を算出（None 値除外）。
    - pandas 等外部依存を排した純粋な標準ライブラリ + DuckDB ベースの実装。

### 変更（設計上の重要点）
- ルックアヘッドバイアス対策
  - AI モジュールとファクター計算は内部で datetime.today()/date.today() を直接参照せず、呼び出し側から target_date を与えることで未来データ参照を防止。
  - prices_daily 等のクエリは target_date 未満、または LEAD/LAG を適切に使用してデータ範囲を明確に制御。

- OpenAI 統合方針
  - gpt-4o-mini を使用し、JSON Mode（response_format={"type": "json_object"}）での厳密な JSON 出力を想定。
  - API エラーの扱いを明確化（リトライ対象としないエラーは即スキップし、スコアはフォールバック）。
  - テスト容易性のため内部 API 呼び出しポイントを差し替え可能に設計。

- DB 書き込みの冪等性
  - market_regime / ai_scores などへの書き込みは「DELETE（既存を消す）→ INSERT」のパターンや ON CONFLICT 相当で冪等性を確保。
  - DuckDB の executemany の空リスト制約を考慮したガードを実装。

### 修正（バグ修正等）
- 初回リリースのため該当なし。

### セキュリティ / 注意事項
- .env の自動読み込みはデフォルトで有効だが、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。自動読み込みはプロジェクトルート検出に依存する。
- OS 環境変数は protected として .env による上書きから保護される。
- OpenAI API キーや他の必須環境変数が未設定の場合は明確な ValueError を発生させる（fail-fast な箇所あり）。一部フェイルセーフ（API 失敗時スコアを 0 にする）も組み合わせている。

### テスト性 / 拡張性
- OpenAI 呼び出し関数は内部で分離されており、unittest.mock.patch 等で差し替え可能（テストでのモックを容易にする）。
- 各処理は DuckDB の接続オブジェクトを受け取る設計で、外部副作用を限定しやすくなっている。

--- 

今後の予定（例）
- ai モジュールの追加モデルサポートやプロンプト改善
- ETL の品質チェックルール拡充と自動通知連携（Slack 等）
- 研究向けの可視化ユーティリティ追加

もし CHANGELOG に追記してほしい点（例えば個別コミットや貢献者情報、より詳細な API 例）があれば教えてください。