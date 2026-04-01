# Changelog

すべての注記は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に準拠します。

現在バージョン: 0.1.0 (初回公開)

## [0.1.0] - 2026-04-01

初回リリース。日本株自動売買プラットフォームのコアライブラリを実装しました。主な追加点と設計方針・注意点は以下の通りです。

### Added
- パッケージ基盤
  - パッケージエントリポイントを追加（kabusys.__init__）。公開モジュールとして data, strategy, execution, monitoring を想定。
  - バージョン情報: __version__ = "0.1.0"。

- 設定管理
  - kabusys.config: .env ファイルおよび環境変数の自動ロード機能を実装。
    - プロジェクトルートの自動検出 (.git または pyproject.toml 基準) に基づき .env / .env.local を読み込み。
    - .env.local は .env を上書き。OS 環境変数は保護される（上書き保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - 複雑な .env 行（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント）に対応するパーサを実装。
  - Settings クラスを提供（settings インスタンス経由でアクセス）。
    - 必須環境変数チェック（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）。
    - デフォルト値: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH 等。
    - 環境モード検証（development / paper_trading / live）やログレベル検証。
    - is_live / is_paper / is_dev のヘルパー。

- データ基盤
  - kabusys.data.pipeline:
    - ETLResult データクラスを実装（ETL 結果・品質問題・エラーを保持）。
    - ETL 実装方針（差分更新、backfill、品質チェックの扱いなど）を反映。
  - kabusys.data.etl: ETLResult を再エクスポート。
  - kabusys.data.calendar_management:
    - JPX マーケットカレンダー管理機能。
    - 営業日判定 API: is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days。
    - 夜間バッチ更新 job: calendar_update_job（J-Quants クライアント経由で差分取得→冪等保存）。
    - DB にデータが不足する場合の曜日ベースフォールバックを実装（安全性を優先）。
    - 最大探索範囲や健全性チェックを実装して無限ループや明らかな異常値を回避。

- リサーチ（ファクター計算 / 特徴量探索）
  - kabusys.research.factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離の計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率の計算。
    - calc_value: PER / ROE を raw_financials と prices_daily から計算。
    - 設計上、prices_daily / raw_financials のみ参照（発注系 API には接続しない）。
  - kabusys.research.feature_exploration:
    - calc_forward_returns: 指定ホライズンの将来リターン計算（デフォルト [1,5,21]）。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算。
    - rank: 同順位を平均ランクで扱うランク関数を実装（丸めによる ties 対策あり）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を算出。
  - kabusys.research.__init__: 主要関数をエクスポート（zscore_normalize は kabusys.data.stats から）。

- AI（ニュース NLP / レジーム判定）
  - kabusys.ai.news_nlp:
    - score_news: raw_news + news_symbols を集約し、OpenAI（gpt-4o-mini, JSON mode）で銘柄ごとにセンチメントスコアを算出して ai_scores テーブルへ保存。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST を対象（UTC で変換して DB 比較）。
    - バッチ処理（1 API コールあたり最大 20 銘柄）、記事トリム（最大記事数・最大文字数）などトークン肥大化対策を実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列、code と score の検証）。
    - リトライ戦略: 429/ネットワーク/タイムアウト/5xx 系は指数バックオフでリトライ。その他のエラーはスキップして継続。
    - 部分成功時に既存の他銘柄スコアを消さないよう、対象コードのみ DELETE→INSERT する実装。
    - テストしやすさのため OpenAI 呼び出し関数は patch 可能（_unittest.mock.patch 対応）。
  - kabusys.ai.regime_detector:
    - score_regime: ETF 1321 の 200 日 MA 乖離（重み 70%）とニュースベースのマクロセンチメント（重み 30%）を合成して market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出は kabusys.ai.news_nlp.calc_news_window を利用し、キーワードリストでフィルタ。
    - OpenAI 呼び出しは独立実装（module 間でプライベート関数を共有しない設計）。
    - API 失敗時は macro_sentiment = 0.0 として継続するフェイルセーフ。
    - 冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）と例外発生時の ROLLBACK 対応。
    - Look-ahead バイアス防止のため date.today() 等を直接参照しない設計。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーや各種トークン・パスワードが必須の設定として明示。API キー未設定時は該当関数が ValueError を投げて早期検出する実装。
- .env 自動ロード時に OS 環境変数の上書きを保護（protected set）する仕組みを導入。

### Notes / Usage / Breaking details
- 環境変数の必須項目（代表例）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - OpenAI を利用する機能を呼ぶ場合は OPENAI_API_KEY が必須（score_news / score_regime 等）。
- デフォルト DB パス
  - DuckDB: data/kabusys.duckdb（DUCKDB_PATH 環境変数で上書き可）
  - SQLite (監視用): data/monitoring.db（SQLITE_PATH 環境変数で上書き可）
- 自動 .env ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途など）。
- AI 呼び出し部はテスト容易性を考慮し差し替え可能に設計されています（内部 _call_openai_api を patch）。
- ルックアヘッドバイアス回避のため、日付ロジックは target_date 引数ベースで動作し、内部で date.today()/datetime.today() を直接参照しない設計を徹底しています。
- DuckDB へのバルク書き込みでは互換性問題（executemany に空リストを与えない等）を考慮しています。

今後の予定（例）
- strategy / execution / monitoring 周りの具体的実装（現行はパッケージ名でエクスポート想定）。
- 追加の品質チェックルールや ETL のモニタリング機能。
- OpenAI モデルやレスポンスフォーマットに関する運用チューニング。

---

過去の変更履歴はこのファイルに追記していきます。バージョン番号の更新、追加/変更/修正点は各リリースごとに明確に記載してください。