# CHANGELOG

すべての非公開変更はリリースノートに記載してください。  
このファイルは Keep a Changelog の形式に準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

なお、この CHANGELOG はソースコードから推測して作成しています。実際の変更履歴やリリース日は実運用に合わせて調整してください。

## [Unreleased]

### Added
- 開発初期段階の主要モジュールを追加。
  - kabusys パッケージのエントリポイントを追加（__version__ = 0.1.0）。
  - 環境設定管理モジュール (kabusys.config) を追加。
    - .env / .env.local の自動読み込み機能（OS 環境変数優先、.env.local は .env の上書き）。
    - export 形式やクォート・コメントを考慮したパーサ実装。
    - 必須環境変数チェック（_require）と各種設定プロパティ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_* 等）。
    - 環境名（KABUSYS_ENV）とログレベル（LOG_LEVEL）の検証（許容値を限定）。
  - AI 関連:
    - ニュース NLP スコアリング (kabusys.ai.news_nlp)
      - OpenAI（gpt-4o-mini）を用いたバッチ式ニュースセンチメント解析。
      - タイムウィンドウ計算（JSTベースの UTC 変換）。
      - 銘柄ごとに記事を集約して最大バッチサイズ単位で API 送信。
      - レスポンスの厳密な JSON バリデーションとスコアクリッピング（±1.0）。
      - 再試行（429、ネットワーク、タイムアウト、5xx）を指数的バックオフで実装。
      - ai_scores テーブルへの冪等書き込み（DELETE → INSERT、部分失敗時に既存スコアを保護）。
    - 市場レジーム判定 (kabusys.ai.regime_detector)
      - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成。
      - OpenAI を用いたマクロセンチメント算出（JSON 出力期待、フェイルセーフは macro_sentiment=0.0）。
      - レジーム（bull / neutral / bear）の算出と market_regime テーブルへの冪等書き込み。
      - API 呼び出しは独立実装でモジュール結合を避ける設計。
  - Data / ETL:
    - ETL パイプラインの結果表現 ETLResult と pipeline モジュールの追加（kabusys.data.pipeline / etl）。
      - ETLResult は取得数・保存数・品質問題・エラー要約などを保持、to_dict でシリアライズ可能。
    - 市場カレンダー管理 (kabusys.data.calendar_management)
      - JPX カレンダーの差分取得/保存ジョブ（calendar_update_job）。
      - 営業日判定・前後営業日取得・期間内営業日取得・SQ 判定のユーティリティ。
      - DB 未取得時の曜日ベースのフォールバック、探索上限や健全性チェックの導入。
  - Research:
    - ファクター計算・解析モジュール群 (kabusys.research)
      - calc_momentum / calc_value / calc_volatility（prices_daily, raw_financials を使用）。
      - calc_forward_returns（任意ホライズンの将来リターン取得）。
      - calc_ic（Spearman ランク相関に基づく IC 計算）、rank、factor_summary、factor_summary（統計サマリ）。
    - zscore_normalize を data.stats から再公開。

### Changed
- （設計）多数の関数でルックアヘッドバイアス防止を明示
  - datetime.today() / date.today() をアルゴリズム内部で参照せず、必ず target_date を引数として受け取る設計に統一。
- DuckDB 互換性と安全性を考慮した SQL 実装・ executemany の空リスト回避等の注意書きを反映。

### Fixed
- OpenAI API 呼び出しに対して堅牢なエラーハンドリングを実装（リトライ・バックオフ・5xx の判定・非 5xx での速やかなスキップ）。
- .env パーサでのクォート処理・エスケープ処理、インラインコメントの取り扱いを改善。

### Security
- OS 環境変数を保護するための読み込みロジック（protected set）を導入し、.env の自動上書きを制御。

---

## [0.1.0] - 2026-03-31

初回リリースとして想定されるリリースノート。上記 Unreleased の内容をベースに、公開バージョン v0.1.0 として以下をまとめてリリース。

### Added
- パッケージ初期バージョンをリリース（kabusys v0.1.0）。
- 環境設定管理（.env 自動読み込み、設定プロパティ）。
- AI モジュール:
  - ニュース NLP スコアリング（score_news）
  - 市場レジーム判定（score_regime）
  - OpenAI 呼び出しは gpt-4o-mini をデフォルトモデルに設定
- Data モジュール:
  - ETL パイプライン（ETLResult 等）
  - JPX カレンダー管理とバッチ更新ジョブ
- Research モジュール:
  - momentum / volatility / value ファクター計算
  - 将来リターン calc_forward_returns、IC 計算 calc_ic、統計サマリ等
- DuckDB を利用する設計で、prices_daily / raw_news / raw_financials / market_calendar / ai_scores 等のテーブル操作をサポート。

### Changed
- N/A（初回リリースのため変更履歴なし）

### Fixed
- N/A（初回リリースのため修正履歴なし）

### Security
- 環境変数未設定時の挙動（必須変数で ValueError を投げる）を明示。
- 自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。

---

補足 (運用メモ)
- 必要な環境変数（少なくとも開発で利用するもの）:
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（必須）
  - OPENAI_API_KEY（score_news / score_regime 実行時に必要）
  - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
  - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- DuckDB ファイルパスのデフォルト:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- OpenAI 呼び出しはテスト容易性のため内部呼び出し点をモック可能に設計（_call_openai_api をパッチして置き換えられる）。

この CHANGELOG はコードの構造・ドキュメンテーション文字列から推測して作成しています。実際のリリース日やリリース範囲はプロジェクトの運用に合わせて編集してください。