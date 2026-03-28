# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

最新の変更は上に記載します。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-28
初回リリース。日本株自動売買プラットフォームのコア機能群を実装しました。

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報の定義（kabusys.__version__ = "0.1.0"）。
  - サブパッケージ公開: data, research, ai, execution, monitoring, strategy（__all__ に基づく公開方針）。

- 環境変数 / 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。自動ロードはプロジェクトルート（.git または pyproject.toml を探索）に基づいて実行。
  - .env と .env.local の読み込み優先度を実装（OS 環境変数 > .env.local > .env）。.env.local は上書き（override=True）として扱う。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テストで利用）。
  - .env のパース処理を堅牢化（コメント行、export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメント扱いなどに対応）。
  - 必須環境変数取得ヘルパー _require を提供（未設定時は ValueError を送出）。
  - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得可能：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - データベースパス (DUCKDB_PATH, SQLITE_PATH) のデフォルト値
    - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の検証 (`development` / `paper_trading` / `live`、および標準ログレベル)
    - ヘルパープロパティ is_live / is_paper / is_dev

- AI モジュール (kabusys.ai)
  - ニュースセンチメント解析 (news_nlp.score_news)
    - raw_news / news_symbols を集約して銘柄別にニュースをまとめ、OpenAI（gpt-4o-mini）にバッチ送信して銘柄ごとのセンチメントを算出する。
    - JST 時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を正確に計算する util (calc_news_window)。
    - 1チャンク最大20銘柄、1銘柄あたり最大記事数および文字数でトリムする仕組みを実装。
    - API 呼び出しは JSON mode を使い、レスポンスのバリデーションと数値変換、±1.0 クリップを行う。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライを実装。失敗時は該当チャンクをスキップして継続するフェイルセーフ設計。
    - レスポンスの JSON が前後に余計なテキストを含むケースに対する復元ロジックを実装。
    - 書き込みは冪等（DELETE → INSERT）で実行し、部分失敗時にも既存の他コードスコアを保護。

  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321（日経225連動）の 200 日移動平均乖離 (ma200_ratio) と、ニュース NLP によるマクロセンチメントを重み付け（70% / 30%）して日次レジーム（bull/neutral/bear）を判定。
    - DuckDB 上の prices_daily / raw_news / market_regime を参照して計算・書き込みを実施。書き込みは冪等処理（BEGIN / DELETE / INSERT / COMMIT）。
    - OpenAI 呼び出しは専用のラッパー実装で行い、API エラー時は macro_sentiment=0.0 にフォールバックするフェイルセーフ。
    - API 呼び出しのリトライと 5xx 判定、JSON パース失敗時のログ・フォールバックを実装。

- データ基盤 (kabusys.data)
  - マーケットカレンダー管理 (calendar_management)
    - market_calendar テーブルを用いた営業日判定とユーティリティを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録値を優先し、未登録日は曜日ベース（土日非営業）でフォールバックする一貫性のある実装。
    - カレンダー夜間バッチ更新ジョブ (calendar_update_job)：J-Quants API から差分取得して market_calendar を冪等保存。バックフィル・健全性チェックを実装。
  - ETL パイプライン (pipeline.ETLResult / etl re-export)
    - ETL 実行結果を表す ETLResult dataclass を実装（取得数・保存数・品質問題・エラーメッセージ等を保持）。
    - ETL の内部ユーティリティ（テーブル存在チェック、最大日付取得、カレンダー補正等）を実装。
    - jquants_client と quality モジュールを組み合わせた差分取得・保存・品質チェックのための下地を整備（実装の指針をコメントで記載）。

- リサーチ（kabusys.research）
  - ファクター計算 (factor_research)
    - モメンタム: calc_momentum（1M/3M/6M リターン、200 日 MA 乖離）
    - ボラティリティ/流動性: calc_volatility（20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率）
    - バリュー: calc_value（PER、ROE）
    - DuckDB を用いた SQL ベースの実装。データ不足時の None 扱い等、現実的な欠損処理を実装。
  - 特徴量探索 (feature_exploration)
    - 将来リターン計算: calc_forward_returns（任意ホライズンのリターンを一度で取得可能）
    - IC（Information Coefficient）計算: calc_ic（スピアマンのランク相関）
    - 統計サマリー: factor_summary（count/mean/std/min/max/median）
    - ランク変換ユーティリティ: rank（同順位は平均ランク、丸めにより ties の検出安定化）

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- .env 読み込みにおけるファイル読み込み失敗時に警告を出してスキップする挙動を実装（OSError ハンドリング）。
- OpenAI 呼び出し関連で発生し得る多種のエラーに対して明示的にログ出力し、フォールバック値を用いる耐障害性を向上。

### 既知の制限 / 注意事項 (Known issues / Notes)
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY のいずれかで指定する必要があります。未設定時は ValueError を送出します。
- 必須の環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）は未設定だと Settings の該当プロパティアクセス時にエラーになります。
- DuckDB の executemany に対する互換性制約（空リスト不可）を考慮して実装していますが、使用する DuckDB バージョンによっては微妙な差異が生じる可能性があります。
- 日付/時間は内部的に date / naive UTC datetime を用いており、タイムゾーン混入を避ける設計です。JST ↔ UTC の変換ロジックは calc_news_window 等で明示的に扱っています。
- 本リリースでは PBR・配当利回りなど一部バリューファクターは未実装です（将来追加予定）。

### セキュリティ (Security)
- なし

---

参照:
- 環境変数自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
- デフォルト DuckDB パス: data/kabusys.duckdb
- デフォルト SQLite パス（モニタリング用）: data/monitoring.db

（必要に応じて、次リリースでの機能改善・バグ修正点を Unreleased セクションに追記してください。）