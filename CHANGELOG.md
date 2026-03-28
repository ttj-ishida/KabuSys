# Changelog

すべての重要な変更はこのファイルに記録しています。  
フォーマットは「Keep a Changelog」に準拠しています。  

現在のリリース日: 2026-03-28

## [Unreleased]
- なし

## [0.1.0] - 2026-03-28
初回公開リリース

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージを追加。公開 API: data, strategy, execution, monitoring を __all__ に定義。
  - バージョン番号を `0.1.0` として設定。

- 環境設定
  - `kabusys.config.Settings` を実装。環境変数から各種設定（J-Quants / kabuステーション / Slack / DB パス / ログレベル等）を安全に取得。
  - .env 自動ロード機能を実装（プロジェクトルート判定は .git または pyproject.toml を基準）。優先順位: OS 環境変数 > .env.local > .env。
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` による自動ロード無効化をサポート。
  - 必須環境変数未設定時に明確なエラーメッセージを出す `_require` を提供。
  - 環境値検証（KABUSYS_ENV / LOG_LEVEL の有効値チェック）を実装。

- データプラットフォーム関連
  - data パッケージ基盤を実装（空の __init__ とサブモジュール）。
  - calendar_management: JPX マーケットカレンダー管理、営業日判定ロジック、next/prev/get_trading_days、SQ 日判定、calendar_update_job（J-Quants から差分フェッチして冪等保存）を実装。
    - market_calendar が未登録の場合は曜日ベースのフォールバックを行う設計。
    - バックフィル・健全性チェックをサポート。
  - pipeline / etl: ETL パイプラインのインターフェースと `ETLResult` データクラスを実装。
    - 差分取得、保存、品質チェックの観点を想定した設計。
    - ETL 実行結果（品質問題・エラーの集約）を可視化可能に。

- 研究 (research)
  - research パッケージを追加。
  - factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算を実装。
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離を算出。
    - calc_volatility: 20日 ATR、相対 ATR、平均売買代金、出来高比率を算出。
    - calc_value: 最新財務データに基づいた PER / ROE を算出。
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー等を実装。
    - calc_forward_returns: 任意ホライズンの将来リターンを一括取得。
    - calc_ic: ランク相関（Spearman ρ）を計算。
    - rank / factor_summary: ランキングと要約統計ユーティリティを提供。
  - zscore_normalize は data.stats から再エクスポート。

- AI（自然言語処理）モジュール
  - ai パッケージを追加。news_nlp.score_news を公開。
  - news_nlp:
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini、JSON Mode）へバッチ送信して銘柄別センチメント（-1.0〜1.0）を算出、ai_scores テーブルへ書き込み。
    - バッチサイズ、記事数・文字数上限、リトライ（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）やレスポンス検証ロジックを実装。
    - レスポンスの柔軟なパース（前後余計テキストの復元）と厳格なバリデーションを実装。無効レスポンスはスキップしてフェイルセーフ。
    - テスト容易性のため OpenAI 呼び出し関数を差し替え可能に設計。
  - regime_detector:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等書き込み。
    - マクロニュース取得のためのキーワードフィルタ、OpenAI 呼び出し（gpt-4o-mini）とリトライ・フォールバックロジックを実装。
    - API 失敗時は macro_sentiment=0.0 として継続。

### 変更 (Changed)
- アーキテクチャ設計方針（実装中・設計注記）
  - ルックアヘッドバイアス防止のため、いずれの処理も内部で datetime.today()/date.today() を参照せず、明示的な target_date を受け取る設計を採用。
  - DuckDB をデータ層として想定し、SQL と Python を組み合わせた実装。DuckDB の制約（executemany の空リスト不可等）に対応した実装を行った。

### 修正 (Fixed)
- API レスポンスや DB 書き込みの失敗時に部分的なデータ消失が起きないよう、各種処理で冪等性・トランザクション制御（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）を採用。
- news_nlp と regime_detector で OpenAI API の例外型に応じた適切なリトライ判定・ログ出力を追加。

### セキュリティ (Security)
- 現時点でセキュリティフィックスはなし。
- 注意: OpenAI API キーや各種トークンは環境変数で管理する設計。`.env` に平文で置く場合は適切な運用（.gitignore 等）を推奨。

### 既知の制約 / 注意事項 (Known issues / Notes)
- OpenAI を利用する機能（news_nlp, regime_detector）は API キー（OPENAI_API_KEY）が必須。キー未設定時は ValueError を送出。
- DB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar など）は外部で準備する必要あり。サンプルスキーマ/マイグレーションは未提供。
- 一部の関数は DuckDB バージョンに依存する挙動（リスト型バインド等）があるため、DuckDB の互換性に注意。
- デフォルトの DB パス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (monitoring): data/monitoring.db
  いずれも環境変数（DUCKDB_PATH / SQLITE_PATH）で上書き可能。

### マイグレーション / 導入手順 (Migration / Upgrade notes)
- 必須環境変数（例）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY
- .env 自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- DuckDB の準備と必要テーブルのスキーマ作成を行ってから、AI スコアリングやレジーム判定を実行してください。

---

今後の予定（TODO）
- strategy / execution / monitoring の具象実装（売買ロジック、発注ラッパー、監視アラート等）。
- DB スキーマ・マイグレーションツールとサンプルデータの提供。
- CI 用のモックを用いたユニットテストの追加（OpenAI 呼び出しモック等）。