# Changelog

すべての重要な変更履歴はこのファイルに記録します。フォーマットは Keep a Changelog に準拠します。  

## [Unreleased]

（現時点のコードベースでは初回リリース相当の機能群が導入されています。次回以降の変更はここに記載してください。）

---

## [0.1.0] - 2026-03-31

初期リリース。日本株自動売買プラットフォームのコアライブラリ群を提供します。設計方針として「ルックアヘッドバイアスの排除」「DuckDB を用いたローカル分析基盤」「外部 API 呼び出しのフェイルセーフ化」「モジュール分離とテスト容易性」を重視しています。

### Added
- パッケージ基礎
  - kabusys パッケージの公開モジュール定義を追加（data, strategy, execution, monitoring を __all__ として公開）。
  - パッケージバージョンを 0.1.0 に設定。

- 設定 / 環境変数管理（kabusys.config）
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込みする仕組みを追加。
  - 自動読み込みを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサーは export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメント処理をサポートする堅牢な実装。
  - OS 環境変数（既存の os.environ）の保護（protected set）や override フラグをサポート。
  - Settings クラスを追加し、J-Quants / kabu API / Slack / DB パス / 監視閾値 / 環境（development/paper_trading/live）/ログレベルをプロパティ経由で取得・検証する API を提供。
  - 必須環境変数未設定時は ValueError を発生させる _require() を実装。

- AI モジュール（kabusys.ai）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約し、銘柄ごとに記事（タイトル＋本文）を結合して OpenAI（gpt-4o-mini）の JSON モードでバッチ評価。
    - JST ベースのニュース収集ウィンドウ計算（前日15:00 JST〜当日08:30 JST）を calc_news_window() で実装。
    - バッチサイズ制御、1銘柄あたりの記事数・文字数トリム、最大リトライ（429/ネットワーク/タイムアウト/5xx）と指数バックオフを実装。
    - レスポンスの厳密バリデーション（JSON 抽出、results 配列、code/score の型チェック、未知コードは無視、数値の有限性確認）を実装。
    - ai_scores テーブルへの冪等的置換（DELETE→INSERT）を実装。DuckDB の executemany 空リスト制約に対応。
    - API 呼び出し箇所をモジュールローカル関数化し、テスト時に unittest.mock.patch で差し替え可能。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（ma200_ratio）とマクロニュースの LLM センチメントを重み合成して日次の市場レジーム（bull/neutral/bear）を算出。
    - マクロキーワードによる raw_news フィルタ、OpenAI 呼び出し（gpt-4o-mini）による JSON レスポンス解析、リトライ/フォールバック（失敗時 macro_sentiment=0.0）を実装。
    - レジームスコア合成ロジック（MA 重み 70% / macro 重み 30%、スコアクリップ）と market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を提供。
    - OpenAI クライアント生成を引数なしでも環境変数 OPENAI_API_KEY から解決可能。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA に対する乖離(ma200_dev) を DuckDB SQL ウィンドウで計算。データ不足時の None 処理。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率（volume_ratio）を計算。true_range 計算で NULL 伝播を考慮。
    - calc_value: raw_financials から最新の EPS/ROE を結合して PER/ROE を計算。target_date 以前の最新財務データを取得。
  - feature_exploration:
    - calc_forward_returns: 指定 horizon（営業日）ごとの先行リターンを LEAD を使って一度に取得。horizons のバリデーションあり。
    - calc_ic: スピアマンランク相関（Information Coefficient）を実装。必要件数 3 未満で None を返す。
    - rank: 同順位の平均ランク（ties を平均順位で処理）を実装（丸め対策あり）。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を計算するユーティリティ。

- データ基盤（kabusys.data）
  - calendar_management:
    - market_calendar を用いた営業日判定ユーティリティ群（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を追加。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫した挙動を実装。
    - calendar_update_job による J-Quants からの差分取得・バックフィル（直近 BACKFILL_DAYS）・健全性チェック（未来日付上限）・冪等保存を実装。jquants_client を利用して取得/保存を委譲。
  - pipeline / etl:
    - ETLResult dataclass を実装（取得件数、保存件数、quality_issues、errors 等を格納）。has_errors / has_quality_errors / to_dict を提供。
    - 差分更新フローに合わせた定数・ユーティリティ関数を実装（テーブル存在チェック、最大日付取得など）。
  - etl モジュールは ETLResult を再エクスポート。

- その他
  - モジュールレイアウトおよび public API の __all__ 設定を各パッケージで整備。
  - ロギング呼び出し（info/warning/debug）を各処理に追加し運用時の観測性を確保。

### Changed
- （初回リリースのため変更履歴は存在しません）

### Fixed
- （初回リリースのため修正履歴は存在しません）

### Deprecated
- なし

### Removed
- なし

### Security
- OpenAI API キーは引数経由または環境変数 OPENAI_API_KEY で解決され、未設定時は ValueError により早期に失敗する仕様を明示（誤った無効操作を防止）。
- .env 自動ロードでは既存の OS 環境変数を保護する設計（protected set）。

---

注記:
- 多くの外部 API 呼び出し箇所（OpenAI / J-Quants など）は例外発生時にログ警告を出しつつフォールバックや部分スキップするよう設計されており、本番プロセスの安定性を重視しています。
- テスト容易性のため、OpenAI 呼び出し等はモジュール内プライベート関数に分離しており、unittest.mock.patch による差し替えが想定されています。