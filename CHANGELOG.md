# CHANGELOG

すべての注目すべき変更を記録します。  
このファイルは Keep a Changelog の形式に準拠しており、セマンティック バージョニングを使用します。  

## [0.1.0] - 2026-03-31
初回公開リリース。

### 追加
- パッケージ初期化
  - パッケージルート: `kabusys` を導入。バージョンは `0.1.0`。
  - public API エクスポート: `data`, `strategy`, `execution`, `monitoring` を __all__ に定義。

- 設定・環境変数管理 (`kabusys.config`)
  - `.env` / `.env.local` の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で探索）。
  - 読み込みの優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロードを無効化するフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート（テスト用途）。
  - .env パーサは export 構文・クォート・エスケープ・インラインコメントに対応する堅牢な実装。
  - Settings クラスを提供し、各種必須設定をプロパティ経由で取得:
    - J-Quants / kabuAPI / Slack / DB（DuckDB/SQLite）パス / 環境（development, paper_trading, live）/ ログレベル など。
  - 必須環境変数が欠落した場合は明示的な ValueError を発生させる。

- データプラットフォーム関連 (`kabusys.data`)
  - ETL 周り:
    - `pipeline.ETLResult` を公開（`kabusys.data.etl` 経由で再エクスポート）。
    - ETL 実行結果を表す dataclass（品質チェック結果・エラー一覧を含む）。
    - ETL の補助ユーティリティ（テーブル存在確認、最大日付取得、トレーディング日調整など）。
  - カレンダー管理 (`calendar_management`):
    - JPX マーケットカレンダーの差分取得・夜間更新ジョブ `calendar_update_job`。
    - 営業日判定・前後営業日取得・期間内営業日一覧取得・SQ判定の API を提供（DuckDB ベース）。
    - market_calendar がない場合の曜日ベースフォールバックや最大探索日数制限を実装。
    - J-Quants クライアント（`jquants_client`）との連携を想定した設計。

- AI（自然言語処理）機能 (`kabusys.ai`)
  - ニュース NLP スコアリング (`news_nlp.score_news`):
    - raw_news / news_symbols を集約して銘柄ごとのニュースを生成し、OpenAI（gpt-4o-mini、JSON mode）でセンチメントを評価。
    - バッチ処理（最大 20 銘柄 / コール）、記事数 / 文字数のトリミング、429/ネットワーク/5xx に対する指数バックオフリトライを実装。
    - レスポンスの厳密なバリデーション（JSON 抽出、results フォーマット、既知コードフィルタ、数値検証）を実施。
    - 得られたスコアを ±1.0 にクリップし、ai_scores テーブルへ冪等的に（DELETE → INSERT）書き込み。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を厳密に定義し、ルックアヘッドバイアスを回避。
    - API キーは引数または環境変数 OPENAI_API_KEY で解決。未設定時は ValueError を発生。
  - 市場レジーム判定 (`regime_detector.score_regime`):
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出。
    - prices_daily / raw_news を参照して ma200_ratio とマクロニュースタイトルを取得、LLM により macro_sentiment を評価。
    - レジームスコア合成後、market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時は ROLLBACK を試行して例外を伝播。
    - LLM 呼び出しは別実装の内部関数を用い、モジュール結合を低減。API エラー時はフェイルセーフとして macro_sentiment = 0.0 にフォールバック。
    - ルックアヘッドバイアス防止に配慮（target_date 未満のみ参照、datetime.today() を直接参照しない）。

- リサーチ（因子・特徴量）機能 (`kabusys.research`)
  - ファクター計算 (`factor_research`):
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）。
    - Volatility / Liquidity: 20 日 ATR（atr_20、atr_pct）、20 日平均売買代金、出来高比率。
    - Value: PER（EPS が 0 または欠損時は None）、ROE（raw_financials より取得）。
    - DuckDB による SQL + Python 実装。欠損データ時の扱い・データ不足判定を明記。
  - 特徴量探索 (`feature_exploration`):
    - 将来リターン計算（複数ホライズン対応、デフォルト [1,5,21]）。
    - Information Coefficient（Spearman ρ）計算、ランク化ユーティリティ `rank`（同順位は平均ランク）。
    - ファクター統計サマリー `factor_summary`（count, mean, std, min, max, median）。
  - 既存ユーティリティ `zscore_normalize` を再エクスポート（`kabusys.data.stats` 経由）。

### 変更
- （初版のため該当なし）

### 修正（バグ修正 / 安全対策）
- DB 書き込み時の堅牢化:
  - トランザクションを使用し、例外時は ROLLBACK を試行（失敗時はログを出力）。
  - DuckDB の executemany に関する制約（空リスト不可）に対する回避処理を追加。
- OpenAI API 呼び出し周りの安定化:
  - 429 / 接続エラー / タイムアウト / サーバー 5xx に対するリトライ戦略を実装。
  - JSON パース失敗や予期せぬレスポンスを検出した場合は該当チャンクをスキップし、サービス全体の停止を防止。

### セキュリティ
- （初版のため該当なし）

### 既知の制限 / 注意点
- 外部依存:
  - J-Quants クライアント（`kabusys.data.jquants_client`）や OpenAI SDK が必要。
  - 実行には各種環境変数（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID、OPENAI_API_KEY など）の設定が必要。
- strategy / execution / monitoring など一部の API は __all__ にエクスポートされているが、本リリースのコードスナップショットでは詳細実装の記載が限定的（今後の拡張を想定）。
- LLM 利用に伴うコスト・レイテンシ・モデルの変更リスクはユーザー側で管理する必要あり。

---

今後の予定（例）
- モデル切替やローカル代替モデル対応、監視・アラート機能の追加、strategy / execution 周りの発注実装などを予定しています。