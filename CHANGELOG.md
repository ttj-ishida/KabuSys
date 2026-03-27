# Changelog

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog のフォーマットに準拠します。  

※ 初回公開版としてリリース情報をコードベースから推測して作成しています。

## [Unreleased]

- （なし）

## [0.1.0] - 2026-03-27

初回リリース — 日本株自動売買プラットフォームの基礎機能を実装。

### 追加 (Added)
- パッケージのエントリポイントを追加
  - `kabusys.__version__ == "0.1.0"`。公開モジュール: `data`, `strategy`, `execution`, `monitoring`。

- 環境変数 / 設定管理
  - `kabusys.config.Settings` を提供。主要プロパティ:
    - `jquants_refresh_token`, `kabu_api_password`, `kabu_api_base_url`
    - `slack_bot_token`, `slack_channel_id`
    - `duckdb_path`, `sqlite_path`
    - `env`, `log_level`, `is_live`, `is_paper`, `is_dev`
  - 自動的な .env 読み込み機構を実装（プロジェクトルートは `.git` または `pyproject.toml` で検出）。
    - 読み込み優先順位: OS 環境変数 > `.env.local` > `.env`
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
    - ファイル読み込み時に既存 OS 環境変数を保護する仕組み（protected set）。
  - `.env` の解析は引用符・エスケープ・インラインコメントに対応。

- AI（ニューラル/LLM）機能
  - ニュースセンチメントスコアリング: `kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)`
    - J-Quants の `raw_news` と `news_symbols` を集約し、OpenAI（`gpt-4o-mini`）に対して銘柄単位でセンチメントを要求。
    - バッチ処理（最大 20 銘柄/リクエスト）、リトライ（429/ネットワーク/5xx に対する指数バックオフ）を実装。
    - レスポンスのバリデーションと ±1.0 のクリッピングを実施。
    - 書き込みは冪等に行い、取得成功した銘柄のみ `ai_scores` テーブルを置換（DELETE → INSERT）。
    - ニュース取得ウィンドウ:
      - JST 基準で「前日 15:00 〜 当日 08:30」（内部では UTC naive に変換して DB を比較）。
  - 市場レジーム判定: `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`
    - ETF 1321（Nikkei225 連動型）の 200 日移動平均乖離（重み 70%）と、マクロ記事の LLM センチメント（重み 30%）を合成して日次レジーム（`bull` / `neutral` / `bear`）を算出。
    - OpenAI の呼び出しは独立実装で、API 失敗時は `macro_sentiment = 0.0` のフォールバック。
    - 計算結果は `market_regime` テーブルへ冪等に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - 内部での設計方針として、ルックアヘッドバイアスを防ぐために `datetime.today()` 等を参照しない。

- 研究 (Research) モジュール
  - `kabusys.research` を提供し、以下の主要 API を公開:
    - ファクター計算: `calc_momentum`, `calc_value`, `calc_volatility`
      - モメンタム: 1M/3M/6M リターン、200 日 MA 乖離など。
      - バリュー: PER, ROE（`raw_financials` を参照）。
      - ボラティリティ/流動性: 20 日 ATR、平均売買代金、出来高比率など。
    - 特徴量探索 / 統計: `calc_forward_returns`, `calc_ic`, `factor_summary`, `rank`
      - 将来リターン計算は任意のホライズン（デフォルト [1,5,21]）対応。
      - IC（Spearman）の実装、ランク付けユーティリティ、列ごとの統計サマリを提供。
  - すべて DuckDB 接続を受け取り、DB のみを参照する（外部 API や発注 API にアクセスしない設計）。

- データプラットフォーム / ETL
  - `kabusys.data.pipeline.ETLResult` と ETL ユーティリティを追加。
    - ETL の取得数・保存数・品質チェック結果・エラー集約を表現する dataclass。
  - カレンダー管理: `kabusys.data.calendar_management` を追加
    - 営業日判定とユーティリティ:
      - `is_trading_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`, `is_sq_day`
    - DB にカレンダーが無い場合は曜日ベースのフォールバック（週末 = 非営業日）。
    - 夜間バッチ: `calendar_update_job` で J-Quants から差分取得し `market_calendar` に冪等保存。バックフィル、健全性チェックを実装。

- DuckDB を主要なデータ層に採用
  - 主要テーブル名（コードにより参照）:
    - `prices_daily`, `raw_news`, `news_symbols`, `ai_scores`, `market_regime`, `market_calendar`, `raw_financials` など。

- OpenAI クライアントの利用方針
  - モデル: `gpt-4o-mini`、JSON Mode（response_format={"type":"json_object"}）を用いる。
  - タイムアウトやリトライ方針を統一して実装（最大リトライ数、指数バックオフ）。
  - テスト容易性のため `_call_openai_api` を patch して差し替え可能にしている。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 既知の制約・設計上の注意 (Known limitations / Notes)
- 多くの処理は DuckDB 上のテーブル存在を前提とする。テーブル未作成・データ不足の場合はフォールバック（例: ma200_ratio のデータ不足で中立=1.0 を返す等）や警告ログを出す。
- OpenAI API キーは `api_key` 引数または環境変数 `OPENAI_API_KEY` で渡す必要がある。未設定時は `ValueError` を投げる。
- LLM 呼び出しの失敗は基本的に例外を投げずフォールバック（0.0）やスキップで継続する設計（フェイルセーフ）。一部 DB 書き込み失敗時は例外を伝播させる。
- NEWS ウィンドウや時間処理は JST ベースで定義され、内部では UTC naive datetime に変換して DB と比較する。
- `.env` 自動ロードはプロジェクトルートが検出できない場合はスキップされる。
- README / ドキュメント、ユニットテスト、CI 設定、デプロイ手順は今後整備が必要。

### 将来の予定（参考）
- Strategy / execution / monitoring 周りの発注・監視ロジックの実装・統合。
- テストカバレッジの拡充・CI パイプライン整備。
- 追加 API（J-Quants クライアント、kabuステーション連携）の公開インターフェース明文化。
- モデルやプロンプトの改善、より堅牢なレスポンス検証、メトリクス収集。

---

この CHANGELOG はコードの内容から推測して作成しています。実際のリリースノート作成時はリポジトリのコミット履歴・リリース方針に基づき適宜修正してください。