# Changelog

すべての重要な変更点を記録します。本ファイルは Keep a Changelog 準拠の形式を採用しています。  
このプロジェクトの初回公開リリース（v0.1.0）の内容は以下のとおりです。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-27
初回公開リリース。

### Added
- パッケージのエントリポイントを追加
  - パッケージ名: kabusys、バージョン 0.1.0
  - __all__ に data / strategy / execution / monitoring を公開

- 設定管理モジュール（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動読み込み機構を実装
    - 読み込み順: OS 環境変数 > .env.local > .env
    - プロジェクトルート判定は .git または pyproject.toml を探索して行う（CWD 非依存）
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env パーサを実装（export 構文、クォート、エスケープ、コメント処理に対応）
  - Settings クラスを提供（プロパティ経由で設定取得）
    - 必須環境変数の検査とエラーメッセージ（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）
    - デフォルト値（例: KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH）
    - KABUSYS_ENV / LOG_LEVEL の検証ロジック
    - ユーティリティプロパティ: is_live / is_paper / is_dev

- AI 関連モジュール（kabusys.ai）
  - ニュースセンチメント解析（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄ごとのニュースを作成
    - OpenAI（gpt-4o-mini, JSON Mode）にバッチ送信して銘柄別スコアを取得
    - バッチサイズ、文字数上限、記事数上限、リトライ (429/ネットワーク/5xx) を実装
    - レスポンスの厳密なバリデーションと ±1.0 のクリップ
    - DuckDB への冪等書き込み（DELETE → INSERT）を実装
    - メイン公開関数: score_news(conn, target_date, api_key=None)
    - タイムウィンドウ計算ユーティリティ: calc_news_window(target_date)
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（Nikkei 225 連動）の 200 日移動平均乖離（重み 70%）と
      マクロニュース LLM センチメント（重み 30%）を合成して日次でレジーム判定
    - LLM 呼び出しは専用実装、API エラーに対するリトライとフェイルセーフ（失敗時 macro_sentiment=0.0）
    - レジームスコア合成と label 判定（bull / neutral / bear）
    - 結果を market_regime テーブルへ冪等書き込み
    - メイン公開関数: score_regime(conn, target_date, api_key=None)

- データプラットフォーム関連（kabusys.data）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - 営業日判定: is_trading_day, is_sq_day
    - 近傍営業日取得: next_trading_day, prev_trading_day
    - 期間内営業日一覧取得: get_trading_days
    - 夜間バッチ更新ジョブ: calendar_update_job(conn, lookahead_days=...)
    - market_calendar が未取得時の曜日ベースフォールバック実装
    - DB 値優先の一貫した挙動（未登録日はフォールバック）
    - 最大探索日数制限で無限ループ防止
  - ETL パイプライン（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult データクラスを公開（取得件数・保存件数・品質問題・エラー一覧などを保持）
    - 差分取得、バックフィル、品質チェック、Idempotent 保存の設計方針に準拠するユーティリティ群
    - DuckDB のテーブル存在チェック、最大日付取得等の補助関数を実装

- 研究／リサーチモジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）
    - Value（PER、ROE：raw_financials から取得）
    - Volatility（20 日 ATR、平均売買代金、出来高変化率）
    - 関数: calc_momentum, calc_value, calc_volatility
    - DuckDB ベースの SQL + Python で計算し、(date, code) 形式の dict リストを返す
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算: calc_forward_returns (horizons 指定可)
    - IC 計算（Spearman ランク相関）: calc_ic
    - 値のランク化ユーティリティ: rank
    - 統計サマリー: factor_summary

- その他
  - DuckDB を前提とした SQL 実装とトランザクション（BEGIN/COMMIT/ROLLBACK）を多くの書き込み処理で採用
  - OpenAI SDK 呼び出しをラップした内部関数（_call_openai_api）をそれぞれのモジュールで用意しテスト時に差し替え可能
  - ロギングによる詳細な情報・警告出力を充実

### Changed
- 初回リリースのため該当なし

### Fixed
- 初回リリースのため該当なし

### Security
- 初回リリースのため該当なし

### Notes / 設計上の重要点と制約
- ルックアヘッドバイアス防止
  - AI スコア算出やファクター計算では内部で datetime.today() / date.today() を使用せず、必ず引数で target_date を受け取る設計。
  - DB クエリは target_date より未来のデータを参照しないよう明示的に制御。

- OpenAI 呼び出しのフェイルセーフ
  - API エラーやパース失敗時は例外を投げずにフェイルセーフ値（例: macro_sentiment=0.0、ai_scores のスキップ）で継続する方針。
  - リトライ（指数バックオフ）を実装して一時的な障害に耐性を持たせている。

- スコアのクリップとバリデーション
  - LLM からのスコアは必ず範囲でクリップ（例: ±1.0）し、レスポンスの構造と型を厳密に検証する。

- DB 書き込みの冪等性
  - ai_scores / market_regime 等への書き込みは既存レコードを個別に DELETE してから INSERT することで冪等性を確保（部分失敗時の保護を意図）。
  - DuckDB executemany の仕様に留意し、空リストでの executemany 呼び出しを回避するチェックを行っている。

- 環境変数の取り扱い
  - 必須の機密情報（OpenAI API キー、J-Quants リフレッシュトークン、kabu API パスワード、Slack トークン等）は Settings にて明示的にチェックする。
  - auto .env ロードはテストのために無効化可能。

### Usage / マイグレーション注意点
- OpenAI を利用する機能（score_news, score_regime）は OPENAI_API_KEY を渡すか環境変数に設定する必要があります。
- DuckDB に必要なテーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等）を事前に用意してください。
- .env のパースはシェル形式の変種（export、クォート、エスケープ、インラインコメント）に対応していますが、極端に特殊なケースでは期待通りに動作しない可能性があります。
- calendar_update_job は J-Quants クライアント（kabusys.data.jquants_client）の fetch/save を利用します。API クライアント側の設定（トークン等）を確認してください。

---

今後のリリースでは、運用上の観測・監視機能、strategy・execution・monitoring パッケージ内の注文実行ロジック、追加モデルやバックテスト機能の拡張を予定しています。要望やバグ報告は Issue にてお知らせください。