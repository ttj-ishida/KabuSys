# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載します。  
このファイルはコードベースから推測できる実装・挙動に基づき作成しています。

全般的なバージョニングポリシー: SemVer を想定。

## [Unreleased]

（今後の変更を記載）

---

## [0.1.0] - 2026-03-29

初回リリース。日本株自動売買・データ基盤・リサーチ用ユーティリティを提供する最小実装を含みます。

### 追加 (Added)
- パッケージの公開インターフェースを追加
  - パッケージルート: kabusys.__version__ = 0.1.0, __all__ に主要サブパッケージを定義（data, strategy, execution, monitoring）。
- 環境変数・設定管理モジュールを追加（src/kabusys/config.py）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - export KEY=val 形式やクォート／エスケープ、行内コメント等に対応した堅牢な .env 解析ロジックを実装。
  - OS 環境変数を保護する protected 機構の実装（.env.local は override=true）。
  - Settings クラスを導入し、J-Quants / kabuステーション / Slack / DB パス / 実行環境（KABUSYS_ENV）等のプロパティを提供。値検証（env / log_level の有効値チェック）を実装。
- AI モジュール（src/kabusys/ai）を追加
  - ニュースNLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約して銘柄ごとにニュースを結合し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄別センチメント（-1.0〜1.0）を算出して ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ（前日15:00 JST〜当日08:30 JST）計算ユーティリティ calc_news_window を実装。
    - バッチ処理（最大 20 銘柄/リクエスト）、文字数・記事数トリム、レスポンス検証、スコアクリップ、トランザクションによる idempotent な更新（DELETE → INSERT）を実装。
    - スロットリング／ネットワークエラー／5xx に対する指数バックオフリトライを実装。失敗時はフェイルセーフで該当チャンクをスキップし、全体処理を継続。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日 MA 乖離（重み70%）とニュース由来の LLM マクロセンチメント（重み30%）を合成して日次の market_regime を算出・保存する処理を実装。
    - prices_daily / raw_news の参照、OpenAI（gpt-4o-mini）呼び出し、API エラーやパースエラー時のフォールバック（macro_sentiment = 0.0）、冪等的 DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
  - ai.__init__.py で score_news を公開。
- データモジュール（src/kabusys/data）を追加
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを用いた営業日判定、次/前営業日取得、期間内営業日列挙、SQ 判定等のユーティリティを実装。
    - DB 未取得時の曜日ベースフォールバック、DB 値優先の設計、探索上限（最大探索日数）や健全性チェックを実装。
    - calendar_update_job により J-Quants API から差分取得して market_calendar を更新するバッチ処理を実装（バックフィル・健全性チェック・例外ハンドリング）。
  - ETL パイプライン（src/kabusys/data/pipeline.py / etl.py）
    - ETLResult データクラスを追加し、ETL 実行結果（取得数・保存数・品質問題・エラー等）を構造化して返却・ログ用途に変換可能に。
    - 差分取得・backfill・テーブル存在チェック等のユーティリティを実装（_get_max_date など）。
    - etl.py で ETLResult を再エクスポート。
- Research モジュール（src/kabusys/research）を追加
  - factor_research.py：モメンタム、バリュー、ボラティリティ／流動性の定量ファクター計算を実装
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR / 相対 ATR、20 日平均売買代金、出来高比率を計算。データ不足時は None を返す。
    - calc_value: raw_financials から直近財務を取得し PER / ROE を計算（EPS 不在/0 は None）。
  - feature_exploration.py：将来リターン、IC（Spearman の ρ）、ランク変換、統計サマリーを実装
    - calc_forward_returns: 指定ホライズンの将来リターン（LEAD を使用）を一括取得。
    - calc_ic: factor と forward returns を code で結合し、スピアマンランク相関を計算（有効サンプルが 3 未満なら None）。
    - rank: 同順位は平均ランクを採るランク変換実装（round(v,12) で丸めて ties の判定安定化）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー関数。
- その他のユーティリティ
  - DuckDB を前提としたクエリ／変換ロジックを各モジュールで使用（fetch/aggregations に最適化された SQL）。
  - OpenAI クライアント呼び出しはテスト容易性のため個別の _call_openai_api をラップし、unittest.mock で差し替え可能に。

### 変更 (Changed)
- （初期リリースにつき該当なし）

### 修正 (Fixed)
- （初期リリースにつき該当なし）

### 破壊的変更 (Breaking Changes)
- なし（初回リリース）

### 注意 (Notes)
- 全ての日付処理はルックアヘッドバイアス防止のため、date.today() や datetime.now() に依存しない設計を採用している関数が多く、処理は引数で与えた target_date に基づき行われます。ETL / スコアリングの呼び出し時は target_date を明示的に指定してください。
- OpenAI API を利用する機能（news_nlp, regime_detector）は API キー（OPENAI_API_KEY）を必要とします。api_key を引数で注入可能な設計になっていますが、環境変数または引数でキーを提供してください。
- .env の自動ロードはプロジェクトルートの検出に依存します（.git または pyproject.toml）。配布後に自動ロードが不要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の executemany は空リストを受け付けないバージョン（例: 0.10）に配慮した実装になっています。空の params に対する実行を回避するため、書き込み前に件数チェックを行います。
- OpenAI レスポンスは JSON Mode を期待していますが、万一前後に余計なテキストが混入するケースに備え JSON 抽出や堅牢なパースを実装しています。パースに失敗した場合は該当チャンクをスキップして全体処理を継続します（フェイルセーフ）。

---

今後のリリース案（例）
- AI モジュール: 別モデルやローカル LLM サポート、評価・キャリブレーション機能
- ETL: より細かい品質チェック・自動修復ルール、ジョブ監視
- リサーチ: パネル分析用出力（CSV/Parquet）、可視化ユーティリティ

