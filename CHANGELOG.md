# Changelog

すべての変更は Keep a Changelog の形式に従い、重要度・種類別に分類しています。  
このリポジトリはセマンティックバージョニングを採用しています。

現在の日付: 2026-03-29

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-29
初回公開リリース。

### Added
- パッケージ基盤
  - パッケージ初期化: kabusys.__init__ にてバージョン "0.1.0" と主要サブパッケージ（data, research, ai, ...）をエクスポート。

- 環境設定・起動時自動 .env 読み込み
  - kabusys.config モジュールを追加。
  - プロジェクトルート（.git または pyproject.toml）を基に .env/.env.local を自動読み込みする仕組みを実装（テスト用に KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - .env パーサーは export 形式・クォート・エスケープ・インラインコメントを考慮した堅牢な実装。
  - Settings クラスを提供し、アプリ設定をプロパティ経由で取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL など）。
  - env / log_level のバリデーション（許容値チェック）および is_live / is_paper / is_dev ヘルパーを実装。

- AI ニュース NLP
  - kabusys.ai.news_nlp モジュールを追加。
  - raw_news と news_symbols を集約し、銘柄毎に OpenAI（gpt-4o-mini の JSON Mode）へバッチ送信してセンチメント（-1.0〜1.0）を算出。
  - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を実装（calc_news_window）。
  - チャンク処理（最大 20 銘柄/コール）、記事トリム（最大記事数・文字数制限）を実装。
  - レスポンス検証ロジック（JSON 抽出、results 配列検証、コード正規化、数値チェック、スコアクリップ）を実装。
  - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ。失敗時はスキップしてフェイルセーフに継続。
  - DuckDB への書き込みは冪等的に DELETE → INSERT（部分失敗時に既存スコアを保護）する実装。
  - テスト容易性のため OpenAI 呼び出し箇所を差し替え可能（_call_openai_api を patch で差し替え可能）。

- 市場レジーム判定
  - kabusys.ai.regime_detector モジュールを追加。
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を算出。
  - マクロ記事は news_nlp の calc_news_window を再利用して抽出。OpenAI 呼び出しは JSON Mode を用い、失敗時は macro_sentiment=0.0 にフォールバック。
  - スコアのクリッピング、閾値によるラベリング、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT と ROLLBACK ハンドリング）を実装。
  - 日付に関してルックアヘッドバイアスを防止する設計（datetime.today()/date.today() を直接参照しない等）。

- リサーチ / ファクタ計算
  - kabusys.research パッケージを追加。以下関数を公開:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離の計算（prices_daily を使用）。
    - calc_value: PER / ROE の計算（raw_financials と prices_daily の組合せ）。
    - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率の計算。
    - calc_forward_returns: 将来リターン（任意ホライズン）を一括取得。
    - calc_ic: factor と将来リターンのスピアマンランク相関（IC）を計算。
    - rank, factor_summary, factor_summary といった統計ユーティリティを実装。
  - DuckDB SQL を多用して効率的に集計・窓関数での計算を実現。
  - 欠損・データ不足時の None ハンドリング、ログ出力を適切に実装。

- データプラットフォーム（ETL・カレンダー等）
  - kabusys.data パッケージを追加（部分実装）。
  - calendar_management モジュール:
    - market_calendar に基づく営業日判定（is_trading_day, is_sq_day）と隣接営業日取得（next_trading_day, prev_trading_day, get_trading_days）。
    - DB 未取得時は曜日ベースでフォールバック（週末は非営業日）。
    - calendar_update_job により J-Quants からの差分取得 → 保存（jq.fetch_market_calendar / jq.save_market_calendar を利用）を実装。バックフィル・健全性チェックを実装。
  - ETL パイプラインの骨組み:
    - pipeline.ETLResult データクラスを実装し、ETL 実行結果の集約 (fetch/save 件数、quality_issues、errors 等) を提供。
    - data.etl で ETLResult を再エクスポート。
    - 差分取得、backfill、品質チェックとの連携を想定した設計（quality モジュール参照）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは引数注入または環境変数 OPENAI_API_KEY を利用する設計（コード内にハードコードしない）。API 呼び出し失敗時は外部にエラーを送出せずフォールバックするため、意図せぬ例外によるクラッシュを抑止。

### Notes / 設計上の重要ポイント
- ルックアヘッドバイアス防止: AI / リサーチ関連の全関数は内部で datetime.today() を参照せず、必ず呼び出し側から target_date を受け取る設計。
- テスト容易性: OpenAI 呼び出しや自動 .env ロードの無効化などテストで差し替え可能なフックを用意。
- DuckDB 互換性: executemany に空リストを渡せない等のバージョン依存を回避するための保護ロジックを実装。
- フェイルセーフ: API 呼び出しエラーやデータ不足時は中立値（スコア 0 や ma200_ratio=1.0）にフォールバックして処理継続する実装方針。

---

今後のリリースでは、ドキュメント強化、ユニット/統合テスト追加、jquants_client の実装詳細公開、Slack 通知や実運用向けの監視・モニタリング機能の追加を予定しています。