# Changelog

すべての重要な変更点は Keep a Changelog の形式に従って記載しています。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [Unreleased]

## [0.1.0] - 2026-03-27
初回リリース。日本株自動売買システムの基盤ライブラリを追加しました。主な追加点は以下の通りです。

### Added
- パッケージ初期化
  - kabusys パッケージのバージョンを 0.1.0 として定義。public モジュールとして data, strategy, execution, monitoring を公開（src/kabusys/__init__.py）。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env ファイルおよび OS 環境変数から設定を読み込む自動読み込み実装。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を起点）で CWD に依存しない探索。
  - .env のパース具合を厳密に実装（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理の細かな挙動）。
  - 読み込みの優先順位: OS 環境変数 > .env.local（override） > .env（非上書き）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
  - Settings クラスを提供（プロパティ経由で必須トークン・パス・ENV/LOG_LEVEL のバリデーションを実施）。
    - 必須項目: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - デフォルト値: KABUSYS_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH 等
    - KABUSYS_ENV と LOG_LEVEL の許容値チェック（development / paper_trading / live 等）
  - 環境変数未設定時は明示的なエラーを投げる _require() ユーティリティ。

- データプラットフォーム（src/kabusys/data/*）
  - calendar_management
    - JPX マーケットカレンダーを管理するユーティリティ群。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day の提供。
    - market_calendar が未取得の場合は曜日ベース（土日除外）でフォールバックする堅牢な設計。
    - calendar_update_job により J-Quants から差分取得し冪等保存（バックフィル・健全性チェックあり）。
  - pipeline / etl
    - ETLResult データクラスと ETL パイプライン用ユーティリティを追加。
    - 差分取得、バックフィル、品質チェック連携を想定した骨組みを実装。
    - DuckDB 上の最大日付取得等のヘルパーを実装。
  - jquants_client を介したデータ取得・保存を想定（クライアントモジュールは外部）。

- AI（src/kabusys/ai/*）
  - news_nlp モジュール（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を基に銘柄ごとのニュースを集約して OpenAI （gpt-4o-mini, JSON mode）でセンチメント評価。
    - calc_news_window による JST ベースのニュース収集ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して扱う）。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄/回）、1銘柄あたりのトリム制限（記事数・文字数）を実装。
    - レスポンスのバリデーション（JSON 抽出、results フォーマット、コード照合、数値チェック）、スコアは ±1.0 にクリップ。
    - API エラー（429/ネットワーク/タイムアウト/5xx）は指数バックオフで再試行、失敗時は該当チャンクをスキップ（フェイルセーフ）。
    - スコア結果は ai_scores テーブルへ冪等的に書き込む（DELETE → INSERT、部分失敗時に既存データを保護）。
    - テスト用に _call_openai_api を patch して差し替え可能。
  - regime_detector モジュール（src/kabusys/ai/regime_detector.py）
    - 日次で市場レジーム（bull / neutral / bear）を判定する処理を実装。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（ニュース LLM、重み 30%）を合成してスコア算出。
    - ma200_ratio の計算は target_date 未満のデータのみを使用（ルックアヘッド防止）。
    - マクロニュースの抽出はマクロキーワードでフィルタ、最大取得件数制限あり。
    - OpenAI 呼び出しは独立実装でリトライ/バックオフを実装し、API 失敗時は macro_sentiment=0.0 で継続するフェイルセーフ。
    - 計算結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、ROLLBACK ハンドリング）。
    - テスト用に _call_openai_api を patch して差し替え可能。

- リサーチ（src/kabusys/research/*）
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR（平均）、相対 ATR、20 日平均売買代金、出来高比率等を計算。tr/prev_close の NULL 伝播を適切に扱う。
    - calc_value: raw_financials から最新の財務データを取得して PER（EPS が 0/欠損時は None）・ROE を計算。
    - DuckDB ベースの SQL 実行により高効率に集計。
  - feature_exploration
    - calc_forward_returns: 指定日の終値から指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算（営業日スキップは LEAD ウィンドウで扱う）。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装。データ不足（有効レコード < 3）の場合は None。
    - rank: 同順位は平均ランクとするランク付け関数（丸め誤差対策あり）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリ機能。
  - 研究用ユーティリティは外部ライブラリに依存せず標準ライブラリ + DuckDB のみで実装。

### Security
- なし（初回リリース）。

### Notes / Migration / Usage tips
- 環境変数:
  - 必須: OPENAI_API_KEY（AI 機能を使う場合）、JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - .env.example を参考に .env/.env.local をプロジェクトルートに配置してください。
  - 自動 .env ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に便利）。
- DB スキーマ:
  - 本ライブラリは DuckDB テーブル名（例: prices_daily, raw_news, ai_scores, market_regime, market_calendar, raw_financials, news_symbols）を前提として処理します。これらのテーブルは利用前に作成・準備してください。
- LLM 呼び出し:
  - OpenAI SDK（OpenAI クライアント）を利用します。テスト可能性のため _call_openai_api を patch して外部呼び出しを模擬できます。
  - API 呼び出しは再試行ロジックとフォールバック（スコア 0.0 / チャンクスキップ）を備えており、部分的障害がシステム全体を停止させない設計です。
- ルックアヘッドバイアス対策:
  - すべての時間判定で date 引数を明示的に受け、datetime.today()/date.today() を内部ロジックで不用意に参照しないように設計されています（再現性の確保）。

今後の予定（想定）
- Strategy / execution / monitoring モジュールの実装（初期公開では skeleton のみ）。
- jquants_client の実装例およびテスト用の DuckDB の初期データセット提供。
- CI での OpenAI 呼び出しのモック事例と ETL の統合テストの整備。

---

これ以降のバージョンでは、功能追加・API 仕様の変更・DB スキーマ変更をセマンティックバージョニングに従って明確に記録します。