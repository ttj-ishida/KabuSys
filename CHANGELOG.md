CHANGELOG
=========

すべての注目すべき変更点を記載します。本ファイルは「Keep a Changelog」形式に準拠しています。

フォーマットのルール:
- 変更は意味のあるまとまり（Added / Changed / Fixed / Removed / Security 等）で整理しています。
- 日付はリリース日を示します。

Unreleased
----------

- （今後の変更をここに記載）

[0.1.0] - 2026-03-27
-------------------

Added
- 初回公開リリース。
- パッケージのエントリポイント (src/kabusys/__init__.py) にて、data, strategy, execution, monitoring を公開。
- 環境設定管理モジュール (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサーは export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
  - 環境変数の上書き制御（override, protected）をサポート。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 実行環境 / ログレベル等の設定取得用プロパティを定義（必須項目は未設定時に ValueError を送出）。
  - env / log_level のバリデーション（許容値集合）を実装。
- Data モジュール
  - ETL パイプラインインターフェース (kabusys.data.pipeline, ETLResult) を実装・公開（kabusys.data.etl で再エクスポート）。
  - market_calendar を扱うマーケットカレンダー管理 (kabusys.data.calendar_management) を実装。
    - 営業日判定・前後営業日取得・期間内営業日取得・SQ判定等のユーティリティを提供。
    - DB の値がない場合は曜日ベースのフォールバックを用いる堅牢な設計。
    - calendar_update_job により J-Quants から差分取得して冪等に保存する処理を実装（バックフィル・健全性チェック含む）。
- Research モジュール (kabusys.research)
  - ファクター計算（momentum, value, volatility）を実装（prices_daily / raw_financials を参照）。
  - 特徴量探索ユーティリティ（forward returns, IC 計算, 統計サマリー, ランク化）を実装。
  - zscore_normalize を data.stats から利用可能にするエクスポート。
- AI モジュール (kabusys.ai)
  - ニュースセンチメント解析 score_news を実装（gpt-4o-mini + JSON mode を使用）。
    - 前日 15:00 JST 〜 当日 08:30 JST のウィンドウ定義（UTC 変換）に基づいて raw_news と news_symbols を集約。
    - 1銘柄あたり最大記事数・文字数でトリムし、最大バッチサイズで分割して API 呼び出し。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。
    - レスポンスバリデーション（JSONパース、results 配列、既知コード照合、数値チェック）を実装。スコアは ±1.0 にクリップ。
    - スコア取得済みコードのみを置換することで部分失敗時に既存データを保護。
  - 市場レジーム判定 score_regime を実装。
    - ETF 1321（日経225連動）200日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成。
    - ma200_ratio 計算（target_date 未満のデータのみ使用）とマクロ記事抽出、OpenAI 呼び出し、合成スコアのクリップ、ラベル化（bull/neutral/bear）、そして market_regime への冪等書き込みを行う。
    - API 失敗時は macro_sentiment を 0.0 にフォールバックするフェイルセーフ設計。
  - OpenAI クライアント呼び出しロジックは各モジュールで独立実装（テストで差し替え可能）。
- 設計上の重要な方針（クロスモジュール）
  - ルックアヘッドバイアス防止のため、datetime.today() / date.today() を内部的に参照しない設計（すべて target_date パラメータ駆動）。
  - DuckDB を主要なデータアクセス手段として使用（SQL + Python の組合せ）。
  - API 呼び出しのフェイルセーフ（失敗時はスキップまたはデフォルト値を使用して処理継続）。
  - DuckDB の executemany の制約を考慮した実装（空リスト渡し回避等）。

Changed
- （初版のため無し）

Fixed
- （初版のため無し）

Removed
- （初版のため無し）

Notes / Usage
- OpenAI API を利用する機能（score_news / score_regime）は API キー（api_key 引数または環境変数 OPENAI_API_KEY）が必須。未設定時は ValueError。
- 必須の環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- データベース既定パス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (monitoring 用): data/monitoring.db
- .env の自動ロードはプロジェクトルート検出に成功した場合にのみ行われ、OS 環境変数は保護される（.env.local は override=True で読み込み）。

設計上の注意点（重要）
- AI レスポンスのパース失敗や API の恒常失敗は例外を投げずにログ出力してスコアを 0.0 または空集合にフォールバックするため、監視・ログの確認を推奨します。
- DuckDB 内のテーブル構成（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar 等）を事前用意することが想定されています。
- calendar_update_job と ETL パイプラインは idempotent（冪等）に設計されており、部分的な再実行やバックフィルに耐える実装になっています。

References
- リポジトリ内の doc（DataPlatform.md, StrategyModel.md 等）に設計の背景・前提が記載されていることを想定しています。必要に応じてそちらも参照してください。