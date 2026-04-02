# CHANGELOG

すべての重要な変更をここに記載します。フォーマットは「Keep a Changelog」に準拠します。

現在のリリース方針: まだ安定リリースに達していないため Semantic Versioning を目安にしています。

## [Unreleased]
- (なし)

## [0.1.0] - 2026-04-02
初期リリース。日本株自動売買およびデータプラットフォーム向けの基盤ライブラリを提供します。主な機能は以下の通りです。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期構成。公開 API: data, research, ai, execution, monitoring（実体は一部モジュール）。
  - バージョン情報: __version__ = "0.1.0"。

- 環境設定・自動 .env ロード (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込み。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env ファイルの堅牢なパーサ実装:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - コメント処理（クォート外かつ直前が空白/タブの `#` をコメントとして扱う）
  - 環境変数必須チェック用 _require() と Settings クラス:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など
    - パスや閾値の型変換（duckdb/sqlite/pid ファイルパス、CPU/メモリ/ディスク閾値など）
    - KABUSYS_ENV / LOG_LEVEL のバリデーション（許容値チェック）
    - is_live / is_paper / is_dev のヘルパー属性

- AI モジュール (kabusys.ai)
  - news_nlp.score_news:
    - raw_news / news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）でセンチメント評価。
    - JST ベースのニュースウィンドウ（前日15:00〜当日08:30）を UTC 換算して扱う（calc_news_window）。
    - 銘柄バッチ処理（最大 20 銘柄/リクエスト）、1銘柄あたり記事数・文字数制限でトークン肥大化を抑制。
    - JSON Mode を想定した厳密なレスポンス検証・パースとスコアの ±1.0 クリップ。
    - レート制限/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ。
    - フェイルセーフ: API エラーやパース失敗時は当該チャンクをスキップし続行（例外を上げずにログ出力）。
    - DuckDB へは冪等に DELETE → INSERT を行う。部分失敗時に他コードの既存スコアを保護。

  - regime_detector.score_regime:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次で market_regime を書き込み。
    - ma200_ratio を計算（target_date 未満のデータのみ利用しルックアヘッドを防止）。
    - マクロ記事は定義済みマクロキーワードでフィルタ（最大 20 記事）。
    - OpenAI 呼び出しに対するリトライ制御・フェイルセーフ（API失敗時は macro_sentiment=0.0）。
    - レジーム判定: score を -1.0〜1.0 にクリップし、閾値（bull: >= 0.2、bear: <= -0.2）でラベル付け。
    - market_regime への書き込みは BEGIN/DELETE/INSERT/COMMIT の冪等処理。書き込み失敗時は ROLLBACK を試行。

- データプラットフォーム機能 (kabusys.data)
  - calendar_management:
    - market_calendar テーブルの存在有無に応じた営業日判定ロジック（DB 優先、未登録日は曜日ベースでフォールバック）。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等保存（バックフィルと健全性チェック付き）。
    - 最大探索範囲やバックフィル日数等の安全パラメータを導入（_MAX_SEARCH_DAYS, _BACKFILL_DAYS 等）。

  - ETL パイプライン (kabusys.data.pipeline)
    - ETLResult dataclass を導入し、取得数・保存数・品質問題・エラーを集約。
    - 差分更新・バックフィル・品質チェック方針に基づく設計。
    - jquants_client と quality モジュールを利用してデータ取得と検証を行う想定のインターフェースを提供。

  - パイプラインの公開 (kabusys.data.etl)
    - ETLResult を再エクスポート。

- Research（因子・特徴量解析） (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、ma200_dev（200日MA乖離率）を計算。データ不足時は None。
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率を計算。欠損管理あり。
    - calc_value: raw_financials と prices_daily を用いて PER/ROE を算出（EPS が 0/欠損なら None）。
    - すべて DuckDB の SQL ウィンドウ関数で実装し、外部 API にはアクセスしない。

  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得する SQL 実装。
    - calc_ic: Spearman ランク相関（IC）を計算する実装（結合/欠損処理/最小サンプルチェック）。
    - rank: 同順位は平均ランクで扱うランク関数（丸め処理で ties を安定化）。
    - factor_summary: 各列の count/mean/std/min/max/median を算出（None を除外）。

- 例外・ログ・安全性
  - 多くの箇所で詳細なログ出力を実装（info/debug/warning/exception）。
  - DB トランザクションにおける ROLLBACK の冗長ハンドリング（ROLLBACK 失敗時は警告ログ）。
  - ルックアヘッドバイアス回避のため、内部で datetime.today()/date.today() を直接参照しない設計（関数引数で基準日を受ける）。

### 変更 (Changed)
- 初期リリースのため、既存コードの内部設計を反映（設計方針やフェイルセーフ挙動を明記）。

### 修正 (Fixed)
- 初期リリースのため、特定のバグ修正履歴はなし（このリリース時点での動作を仕様として記載）。

### 既知の制約 / 注意点 (Notes)
- OpenAI（gpt-4o-mini）を利用する機能は API キー（OPENAI_API_KEY）を必要とする。キーが不足している場合は ValueError を送出する設計。
- DuckDB を前提とした SQL を多用しているため、DuckDB 環境での実行を想定。
- news_nlp と regime_detector はそれぞれ独自の _call_openai_api 実装を持ち、モジュール間でプライベート関数を共有しない設計。
- ETL / calendar_update_job / news スコアリングは外部 API（J-Quants / OpenAI）に依存するため、API エラー時はフェイルセーフで処理を継続するが、結果が欠損する場合がある。

### 互換性の破壊 (Breaking Changes)
- なし（初期リリース）。

---

今後のリリースでは、実運用で確認されたバグ修正、スキーマ変更、API 安定化、性能改善（例えば並列化やキャッシュ）、および追加の実行/監視モジュールの実装を予定しています。必要な変更点や追加機能があれば指示ください。