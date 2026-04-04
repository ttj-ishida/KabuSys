# CHANGELOG

すべての重要な変更を Keep a Changelog の形式で記載します。  
慣例に従いセマンティックバージョニングを採用しています。

フォーマット:
- Added: 新規機能
- Changed: 変更・改善
- Fixed: バグ修正
- Security: セキュリティ関連

## [Unreleased]

## [0.1.0] - 2026-04-04
最初の公開リリース。日本株自動売買システムのコア機能群を含みます。

### Added
- パッケージ基盤
  - kabusys パッケージ初期版を追加。バージョンは 0.1.0 に設定。
  - __all__ に data / strategy / execution / monitoring を公開。

- 設定・環境変数管理 (kabusys.config)
  - .env または OS 環境変数から設定を読み込む自動ローダを実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - プロジェクトルートは .git または pyproject.toml を基準に検出（CWD 非依存）。
  - .env パーサ実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応）。
  - .env 読み込み時の上書き制御 (override / protected) を実装し、既存 OS 環境変数を保護。
  - Settings クラスを追加し、アプリケーション設定をプロパティ経由で提供：
    - J-Quants: JQUANTS_REFRESH_TOKEN（必須）
    - kabuステーション API: KABU_API_PASSWORD（必須）、KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - LINE Messaging: LINE_CHANNEL_ACCESS_TOKEN、LINE_USER_ID（任意）
    - DB パス: DUCKDB_PATH（デフォルト data/kabusys.duckdb）、SQLITE_PATH（デフォルト data/monitoring.db）
    - 監視設定: PID_FILE_PATH、KILL_FLAG_PATH、KILL_FLAG_CLEAR_ON_START、CPU/MEMORY/DISK 閾値
    - 環境種別検証: KABUSYS_ENV（development / paper_trading / live）、LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev のユーティリティプロパティ

- AI/NLP モジュール (kabusys.ai)
  - news_nlp: ニュースセンチメント解析機能を追加
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI (gpt-4o-mini) に JSON Mode で問い合わせてスコアを取得。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB クエリに適用）。calc_news_window ユーティリティを提供。
    - バッチ処理: 最大 20 銘柄/コール、1 銘柄あたり最大 10 記事・最大 3000 文字でトリム。
    - 再試行（429/ネットワーク/タイムアウト/5xx）：指数バックオフで最大リトライを実施。
    - レスポンスバリデーション: JSON 抽出、results リストとコード/スコアの検証、未知コードは無視、スコアは ±1.0 にクリップ。
    - ai_scores テーブルへの冪等的な置換（対象コードのみ DELETE → INSERT）を実装。
    - テスト容易化のため _call_openai_api を patch 可能に設計。
  - regime_detector: 市場レジーム判定機能を追加
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次でレジーム（bull/neutral/bear）を判定。
    - マクロニュースは news_nlp の calc_news_window を利用して取得、OpenAI を呼び出して macro_sentiment を算出。
    - スコア合成ロジックと閾値（BULL / BEAR）を実装、結果を market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - API/パース失敗時はフェイルセーフで macro_sentiment=0.0 を採用し処理継続。
    - OpenAI 呼び出しの再試行ロジックとログ記録を実装。
    - LLM 呼び出し関数は news_nlp の同名関数と意図的に分離（モジュール結合を低減）。

- Research / ファクター・特徴量解析 (kabusys.research)
  - factor_research:
    - モメンタム: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）
    - ボラティリティ/流動性: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率
    - バリュー: PER（price / EPS）、ROE（raw_financials から取得）
    - DuckDB 接続を受け取り prices_daily / raw_financials のみを参照する実装。
    - データ不足時の None ハンドリング、および結果を (date, code) をキーとする dict のリストで返す。
  - feature_exploration:
    - calc_forward_returns: 将来リターン（既定 horizons=[1,5,21]）を一括で取得する効率的クエリを実装。
    - calc_ic: スピアマンランク相関（IC）を計算。3 件未満で None を返す。
    - rank: 同順位は平均ランクとするランク関数を実装（丸めで ties 検出を安定化）。
    - factor_summary: count/mean/std/min/max/median の統計サマリーを計算。
  - zscore_normalize をデータ層から再公開（kabusys.data.stats を参照）。

- Data プラットフォーム (kabusys.data)
  - calendar_management:
    - 市場カレンダー管理（market_calendar）と営業日ユーティリティを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - DB 登録がある場合は DB 値優先、未登録日は曜日フォールバック（週末除外）で一貫した判定を提供。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等的に保存する夜間バッチ処理。バックフィルや健全性チェックを実装（_BACKFILL_DAYS, _SANITY_MAX_FUTURE_DAYS）。
  - pipeline / ETL:
    - ETLResult データクラスを公開（pipeline.ETLResult を kabusys.data.etl 経由で再エクスポート）。
    - ETL の設計方針に基づく差分取得 / 保存 / 品質チェックのための骨組みを実装（_get_max_date などのユーティリティを含む）。
    - デフォルトのバックフィル日数、カレンダー先読み等の定数を定義。

### Changed
- 設計上の決定（ライブラリ全体）
  - ルックアヘッドバイアス防止のため、モジュール内で datetime.today() / date.today() の直接参照を避ける設計方針を採用（target_date を明示的に受け取る関数群）。
  - OpenAI 呼び出しのエラー処理はロバストネス重視（API失敗時は例外を上げずフェイルセーフ挙動を優先する箇所あり）。
  - DuckDB に対する互換性考慮（executemany に空リストを渡さないガードなど）を追加。

### Fixed
- （初版リリースにつき特定のバグ修正履歴はありません）

### Security
- 明示的にシークレット系の取得・保護方針を実装
  - 環境変数読み込み時に OS 環境変数を protected として上書きを防止。
  - OpenAI API キーや外部 API トークンは Settings 経由または関数引数で明示的に注入する設計（デフォルトでの無自覚な読み込みやハードコードを回避）。

---

備考:
- 各モジュールは単体テスト容易性を考慮して設計されており、OpenAI 呼び出しやファイル読み込み部分は patch / モックがしやすい構造になっています。
- 本 CHANGELOG はコードベースの内容から推測して作成しています。将来の変更（バグ修正や API 仕様変更）により更新してください。