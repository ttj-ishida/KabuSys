# Changelog

すべての注目すべき変更点をここに記載します。  
このファイルは「Keep a Changelog」フォーマットに従っています。

※バージョン情報はパッケージ内の __version__（0.1.0）から推測して初回リリースとして記載しています。

## [Unreleased]

## [0.1.0] - 2026-03-27

### Added
- パッケージ構成
  - KabuSys 初期機能群を追加。モジュール群:
    - kabusys.config, kabusys.ai, kabusys.data, kabusys.research などを含むパッケージ基盤。
    - パッケージバージョン: 0.1.0（src/kabusys/__init__.py）。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルまたは OS 環境変数から設定を自動で読み込む仕組みを実装。
    - プロジェクトルート検出は .git または pyproject.toml を起点に行うため、CWD に依存しない。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサ: export プレフィックス、シングル/ダブルクォート中のバックスラッシュエスケープ、インラインコメント規則などに対応。
  - Settings クラスを提供し、プロパティ経由で設定取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須として検証。
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH にデフォルト値を提供。
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL（DEBUG/INFO/...）の検証ロジック。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- AI ニュース解析 (kabusys.ai.news_nlp)
  - raw_news と news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode（response_format）で一括センチメント評価。
  - 実装の特徴:
    - JST 基準のニュースウィンドウ計算（前日15:00 JST ～ 当日08:30 JST）を calc_news_window で提供（DB 比較は UTC naive datetime）。
    - バッチ処理: 最大 20 銘柄 / リクエスト、記事数・文字数のトリム（最大記事数・最大文字数制限）でトークン肥大化を抑制。
    - 再試行（429, ネットワーク断, タイムアウト, 5xx）を指数バックオフで実装。失敗時は当該チャンクをスキップして他チャンクへ継続するフェイルセーフ設計。
    - レスポンスの厳密なバリデーション（JSON 抽出/パース、"results" リスト、code/score の型検証、既知コードのみ採用、数値の有限性確認）。
    - スコアは ±1.0 にクリップ。
    - 書き込みは ai_scores テーブルへ（部分失敗時に他コードの既存スコアを消さないため、DELETE → INSERT を code を絞って実行）。DuckDB の executemany の制約に配慮して空リスト処理をガード。
    - API キーは引数経由または環境変数 OPENAI_API_KEY を使用。未設定時は ValueError。

- マーケットレジーム判定 (kabusys.ai.regime_detector)
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を決定する score_regime を実装。
  - 特徴:
    - ma200_ratio の計算でルックアヘッドを防止（target_date 未満のデータのみ利用）。
    - マクロキーワードで raw_news タイトルを抽出し、OpenAI により macro_sentiment を評価。記事がない場合や API 失敗時は macro_sentiment=0.0 としてフォールバック。
    - 合成スコアのクリップと閾値判定でラベル付与。結果は market_regime テーブルへ冪等的に書き込む（BEGIN / DELETE / INSERT / COMMIT）。API キーは引数または OPENAI_API_KEY。

- リサーチ・ファクター計算 (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M のリターン、200 日 MA 乖離（ma200_dev）を計算。データ不足の銘柄は None を返す。
    - calc_volatility: 20 日 ATR（平均 true range）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率等を計算。true_range の NULL 伝播と窓内カウントで欠損制御。
    - calc_value: raw_financials から直近財務（report_date <= target_date）を取得し PER／ROE を計算（EPS が 0 または NULL の場合は None）。
    - いずれも DuckDB の SQL を活用して高速に集計し、結果は (date, code) キーを持つ dict のリストで返す。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）で将来リターンを LEAD で取得。horizons バリデーションあり。
    - calc_ic: factor_records と forward_records を code で結合して Spearman（ランク相関）で IC を算出（有効サンプル 3 未満は None）。
    - rank: 同順位は平均ランクを返す実装（round(v,12) による安定化）。
    - factor_summary: count/mean/std/min/max/median を計算するユーティリティ。

- データプラットフォーム（DuckDB ベース） (kabusys.data)
  - calendar_management:
    - market_calendar を使った営業日判定ユーティリティを提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB にデータがない場合は曜日（土日）ベースのフォールバックを行う設計。
    - calendar_update_job: J-Quants API（jquants_client）から差分取得して market_calendar を Idempotent に保存。直近のバックフィル、健全性チェック（過度の未来データ検出）を実装。
  - pipeline / etl:
    - ETLResult dataclass を導入し、ETL 実行結果（取得数、保存数、品質問題、エラー）を一元管理。
    - _get_max_date 等のヘルパー、差分取得・バックフィル方針、品質チェック（quality モジュール）との連携設計。
    - kabusys.data.etl は ETLResult を再エクスポート。

- 基本設計方針（全体）
  - ルックアヘッドバイアス防止のため、datetime.today()/date.today() を直接参照する処理は最小化（target_date 引数ベースの設計）。
  - DuckDB を分析 DB として利用し、SQL と Python を組み合わせて効率的に集計。
  - API 呼び出しは堅牢化（リトライ・バックオフ・フェイルセーフ）を優先し、部分失敗時に他データを保護するよう DB 書き込みを工夫。
  - OpenAI 呼び出しは各モジュールで独立実装（モジュール結合を避けるため同名のプライベート関数は共有しない設計）。
  - ロギング／ワーニングを多用して異常検知を容易にする。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Security
- OpenAI API キー、各種トークンは環境変数で管理する設計（Settings で必須チェックを行う）。  
  - 実運用時は secrets 管理やアクセス制御を行ってください。
- .env 自動ロードは明示的に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

---

参考: 各モジュールの設計や制約はソース中の docstring・コメントに詳述されています。実運用や拡張時は README / ドキュメントと合わせて参照してください。