# CHANGELOG

すべての注目すべき変更・追加点をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-02
初回公開リリース。

### 追加 (Added)
- パッケージ全体
  - kabusys コアパッケージを追加。モジュールを公開: data, research, ai, monitoring, strategy, execution 等（__all__ により一部公開）。
  - パッケージバージョンを 0.1.0 に設定。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機能を提供（プロジェクトルートの検出: .git または pyproject.toml を基準）。
  - .env のパースは export 形式、シングル/ダブルクォート、エスケープ、行内コメントの扱いに対応。
  - 読み込み優先順位: OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - 必須キー取得時の _require()、環境値検証（KABUSYS_ENV の許容値、LOG_LEVEL の検証）や設定プロパティ（J-Quants / kabu / Slack / DB パス / 監視しきい値 等）を提供。

- AI モジュール (src/kabusys/ai)
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を用いて銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルに書き込む score_news を実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window として提供。
    - バッチ送信（最大 20 銘柄/チャンク）、記事数 / 文字数のトリム、JSON Mode + レスポンス検証、スコアの ±1.0 クリップを実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。
    - テスト容易性のため _call_openai_api を差し替え可能に設計。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 (日経225連動型) の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - ma200_ratio 計算、マクロニュース抽出、OpenAI 呼び出し（gpt-4o-mini）と合成ロジック、閾値判定、market_regime テーブルへの冪等書き込みを実装。
    - API 失敗時は macro_sentiment を 0.0 とするフェイルセーフを採用。こちらも _call_openai_api を差し替え可能。

- リサーチ / ファクター計算 (src/kabusys/research)
  - factor_research.py
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離等のモメンタム系ファクターを実装。
    - calc_volatility: 20 日 ATR、ATR 比、平均売買代金、出来高比等のボラティリティ / 流動性指標を実装。
    - calc_value: raw_financials から最新財務を取得して PER / ROE を計算（PBR/配当利回りは未実装）。
  - feature_exploration.py
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括で取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。
    - factor_summary / rank: 基本統計量の算出とランク化ユーティリティを提供。
  - research パッケージで主要関数を再エクスポート。

- データプラットフォーム (src/kabusys/data)
  - calendar_management.py
    - market_calendar テーブルを用いた営業日判定ユーティリティ群（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - DB が未取得の場合の曜日ベースのフォールバック、最大探索日数制限、安全性チェックを導入。
    - calendar_update_job: J-Quants からの差分取得、バックフィルロジック、健全性チェック、冪等保存を実装。
  - pipeline.py / etl.py
    - ETLResult dataclass を定義し、ETL の結果（取得件数・保存件数・品質問題・エラー）を集約できるようにした。
    - 差分更新、バックフィル、品質チェックの設計方針を実装（jquants_client / quality モジュールと連携する想定）。
    - etl モジュールで ETLResult を再エクスポート。

- DB 使用
  - 全体を通じて DuckDB を利用。SQL はパフォーマンスを考慮したウィンドウ関数や集約で実装。
  - 書き込み操作は可能な限り冪等に（BEGIN / DELETE / INSERT / COMMIT）。失敗時は ROLLBACK とログ出力。

### 変更 (Changed)
- 設計上の重要ポイント（明記）
  - すべての解析関数は datetime.today() / date.today() に依存しない設計（ルックアヘッドバイアス回避）。target_date を明示的に受け取る API を採用。
  - OpenAI 呼び出しは JSON Mode を使用し、レスポンスの厳密なバリデーションを行う。
  - LLM 呼び出し時にモジュール間でプライベート関数を共有しない設計（news_nlp と regime_detector で _call_openai_api を独立実装）。
  - DuckDB の executemany に関する注意（空リストは実行不可）を踏まえた実装。
  - API 呼び出し失敗時は例外を上げずフェイルセーフで処理を継続する箇所を多数実装（部分的な処理失敗が他データを壊さない設計）。

### 修正 (Fixed)
- データ欠損時のフェールバックを明示化
  - MA 計算でデータ不足の場合は中立値（1.0 または None）を返して downstream を壊さないようにした。
  - LLM レスポンスパース失敗や API エラーはロギングして 0.0（中立）にフォールバックする実装を追加。

### セキュリティ (Security)
- 機密情報の取り扱い
  - 実行に必須の環境変数を明確化: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等。
  - OpenAI API キーは score_news / score_regime の引数または環境変数 OPENAI_API_KEY で供給。未設定時は ValueError を発生させることで誤操作を防止。

### 既知の制約 / 未実装 (Known issues / Limitations)
- ファイナンス指標
  - PBR や配当利回りは現バージョンでは未実装（calc_value 注記）。
- 外部依存
  - J-Quants / OpenAI / kabu API 等の外部サービス依存があるため、実行環境でのトークン・ネットワーク設定が必要。
- DuckDB のバージョン差異により一部バインド方法が不安定になり得るため、executemany による削除/挿入で互換性を保つ実装を採用している。

---

この CHANGELOG はソースコードの実装内容から推測して作成しています。実際のリリースノート作成時は変更履歴（コミットログ・リリース差分）に基づいて適宜更新してください。