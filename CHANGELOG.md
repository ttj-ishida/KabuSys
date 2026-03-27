# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに従って記載します。  
このプロジェクトはセマンティックバージョニングに従います。  

※この CHANGELOG は与えられたコードベースから推測して作成した初期リリースの記録です。

## [Unreleased]

## [0.1.0] - 2026-03-27
初回公開リリース。日本株自動売買システムのコアライブラリ群を実装しました。主な追加点は以下のとおりです。

### Added
- パッケージエントリポイント
  - kabusys パッケージのバージョン管理と公開モジュール定義を追加（__version__ = 0.1.0, __all__ を設定）。

- 環境設定読み込み機能（kabusys.config）
  - .env / .env.local ファイルおよび OS 環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 自動ロードを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサを実装（export 形式対応、シングル/ダブルクォート内のエスケープ処理、コメント処理の細かい取り扱い）。
  - ファイル読み込み失敗時は警告を出す堅牢な実装。
  - 上書き動作: .env と .env.local の優先順位を実装（OS 環境変数は保護される）。
  - Settings クラスを導入し、以下の設定プロパティを提供：
    - J-Quants、kabuステーション、Slack、データベースパス（DuckDB/SQLite）、環境（development/paper_trading/live）およびログレベルの取得とバリデーション。
  - 必須環境変数未設定時は ValueError を送出する挙動を実装（ユーザ向けエラーメッセージ付き）。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols を集約して銘柄別のニュースを OpenAI（gpt-4o-mini）へ送信し、センチメント（ai_score）を ai_scores テーブルへ書き込む処理を実装。
  - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算するユーティリティ（calc_news_window）。
  - バッチ処理（1 API コールあたり最大 20 銘柄）、1銘柄あたり記事数上限（デフォルト 10 記事）、文字数トリム（3000 文字）を実装しトークン肥大化を抑制。
  - JSON Mode を利用した厳密な JSON レスポンス想定。レスポンス整形・パースの冗長性対策（前後余計なテキストが混じるケースの復元）を実装。
  - リトライ戦略: 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフによるリトライ。
  - レスポンスのバリデーション（results 配列、code と score の存在、数値化、既知コードのみ抽出）を実装。スコアを ±1.0 にクリップ。
  - 部分失敗に備えた DB 書き込み（取得済みコードのみ DELETE→INSERT で置換）を実装。DuckDB の executemany の制約を考慮。
  - API キーを引数で注入可能（テスト容易化）。_call_openai_api をテスト時にモック差し替え可能。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する機能を実装。
  - MA200 の計算においてルックアヘッドバイアスを排除（target_date 未満のみを使用）。
  - マクロニュース抽出（マクロキーワードによるフィルタ）・LLM 呼び出し（gpt-4o-mini、JSON Mode）・リトライ（指数バックオフ）・フェイルセーフ（API 失敗時 macro_sentiment=0.0）を実装。
  - スコア合成ロジック（クリッピング、閾値に基づくラベリング）と、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
  - API キー注入可能、テスト時の差し替えフックを用意。

- データ処理・プラットフォーム（kabusys.data）
  - ETL インターフェース: pipeline.ETLResult を公開（kabusys.data.etl）。
  - ETL パイプライン（kabusys.data.pipeline）:
    - 差分更新ロジック（最終取得日ベース）、backfill（デフォルト 3 日）、品質チェックフレームワークとの統合を想定。
    - ETLResult dataclass を導入し、取得数・保存数・品質問題・エラー概要などを集約・シリアライズ可能に実装。
    - DuckDB 上で最大日付取得などユーティリティを実装。
  - マーケットカレンダー管理（kabusys.data.calendar_management）:
    - market_calendar テーブルを基に営業日判定ロジックを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にカレンダーがない場合は曜日ベースのフォールバック（土日除外）。
    - next/prev_trading_day は最大探索日数（_MAX_SEARCH_DAYS=60）を設定して無限ループを防止。
    - calendar_update_job を実装し、J-Quants API から差分取得→冪等保存（ON CONFLICT 相当）・バックフィル・健全性チェック（将来日付の異常検出）を行う。
    - jquants_client を呼び出しての取得・保存呼び出しを想定（失敗時はログ出力して 0 を返す）。

- リサーチ・特徴量（kabusys.research）
  - factor_research モジュール:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER、ROE）を計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB に対して SQL を中心に計算し、結果を (date, code) キーの辞書リストで返す設計。
    - データ不足時の None 扱いなど堅牢な扱い。
  - feature_exploration モジュール:
    - 将来リターン計算（calc_forward_returns、任意ホライズン、デフォルト [1,5,21]）。
    - IC（Information Coefficient）計算（calc_ic: スピアマンのランク相関を実装、3 件未満で None）。
    - ランキング（rank: 同順位は平均ランクを取る実装）および統計サマリー（factor_summary: count/mean/std/min/max/median）。
  - research/__init__.py で主要ユーティリティを公開（zscore_normalize は外部モジュールから再利用）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security / Operational notes
- .env 読み込み時に OS 環境変数は保護され、.env.local の上書きでも OS 環境変数は上書かれません（protected set）。
- OpenAI API キーは関数引数から注入可能で、環境変数 OPENAI_API_KEY を参照する挙動を持ちます。未設定時は ValueError を送出します。
- LLM 呼び出しは明示的に JSON Mode を利用し、パース失敗時は安全にフォールバック（多くのケースで 0.0 またはスキップ）します。

### Testing / Extensibility
- LLM 呼び出し点は内部関数（_call_openai_api）で抽象化されており、ユニットテストでパッチ可能。
- 環境読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD を使ってテスト時に無効化可能。

---

将来的なリリースでは、既存機能のバグ修正、API 呼び出しのさらなる堅牢化、より多くのファクタや取引戦略・実行モジュール（strategy / execution / monitoring）などの追加を想定しています。