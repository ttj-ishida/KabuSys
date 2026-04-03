# CHANGELOG

この CHANGELOG は、提供されたコードベースの内容から推測して作成したものです。実際のリリースノートはリポジトリの履歴（コミットやリリースタグ）に基づいて運用してください。

フォーマットは "Keep a Changelog" に準拠しています。

## [Unreleased]

- （現時点での開発中の変更点はここに記載してください）

## [0.1.0] - 2026-04-03

### Added
- パッケージの初期リリース。モジュール構成:
  - kabusys.config: 環境変数 / .env 管理（自動読み込み機能、.env/.env.local の優先度、保護された OS 環境変数扱い）
    - .env ファイルのパース機能を実装（コメント・export句・クォート・エスケープ対応）。
    - プロジェクトルート検出（.git または pyproject.toml 基準）により CWD に依存しない自動読み込み。
    - 必須環境変数チェック（_require）、環境・ログレベルのバリデーションを備えた Settings クラスを提供。
    - 各種パス／監視閾値／API ベース URL などの設定プロパティを実装。
  - kabusys.ai:
    - news_nlp: ニュース記事を OpenAI（gpt-4o-mini）へ送って銘柄ごとのセンチメントスコアを生成し、ai_scores テーブルへ書き込む処理を実装。
      - ニュース収集ウィンドウ（前日15:00 JST ～ 当日08:30 JST）を計算する calc_news_window を提供。
      - 記事集約、1銘柄あたりのトリミング（記事数・文字数制限）、バッチ送信（最大20銘柄/チャンク）を行う。
      - OpenAI 呼び出しに対するリトライ（429 / ネットワーク / タイムアウト / 5xx）と指数バックオフを実装。
      - レスポンスの厳密なバリデーションとスコアクリップ（±1.0）を実施し、不正レスポンスは安全にスキップ。
      - テスト容易化のため OpenAI 呼び出しを差し替え可能（内部 _call_openai_api を patch 可能）。
    - regime_detector: ETF (1321) の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ冪等書き込みを行う。
      - ma200_ratio の計算（ルックアヘッドバイアス防止のため target_date 未満のデータのみを使用）。
      - マクロキーワードによるニュース抽出、LLM でのセンチメント評価（JSON 出力想定）、リトライ/フォールバック（API 失敗時は macro_sentiment=0.0）。
      - 合成スコアの閾値判定と BEGIN/DELETE/INSERT/COMMIT による冪等化を実装。
  - kabusys.data:
    - calendar_management: JPX マーケットカレンダー管理（market_calendar テーブル参照 / 曜日ベースのフォールバック）。
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
      - calendar_update_job により J-Quants から差分取得して market_calendar を更新（バックフィル、健全性チェックを含む）。
    - pipeline / etl: ETL パイプラインと補助機能。
      - ETLResult データクラス（ETL 実行結果・品質問題・エラー列挙・シリアライズ）を実装。
      - 差分更新・バックフィル・品質チェックを想定した設計。jquants_client 経由での取得と保存を前提。
    - etl: pipeline.ETLResult を公開再エクスポート。
  - kabusys.research:
    - factor_research: ファクター計算（モメンタム、ボラティリティ、バリュー）を実装。
      - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None を返す）。
      - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
      - calc_value: raw_financials から最新財務データを結合して PER / ROE を算出（EPS 無しや 0 の場合は None）。
    - feature_exploration: 将来リターン計算と統計解析ツールを提供。
      - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括で取得可能。
      - calc_ic: factor と forward returns のスピアマンランク相関（IC）を計算（データ不足時は None）。
      - rank: 同順位は平均ランクになるランク付けユーティリティ（丸めで tie 検出安定化）。
      - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
  - package 初期エクスポート設定（kabusys.__init__ にて __version__ = "0.1.0"、主要サブパッケージの __all__ を定義）。

### Changed
- （初回リリースのため特定の「変更」は無し — 初期実装の設計上の決定点を記載）
  - 多くのモジュールで「ルックアヘッドバイアス防止」のため datetime.today()/date.today() を直接参照しない設計を採用（target_date を明示的に引数として受ける）。

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- API キー等の取り扱いに注意:
  - OpenAI API キーは関数引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出して誤操作を防止。
  - 自動 .env 読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テストシナリオ用）。

---

注記:
- DuckDB を前提とした SQL クエリとデータ型変換ロジックが各所に実装されています。実行には DuckDB 接続と想定スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials 等）が必要です。
- OpenAI 呼び出し部分は外部 API に依存するため、実運用では API 料金・レート制限・レスポンス検証・例外ハンドリングを考慮してください。テスト時には内部の _call_openai_api をモックすることで依存を切り離せる設計になっています。
- この CHANGELOG はコード内容から推測してまとめたものであり、実際の機能仕様やリリース履歴と差異がある可能性があります。