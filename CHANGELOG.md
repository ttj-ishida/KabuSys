# Changelog

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
比較的初期のリリースとして、コードベースから推測できる機能・設計の要点をまとめています。

参考: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
- なし

## [0.1.0] - 2026-03-28
初回公開リリース。システムは日本株向けのデータ収集・解析・研究・AI支援判定を行うモジュール群で構成されています。主な追加点・設計方針は以下の通りです。

### Added
- 基本パッケージ構成
  - kabusys パッケージのエントリポイントを追加（バージョン: 0.1.0）。
  - パッケージ公開 API に data, research, ai, その他サブパッケージを想定した __all__ 定義。

- 環境変数・設定管理（kabusys.config）
  - .env/.env.local 自動読み込み機能（プロジェクトルート検出：.git または pyproject.toml を基準）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
  - .env パーサ実装（export 形式、クォート内エスケープ、インラインコメント処理に対応）。
  - Settings クラスで環境変数を型的に取得するプロパティ群（J-Quants, kabuAPI, Slack, DB パス, ログ/環境判定など）。
  - 必須環境変数未設定時の明示的エラー（_require）。

- AI モジュール（kabusys.ai）
  - ニュースセンチメント解析（news_nlp.score_news）
    - raw_news と news_symbols を用いて銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）でスコアリングして ai_scores テーブルへ書き込み。
    - バッチサイズ、文字数制限、最大記事数、JSON mode といった実装上の制約と保護。
    - リトライ（429/ネットワーク断/タイムアウト/5xx）を指数バックオフで実装。エラー時は個別チャンクをスキップしてフェイルセーフに継続。
    - レスポンスバリデーション（JSON 抽出、results 配列、コード整合、数値検査）とスコアの ±1.0 クリップ。
    - テスト用に OpenAI 呼び出しを差し替え可能なフック（_call_openai_api）を用意。

  - 市場レジーム判定（ai.regime_detector.score_regime）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出用キーワード群を定義、OpenAI 呼び出しは独立実装でモジュール間結合を避ける。
    - LLM 呼び出し失敗時は macro_sentiment=0.0 にフォールバック。
    - API 呼び出しでのリトライ（RateLimit, Connection, Timeout, 5xx）と JSON パースの堅牢化。
    - ルックアヘッドバイアスを防ぐ設計（date 比較は target_date 未満／以前のみ使用、datetime.today() を直接参照しない）。

- リサーチ（kabusys.research）
  - factor_research: calc_momentum / calc_volatility / calc_value を実装
    - Momentum: 1M/3M/6M リターン、200日 MA 乖離（データ不足時は None）。
    - Volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率（部分窓に対応）。
    - Value: PER（EPS が無効時は None）、ROE を raw_financials と prices_daily から取得。
    - 全て DuckDB SQL を利用した実装。外部 API への依存なし。
  - feature_exploration: calc_forward_returns / calc_ic / rank / factor_summary
    - 将来リターンを任意ホライズンで計算（horizons の検証あり）。
    - Spearman ランク相関（IC）実装。最小有効サンプルチェック、欠損除外。
    - 値のランク化（同順位は平均ランク）と統計サマリー（count/mean/std/min/max/median）。
    - pandas 等に依存せず標準ライブラリと DuckDB のみで実装。

- データプラットフォーム（kabusys.data）
  - calendar_management モジュール
    - market_calendar を元に営業日判定ロジックを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB のデータがない場合の曜日ベースフォールバック、最大探索範囲による安全機構。
    - JPX カレンダーを J-Quants から差分取得して保存する夜間バッチ（calendar_update_job）。バックフィル・健全性チェック付き。
  - ETL パイプライン（data.pipeline, data.etl）
    - ETLResult dataclass を公開（対象日、取得/保存件数、品質問題、エラー一覧等を含む）。
    - 差分取得・idempotent 保存・品質チェックの設計（品質問題は収集するが ETL 自体は継続し呼び出し元へ判断を委ねる）。
    - jquants_client と quality モジュールを用いる設計（save_*, fetch_* を想定）。

### Changed
- （初回リリースのため変更は無し）

### Fixed
- （初回リリースのため修正は無し）

### Design / Implementation notes（設計上の重要点）
- ルックアヘッドバイアス対策: すべての分析関数は内部で datetime.today()/date.today() を直接参照せず、呼び出し側が target_date を指定する方式。
- データベース操作: DuckDB を主要な分析 DB として使用。書き込みは冪等性（DELETE → INSERT, ON CONFLICT 相当）やトランザクション（BEGIN/COMMIT/ROLLBACK）を意識。
- フェイルセーフ: 外部 API（OpenAI, J-Quants）失敗時は極力例外を全体に波及させず、該当処理のフォールバック／スキップを行う設計。
- テストしやすさ: OpenAI 呼び出し等は内部関数をモック差し替え可能にしてユニットテストを容易にするフックを用意。
- ロギング: 各主要処理に info/debug/warning/exception ログを追加し運用観測性を確保。

---

もし CHANGELOG に追記したいリリースや細かなコミットメッセージ（バグ修正・最適化等）が別途ある場合は、その差分（ファイル名・関数名・修正内容）を教えていただければ、リリースノートとして反映します。