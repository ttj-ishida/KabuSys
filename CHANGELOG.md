# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

### Added
- 主要パッケージの初期公開に相当する機能群を追加。
  - パッケージメタ情報: kabusys.__version__ を追加（"0.1.0"）。
- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数の自動読み込み機構を実装（プロジェクトルート検出: .git または pyproject.toml）。
  - .env のパース処理を詳細実装（コメント、export 構文、シングル/ダブルクォート内でのバックスラッシュエスケープ対応）。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - settings API を提供（Settings クラス）:
    - J-Quants / kabuステーション / LINE API / DB（duckdb/sqlite）/Paper Trading 設定項目をプロパティとして取得。
    - PAPER_FILL_MODE の妥当性検証（instant/partial/never/reject）。
    - KABUSYS_ENV / LOG_LEVEL の妥当性検証。
    - 各種監視用しきい値（CPU/MEM/DISK）や pid/kill フラグ等を環境変数経由で取得。
- AI 関連（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - OpenAI（gpt-4o-mini） を用いたニュースセンチメント解析機能を実装（score_news）。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）および DuckDB からの記事集約処理を実装。
    - バッチ処理（1 API コール最大 20 銘柄）・トークン過膨張対策（記事数・文字数のトリム）を実装。
    - JSON Mode 応答のバリデーションと復元処理（前後余計なテキストが混ざるケースへの対処）。
    - レート制限・ネットワーク断・5xx に対する指数バックオフリトライ。API 失敗時はスキップしてフェイルセーフで継続。
    - テスト用フック: _call_openai_api を unittest.mock.patch で差し替え可能。
    - ai_scores テーブルへの冪等書き込み（失敗時に他コードの既存スコアを消さないようコード単位で DELETE → INSERT）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次でレジーム判定（score_regime）。
    - prices_daily / raw_news / market_regime を参照して冪等で DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - マクロキーワードによる記事抽出、LLM 呼び出しのリトライ／フェイルセーフ実装。
    - API キー注入可能（引数または環境変数 OPENAI_API_KEY）。
- Data（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダー管理ロジック、営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。
    - market_calendar が未取得の場合は曜日ベース（平日）でのフォールバックを実装。
    - 夜間バッチ更新 job（calendar_update_job）を実装（J-Quants から差分取得し冪等保存、バックフィル、健全性チェック）。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを導入（ETL 実行結果の集約、品質問題・エラーの保持、辞書化ユーティリティ）。
    - pipeline の公開型を etl モジュールで再エクスポート（ETLResult）。
    - 差分取得・バックフィル・品質チェック等の方針を実装（実装の骨子）。
- Research（kabusys.research）
  - factor_research モジュールを実装
    - モメンタム、ボラティリティ（ATR/出来高/売買代金）、バリュー（PER/ROE）などのファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB を用いた SQL 主体の実装、データ不足時の None ハンドリング。
  - feature_exploration モジュールを実装
    - 将来リターンをまとめて計算する calc_forward_returns（任意ホライズン対応、入力検証あり）。
    - IC（Spearman のランク相関）計算（calc_ic）、ランク変換ユーティリティ（rank）。
    - ファクター統計サマリー（factor_summary）。
  - research パッケージの __all__ を整備して主要関数を公開。

### Changed
- （初期公開のため該当なし）

### Fixed
- （初期公開のため該当なし）

### Security
- OpenAI API キーは引数または環境変数で注入する設計。自動で .env を読み込むが、環境変数優先、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化が可能。

## [0.1.0] - 2026-04-09

初回公開（ベースライン機能）。上記「Added」に含まれる機能群を含むリリース。

- 主要な機能
  - 環境変数 / .env 管理（settings）
  - DuckDB を前提としたデータ ETL / calendar / research / factor 計算基盤
  - OpenAI を用いたニュースセンチメント解析と市場レジーム判定
  - Paper Trading / モニタリング用設定を含む運用支援機能群

- 実装上の注意（重要）
  - ルックアヘッドバイアス回避: 各 AI / リサーチ処理は内部で datetime.today() / date.today() を参照せず、外部から与えた target_date に基づいて処理を行う設計になっています。
  - API 失敗時のフェイルセーフ: OpenAI や外部 API の失敗は基本的に例外で全体を止めず、デフォルト値（例: macro_sentiment=0.0）やスキップで継続する実装です。
  - DuckDB executemany の互換性: 一部処理で空リストを executemany に渡さないようガードを入れています（DuckDB 0.10 対策）。
  - テスト容易性: OpenAI 呼び出しの内部関数はモジュール内で分離しており、テストで差し替え可能です。

---

参照: この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノートはプロジェクトのリリース管理方針に合わせて調整してください。