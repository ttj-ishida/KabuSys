# Keep a Changelog — kabusys

すべての重要な変更を記録します。慣例に従い、各リリースごとに「Added / Changed / Fixed / Removed / Deprecated / Security」等で分類しています。

## [Unreleased]
（次回以降の変更をここに記載）

## [0.1.0] - 2026-04-04
初回公開リリース。本リリースでは日本株自動売買システムのコアとなる以下の機能群を実装しています：データ ETL / マーケットカレンダー管理 / リサーチ（ファクター計算・特徴量解析） / ニュース NLP と市場レジーム判定 / 環境設定 といった基盤コンポーネント。主な追加点と設計上の重要な振る舞いは次の通りです。

### Added
- パッケージ基本情報
  - kabusys パッケージを追加。バージョンは `0.1.0`。
  - パッケージ公開 API として modules を __all__ で定義（data, strategy, execution, monitoring）。

- 環境設定 / 自動 .env ロード
  - 環境変数・設定管理モジュールを追加（kabusys.config）。
  - プロジェクトルートを .git または pyproject.toml から探索して .env / .env.local を自動読み込み。
  - 自動ロードを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサ（クォート付き文字列、export プレフィックス、インラインコメント処理、保護された OS 環境変数考慮）を実装。
  - Settings クラスを追加し、J-Quants / kabuAPI / LINE / DB パス / 監視閾値 / 環境種別（development/paper_trading/live）/ログレベルなどの取得・バリデーションを提供。

- ニュース NLP（AI）機能
  - kabusys.ai.news_nlp: raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）によりニュースセンチメントを算出し ai_scores テーブルへ書き込む機能を実装。
    - タイムウィンドウ（前日15:00 JST ～ 当日08:30 JST）の計算ユーティリティ。
    - 銘柄ごとに記事を集約し（最大記事数・文字数トリム）、最大 20 銘柄/チャンクでバッチ送信。
    - JSON Mode レスポンスの検証処理とスコアの ±1.0 クリップ。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ実装。
    - 部分失敗に備え、書き込みは取得した銘柄のみ DELETE→INSERT（冪等性確保）。
    - テスト容易性のため OpenAI 呼び出し部分をモック差替え可能（内部関数を patch しやすい設計）。
  - kabusys.ai.regime_detector: ETF 1321（日経225連動）200日移動平均乖離（重み70%）とニュース由来の LLM マクロセンチメント（重み30%）を合成して日次の market_regime を計算・保存する機能を追加。
    - ma200_ratio の計算（target_date 未満のデータのみ使用しルックアヘッドを回避）。
    - マクロキーワードで raw_news タイトルを抽出し LLM へ送信、API の冗長性対策（リトライ・5xx 判定・フェイルセーフ）。
    - レジームスコア合成とラベリング（bull / neutral / bear）。
    - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）とトランザクションロールバック処理。

- データプラットフォーム（ETL / カレンダー / パイプライン）
  - kabusys.data.pipeline / etl: ETLResult データクラスと ETL の公開インターフェースを追加。
    - 差分取得、保存、品質チェックを想定した設計（backfill、品質問題の収集）。
    - ETLResult に品質問題・エラー一覧の集約と to_dict 変換を実装。
  - kabusys.data.etl: pipeline.ETLResult の再エクスポートを追加。
  - kabusys.data.calendar_management: JPX 市場カレンダー管理
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。
    - market_calendar のデータ優先、未登録日は曜日ベースのフォールバック（週末を休場）を採用。
    - カレンダー夜間バッチ calendar_update_job を実装（J-Quants API 経由で差分取得→保存、バックフィル、健全性チェックを含む）。
    - 最大探索日数・見越し日数などの安全策を導入（無限ループ回避、過剰未来日数チェック）。

- リサーチ（ファクター計算・特徴量探索）
  - kabusys.research.factor_research: モメンタム / ボラティリティ / バリュー等の定量ファクター計算関数を追加。
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（データ不足時は None を返す仕様）。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比を計算（データ不足時の処理あり）。
    - calc_value: PER、ROE を raw_financials と prices_daily 組合せで算出（EPS が 0/欠損時は None）。
    - 設計方針として DuckDB クエリ主体で外部発注 API へのアクセスは行わない。
  - kabusys.research.feature_exploration: 将来リターン calc_forward_returns、IC（calc_ic）、ランク化 rank、factor_summary 等を追加。
    - calc_forward_returns: 複数ホライズンに対応、入力バリデーションあり（horizons は 1..252 の整数）。
    - calc_ic: スピアマン（ランク）相関を実装、サンプル数不足時は None を返す。
    - rank / factor_summary: 同順位の平均ランク処理、基本統計量（count/mean/std/min/max/median）算出。

- 全体設計上の注意点（ドキュメント・コード内コメント）
  - ルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない設計（target_date 引数中心）。
  - OpenAI API 呼び出しは各モジュール内で独立実装し、モジュール間で private helper を共有しない（結合低減）。
  - DuckDB をデフォルト DB として利用。書き込みの冪等性を意識した実装（DELETE→INSERT パターン等）。
  - API 失敗時は例外を上位に投げる箇所とフェイルセーフで 0.0 / スキップする箇所を明確に分離。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Deprecated
- 初回リリースのため該当なし。

### Security
- 環境変数の自動読込時、既存 OS 環境変数は保護され .env.local による上書きは OS 環境変数に影響しないよう設計。
- OpenAI API キーは関数引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を投げることにより誤設定を明確化。

---

メンテナンスノート:
- OpenAI SDK のエラー型（status_code の有無など）に依存しないように getattr を用いた堅牢な処理を導入しています。SDK の将来変更に対する互換性を考慮しています。
- テストのために内部の API 呼び出し関数（_news_nlp._call_openai_api 等）を unittest.mock.patch で差し替えやすい設計にしています。

（以上）