# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

注: この CHANGELOG は提供されたソースコードの内容から推測して作成した初期のリリースノートです。

## [0.1.0] - 2026-03-31

初回公開リリース。

### 追加 (Added)
- パッケージ基盤
  - パッケージエントリポイントを追加（kabusys.__version__ = 0.1.0、__all__ に主要サブパッケージを公開）。
- 設定管理
  - kabusys.config: .env ファイルまたは環境変数から設定を自動読み込みするユーティリティを実装。
    - プロジェクトルートを .git または pyproject.toml を基準に自動検出。
    - 読み込み順: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - クォートやエスケープ、コメントを考慮した行パーサを実装。
  - Settings クラスを提供し、以下の設定プロパティを取得可能:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（development/paper_trading/live 検証）、LOG_LEVEL（検証）
    - ヘルパー: is_live / is_paper / is_dev
- AI（OpenAI）関連
  - kabusys.ai.news_nlp:
    - raw_news / news_symbols を集約して銘柄ごとのニューステキストを作成し、OpenAI（gpt-4o-mini、JSON Mode）でセンチメントを算出。
    - バッチ処理（最大 20 銘柄/コール）、1 銘柄あたり記事数・文字数制限を実装。
    - エラー・429・ネットワーク・5xx に対する指数バックオフリトライ。
    - レスポンスの厳密なバリデーションとスコアのクリップ（±1.0）。
    - ai_scores テーブルへの冪等的な書き込み（DELETE → INSERT、部分失敗時に他レコードを保護）。
    - テスト容易性のため _call_openai_api をモック差し替え可能。
  - kabusys.ai.regime_detector:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news を利用して ma200_ratio とマクロ記事を収集。
    - OpenAI 呼び出し、リトライ、レスポンスパース、フォールバック（API 失敗時は macro_sentiment=0.0）。
    - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - テスト容易性のため _call_openai_api を独自実装（モジュール間で共有しない方針）。
- データプラットフォーム（DuckDB ベース）
  - kabusys.data.calendar_management:
    - JPX カレンダー管理と営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - market_calendar がない場合は曜日ベース（週末）でフォールバック。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等保存（バックフィル・健全性チェックあり）。
  - kabusys.data.pipeline / kabusys.data.etl:
    - ETLResult データクラスを実装して ETL 実行結果を集約。
    - ETL モジュールの内部ユーティリティ（最終日取得、テーブル存在チェック、カレンダーヘルパー等）。
    - 差分更新・バックフィル・品質チェックを想定した設計（jquants_client / quality モジュールとの連携を想定）。
- リサーチ・因子
  - kabusys.research.factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を DuckDB クエリで計算。
    - calc_volatility: 20 日 ATR、ATR 比（atr_pct）、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と価格を組み合わせて PER, ROE を算出（最新の報告期を銘柄ごとに取得）。
    - すべて DuckDB SQL を主体とし、外部 API に依存しない設計。
  - kabusys.research.feature_exploration:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを計算（LEAD を利用）。
    - calc_ic: factor と将来リターンのスピアマンランク相関（IC）を計算（None / 非有限値を除外、3 件未満で None）。
    - rank: 同順位は平均ランクで処理（丸め誤差対策あり）。
    - factor_summary: count/mean/std/min/max/median の統計サマリーを標準ライブラリのみで実装。
- その他ユーティリティ
  - kabusys.data.jquants_client 等の外部クライアントを利用する設計（関数呼び出し部分を分離）。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- OpenAI/API 呼び出しに関する堅牢化:
  - 429・ネットワーク断・タイムアウト・サーバー側 5xx に対して指数バックオフで再試行する実装を導入。
  - JSON パース失敗や予期しないレスポンス構造に対してフォールバック（スキップして処理継続、0.0 を返す等）。
- DuckDB に関する互換性配慮:
  - executemany に空リストを渡さないガード（DuckDB 0.10 の制約回避）。
  - DATE 型の取り扱いを明示的に date オブジェクトへ変換。

### セキュリティ (Security)
- API キーの扱い:
  - OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY を利用。未設定時は ValueError を送出して明示的に失敗させる設計。
  - 自動 .env 読み込みは環境変数で無効化可能（テストや CI 対応）。
- 重要な秘密情報（J-Quants / kabuステーション / Slack）の読み取りは Settings 経由で必須チェックを行う。

### 注意事項 / 設計上の特徴 (Notes)
- ルックアヘッドバイアス対策:
  - ほとんどの処理（ニュースウィンドウ計算、MA 計算、ETL/リサーチ関数、レジーム判定等）で datetime.today() / date.today() を直接参照せず、target_date を明示的に受け取る設計。
- 冪等性:
  - 各テーブルへの書き込みは冪等を意識（DELETE → INSERT、ON CONFLICT を想定）しており、部分失敗時に既存データを不必要に消去しないよう配慮。
- テスト容易性:
  - OpenAI 呼び出し箇所は内部で _call_openai_api 関数を定義し、ユニットテストでパッチ可能にしている。
- DuckDB 前提:
  - データ処理は DuckDB を前提に SQL を中心に実装。テーブル名やスキーマはコード内のクエリに依存。

---

今後のリリースでは以下のような改善が想定されます（未実装/今後の TODO）:
- jquants_client の詳細な実装・エラーハンドリングの拡充。
- ai モジュールの JSON スキーマ検証強化とカバレッジ向上。
- パフォーマンスチューニング（大規模データでのクエリ最適化、並列化）。
- 追加のファクター・ポートフォリオ構築・バックテスト機能。