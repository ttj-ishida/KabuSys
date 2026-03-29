# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングを使用します。

現在の日付: 2026-03-29

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-29
初回リリース。日本株自動売買プラットフォームのコアライブラリを提供します。主な追加点をモジュール別にまとめます。

### Added
- パッケージ初期化
  - kabusys パッケージのバージョンを 0.1.0 として公開（src/kabusys/__init__.py）。
  - 主要サブパッケージを __all__ にて公開: data, strategy, execution, monitoring。

- 設定管理
  - 環境変数 / .env ファイル読み込みユーティリティを追加（src/kabusys/config.py）。
    - プロジェクトルートの自動検出（.git または pyproject.toml を基準）。
    - .env / .env.local の自動読み込み（優先順位: OS 環境 > .env.local > .env）。
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
    - .env 行パーサは export 形式、シングル/ダブルクォート、エスケープ、インラインコメントを考慮。
    - 必須環境変数未設定時に例外を投げる _require と Settings クラスを提供。
    - 利用可能な設定例:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
      - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
      - DUCKDB_PATH (デフォルト data/kabusys.duckdb), SQLITE_PATH (デフォルト data/monitoring.db)
      - KABUSYS_ENV（development/paper_trading/live を検証）、LOG_LEVEL（DEBUG/INFO/... を検証）
    - Settings で is_live / is_paper / is_dev ヘルパーを提供。

- AI（自然言語処理）関連
  - ニュースセンチメントスコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約して銘柄ごとのテキストを作成。
    - JST 時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を UTC に変換して処理。
    - OpenAI（gpt-4o-mini）へバッチ送信（最大 20 銘柄／チャンク）。
    - JSON Mode を利用しレスポンスを厳密に検証。スコアを ±1.0 にクリップ。
    - レート制限（429）・ネットワーク断・タイムアウト・5xx に対して指数バックオフでリトライ。
    - 書き込みは ai_scores テーブルへの冪等更新（DELETE → INSERT。部分失敗時に既存スコアを保護）。
    - 外部依存を抑え、テスト時は内部の _call_openai_api をモック可能に設計。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書込銘柄数を返す。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次で 'bull'/'neutral'/'bear' を判定。
    - calc_news_window を利用してニュースウィンドウを計算し、raw_news からマクロキーワードでフィルタしたタイトルを取得。
    - OpenAI（gpt-4o-mini）を呼び出してマクロセンチメントを取得。API 失敗時は macro_sentiment=0.0 でフォールバック（フェイルセーフ）。
    - レジームスコア算出ロジック（クリップ、閾値）および market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - 公開 API: score_regime(conn, target_date, api_key=None) → 成功時に 1 を返す。

- 研究（Research）モジュール
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離などを計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務データを取り、PER・ROE を算出（EPS が不適切な場合は None）。
    - DuckDB を用いた SQL ベースの実装で、lookahead バイアスに配慮。

  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons の検証を実施。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。有効レコードが 3 未満なら None。
    - rank: 同順位は平均ランクを与えるランク関数（丸めによる ties 対応）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー。

- データ（Data）モジュール
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - market_calendar テーブルがない場合は曜日（平日）ベースでフォールバック。
    - DB 登録値があればそれを優先し、未登録日は曜日フォールバックで一貫した判定を保証。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を更新（バックフィルや健全性チェックを実装）。
    - 最大探索範囲やバックフィル、異常検出のための定数を設定（例: _MAX_SEARCH_DAYS, _BACKFILL_DAYS, _SANITY_MAX_FUTURE_DAYS）。

  - ETL パイプライン（src/kabusys/data/pipeline.py）
    - ETLResult データクラスを導入（target_date、取得/保存件数、品質問題、エラー一覧など）。
    - 差分更新／バックフィルのロジック、DuckDB のテーブル存在チェック、最大日付取得ユーティリティなどを提供。
    - jquants_client（外部モジュール）と連携してデータ取得・保存・品質チェックを行う想定。

  - etl モジュールの公開インターフェース（src/kabusys/data/etl.py）
    - ETLResult を再エクスポート。

- その他
  - DuckDB を主要データストアとして利用する前提（多くのモジュールが DuckDB 接続を受け取る）。
  - ロギングと堅牢性
    - API 呼び出し失敗時のリトライ／フォールバック設計（OpenAI、J-Quants）。
    - DB 書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で保護。ROLLBACK の失敗時は警告ログ。
    - ルックアヘッドバイアス防止のため、datetime.today()/date.today() に依存しない設計方針が明記された箇所あり（主要処理は target_date に基づく）。

### Changed
- 初回公開のため変更履歴なし。

### Fixed
- 初回公開のため修正履歴なし。

### Security
- 初版のため該当なし。ただし、API キーや機密情報は環境変数で管理する設計。`.env` 自動読み込みをオフにするフラグも用意。

---

注記:
- 本 CHANGELOG はソースコードから推測して作成しています。実際のリリースノートや公開パッケージの配布日・範囲とは差異がある場合があります。必要に応じて日付や細部を調整してください。