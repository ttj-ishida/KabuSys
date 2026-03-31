# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。  
このリポジトリの初期リリースとしてバージョン 0.1.0 を登録します。

## [0.1.0] - 2026-03-31

### 追加
- パッケージ初期リリース "KabuSys"（日本株自動売買システム）のコアモジュール群を追加。
  - モジュール構成: kabusys.data, kabusys.research, kabusys.ai, kabusys.config, kabusys.research, kabusys.__init__ 等を公開。
  - バージョン: __version__ = "0.1.0"。

- 環境設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動ロードする機能を実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env のパース機能を実装（export プレフィックス対応、クォート・エスケープ、インラインコメント処理）。
  - override と protected オプションをサポートする .env 読み込みロジック。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 実行環境（development / paper_trading / live）などの設定プロパティを公開。
  - 不正な env 値に対する検証（KABUSYS_ENV、LOG_LEVEL）と必須キー取得時のエラー（_require）を追加。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）で銘柄ごとにセンチメントを算出する score_news を実装。
  - JST ベースのニュースウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を提供（calc_news_window）。
  - バッチ処理（最大 20 銘柄／コール）、トリム（記事数・文字数制限）、レスポンスバリデーション（JSON 抽出、results 構造検証、スコア数値化、クリップ ±1.0）を実装。
  - API リトライ（429・ネットワーク断・タイムアウト・5xx）を指数バックオフで実施。失敗時はフェイルセーフでスキップし、例外を伝播させない設計。
  - DuckDB へ冪等的に書き込む（DELETE → INSERT、部分失敗時に既存スコアを保護）。
  - テスト容易性のため _call_openai_api をモック差し替え可能に設計。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次市場レジーム（bull/neutral/bear）を算出する score_regime を実装。
  - prices_daily からの MA200 計算、raw_news からマクロキーワードに基づく記事抽出、OpenAI 呼び出し（gpt-4o-mini + JSON mode）、スコア合成、market_regime テーブルへの冪等書き込みを実装。
  - ルックアヘッドバイアス回避設計（target_date 未満のデータのみ使用、datetime.today()/date.today() を直接参照しない）。
  - API 失敗時のフォールバック（macro_sentiment=0.0）やリトライロジックを提供。
  - OpenAI 呼び出し関数は news_nlp 側と独立させ、モジュール間結合を低減。

- 研究用ファクター群（kabusys.research）
  - factor_research: calc_momentum, calc_value, calc_volatility を実装。
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None）。
    - Volatility: 20 日 ATR（true range の扱いに注意）および相対 ATR、20 日平均売買代金、出来高比率。
    - Value: raw_financials から最新財務データを取得して PER、ROE を計算。
  - feature_exploration: calc_forward_returns（任意ホライズンに対応）、calc_ic（Spearman ランク相関）、factor_summary（基本統計量）、rank（同順位は平均ランク）を実装。
  - zscore_normalize を kabusys.data.stats から再エクスポート（kabusys.research.__init__）。
  - DuckDB を使用し、外部 API にアクセスしない設計。結果は list[dict] 形式で返却。

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - market_calendar を基に営業日判定（is_trading_day）、前後営業日取得（next_trading_day, prev_trading_day）、期間内営業日列挙（get_trading_days）、SQ日判定（is_sq_day）を実装。
    - DB未取得日や NULL 値のフォールバックとして曜日ベース（週末除外）判定を提供。最大探索範囲で無限ループ防止。
    - JPX カレンダー差分取得と冪等保存を行う夜間ジョブ calendar_update_job を実装（バックフィル・健全性チェック含む）。jquants_client 経由で API 呼び出しを行う。
  - ETL パイプライン（pipeline）
    - ETLResult データクラスを実装（取得件数／保存件数／品質問題／エラーの集約）。
    - 差分取得・バックフィル・品質チェック（quality モジュールを利用）・冪等保存の設計方針を反映。
    - DuckDB のテーブル存在チェック、最大日付取得ユーティリティを提供。
  - etl モジュールで pipeline.ETLResult を再エクスポート。

### 変更（設計上の選択）
- ルックアヘッドバイアスを避けるため、すべての「日次」処理は内部で現在時刻を参照せず、呼び出し側から target_date を受け取る設計に統一。
- OpenAI 呼び出しは JSON mode（response_format={"type":"json_object"}）を使い厳密な JSON 出力を期待する一方で、パースの堅牢性のため前後余計なテキストが混入した場合の復元ロジックを追加。
- DuckDB のバージョン差異（executemany に空リストが渡せない等）を考慮した互換的実装を採用。
- モジュール間のテスト容易性のため、外部呼び出し（OpenAI, jquants_client）を差し替え可能に設計。

### 修正（バグ修正・堅牢化）
- API 呼び出しのエラー処理を強化（429・ネットワーク断・タイムアウト・5xx に対する再試行、その他はログ出力して安全にフォールバック）。
- DB 書き込み時のトランザクション管理（BEGIN / DELETE / INSERT / COMMIT）と、例外発生時に ROLLBACK を実行し、ROLLBACK が失敗した場合も警告ログを出すようになりました。
- news_nlp と regime_detector のレスポンスパース失敗時にスコアを 0.0 にフォールバックし、例外を上位に伝播させないフェイルセーフ動作を追加。
- .env パーサーのクォート内エスケープやインラインコメント処理を改善し、より多くの .env フォーマットに対応。

### 既知の制限・注意事項
- OpenAI API キーは score_news / score_regime に渡すか環境変数 OPENAI_API_KEY を設定する必要があります。未設定時は ValueError を送出します。
- 現段階では PBR・配当利回りなどの一部バリューファクターは未実装です（calc_value に注記あり）。
- DuckDB の挙動（特にバインド型周り）が環境に依存する可能性があります。テスト時は実際の DB スキーマと互換性を確認してください。
- news_nlp / regime_detector の LLM 評価は外部 API に依存するため、API 利用料・レイテンシ・レート制限に注意してください。

### セキュリティ
- 機密情報（API トークン等）は .env または環境変数で管理する想定です。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化できます。

---

今後の予定（例）
- 追加のファクター・ポートフォリオ構築ロジックの実装
- モデル評価パイプライン（ウォークフォワード等）
- 運用用 execution / monitoring モジュールの拡充

（以上）