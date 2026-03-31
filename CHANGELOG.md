# Changelog

すべての変更は Keep a Changelog の形式に従います。   
現在のパッケージバージョン: 0.1.0（初期公開）

## [Unreleased]

## [0.1.0] - 2026-03-31
初期リリース。日本株自動売買プラットフォーム「KabuSys」のコア機能群を追加しました。主な追加項目は以下のとおりです。

### Added
- パッケージ基礎
  - パッケージ初期化ファイルを追加（kabusys.__init__）。公開サブパッケージ: data, strategy, execution, monitoring（注: monitoring はエクスポートされているが、今回の差分に実装ファイルが含まれない場合あり）。
  - パッケージバージョンを `0.1.0` に設定。

- 環境設定管理
  - `kabusys.config.Settings` を追加。環境変数からアプリ設定（J-Quants, kabuステーション, Slack, DBパス, 監視閾値, 環境・ログレベル判定など）を取得するためのプロパティ群を提供。
  - .env 自動ロード機能を実装:
    - プロジェクトルートの検出は `.git` または `pyproject.toml` を基準に行い、CWD に依存しない探索を実現。
    - 読み込み順序: OS 環境変数 > .env.local > .env
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` による自動ロード無効化に対応（テスト用途）。
    - .env のパースロジックを実装（コメント、 export 形式、クォート内のエスケープ処理、インラインコメント処理などに対応）。
    - `Settings` のバリデーション（KABUSYS_ENV / LOG_LEVEL の許容値チェック、必須項目は未設定時に ValueError を送出）。

- AI（自然言語処理 / レジーム判定）
  - `kabusys.ai.news_nlp.score_news`:
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI (gpt-4o-mini) の JSON mode を用いて銘柄毎のセンチメント（ai_score）を算出。
    - バッチ処理（最大 20 銘柄 / リクエスト）、トークン肥大対策（記事トリム）、リトライ（429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ）を実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results リスト構造、コード照合、数値性チェック、±1.0 クリップ）を行い、ai_scores テーブルへ部分更新（該当コードのみ DELETE → INSERT）。DuckDB の executemany の挙動に配慮した実装。
    - テスト用に API 呼び出し関数 (_call_openai_api) を置き換え可能に実装。
    - ルックアヘッドバイアス防止のため datetime.today() を直接参照しない設計。ニュースウィンドウ計算 (calc_news_window) を提供。
  - `kabusys.ai.regime_detector.score_regime`:
    - ETF 1321（Nikkei 225 連動 ETF）の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news / market_regime を用いた計算、OpenAI 呼び出しのリトライ・フェイルセーフ（API 失敗時は macro_sentiment = 0.0）を実装。
    - レジームスコアのクリッピングと冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）に対応。
    - テスト容易性のため API 呼び出しを差し替え可能。

- Data（データ基盤）
  - `kabusys.data.pipeline.ETLResult` を含む ETL パイプライン向けデータクラスを追加。ETL の実行結果（取得数・保存数・品質問題・エラー等）を構造化して返すインターフェースを提供。
  - ETL パイプライン用ユーティリティ（差分取得、バックフィル、品質チェックの設計方針を反映した実装を想定）。
  - `kabusys.data.etl` で ETLResult を再エクスポート。
  - `kabusys.data.calendar_management`:
    - JPX カレンダー管理（market_calendar）および営業日判定機能を実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装。DB データがまばらな場合でも一貫した挙動を維持するために、DB 値優先・未登録は曜日ベースフォールバックのルールを採用。
    - calendar_update_job: J-Quants API からの差分取得と market_calendar への冪等保存、バックフィルや健全性チェックを実装。
    - 最大探索日数やバックフィル設定等の安全策を組み込み、異常な未来日付の検出や API エラー時の処理を考慮。

- Research（リサーチ／因子計算）
  - `kabusys.research.factor_research`:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR、ATR の相対値（atr_pct）、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と価格を組み合わせて PER, ROE を算出（EPS 欠損時は None）。
    - DuckDB 上で完結する SQL + Python 実装。ルックアヘッドバイアスを避ける設計。
  - `kabusys.research.feature_exploration`:
    - calc_forward_returns: 指定ホライズン（営業日ベース）の将来リターンを一括取得する汎用実装（horizons の検証・並列取得をサポート）。
    - calc_ic: スピアマンのランク相関（IC）を計算するユーティリティ（一致する code での結合、少数データの取り扱い）。
    - rank: 同順位は平均ランクを返す安定的なランク付け実装（浮動小数点丸め対策を含む）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を標準ライブラリのみで計算。
  - `kabusys.research.__init__` で主要関数をエクスポート。

### Changed
- 設計方針として、全ての分析/スコアリング関数で「datetime.today()/date.today() を直接参照しない」実装を採用。外部から target_date を与えることによりルックアヘッドバイアスを防止。

### Fixed
- DuckDB の互換性のため、executemany に空リストを渡さないガードを実装（空リスト渡しによるエラー回避）。
- OpenAI レスポンスのパースにおいて、JSON mode でも前後に余計なテキストが混じるケースを吸収するための最外殻の {} 抽出ロジックを追加。

### Security
- 必須の機密情報（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID 等）は Settings のプロパティ取得時に未設定だと ValueError を送出して明示的に扱うようにし、誤った実行を未然に防止。

### Notes / Implementation details
- OpenAI API 呼び出しは gpt-4o-mini を想定し JSON Mode を利用。リトライ戦略（指数バックオフ）、サーバーエラー判定（status_code による 5xx 判定）などを盛り込み、フェイルセーフとして「API 失敗時は該当スコアを無視（0.0 またはスキップ）」する設計としています。
- テスト容易性を考慮して ai モジュール内の private な _call_openai_api を patch できるように実装しています。
- DB 操作は可能な限り冪等性を保つ（DELETE してから INSERT、トランザクションで COMMIT/ROLLBACK を管理）。
- 一部モジュール（例: monitoring）の実装ファイルが差分中にない場合があります。必要に応じて今後追加予定です。

---
もし CHANGELOG に追記すべき細かい実装差分や、実際のコミット履歴・リリースノートの書式ポリシー（例: セマンティックリリースタグ、変更分類の厳密化など）があれば教えてください。提供されたソースコードから推測して作成していますので、実際のコミット履歴と突き合わせて微調整できます。