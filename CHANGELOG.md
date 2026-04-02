# CHANGELOG

すべての変更は Keep a Changelog の形式に従い、重大度（Added / Changed / Fixed / Deprecated / Removed / Security）を区分して記載します。

## [Unreleased]
- 開発中の変更はここに記載します。

## [0.1.0] - 2026-04-02
初回リリース。日本株自動売買システム「KabuSys」のコア機能群を実装しました。主な追加点と設計上のポイントは以下の通りです。

### Added
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。公開 API（__all__）として data, strategy, execution, monitoring を準備。
- 設定管理（kabusys.config）
  - 環境変数 / .env ファイル読み込みモジュールを実装。
  - プロジェクトルート自動検出（.git または pyproject.toml を基準）によりカレントディレクトリに依存しない .env 自動読み込みを実装。
  - .env のパースは export 形式、シングル/ダブルクォート、エスケープ、インラインコメント等を丁寧に扱う実装。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を用意（テスト向け）。
  - OS 環境変数を保護する protected パラメータによる上書き制御（.env.local を override=True で読み込むが既存 OS 環境変数は保護）。
  - Settings クラスを実装し、J-Quants / kabuステーション / Slack / DB / 監視 / システム設定 をプロパティで提供。必須設定は _require() が ValueError を投げる。
  - 環境値の簡潔なバリデーション（KABUSYS_ENV / LOG_LEVEL の許容値チェック）を実装。
- AI（kabusys.ai）
  - news_nlp モジュール（score_news）を実装し、raw_news と news_symbols から銘柄ごとのニュースを集約して OpenAI（gpt-4o-mini）へ送信、JSON-mode レスポンスを検証して ai_scores テーブルへ書き込む処理を提供。
    - タイムウィンドウ計算（JST基準の前日15:00〜当日08:30）を calc_news_window で実装。
    - API 呼び出しはチャンク（最大20銘柄）で投げる実装（1銘柄あたり記事数・文字数制限付き）。
    - レスポンスの厳密なバリデーション（JSONパース回復処理、results フォーマット、コード整合性、数値判定、±1.0クリップ）。
    - リトライ戦略（429・ネットワーク・タイムアウト・5xx は指数バックオフでリトライ）、失敗時はスキップしてフェイルセーフにする設計。
    - テスト容易性のため _call_openai_api をモック差替え可能に設計。
  - regime_detector モジュール（score_regime）を実装し、ETF 1321 の 200 日移動平均乖離（重み70%）とマクロ記事の LLM センチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）を判定・保存する処理を提供。
    - ma200_ratio 計算は target_date 未満のデータのみを使用し、データ不足時は中立（1.0）でフォールバック。
    - マクロ記事取得のためのキーワード群を定義し、該当タイトルを抽出。記事が無ければ LLM 呼び出しを行わずマクロセンチメントは 0.0。
    - OpenAI 呼び出しは news_nlp と意図的に別実装にし、リトライ・エラー処理・JSON パースエラーでゼロフォールバックする堅牢性を確保。
    - market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
- Research（kabusys.research）
  - factor_research：モメンタム / バリュー / ボラティリティ等のファクター計算関数を実装（calc_momentum, calc_value, calc_volatility）。
    - モメンタムは約1m/3m/6m リターン・200日 MA 乖離を計算。データ不足時は None を返す。
    - ボラティリティでは 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。true_range の NULL 伝播制御を実装。
    - バリューでは raw_financials から report_date <= target_date の最新レコードを銘柄毎に取得し PER/ROE を算出。
  - feature_exploration：将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク変換/統計サマリー（rank, factor_summary）を実装。
    - calc_forward_returns は任意のホライズン（デフォルト [1,5,21]）をまとめて取得する効率的クエリを実装。horizons の入力検証あり。
    - calc_ic は Spearman（ランク相関）を自己実装（外部依存なし）し、データ不足時は None を返す。
    - rank は同順位を平均ランクにする実装（浮動小数点丸めを考慮）。
    - factor_summary は count/mean/std/min/max/median を計算。
  - 研究ユーティリティとして zscore_normalize（kabusys.data.stats から再利用）などを公開。
- Data（kabusys.data）
  - calendar_management：market_calendar を用いた営業日判定・次/前営業日検索・期間内営業日取得・SQ日判定・夜間カレンダー更新ジョブ（calendar_update_job）を実装。
    - DB にカレンダーがない場合は曜日ベース（土日非営業）でフォールバック。
    - next/prev_trading_day は DB 登録値を優先し、未登録日は曜日フォールバックで一貫性を保持。探索上限（_MAX_SEARCH_DAYS）を設けて無限ループ防止。
    - calendar_update_job は J-Quants から差分取得して保存（バックフィル・健全性チェックを含む）。
  - pipeline / ETL：ETLResult データクラスを実装して ETL 実行結果を集約（取得数・保存数・品質問題・エラーなどを管理）。ETL モジュールの基本設計（差分取得・保存・品質チェック）を実装方針として定義。
  - etl モジュールで ETLResult を再エクスポート。
- DuckDB 統合
  - 多くのモジュールが duckdb.DuckDBPyConnection を引数に取り、SQL と Python の組合せで処理を行う設計。
- ロギングとフェイルセーフ
  - 各所で詳細な logger 呼び出しを追加し、API 失敗時は例外を直接上げずにフォールバックする方針（ただし DB 書き込み失敗等致命的なケースは上位へ伝播）。

### Changed
- 設計方針の明確化（ドキュメント化）
  - ほとんどのモジュールで「ルックアヘッドバイアス防止」のため datetime.today()/date.today() の直接参照を避ける方針を採用（関数に target_date を渡す設計）。
  - AI 呼び出し部は JSON-mode を利用して厳密な構造を期待し、レスポンス復元ロジック（文字列から最外の {} を抽出）を実装。

### Fixed
- （初版リリースのため特定のバグ修正履歴はなし）

### Deprecated
- （なし）

### Removed
- （なし）

### Security
- OpenAI API キー未設定時に明確な ValueError を投げるため、誤利用や未設定の検出が容易になっています（news_nlp, regime_detector）。環境変数管理で OS の既存キーを保護する実装により、意図しない上書きを防止します。

---

注記:
- 本 CHANGELOG はソースコードから推測して作成しています。実際のコミット履歴や変更差分に基づくものではありません。リリース時には実際のコミットハッシュ、担当者、テスト状況等を追記してください。