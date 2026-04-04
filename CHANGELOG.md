# Changelog

すべての注目すべき変更点を記録します。本ファイルは「Keep a Changelog」準拠で作成しています。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-04

初回リリース（ベース機能セットを実装）。

### Added
- パッケージ基盤
  - kabusys パッケージの初期構成を追加。サブパッケージ: data, research, ai, monitoring, execution, strategy（__all__ に公開）。
  - バージョン情報: __version__ = "0.1.0"。

- 環境設定 (kabusys.config)
  - .env ファイルまたは環境変数から設定値を読み込む自動ロード機能を実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - プロジェクトルート検出は .git または pyproject.toml を起点に行い、CWD に依存しない（パッケージ配布後も動作）。
  - .env パーサを実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ、インラインコメントの取り扱い）。
  - .env 読み込み時の保護キー（OS 環境変数）ロジックを実装（override フラグと protected セット）。
  - Settings クラスを実装し、J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境（development/paper_trading/live）/ログレベルなどをプロパティとして公開。
    - デフォルト値（例: KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH、PID/KILL フラグパス、閾値）を設定。
    - env と log_level の値検証を実装（想定外値は ValueError）。

- データ層 (kabusys.data)
  - ETL 用の結果クラス ETLResult を公開（kabusys.data.pipeline.ETLResult を re-export）。
  - ETL パイプライン基盤（kabusys.data.pipeline）を実装:
    - 差分取得・バックフィル・品質チェックを考慮した設計。
    - ETLResult dataclass（品質問題/エラーの集約、辞書変換ユーティリティ）。
    - DuckDB テーブル存在チェック、最大日付取得などのユーティリティ（パイプライン実装の土台）。
  - カレンダー管理モジュール（kabusys.data.calendar_management）を実装:
    - market_calendar テーブルを利用した営業日判定（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）。
    - DB 登録値優先、未登録日は曜日ベースのフォールバック。
    - next/prev の探索上限（_MAX_SEARCH_DAYS）を設け無限ループ回避。
    - calendar_update_job: J-Quants API から差分取得 → 冪等的保存（ON CONFLICT 相当）・バックフィル・健全性チェックを実装。
    - DuckDB の日付型取り扱いと NULL/データ欠落時のログ出力を配慮。

- 研究（Research）モジュール (kabusys.research)
  - ファクター計算群を実装（kabusys.research.factor_research）:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算。データ不足時の None ハンドリング。
    - calc_volatility: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比率（volume_ratio）を計算。データ不足時の None ハンドリング。
    - calc_value: raw_financials から EPS/ROE を用いた PER / ROE を計算（report_date <= target_date の最新財務データを採用）。
    - DuckDB SQL を活用した高効率な時間窓処理（LAG/LEAD/ウィンドウ関数）。
  - 特徴量探索（kabusys.research.feature_exploration）を実装:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD を用いて一括取得。horizons の検証あり。
    - calc_ic: スピアマン（ランク）相関による IC 計算。欠測や同一値（分散ゼロ）ケースで None を返す安定実装。
    - rank: 同順位は平均ランクを返す実装（float の丸めで ties の安定化）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリ。

- AI モジュール (kabusys.ai)
  - ニュースセンチメント（score_news: kabusys.ai.news_nlp）を実装:
    - 対象ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB と比較）。
    - raw_news と news_symbols を元に銘柄ごとに記事を集約（件数・文字数上限でトリム）。
    - OpenAI（gpt-4o-mini, JSON Mode）へ銘柄バッチ（最大 20 銘柄/チャンク）で問い合わせ。
    - エラー耐性: 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ + リトライ、その他はスキップして続行。
    - レスポンスの堅牢なバリデーション: JSON モードでも前後余計な文字列が混ざるケースを補正してパース、results 配列の検査、未知コードの無視、数値チェック、スコアの ±1.0 クリップ。
    - 書き込みは部分失敗耐性を持たせるため「取得成功コードのみ」DELETE→INSERT の置換を実施（DuckDB executemany の空リスト注意点に対応）。
    - テスト容易性のため OpenAI API 呼び出しを差し替え可能に実装（内部 _call_openai_api を patch 可能）。
  - 市場レジーム判定（score_regime: kabusys.ai.regime_detector）を実装:
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロセンチメントは raw_news からマクロキーワードで抽出したタイトルを LLM（gpt-4o-mini JSON Mode）で評価。
    - ルックアヘッドバイアス防止: prices_daily クエリは target_date 未満のみ使用、モジュール内部で datetime.today()/date.today() を参照しない設計。
    - API 失敗時は macro_sentiment=0.0 で継続（フェイルセーフ）。レスポンス JSON の堅牢な取り扱い、API の 5xx/ネットワークのリトライ実装。
    - 結果は market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）、失敗時は ROLLBACK を試行して例外を上位へ伝播。

### Design / Implementation Notes
- いくつの重要な設計方針を採用：
  - ルックアヘッドバイアス防止のため、日付計算において datetime.today()/date.today() を直接参照しない方針を徹底。
  - OpenAI API 呼び出しは JSON Mode を利用し、レスポンスの堅牢性（前後の余計なテキスト、部分的欠陥）を考慮した復元処理を実装。
  - 外部 API 呼び出しは失敗時にプロセスを停止させずフォールバック（デフォルト値）やスキップで継続する設計（可用性重視）。
  - DuckDB のバージョン差分（executemany の空リスト制約など）に配慮した実装。
  - テストしやすさのため外部呼び出し（OpenAI）を差し替え可能に実装。

### Fixed
- なし（初回リリース）

### Changed
- なし（初回リリース）

### Removed
- なし（初回リリース）

---

参照:
- 各モジュールの詳細な設計コメント・ドキュメントは各ソースファイルの docstring に記載されています。質問や補足があれば対象モジュール名を指定して下さい。