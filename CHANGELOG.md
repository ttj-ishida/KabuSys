# Keep a Changelog — KabuSys

すべての変更は Keep a Changelog の形式に従います。  
このファイルはコードベースから推測して作成した初期リリース向けの変更履歴です。

注意: 日付は本ドキュメント作成日時（2026-04-03）を使用しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-03

### Added
- パッケージ初期リリース。
  - パッケージ名: KabuSys
  - バージョン: 0.1.0

- 環境設定管理
  - env 読み込みユーティリティを追加（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml から探索して .env / .env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメント（空白の直前の # をコメント扱い）に対応する堅牢なパーサ実装。
    - OS 環境変数を保護する protected パラメータと override ロジック。
  - Settings クラスを提供（環境変数をプロパティとして取得）。
    - J-Quants / kabuAPI / LINE / DB パス（DuckDB, SQLite）/ 監視閾値 / ログレベル / 実行環境（development/paper_trading/live）等のプロパティ。
    - env と log_level の妥当性チェック、is_live/is_paper/is_dev ヘルパー。

- データプラットフォーム機能（DuckDB ベース）
  - calendar_management モジュール（src/kabusys/data/calendar_management.py）
    - JPX カレンダー管理のロジックを実装（market_calendar テーブル参照）。
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供。
    - DB 登録がない場合は曜日ベースのフォールバック（週末は非営業日）を採用。
    - calendar_update_job により J-Quants から差分取得→冪等保存（fetch/save via jquants_client）。
    - バックフィル、健全性チェック（極端な将来日付のスキップ）導入。
  - ETL / パイプライン ユーティリティ（src/kabusys/data/pipeline.py, etl.py）
    - ETLResult dataclass を公開（取得件数、保存件数、品質問題、エラー一覧などの集約）。
    - 差分更新、バックフィル方針、品質チェック設計（品質問題は収集して呼び出し元で判断）。
    - DuckDB テーブル存在チェック等のユーティリティ。

- AI/NLP 機能
  - news_nlp モジュール（src/kabusys/ai/news_nlp.py）
    - raw_news＋news_symbols から銘柄別に記事を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込む。
    - バッチサイズ制御、記事数・文字数トリム、JSON Mode レスポンスの堅牢なバリデーション、スコアのクリップ（±1.0）。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフでのリトライ、失敗時は当該チャンクをスキップして処理継続（フェイルセーフ）。
    - テスト容易性のため OpenAI 呼び出し箇所を差し替え可能（_call_openai_api を patch 可能）。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST 相当）を計算する calc_news_window を提供。
  - regime_detector モジュール（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を計算し market_regime テーブルへ冪等書き込み。
    - OpenAI 呼び出しのリトライ、API障害時は macro_sentiment=0.0 にフォールバックする堅牢設計。
    - LLM 呼び出しは独自の _call_openai_api を用い、news_nlp とは分離してモジュール結合を避ける。

- リサーチ / ファクター計算機能（src/kabusys/research）
  - factor_research モジュール
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）等を計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率等を計算。
    - calc_value: raw_financials と当日の株価から PER / ROE を計算（EPS 不在時は None）。
    - DuckDB の SQL ウィンドウ関数を活用した実装、欠損時の安全な None 処理。
  - feature_exploration モジュール
    - calc_forward_returns: 指定ホライズン先の将来リターン計算（複数ホライズン対応、入力検証あり）。
    - calc_ic: ランク相関（Spearman 的）で IC を計算（同位は平均ランク）。
    - rank: 値リスト→ランク変換（同順位は平均ランク、丸め対策）。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリだけで計算する統計サマリー。
  - research パッケージの __all__ で主要関数を再エクスポート。

- パッケージ構成と再エクスポート
  - ai, data, research パッケージの主要関数・型を __all__ で公開。
  - data.etl は ETLResult を再エクスポート。

### Changed
- （初期リリースのため該当なし）

### Fixed
- .env パーサの改良点（config モジュール）
  - export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの扱い、キー存在チェックなどを堅牢化。

### Security
- OpenAI API キー管理
  - API キーは api_key 引数または環境変数 OPENAI_API_KEY を使用。未設定時は ValueError を投げることで不正利用を防止。
- 環境変数自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能（テストや CI 向け）。

### Notes / 備考
- 全モジュールで「ルックアヘッドバイアス防止」の設計方針を採用（datetime.today()/date.today() を直接参照せず、target_date ベースで計算）。
- DuckDB のバージョン依存性に配慮した実装（executemany の空リスト回避等）。
- LLM レスポンスの不確実性に対する堅牢化（JSON モードでも余計な前後テキストの復元、未知コードは無視する等）。
- ETL の品質チェックは問題を収集するが自動で Fail-Fast にはしない設計（呼び出し元で判断）。

### Breaking Changes
- なし（初版のため互換性破壊は無し）

### Removed / Deprecated
- なし

---

この CHANGELOG はコードベースの実装内容から推測して作成しています。実際のリリースノートや運用ルールに合わせて必要に応じて修正してください。