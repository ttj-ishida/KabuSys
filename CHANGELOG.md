# Changelog

すべての注目すべき変更点は Keep a Changelog に準拠して記載します。  
慣例: 重大度の高い変更は Breaking Changes として別途記載します。

## [0.1.0] - 2026-03-31

### Added
- パッケージ初期リリース。モジュール群を実装・公開。
  - kabusys.config
    - .env ファイルと環境変数の読み込み機能を実装。
    - プロジェクトルート（.git または pyproject.toml を基準）から .env/.env.local を自動読み込み（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - 複雑な .env パース処理を実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント処理などに対応）。
    - OS 環境変数を保護する protected 上書きロジックを実装（.env.local は上書き、.env は既存変数を上書きしない）。
    - Settings クラスを公開（J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / 環境・ログレベル判定等のプロパティ）。
    - 必須変数未設定時は明確な ValueError を発生させる _require 実装。
  - kabusys.ai.news_nlp
    - ニュース記事を OpenAI（gpt-4o-mini、JSON mode）でセンチメント評価し、銘柄ごとに ai_scores テーブルへ書き込む機能を実装（score_news）。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC 変換）を提供（calc_news_window）。
    - バッチ化（最大 20 銘柄/チャンク）、トークン肥大対策（記事数・文字数トリム）を実装。
    - OpenAI API のリトライ（429, ネットワーク断, タイムアウト, 5xx）と指数バックオフを実装。
    - レスポンスの厳密バリデーションとスコア ±1.0 クリッピング、部分成功時の DB 置換ロジック（DELETE → INSERT）により冪等性と部分障害耐性を確保。
    - テスト容易性のため API 呼び出し関数を差替え可能に設計（unitest.mock.patch を想定）。
  - kabusys.ai.regime_detector
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と macro ニュースの LLM センチメント（重み 30%）を合成し、日次で市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ冪等書き込みする機能を実装（score_regime）。
    - MA 計算はルックアヘッドを防止するクエリ条件（date < target_date）を採用。
    - LLM 呼び出しは失敗時に安全に macro_sentiment=0.0 として継続するフェイルセーフ（例外を上げずログ警告）。
    - API レート制限や 5xx に対するリトライ、JSON パース失敗のハンドリング実装。
  - kabusys.research
    - ファクター計算と特徴量探索モジュールを実装・公開。
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算（データ不足時は None を返す仕様）。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率等を計算（データ不足時は None）。
    - calc_value: raw_financials から最新財務データを結合して PER/ROE を計算（EPS 不在・0 の場合 PER は None）。
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン計算を実装。horizons の入力検証あり（1〜252）。
    - calc_ic: スピアマンランク相関（IC）を計算するユーティリティ。レコード不足（<3）時は None を返す。
    - rank / factor_summary: ランク変換（同順位は平均ランク）と統計サマリーを提供。
    - zscore_normalize は kabusys.data.stats から再公開（__init__ によるエクスポート）。
  - kabusys.data
    - calendar_management: JPX カレンダーの管理ロジックを実装。
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
      - market_calendar が未登録のときは曜日ベース（土日非営業）でフォールバック。
      - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等保存する夜間バッチ処理。バックフィル、健全性チェックを実装。
    - pipeline: ETL 用の ETLResult dataclass を実装（取得数・保存数・品質問題・エラーの集約、to_dict エクスポート）。etl モジュールから ETLResult を再エクスポート。
    - 基本的に DuckDB を用いた SQL ベースの集約・計算を採用。
  - パッケージ公開インターフェース
    - kabusys.__init__ により主要サブパッケージ（data, strategy, execution, monitoring）を __all__ で宣言（骨組みの公開方針）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 環境変数・APIキー取り扱いについて注意喚起を実装（必須キー未設定時に ValueError を送出）。OpenAI API キーが必要な機能は明示的にチェックする。

### Notes / Operational details
- 全ての関数は内部で datetime.today() / date.today() を不必要に参照しない設計（ルックアヘッドバイアス防止）。target_date を明示的に引数で与えることを前提とする。
- OpenAI 呼び出しは JSON Mode を想定（厳密な JSON を期待）。API の不安定時はフェイルセーフで処理を継続する（0.0 やスキップ）。
- DuckDB 0.10 の制約（executemany に空リスト不可）を考慮した実装が各所にある。
- テスト容易性: OpenAI 呼び出しや内部待機関数の差し替えを想定した実装（モック可能）を行っている。

---

開発変更や追加機能があれば Unreleased セクションを追加してください。今後のリリースでは Breaking Changes / Added / Changed / Fixed / Security を適宜更新してください。