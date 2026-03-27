# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
現在のバージョンはパッケージ内の __version__ に基づき 0.1.0 です。

## [0.1.0] - 2026-03-27

初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。以下はこのリリースで追加された主な機能、設計方針、注意点の概要です。

### 追加 (Added)
- パッケージ基盤
  - パッケージエントリポイント: kabusys.__init__（__version__ = 0.1.0）
  - モジュール構成: data, research, ai, config, monitoring, strategy, execution（公開インターフェースに準備）

- 設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml で検出）
  - export 形式やクォート、インラインコメント等に対応した .env パーサ実装
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - Settings クラスでアプリ設定をプロパティとして提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL）
  - env 値検証（KABUSYS_ENV / LOG_LEVEL の許容値チェック）および is_live / is_paper / is_dev の補助プロパティ

- データ基盤 (kabusys.data)
  - カレンダー管理 (calendar_management)
    - market_calendar を用いた営業日判定 API（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）
    - J-Quants からのカレンダー差分フェッチを行う夜間バッチ (calendar_update_job)
    - DB未取得時の曜日フォールバック、最大探索日数による安全策を備えた実装
  - ETL パイプラインのインターフェース (etl, pipeline)
    - ETLResult データクラス（ETL 実行結果の集約、品質問題とエラーの収集）
    - 差分取得・バックフィル・品質チェックを想定した設計（jquants_client と quality モジュールとの連携を前提）

- 研究（Research）ユーティリティ (kabusys.research)
  - ファクター計算 (factor_research)
    - モメンタム（1M/3M/6M リターン、200日移動平均乖離）
    - ボラティリティ / 流動性（20日 ATR, 平均売買代金, 出来高比）
    - バリュー（PER, ROE）
    - DuckDB を用いた SQL+Python 実装で (date, code) 単位の結果を返す
  - 特徴量探索 (feature_exploration)
    - 将来リターン計算（calc_forward_returns）
    - IC（Information Coefficient）計算（calc_ic、Spearmanランク相関）
    - ファクター統計サマリー（factor_summary）
    - ユーティリティ: rank（同順位の平均ランク処理）
  - 研究側から再利用できる z-score 正規化関数を data.stats から公開

- AI（自然言語処理） (kabusys.ai)
  - ニュース NLP スコアリング (news_nlp)
    - 前日 15:00 JST ～ 当日 08:30 JST を対象とするニュースウィンドウの計算（calc_news_window）
    - raw_news / news_symbols を集約して銘柄ごとのニューステキストを作成
    - OpenAI（gpt-4o-mini）へバッチ送信し JSON Mode でレスポンスを取得、バリデーションして ai_scores に書き込む（score_news）
    - バッチサイズ、記事数・文字数制限、リトライ（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）を実装
    - レスポンスの堅牢なパース/バリデーションと ±1.0 のクリッピング
    - テスト容易性のため _call_openai_api の差し替え（patch）を想定
  - 市場レジーム判定 (regime_detector)
    - ETF 1321 の 200 日 MA 乖離（ウエイト 70%）とマクロニュース LLM センチメント（ウエイト 30%）を合成して日次レジーム（'bull'/'neutral'/'bear'）を判定（score_regime）
    - prices_daily / raw_news / market_regime を参照し、冪等な DB 書き込みを行う
    - マクロキーワードで raw_news をフィルタ、OpenAI による JSON 出力を期待してパース
    - API失敗時は macro_sentiment=0.0 として継続するフェイルセーフ実装
    - リトライ・バックオフ対応、ログ出力、テスト差し替えポイントあり

### 変更 (Changed)
- （初回リリースのため変更履歴はありません）

### 修正 (Fixed)
- （初回リリースのため修正履歴はありません）
- ただし多くの箇所でエラー発生時の安全側フォールバック（例: API失敗時のデフォルト値、ROLLBACK の試行、空パラメータ回避など）を実装し、部分失敗時に既存データを破壊しない設計を採用

### セキュリティ (Security)
- OpenAI API キーや他のシークレット類は環境変数経由で扱うことを想定（Settings は必須項目の未設定時に ValueError を発生させる）
- .env 自動ロードはプロジェクトルート検出に基づくが、テスト等で無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD を提供

### 既知の注意点 / 設計上の決定
- ルックアヘッドバイアス防止のため、内部処理は datetime.today() / date.today() を直接参照しない設計（外部から target_date を注入する形を採用）
- DuckDB をストレージとして利用する前提（関数は DuckDBPyConnection を受け取る）
- OpenAI SDK（chat completions with JSON mode）への依存があるため、実行時に適切な SDK バージョンが必要
- ETL / カレンダー更新は外部 API（J-Quants）との連携を前提とするため、jquants_client モジュールおよび quality モジュールとの連携実装が必要
- news_nlp/regime_detector 内での _call_openai_api はユニットテスト用に差し替え可能にしている（モックしやすい設計）

### マイグレーション / アップグレード
- 初回リリースのためマイグレーションは不要です。

---

今後のリリースでは、モニタリング・戦略・実行モジュール（monitoring, strategy, execution）の実装拡充、より詳細な品質チェック、ドキュメントの追加、性能改善やテストカバレッジ強化を予定しています。必要であれば本 CHANGELOG の英語版や、各モジュールごとの詳細リリースノートも作成します。