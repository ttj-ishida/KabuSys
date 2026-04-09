# Changelog

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは「Keep a Changelog」の慣例に従っています。  

- フォーマット: https://keepachangelog.com/ja/1.0.0/
- バージョン番号はセマンティックバージョニングに従います。

## [Unreleased]

（今後の変更をここに記載します）

## [0.1.0] - 2026-04-09

初回リリース。日本株自動売買システム "KabuSys" のコア機能群を実装しました。以下は主な追加点と実装上の注意点です。

### Added
- パッケージ基盤
  - パッケージメタ情報と公開 API を追加（src/kabusys/__init__.py）。初期版では data, strategy, execution, monitoring を公開対象としている（各モジュールは順次実装）。
  - バージョン: 0.1.0

- 設定管理
  - 環境変数・設定読み込みモジュールを追加（src/kabusys/config.py）。
    - .env, .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env パーサは export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント（スペース/タブ前の #）に対応。
    - 環境変数上書き挙動: .env は既存変数を上書きせず、.env.local は上書き（ただし OS 環境変数は protected として保護）。
    - Settings クラスを提供し、J-Quants / kabu API / LINE / DB パス /監視閾値 / システム環境などをプロパティで取得。
    - 設定値検証: PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL の許容値チェックを実装（不正時は ValueError を送出）。
    - デフォルト DB パス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"、Paper Trading 用 SQLite のパスは PAPER_TRADING_SQLITE_PATH で変更可能。
    - 監視用 PID/KILL フラグパスやフラグのクリア挙動の設定を提供。

- データ（Data）モジュール
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダー（market_calendar）を扱うユーティリティ群を提供。
    - 営業日判定、前後の営業日取得、期間内営業日取得、SQ判定などの API（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。
    - DB 登録がない日は曜日ベース（土日非営業日）でフォールバックする一貫したロジックを採用。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新（バックフィル・健全性チェックあり）。
  - ETL パイプライン（src/kabusys/data/pipeline.py / etl.py）
    - ETLResult データクラスを公開（etl.py は pipeline.ETLResult を再エクスポート）。
    - 差分更新、保存（idempotent save）、品質チェック（quality モジュール連携）を想定した設計。バックフィル日数、カレンダー先読み、品質チェックの収集方針を定義。
    - 取得開始日やバックフィル等の定数（例: _MIN_DATA_DATE, _DEFAULT_BACKFILL_DAYS）を定義。

- 研究（Research）モジュール
  - factor_research（src/kabusys/research/factor_research.py）
    - モメンタム / ボラティリティ / バリュー等のファクター計算関数を実装。
      - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
      - calc_volatility: 20日 ATR（atr_20）、相対ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算。必要行数未満は None。
      - calc_value: raw_financials から最新財務（report_date <= target_date）を取得し PER/ROE を計算（EPS が 0/欠損 の場合は None）。
    - DuckDB を用いた SQL + Python 実装で、prices_daily / raw_financials のみ参照。
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）：指定ホライズン後の終値からリターンを算出（デフォルト [1,5,21]）。horizons の検証あり。
    - IC（Information Coefficient）計算（calc_ic）：ランク相関（Spearman）を実装。記録が不十分な場合は None。
    - ランク変換ユーティリティ（rank）：同順位は平均ランクを割り当てる。
    - ファクター統計要約（factor_summary）：count/mean/std/min/max/median を算出。None は除外。
  - research パッケージの __init__.py で主な関数を再エクスポート（zscore_normalize は kabusys.data.stats から）。

- AI（自然言語処理）モジュール
  - news_nlp（src/kabusys/ai/news_nlp.py）
    - raw_news + news_symbols を集約し、OpenAI（gpt-4o-mini）を使って銘柄ごとのニュースセンチメントを算出して ai_scores テーブルへ書き込むワークフローを実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で計算。
    - 1 銘柄あたりの記事数/文字数を制限する（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - バッチ処理（_BATCH_SIZE=20）で API に送信し、429・ネットワーク断・タイムアウト・5xx を指数バックオフでリトライ。
    - レスポンスのバリデーション（JSON 抽出, results 配列, code と score の検証、数値チェック）を厳格に行い、スコアは ±1.0 にクリップ。
    - DB 書き込みは部分失敗の保護を考慮し、取得したコードのみ DELETE → INSERT（トランザクション）で置換。
    - API キーは引数で注入可能。未設定時は環境変数 OPENAI_API_KEY を参照し、未設定なら ValueError。
  - regime_detector（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull / neutral / bear）を判定し market_regime テーブルへ冪等書き込みする機能を実装。
    - マクロキーワードで raw_news をフィルタし、最大 20 件を gpt-4o-mini に投げる。API リトライ/フェイルセーフ（失敗時 macro_sentiment=0.0）。
    - MA 計算とニュースウィンドウはルックアヘッドバイアスを避ける設計（target_date 未満のデータのみを利用、datetime.today() を直接参照しない）。
    - OpenAI クライアント呼び出しはモジュール内で独立して実装（news_nlp と共有しない設計）。

- パッケージ構成
  - ai, data, research, などのサブパッケージを実装し、主要ユーティリティを __all__ で公開。
  - テーブル/スキーマへの書き込みは冪等性（DELETE/INSERT や ON CONFLICT を想定）を重視。

### Changed
- 初版リリースのため該当なし。

### Fixed
- 初版リリースのため該当なし。

### Notes / 実装上の注意
- OpenAI API 呼び出し部分はテスト容易性のため _call_openai_api を直接モック可能にしている。
- DuckDB の executemany に空リストを渡せない制約に対応している（空のときは実行をスキップ）。
- 日付/時刻は日付オブジェクト（date）や UTC naive datetime を明確に使い分け、タイムゾーン混入を防止する設計方針。
- 一部モジュール（例: strategy, execution, monitoring）はエントリとして名前が公開されているが、このリリースでは機能実装が限定的／未実装の可能性があるため、実使用時は各モジュールの存在と状態を確認してください。

### Security
- 環境変数の自動ロードはデフォルトで有効。CI/テスト等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI API キー等の秘密情報は環境変数にて管理することを想定しています。 .env ファイルの取り扱いに注意してください。

---

（以降のバージョンでは変更点をこのファイルに追記してください）