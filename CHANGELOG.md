# Changelog

すべての重要な変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。

- フォーマット: https://keepachangelog.com/ja/1.0.0/
- ルール: 変更はカテゴリ別（Added, Changed, Fixed, Deprecated, Removed, Security）で記載します。

## Unreleased

（現在なし）

## [0.1.0] - 2026-04-03

初回リリース。日本株自動売買システム「KabuSys」の基本モジュール群を実装・公開。

### Added
- パッケージ初期化情報
  - src/kabusys/__init__.py
    - __version__ を "0.1.0" に設定。
    - パブリックモジュールとして data, strategy, execution, monitoring をエクスポート。

- 環境設定管理
  - src/kabusys/config.py
    - .env ファイルおよび環境変数の自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml から探索）。
    - .env/.env.local の読み込み順と保護ロジック（OS 環境変数を protected として上書き防止）。
    - 複雑な .env 行パーサを実装（export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメント処理など）。
    - 自動ロードを KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - Settings クラスを追加し、J-Quants / kabuAPI / LINE / DB /監視/システム関連の設定プロパティを提供（入力検証含む）。
    - 環境値の検証: KABUSYS_ENV（development/paper_trading/live）・LOG_LEVEL の検証。

- AI（NLP）モジュール
  - src/kabusys/ai/news_nlp.py
    - news 記事を銘柄別に集約し、OpenAI（gpt-4o-mini）へ JSON Mode で送信して銘柄ごとのセンチメント（ai_score）を計算。
    - タイムウィンドウ計算（JST 前日15:00〜当日08:30）を calc_news_window で実装。
    - バッチ処理（最大 _BATCH_SIZE = 20 銘柄/回）、トークン肥大化対策（記事数・文字数上限）を導入。
    - 再試行・指数バックオフ（429 / ネットワーク断 / タイムアウト / 5xx に対応）と堅牢なレスポンス検証 (_validate_and_extract) を実装。
    - DuckDB への冪等書き込み（DELETE → INSERT）処理を実装し、部分失敗時に既存スコアを保護。
    - 公開関数: score_news(conn, target_date, api_key=None)。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200 日移動平均乖離（重み70%）と、ニュース由来の LLM マクロセンチメント（重み30%）を合成して市場レジーム（bull/neutral/bear）を判定。
    - prices_daily から ma200_ratio を計算する _calc_ma200_ratio、raw_news からマクロ記事抽出する _fetch_macro_news、LLM 呼び出しとリトライロジックを持つ _score_macro を実装。
    - API 失敗時は macro_sentiment=0.0 へフォールバック（フェイルセーフ）。
    - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、ROLLBACK の保護）実装。
    - 公開関数: score_regime(conn, target_date, api_key=None)。
  - 共通点
    - OpenAI クライアントは OpenAI(api_key=...) を使用し、モデルは gpt-4o-mini を想定。レスポンスは JSON モードで期待。
    - テスト容易性のため、内部の OpenAI 呼び出し関数を patch しやすい構造にしている。

- データ処理 / ETL / カレンダー
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理ロジックを実装: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - market_calendar テーブルの有無に応じた DB 優先ルールと曜日ベースのフォールバックを実装。
    - calendar_update_job により J-Quants から差分取得し冪等保存（バックフィル、健全性チェック含む）を行う。
    - 最大探索日数やバックフィル日数等の安全パラメータを導入（_MAX_SEARCH_DAYS, _BACKFILL_DAYS 等）。
  - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
    - ETL パイプラインの基本構造を実装。差分更新、保存、品質チェック（quality モジュールと連携）を想定。
    - ETLResult データクラスを実装（取得数、保存数、品質問題、エラー一覧などを保持）。
    - etl.py は pipeline.ETLResult を再エクスポート。
    - _get_max_date / _table_exists 等のユーティリティを実装（DuckDB 利用）。
  - src/kabusys/data/__init__.py
    - data パッケージを配置（内部で jquants_client などを参照する設計）。

- 研究（Research）モジュール
  - src/kabusys/research/factor_research.py
    - モメンタム、ボラティリティ、バリュー等の定量ファクター計算を実装:
      - calc_momentum(conn, target_date): mom_1m / mom_3m / mom_6m / ma200_dev
      - calc_volatility(conn, target_date): atr_20, atr_pct, avg_turnover, volume_ratio
      - calc_value(conn, target_date): per, roe（raw_financials を参照）
    - DuckDB SQL を活用した高速集計。データ不足時の None 扱いなど堅牢性を確保。
  - src/kabusys/research/feature_exploration.py
    - ファクター探索ユーティリティを実装:
      - calc_forward_returns(conn, target_date, horizons=None)
      - calc_ic(factor_records, forward_records, factor_col, return_col) — スピアマンランク相関（IC）
      - factor_summary(records, columns) — 基本統計量（count/mean/std/min/max/median）
      - rank(values) — 同順位を平均ランクで扱うランクセンシング
    - pandas 等に依存せず標準ライブラリで実装。
  - src/kabusys/research/__init__.py
    - 主要関数をエクスポート（zscore_normalize は kabusys.data.stats から再利用）。

### Changed
（初回リリースのため該当なし）

### Fixed
（初回リリースのため該当なし）

### Deprecated
（初回リリースのため該当なし）

### Removed
（初回リリースのため該当なし）

### Security
- 環境変数の自動読み込みはプロジェクトルートの検出に依存しており、ルートが特定できない場合は自動ロードをスキップ。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD により明示的にオフに可能。

---

備考（設計上の注記）
- AI 関連処理（news_nlp / regime_detector）は、ルックアヘッドバイアスを避けるため datetime.today()/date.today() を直接参照せず、外部から target_date を受け取る設計になっています。
- DuckDB を想定した SQL 実装と冪等な DB 書き込み（DELETE→INSERT）により、部分失敗時の既存データ保護を重視しています。
- OpenAI 呼び出しは堅牢なリトライ・バックオフ戦略とレスポンス検証を備え、API 障害時にシステム全体が停止しないようフェイルセーフを確保しています（例: macro_sentiment=0.0 のフォールバック、スコア未取得銘柄をスキップ）。

もし特定のモジュールや関数についての詳細な変更点（例: API 仕様や DB スキーマの差分）が必要であれば、該当モジュール名を指定してください。さらに細かいリリースノート（影響範囲、移行手順、サンプル用法）を作成します。