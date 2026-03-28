# Changelog

すべての変更は Keep a Changelog のフォーマットに従います。  
また、このプロジェクトはセマンティックバージョニングを採用しています。

## [0.1.0] - 2026-03-28

初回公開リリース。

### 追加 (Added)
- パッケージ初期構成
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - エクスポートモジュール: data, strategy, execution, monitoring

- 設定管理 (kabusys.config)
  - Settings クラスを提供し、環境変数から各種設定を取得するインターフェースを実装。
  - 自動 .env ロード機能:
    - プロジェクトルートを .git または pyproject.toml から検出して .env / .env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - 独自の .env パーサ実装（export形式、クォートとエスケープ、インラインコメントの扱いなどに対応）。
    - OS 環境変数の保護（.env.local は上書き可能だが保護対象キーは上書き不可）。
  - サポートされる設定項目（例）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（development / paper_trading / live）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - 未設定の必須環境変数に対しては ValueError を発生させる _require 実装。

- AI ニュース / レジーム判定 (kabusys.ai)
  - news_nlp.score_news
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメント（ai_scores）を生成・保存。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して扱う）。
    - バッチ処理、トークン肥大対策（1銘柄あたり最大記事数・最大文字数）
    - エラー耐性: 429 / ネットワーク切断 / タイムアウト / 5xx に対する指数バックオフとリトライ。レスポンス検証で不正なら当該チャンクをスキップ。
    - レスポンス検証: JSON 抽出・results 配列の型チェック、コード照合、数値検証、スコア ±1.0 クリップ。
    - DB 書き込みは冪等（該当 date/code の DELETE → INSERT を実行）で部分失敗時の既存データ保護。
  - regime_detector.score_regime
    - ETF (1321) の 200 日移動平均乖離（重み 70%）とニュースのマクロセンチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を算出・保存。
    - マクロニュース抽出はニュースタイトルのキーワードマッチで行い、LLM（gpt-4o-mini）による JSON 出力を期待。
    - API 呼び出し失敗時は macro_sentiment=0.0 のフェイルセーフ。
    - DuckDB を使ったルックアヘッドバイアス対策（target_date 未満のデータのみ使用、datetime.today() を参照しない）。
    - 冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）。書き込み失敗時は ROLLBACK。

- データプラットフォーム関連 (kabusys.data)
  - calendar_management
    - JPX カレンダー管理と営業日ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar が未取得の場合は曜日ベースのフォールバック（週末を非営業日と扱う）。
    - 夜間バッチ calendar_update_job: J-Quants から差分取得・バックフィル・健全性チェック・冪等保存の実装。
  - pipeline / etl
    - ETLResult データクラスを公開（ETL の取得数・保存数・品質問題・エラー集約）。
    - ETL パイプラインの設計に必要なユーティリティ（最終取得日の判定、テーブル存在チェックなど）。
    - 差分取得・バックフィル・品質チェック方針を実装に反映。
  - jquants_client との連携を想定した抽象化ポイントを提供（fetch/save 機能を利用）。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を DuckDB SQL ベースで計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播制御を考慮。
    - calc_value: raw_financials から直近財務データを取得して PER / ROE を計算（EPS が 0/欠損なら None）。
    - 全関数で価格データのみ参照し、外部取引系 API にはアクセスしない設計。
  - feature_exploration
    - calc_forward_returns: 指定ホライズンの将来リターンを一括 SQL で取得（LEAD を利用）。
    - calc_ic: スピアマンランク相関（Information Coefficient）を実装。サンプル数不足時は None。
    - rank, factor_summary: ランク化（同順位は平均ランク）、各カラムの統計要約を純粋 Python 実装（pandas 等非依存）。

- 共通実装上の設計方針（全体）
  - DuckDB を主要なローカル分析 DB として利用。
  - ルックアヘッドバイアス防止: 多くの分析・AI モジュールで datetime.today()/date.today() を参照せず、target_date を明示的に受け取る。
  - DB 書き込みは可能な限り冪等に実装（DELETE → INSERT や ON CONFLICT を想定）。
  - OpenAI API 呼び出しはテスト容易性のため差し替え可能な内部関数でラップ。
  - エラーは原則ログに落として処理を継続できるように（フェイルセーフ設計）。重大エラーは上位へ伝播。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 廃止 (Deprecated)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- OpenAI / J-Quants 等の API キーは環境変数経由で管理。ソースコードに埋め込まないこと。
- .env の自動読み込みはテストや CI のために無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

---

既知の制限 / 注意事項
- OpenAI（gpt-4o-mini）利用部分は API レスポンスの形式（JSON mode）に依存しており、実運用ではレート制限・コスト・レスポンス安定性の考慮が必要。
- news_nlp と regime_detector はそれぞれ独立して OpenAI を呼ぶ実装で、内部の呼び出し関数は共有していません（モジュール結合を低く保つ設計）。
- DuckDB executemany に空リストを渡せないバージョン（例: 0.10）を考慮したガード実装あり。
- calendar_update_job / ETL の外部 API 呼び出し部分（J-Quants クライアント）は外部実装に依存。J-Quants クライアントの実装に合わせて設定・認証が必要。

将来のリリースで想定している改善点（例）
- strategy / execution / monitoring モジュールの実装追加（発注ロジック、モニタリング、Slack 通知等の統合）
- より詳細なテストカバレッジと CI 設定
- OpenAI 呼び出しの共通ラッパー化とレート制御の強化
- PBR・配当利回りなどのバリューファクター追加

--- 

（以上）