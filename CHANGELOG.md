CHANGELOG
=========

すべての重要な変更履歴はこのファイルに記録します。本ファイルは「Keep a Changelog」形式に準拠します。

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- 破壊的変更 (Removed / Breaking Changes) — 該当時に記載

Unreleased
----------
（なし）

[0.1.0] - 2026-04-02
--------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージ公開情報:
    - __version__ = "0.1.0"
    - パッケージ公開モジュール: data, strategy, execution, monitoring（__all__）

- 環境設定 / ロード
  - 自動 .env ロード機能を実装
    - プロジェクトルートを .git または pyproject.toml から探索して .env / .env.local を自動読み込み
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
    - OS 環境変数は保護され、.env の上書きを防止
  - .env パーサ実装
    - export KEY=val 形式対応、シングル/ダブルクォート対応（バックスラッシュエスケープ考慮）、インラインコメントの扱いルール
  - Settings クラスを実装（kabusys.config.settings）
    - J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / システム設定 をプロパティで公開
    - 必須環境変数取得時の検証（未設定時は ValueError）
    - KABUSYS_ENV / LOG_LEVEL の検証（許容値セット）

- データ関連（kabusys.data）
  - カレンダー管理モジュール（calendar_management）
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供
    - market_calendar テーブルへ依存。未取得時は曜日ベースのフォールバック（週末を非営業日扱い）
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等更新（バックフィル・健全性チェック含む）
    - 最大探索範囲（_MAX_SEARCH_DAYS）やバックフィル期間等の保護ロジックを実装
  - ETL / パイプライン（pipeline, etl）
    - ETLResult データクラスを公開（etl.ETLResult を data.ETLResult 経由で再エクスポート）
    - ETLResult に品質チェックの結果（quality_issues）とエラー一覧（errors）を含め、has_errors / has_quality_errors / to_dict を提供
    - pipeline モジュールの設計方針（差分更新、バックフィル、品質チェックの扱い）をコードに反映

- 研究（research）
  - factor_research モジュール
    - calc_momentum: 1m/3m/6m リターン、200日MA乖離（ma200_dev）を計算（prices_daily を参照）
    - calc_volatility: 20日ATR、相対ATR、20日平均売買代金、出来高比率などを計算
    - calc_value: raw_financials から直近財務を取得して PER / ROE を計算
    - DuckDB ベースの SQL 実装で結果を (date, code) ベースの dict リストで返す
  - feature_exploration モジュール
    - calc_forward_returns: 指定ホライズン（既定 [1,5,21]）の将来リターンを計算（LEAD を利用）
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（必要件数未満は None）
    - rank: 平均ランク（同順位は平均）を返すユーティリティ（丸めで ties の安定化）
    - factor_summary: 各ファクターカラムの count/mean/std/min/max/median を計算

- AI / NLP（kabusys.ai）
  - news_nlp モジュール
    - score_news: raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとの ai_score を ai_scores テーブルへ書き込み
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC 変換済み）
    - バッチング、トークン肥大化対策（銘柄あたり最大記事数・文字数制限）、最大バッチサイズ 20 を採用
    - OpenAI 呼び出しは JSON mode（response_format={"type": "json_object"}）を利用し、応答バリデーションを厳密に実施
    - リトライポリシー: 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ（最大試行回数の制御）
    - 応答パースとスコア検証ロジックを実装（_validate_and_extract）
    - スコアは ±1.0 にクリップ、部分失敗時でも既存他コードスコアを保護するためコード絞り込みで DELETE → INSERT 実行
    - API キーは引数または環境変数 OPENAI_API_KEY で指定。未設定時は ValueError を発生
  - regime_detector モジュール
    - ETF 1321（日経225連動ETF）の 200 日 MA 乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定
    - マクロニュースは raw_news からキーワードでフィルタ（複数キーワード定義）して取得、LLM（gpt-4o-mini）でセンチメント評価
    - LLM 呼び出しについてもリトライ・バックオフ・フェイルセーフ（失敗時は macro_sentiment=0.0）
    - レジーム判定後、market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）、DB 書き込み失敗時は ROLLBACK を試行

- 共通設計/運用上の配慮
  - ルックアヘッドバイアス防止: 各 AI / 研究関数は内部で datetime.today()/date.today() を参照せず、target_date 引数に基づいて処理
  - DuckDB を主ストレージとして利用し、SQL と Python を組み合わせた実装
  - DB トランザクションを用いた冪等性確保と部分失敗からの保護（DELETE→INSERT パターンなど）
  - 詳細なログ出力および例外発生時の警告ログで障害の追跡を容易にする実装

Changed
- 初版リリースのため該当なし

Fixed
- 初版リリースのため該当なし

Known limitations / Notes
- 外部依存:
  - OpenAI（gpt-4o-mini）と J-Quants API クライアント（kabusys.data.jquants_client）に依存するため、実行環境での API キー設定とネットワーク接続が必要
- セキュリティ/認証:
  - OPENAI_API_KEY、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN などの機密情報は環境変数または .env で管理する想定
- 未実装/拡張候補:
  - strategy / execution / monitoring モジュールの具体的な発注ロジックや監視エージェントの実装はパッケージ公開インターフェースに含まれているが、このリリースでの詳細実装状況はモジュール毎に異なる（今後拡張予定）

ライセンス / 貢献
- 本プロジェクトへの貢献や問題報告はリポジトリの Issue / Pull Request を利用してください。