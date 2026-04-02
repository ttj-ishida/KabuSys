# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

※ 下記はソースコードの内容から推測して作成したリリースノートです。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-02
初回公開リリース。

### 追加 (Added)
- パッケージ全体
  - パッケージ初期構成を追加。モジュール公開: kabusys.data, kabusys.strategy, kabusys.execution, kabusys.monitoring（__all__）。
  - パッケージバージョンを 0.1.0 に設定。

- 設定 / 環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数からの設定読み込み機能を実装。
  - プロジェクトルート検出: .git または pyproject.toml を基準に自動検出（CWD 非依存）。
  - .env / .env.local の自動ロード（OS 環境変数優先、.env.local は上書き許可）。
  - エクスポート形式 "export KEY=val" やシングル/ダブルクォート、エスケープ、コメント処理等に対応した .env パーサを実装。
  - 環境変数取得ユーティリティ Settings を提供（J-Quants、kabuステーション、Slack、DB パス、監視設定、システム設定等のプロパティを含む）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - バリデーション: KABUSYS_ENV / LOG_LEVEL の允許値チェック、必須変数が未設定の場合は ValueError。

- AI（自然言語処理）関連 (kabusys.ai)
  - news_nlp モジュール
    - raw_news / news_symbols からニュースを銘柄ごとに集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメント（ai_score）を算出。
    - バッチ処理（最大20銘柄／チャンク）、1銘柄当たりの最大記事数・最大文字長でトリムする仕組みを実装。
    - 再試行（429/ネットワーク断/タイムアウト/5xx）に対する指数バックオフ実装。
    - レスポンス検証ロジックを実装（JSON 抽出、results 配列、code/score 検証、スコアの有限性チェック、±1 でクリップ）。
    - 成功スコアのみ ai_scores テーブルへ（DELETE → INSERT）書き込み。部分失敗時に既存スコアを保護する設計。
    - calc_news_window ユーティリティ（JST ベースのニュース収集ウィンドウ計算）を実装。

  - regime_detector モジュール
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース由来の LLM センチメント（重み 30%）を統合して日次の市場レジーム（bull / neutral / bear）を判定。
    - prices_daily から ma200_ratio を計算（ルックアヘッド防止で target_date 未満のみ使用、データ不足時は中立値を採用）。
    - raw_news からマクロキーワードでフィルタしたタイトルを取得し、OpenAI（gpt-4o-mini）に送信して macro_sentiment を取得。
    - API エラー時はフェイルセーフとして macro_sentiment=0.0 を採用。
    - レジームスコア合成後、market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - OpenAI 呼び出しは独立実装で、モジュール結合を避ける設計。

- Data / ETL / カレンダー管理 (kabusys.data)
  - ETL パイプライン用の ETLResult データクラスと基本ロジック（kabusys.data.pipeline を公開）。
  - pipeline モジュール（差分取得・保存・品質チェックの骨格）
    - J-Quants から差分取得して idempotent に保存する方針。
    - backfill 日数、カレンダー先読み等の定数と設計方針の実装。
    - ETL 実行結果（取得件数・保存件数・品質問題・エラー）を集約可能。
  - calendar_management モジュール
    - market_calendar を用いた営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を提供。
    - DB 登録がない場合は曜日ベース（週末除外）のフォールバックを採用。
    - JPX カレンダーを J-Quants API から差分取得して保存する夜間ジョブ calendar_update_job を実装（バックフィル・健全性チェック・保存呼び出し）。
    - 最大探索日数の制限や日付型の扱いに注意した実装。

- Research（ファクター計算・特徴量探索） (kabusys.research)
  - factor_research
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性指標（20 日平均売買代金、出来高比）およびバリュー（PER、ROE）を計算する関数を実装。
    - DuckDB のウィンドウ関数を活用した効率的な SQL ベース実装。
    - データ不足時に None を返す等、安全性を考慮。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク変換（rank）、ファクターサマリ（factor_summary）を実装。
    - スピアマンランク相関（ランクの Pearson 計算）により IC を算出。
    - pandas 等の外部依存を避け、標準ライブラリ + duckdb で完結する設計。

### 修正 (Fixed)
- 初版のため特段の「修正履歴」はなし（実装に伴う注意点やフェイルセーフ処理は各モジュールに組み込み済み）。

### 既知の制約・注意事項 (Notes)
- OpenAI
  - news_nlp / regime_detector は OpenAI API（gpt-4o-mini）を利用。OPENAI_API_KEY が必要。api_key 引数も受け付ける。
  - API レスポンスは JSON Mode を前提とするが、万が一余計な前後テキストが混入した場合に備えた復元ロジックを備える。
  - レートリミットや一時的な接続障害に対しては指数バックオフで再試行し、最終失敗時は該当チャンクをスキップして処理継続する（フェイルセーフ）。
- ルックアヘッドバイアス防止
  - 各 AI / ファクター / ETL モジュールは date.today() を基準にしない実装方針が取られており、target_date 引数を明示的に受けることでルックアヘッドを防止している。
- DuckDB
  - データ操作は DuckDB 接続を前提。executemany の空リスト扱い等、DuckDB のバージョン依存の振る舞いに配慮した実装がある。
- 環境変数の自動ロード
  - デフォルトでプロジェクトルートの .env / .env.local が自動ロードされるため、テスト時等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すること。
- 部分書き込み保護
  - news_nlp / ai_scores への書き込みは、取得済みコードのみに対して置換処理（DELETE → INSERT）を行う設計で、部分失敗時に既存データを不必要に削除しない。

### セキュリティ (Security)
- なし

---

今後のリリース候補（想定）
- ETL の細部完成（pipeline の未完成箇所の補完、エラーハンドリング強化）。
- モジュール間のテスト・CI、型注釈の完全化。
- monitoring / execution / strategy の具体的な実装およびドキュメント追加。

（以上）