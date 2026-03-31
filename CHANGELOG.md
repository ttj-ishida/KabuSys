# Changelog

全ての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従い、セマンティックバージョニングを採用しています。  

最新: 0.1.0

## [0.1.0] - 2026-03-31

### 追加
- 基本パッケージ公開
  - パッケージ名: kabusys
  - public modules: data, research, ai, execution, strategy, monitoring（__all__ によりエクスポート）
  - バージョン: 0.1.0 (src/kabusys/__init__.py)

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装
    - プロジェクトルートの自動検出 (`.git` または `pyproject.toml` を探索)
    - 読み込み順序: OS 環境変数 > .env.local > .env
    - 自動ロードを無効化する環境変数: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
  - .env パーサ実装: コメント、export 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの厳密処理に対応
  - Settings クラスを提供（settings インスタンス経由で利用）
    - 必須項目取得時は未設定で ValueError を送出（例: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`）
    - デフォルト値・型変換: `KABUS_API_BASE_URL`, `DUCKDB_PATH`, `SQLITE_PATH`, `LOG_LEVEL`
    - 環境モード検証: `KABUSYS_ENV` は `development` / `paper_trading` / `live` のみ許可
    - ヘルパープロパティ: `is_live`, `is_paper`, `is_dev`

- AI 関連
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）を JSON mode で呼び出して銘柄別センチメント（-1.0〜1.0）を算出
    - バッチ化（最大 20 銘柄／コール）、1 銘柄あたり記事数と文字数のトリム (_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK)
    - リトライ戦略: 429/ネットワーク断/タイムアウト/5xx を対象に指数バックオフ
    - レスポンスの堅牢なバリデーションと部分書き込み（部分失敗時に他の銘柄データを保護）
    - 公開 API: score_news(conn, target_date, api_key=None)
    - ユーティリティ: calc_news_window(target_date)
    - DuckDB 互換性考慮: executemany の空リスト回避など
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF (1321) の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジームを判定（bull / neutral / bear）
    - OpenAI は gpt-4o-mini を使用、JSON 出力を期待
    - API キー注入可能（引数 or 環境変数 OPENAI_API_KEY）
    - フェイルセーフ: API 失敗時は macro_sentiment=0.0 を採用して継続
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）
    - 公開 API: score_regime(conn, target_date, api_key=None)

- データ関連 (kabusys.data)
  - ETL パイプライン (kabusys.data.pipeline)
    - ETLResult データクラスで ETL の実行結果・品質チェック結果・エラーを集約
    - 差分更新・バックフィル方針・品質チェック統合を想定した基盤実装
    - DuckDB 接続を前提としたユーティリティ (_table_exists, _get_max_date 等)
  - ETL の公開 re-export (kabusys.data.etl: ETLResult)
  - マーケットカレンダー管理 (kabusys.data.calendar_management)
    - market_calendar テーブルを利用した営業日判定ユーティリティ群:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - カレンダー夜間更新ジョブ calendar_update_job により J-Quants API から差分取得→保存（jq.fetch_market_calendar / jq.save_market_calendar を利用）
    - DB データが不完全な場合は曜日ベースのフォールバック（週末は非営業日）
    - 健全性チェック・バックフィル・最大探索日数制限を実装

- リサーチ（ファクター）機能 (kabusys.research)
  - factor_research モジュール
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離の算出
    - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率
    - calc_value: PER, ROE（raw_financials と prices_daily を組合せ）
    - 設計方針: DuckDB を使った SQL+Python 実装、外部 API にはアクセスしない
  - feature_exploration モジュール
    - calc_forward_returns: 複数ホライズンの将来リターンを一括で算出（horizons のバリデーションあり）
    - calc_ic: スピアマンランク相関（IC）計算（結合・欠損除外・3件未満は None）
    - rank: 同順位は平均ランクで処理（丸め対策あり）
    - factor_summary: count/mean/std/min/max/median の統計サマリー

- テスト容易性・堅牢性に配慮した設計
  - OpenAI 呼び出し箇所は内部で _call_openai_api として抽象化し、テスト時に patch しやすい実装
  - ルックアヘッドバイアス防止: datetime.today()/date.today() の直接参照を避け、target_date を明示的引数で扱う関数設計
  - DuckDB のいくつかの実装制約（executemany の空リスト等）に対する回避実装

### 変更
- 初期リリースのため該当項目なし

### 修正
- 初期リリースのため該当項目なし

### 非推奨
- 初期リリースのため該当項目なし

### 削除
- 初期リリースのため該当項目なし

### セキュリティ
- OpenAI API キーや各種トークンは環境変数経由で管理する設計。各関数は明示的にキーを引数で渡せるため、テスト時や一時的キー差し替えに対応。

---

## 既知の制限・注意点
- 必須環境変数が未設定の場合、多くの関数が ValueError を送出します（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）。
- DuckDB 上のテーブルスキーマ（raw_news, news_symbols, ai_scores, prices_daily, raw_financials, market_calendar 等）が前提となっています。データが存在しない場合は多くの関数がデフォルトのフォールバックを行いますが、実運用前にスキーマと初期データの準備が必要です。
- OpenAI 呼び出しは gpt-4o-mini を前提にプロンプト設計されています。モデル仕様変更や API レスポンス形式の変化によりパースが失敗する可能性があります（パース失敗時はフェイルセーフとしてスコア 0.0 やスキップで継続）。
- JSON mode を期待するため、外部 API の出力に前後ノイズが含まれる場合の復元処理は実装していますが完全ではありません。
- 外部ライブラリ（pandas 等）に依存しない設計のため、データ量が大きい解析や一部統計処理は手作り実装になっています。必要に応じて最適化や外部ライブラリ導入を検討してください。

---

今後の予定（例）
- 詳細な入力スキーマのドキュメント化（DuckDB テーブル定義）
- モデル切替や API レスポンス変化に対応する拡張性向上
- 監視 / モニタリング周りの実装強化（Slack通知や監査ログ）
- ユニットテストと E2E テストの充実

（この CHANGELOG はソースコードの実装内容から推測して作成しています。細かな実装意図や将来的な変更はリポジトリのコミット履歴・設計ドキュメントを参照してください。）