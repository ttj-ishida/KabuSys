# CHANGELOG

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

注: 本 CHANGELOG はリポジトリ内のソースコードから実装内容を推測して作成しています。実際のリリースノートは必要に応じて調整してください。

## [Unreleased]
- （現在の開発中の変更はここに記載します）

## [0.1.0] - 2026-04-03

### Added
- 初回公開: KabuSys — 日本株自動売買／データ・リサーチ基盤のコアライブラリを追加。
  - パッケージ情報
    - src/kabusys/__init__.py によりパッケージ化。バージョン `0.1.0` を設定。
    - __all__ で主要サブパッケージ（data, strategy, execution, monitoring）を公開。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数からの設定読み込みを実装。
  - 自動ロードの探索はパッケージファイル位置を起点に行い、.git または pyproject.toml をプロジェクトルート判定に使用（CWD に依存しない）。
  - .env/.env.local の読み込み順と上書きルールをサポート（OS 環境変数保護、.env.local は override=True）。
  - export KEY=... 形式やシングル/ダブルクォート、エスケープ、インラインコメントに対応した堅牢な行パーサを実装。
  - 自動ロード無効化用フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを導入し、環境変数から各種設定値をプロパティとして提供：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知用）
    - データベースパス: DUCKDB_PATH（デフォルト: data/kabusys.duckdb）、SQLITE_PATH（監視用）
    - 監視関連: PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU/MEMORY/DISK 閾値
    - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の検証（許容値チェック）とユーティリティ is_live/is_paper/is_dev

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を使い、銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini）でセンチメントを算出。
    - バッチ処理（最大 20 銘柄/コール）、1銘柄あたりの記事上限・文字数トリムを実装。
    - JSON Mode のレスポンス検証（結果構造・型チェック）、数値クリップ（±1.0）。
    - リトライ戦略（429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ）。失敗時は安全にスキップし、部分成功時は既存スコアを保護する実装（DELETE → INSERT で対象コードのみ置換）。
    - calc_news_window(target_date) による JST ベースのニュース収集ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）。
    - パブリック API: score_news(conn, target_date, api_key=None) → 書込件数を返す。API キー未設定時は ValueError を発生。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - prices_daily からの MA 計算（ルックアヘッド防止: date < target_date）、raw_news からマクロキーワードでフィルタ、OpenAI 呼び出し（gpt-4o-mini）で macro_sentiment を評価。
    - LLM 呼び出しの独立実装、API エラー時はフェイルセーフ（macro_sentiment=0.0）を採用。
    - idempotent な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）と適切なロールバック処理。
    - パブリック API: score_regime(conn, target_date, api_key=None) → 成功時に 1 を返す。API キー未設定時は ValueError。

- Data モジュール（kabusys.data）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルからの営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - DB データが存在しない場合は曜日ベースでフォールバック（週末は非営業日）。DB 登録ありの場合は DB 値を優先し、未登録日は一貫して曜日フォールバック。
    - calendar_update_job(conn, lookahead_days=90) による J-Quants からの差分取得・保存処理（バックフィル、健全性チェック、例外ハンドリング）を実装。
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult dataclass を追加（取得/保存件数、品質チェック結果、エラー一覧を保持）。
    - 差分取得ロジック、バックフィル、品質チェックの呼び出し（quality モジュールとの連携を想定）を設計（実装の詳細は pipeline 内の関数群に展開可能）。
    - _table_exists, _get_max_date 等のユーティリティを実装。
  - etl モジュールで ETLResult を再エクスポート（kabusys.data.etl）。

- Research モジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（mom_1m, mom_3m, mom_6m）、ma200_dev（200日移動平均乖離）を calc_momentum(conn, target_date) で算出。
    - Volatility / Liquidity（atr_20, atr_pct, avg_turnover, volume_ratio）を calc_volatility(conn, target_date) で算出（ATR の NULL 伝播制御などを考慮）。
    - Value（per, roe）を calc_value(conn, target_date) で算出（raw_financials から最新レコードを合成）。
    - DuckDB を用いた SQL ベースの処理で、出力は (date, code) ベースの dict リスト。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算 calc_forward_returns(conn, target_date, horizons)（デフォルト [1,5,21]）。
    - IC（Information Coefficient）算出 calc_ic(factor_records, forward_records, factor_col, return_col)（スピアマンのランク相関）。
    - ランク変換ユーティリティ rank(values)（同順位は平均ランク）。
    - 統計サマリー factor_summary(records, columns)（count/mean/std/min/max/median）。
  - research パッケージは data.stats の zscore_normalize を再利用し、主要関数を __all__ で公開。

### Changed
- N/A（初回リリースのため該当なし）

### Fixed
- N/A（初回リリースのため該当なし）

### Security
- 環境変数扱いに関する注意:
  - OpenAI API キー (OPENAI_API_KEY) は明示的に渡すか環境変数で設定する必要がある。未設定時には各 API 呼び出し関数が ValueError を投げるか、フェイルセーフ動作（scoreメソッド内で 0.0 を使用）を行う箇所があるため、運用時は秘密情報の管理に注意すること。

### Notes / Migration
- 環境セットアップ:
  - .env.example を参照して .env を作成してください。自動ロードはデフォルトで有効です（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（Settings のプロパティ参照で ValueError が発生）。
- DuckDB をデフォルトのデータストアとして利用。データベースファイルパスは DUCKDB_PATH で変更可能。
- OpenAI の JSON Mode を利用した結果パースは堅牢化しているが、LLM 出力は常に検証されるため、予期せぬ出力はスキップされる（部分成功パターンに対応）。

---

（以降のリリースでは Added / Changed / Fixed を使って変更履歴を継続してください。）