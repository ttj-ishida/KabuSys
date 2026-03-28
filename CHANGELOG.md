# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に従います。  

※この CHANGELOG はリポジトリ内のソースコードから実装状況を推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-03-28
初回公開リリース。

### Added
- パッケージ初期化
  - kabusys パッケージの基本構成を追加。バージョンは 0.1.0。
  - __all__ に data, strategy, execution, monitoring を公開。

- 設定 / 環境変数管理 (kabusys.config)
  - .env ファイルと環境変数の読み込み機能を実装（自動ロード機能をデフォルト有効）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。プロジェクトルートは .git もしくは pyproject.toml を基準に探索。プロジェクトルートが見つからない場合は自動ロードをスキップ。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応（テスト用）。
  - .env パーサは以下に対応：
    - 空行・コメント行（先頭 # ）の無視
    - export KEY=val 形式のサポート
    - シングル/ダブルクォートとバックスラッシュエスケープの処理
    - インラインコメント検出（クォート外、直前が空白/タブの場合）
  - _load_env_file の override/protected 機能により OS 環境変数の保護と .env.local による上書きを実現。
  - Settings クラスを提供し、必要な環境変数をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須として検証。
    - KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH のデフォルト値。
    - KABUSYS_ENV（development|paper_trading|live）と LOG_LEVEL の値チェック。
    - is_live / is_paper / is_dev のブールヘルパー。

- AI モジュール (kabusys.ai)
  - news_nlp.score_news を公開。
  - regime_detector.score_regime を実装（市場レジーム判定）。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を使い、銘柄単位でニュースを集約して OpenAI（gpt-4o-mini）でセンチメントを評価し ai_scores テーブルへ書き込む機能を実装。
  - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（内部は UTC naive datetime で扱う）。
  - バッチ処理: 最大 _BATCH_SIZE=20 銘柄ずつ送信。1銘柄あたり最大記事数・文字数でトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
  - JSON Mode 応答のバリデーション実装:
    - results キーの存在・型チェック
    - code の正規化（整数を文字列に変換して照合）
    - score の数値変換と有限性チェック
    - スコアは ±1.0 にクリップ
  - 再試行ポリシー: 429、ネットワーク断、タイムアウト、5xx サーバーエラーに対する指数バックオフでのリトライ（最大回数制御）。
  - API 呼び出し部分は _call_openai_api で分離しており、テスト時に差し替え可能（unittest.mock.patch を想定）。
  - DuckDB への書き込みは冪等性を重視（対象コードのみ DELETE→INSERT）し、DuckDB の executemany の空リスト制約に配慮。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次でレジーム判定（'bull' / 'neutral' / 'bear'）を実装。
  - マクロ記事はキーワードベースで抽出（日本・米国/グローバルのマクロキーワードリスト）。
  - LLM 呼び出しに対する再試行・エラーハンドリングを実装（フェイルセーフ時は macro_sentiment=0.0）。
  - 判定結果を market_regime テーブルに日付単位で冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
  - 設計方針としてルックアヘッドバイアスを避けるため date 引数ベースで処理（datetime.today() を参照しない）。

- データモジュール（kabusys.data）
  - calendar_management:
    - JPX カレンダー管理と営業日判定ロジックを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar が未取得の場合の曜日ベースフォールバックを用意。
    - カレンダー更新用の calendar_update_job を追加（J-Quants API クライアント経由で差分取得 → jq.save_market_calendar）。
    - バックフィル、健全性チェック、最大探索日数制限の実装。
  - pipeline / ETL:
    - ETLResult データクラスを公開（ターゲット日、取得数/保存数、品質問題リスト、エラー一覧など）。
    - 差分更新、バックフィル、品質チェック（kabusys.data.quality を利用）の設計に基づくユーティリティを実装。
    - _get_max_date 等の DB ヘルパーを実装し、テーブル未作成/空時の扱いに対応。
  - etl モジュールは pipeline.ETLResult を再エクスポート。

- リサーチモジュール（kabusys.research）
  - factor_research:
    - Momentum: mom_1m/mom_3m/mom_6m、ma200_dev を計算する calc_momentum を実装。
    - Volatility / Liquidity: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算する calc_volatility を実装。
    - Value: raw_financials から最新財務データを取得し PER・ROE を計算する calc_value を実装。
    - SQL + DuckDB ウィンドウ関数を用いた効率的な実装。
  - feature_exploration:
    - 将来リターン計算 calc_forward_returns（任意ホライズンに対応、ホライズン検証あり）。
    - IC（Information Coefficient）計算 calc_ic（Spearman ランク相関）。
    - ランク関数 rank（同順位は平均ランクで処理）。
    - 統計サマリー factor_summary（count/mean/std/min/max/median）。
  - research.__init__ で主要関数群を公開（zscore_normalize は kabusys.data.stats からの再利用）。

### Changed
- なし（初回リリースのため該当なし）。

### Fixed
- なし（初回リリースのため該当なし）。

### Deprecated
- なし。

### Removed
- なし。

---

注記（実装/運用上の重要点）
- OpenAI API 呼び出しは gpt-4o-mini を前提に実装されており、APIキーは引数で注入可能（テスト用）かつ環境変数 OPENAI_API_KEY から解決可能。
- LLM 呼び出し失敗時は例外で止めずフェイルセーフで継続する設計（macro_sentiment=0.0、もしくはスコア取得銘柄をスキップ）により、ETL/スコアリングパイプライン全体の堅牢性を確保。
- DuckDB を主要な永続化エンジンとして想定しており、SQL 内での NULL/カウント制御や executemany の制約に配慮した実装がなされている。
- .env 自動ロードは配布後の挙動（__file__ を基準としたプロジェクトルート探索）を考慮して実装されているため、実行カレントディレクトリに依存しない。

（以降のリリースでは、実運用での問題点・追加要求（例: Slack 通知フロー、execution/monitoring 実装詳細、テレメトリ等）を基に変更を記録してください。）