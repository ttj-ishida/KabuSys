# Changelog

すべての重要な変更をここに記載します。フォーマットは Keep a Changelog に準拠します。  
現在のパッケージバージョン: 0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-27
初回リリース。日本株自動売買・データ基盤・リサーチ・AI支援の基本機能を実装。

### Added
- パッケージ初期化
  - kabusys.__init__: パッケージ名・バージョン定義（__version__ = "0.1.0"）および公開モジュール指定（data, strategy, execution, monitoring）。

- 設定管理
  - kabusys.config:
    - .env/.env.local の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env パーサ（コメント行、export プレフィックス、クォート・エスケープ、インラインコメント処理に対応）。
    - 読み込み優先度: OS環境変数 > .env.local > .env。自動ロード無効化変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - protected 値（既存の OS 環境変数）を上書きから保護する動作。
    - Settings クラス: J-Quants / kabuステーション / Slack / DB パス / システム設定（env, log_level）などのプロパティを提供。必須環境変数の未設定時は ValueError を送出。

- AI モジュール（OpenAI を利用したニュース解析）
  - kabusys.ai.news_nlp:
    - ニュースのタイムウィンドウ計算（JST ベース → UTC 変換）。
    - raw_news と news_symbols を集約し、銘柄ごとに記事を結合、最大文字数・記事数でトリム。
    - バッチ（最大20銘柄）で OpenAI（gpt-4o-mini）の JSON Mode に送信、429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライを実装。
    - レスポンスのバリデーション（JSON 抽出、results 配列、code と score の検証、スコアを ±1.0 でクリップ）。
    - 成功したスコアのみ ai_scores テーブルへ冪等的に置換（DELETE → INSERT）する処理。
    - テスト容易性のため API 呼び出し箇所を patch 可能な設計。
  - kabusys.ai.regime_detector:
    - ETF 1321（日経225連動型）200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）判定。
    - prices_daily から ma200_ratio を計算（target_date 未満データのみを使用しルックアヘッドを防止）。
    - raw_news からマクロキーワードでフィルタしたタイトルを抽出。
    - OpenAI 呼び出し（gpt-4o-mini + JSON Mode）で macro_sentiment を取得。API エラー時はフェイルセーフで 0.0 を使用。
    - レジームスコア合成後、market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。エラー時は ROLLBACK を試行し例外を再送出。
    - 内部での OpenAI 呼び出し実装は news_nlp と独立（モジュール結合を避ける）。

- データ基盤（DuckDB ベース）のユーティリティ
  - kabusys.data.calendar_management:
    - JPX カレンダー管理ロジック（market_calendar テーブルを参照）。
    - 営業日判定 API: is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days。
    - DB にデータがない場合は曜日ベースのフォールバックを用いる一貫した挙動。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等に更新。バックフィル・健全性チェックを実装。
  - kabusys.data.pipeline / kabusys.data.etl:
    - ETLResult データクラスを定義し公開（ETL 実行結果、品質チェック結果、エラー情報を保持）。
    - ETL パイプライン設計に沿った差分取得・保存・品質チェックの基礎を実装（jquants_client 経由の保存、backfill の扱い、最大取得開始日等）。
    - DuckDB 接続ヘルパー（テーブル存在確認、最大日付取得など）。
  - 設計方針の反映:
    - いずれの処理もルックアヘッドバイアスを避ける（内部で datetime.today()/date.today() を直接参照しない箇所を明確化）。
    - DB 書き込みは冪等性を保ち、部分失敗時に既存データを不必要に消さない設計。
    - DuckDB の executemany の制約（空リスト不可）を考慮した実装。

- リサーチ / ファクター
  - kabusys.research:
    - ファクター計算モジュールを公開（momentum, value, volatility 等）と zscore_normalize の再エクスポート。
    - factor_research:
      - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離率の計算。データ不足時の None 扱い。
      - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率の計算。必要行数未満で None を返す仕様。
      - calc_value: raw_financials から最新財務を取得して PER / ROE を計算（EPS が 0 または欠損の場合は None）。
    - feature_exploration:
      - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons のバリデーション（正の整数・最大252）を実装。
      - calc_ic: スピアマンランク相関（IC）計算。3 銘柄未満で None を返す。
      - rank: 同順位の平均ランクを返す実装（丸めによる ties 回避）。
      - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは引数注入または環境変数 OPENAI_API_KEY を使用。未設定時は ValueError を送出して誤操作を防止。
- .env の読み込みはデフォルトで有効だが、KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能（テスト時の安全策）。

### Notes / 実装上の重要ポイント
- ルックアヘッドバイアス防止のため、スコアリング系関数は target_date を受け取り、内部で現在日時を参照しない設計になっています。
- OpenAI 呼び出しは JSON Mode を利用し、レスポンスのパース・バリデーションを厳密に行う設計です。API 障害時は基本的に例外を上位へ伝搬させず、フェイルセーフ値（例: macro_sentiment=0.0、スコア取得スキップ）で継続する方針です。
- DuckDB を主要なローカル DB として想定。DB 書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）の扱いや executemany の制約を考慮しています。
- テスト容易性のため、外部 API 呼び出し点（OpenAI 呼び出し関数など）は patch しやすい形で実装されています。

---

今後のリリースでは、strategy / execution / monitoring の具体的な発注ロジックや Slack 通知・監視周りの実装、より細かな品質チェックやメトリクス出力などが追加される想定です。