# CHANGELOG

すべての重要な変更点を記録します。フォーマットは Keep a Changelog に準拠しています。

リリース日: 2026-03-28

## [0.1.0] - 2026-03-28
最初の公開リリース。日本株自動売買システム「KabuSys」のコアライブラリをまとめて公開します。以下は実装済みの主要機能・モジュールと設計上の注意点です。

### Added
- パッケージ初期化
  - パッケージバージョンを `__version__ = "0.1.0"` として公開。
  - 公開 API: data, strategy, execution, monitoring を __all__ に設定。

- 環境変数・設定管理（kabusys.config）
  - .env ファイル（プロジェクトルートの .env/.env.local）を自動的に読み込む仕組みを実装。
  - 自動ロードを無効化するための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - .env パーサは:
    - `export KEY=val` 形式に対応
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理をサポート
    - インラインコメント処理（クォート外での # を扱うルール）を実装
  - 読み込み時の上書き制御（override）と OS 環境変数を保護する protected キーセットを実装。
  - Settings クラスで必須設定の取得（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等）と、env/log level のバリデーション（許容値チェック）を提供。
  - デフォルト DB パス（DUCKDB_PATH, SQLITE_PATH）の設定と Path 型での展開を提供。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を元に銘柄単位でニュースを集約し、OpenAI（gpt-4o-mini）に対してバッチでセンチメント評価を行い、ai_scores テーブルへ書き込む。
    - バッチサイズ、記事数・文字数のトリム制御、JSON Mode を使った厳密なレスポンス期待、レスポンス検証ロジックを実装。
    - レートリミット(429)、ネットワーク断、タイムアウト、5xx に対する指数バックオフのリトライ実装。
    - リスポンスのパース失敗はスキップ（例外を投げずフェイルセーフ）し、部分成功時も既存スコアを保護するために対象コードのみ DELETE → INSERT を行う。
    - テスト容易性のため OpenAI 呼び出し関数（内部 _call_openai_api）を patch 可能に実装。
    - ニュースウィンドウ計算（前日15:00 JST〜当日08:30 JST を UTC に変換）を提供。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（225連動）200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成し、日次で market_regime に書き込み（冪等処理）。
    - データ不足や API 失敗時のフェイルセーフ（マクロセンチメント=0.0）を実装。
    - OpenAI 呼び出しはニュース NLP とは独立した実装（モジュール結合を防止）。
    - リトライ・エラーハンドリング・JSON レスポンスパースの堅牢化を実装。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダーの夜間差分更新ジョブ（calendar_update_job）を実装。J-Quants からの取得と market_calendar テーブルへの冪等更新を想定。
    - 営業日判定ユーティリティ（is_trading_day、next_trading_day、prev_trading_day、get_trading_days、is_sq_day）を実装。DB の登録値を優先し、未登録日は曜日ベースでフォールバック。
    - 最大探索日数の上限やバックフィル・健全性チェックを導入して安全性を確保。
  - ETL パイプライン（kabusys.data.pipeline, kabusys.data.etl）
    - 差分取得、保存、品質チェックのワークフローを想定した ETLResult を導入。
    - データ最小取得日、バックフィルロジック、品質チェックの収集（重大度判定）などを設計。
    - DuckDB を用いた最大日付取得やテーブル存在チェックなどのユーティリティ実装。
  - jquants_client / quality などのクライアント層と連携を想定（実体は data パッケージ配下で参照）。

- リサーチ（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M、ma200乖離）、ボラティリティ（20日ATR、相対ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER, ROE）を計算する関数を実装。
    - DuckDB の SQL とウィンドウ関数を使い、date / code をキーとした結果を返す設計。
  - feature_exploration:
    - 将来リターン計算（任意 horizon）、IC（Spearman の順位相関）計算、rank（同順位は平均ランク）、factor_summary（count/mean/std/min/max/median）を実装。
    - Pandas に依存せず標準ライブラリで実装。

### Changed
- （初期リリースのため変更履歴はなし）

### Fixed
- （初期リリースのため修正履歴はなし）

### Security
- 環境変数読み込み時に OS 環境変数保護（protected set）を導入し、意図しない上書きを防止。
- API キー（OpenAI等）未設定時は明示的に ValueError を投げ、秘匿情報の取り扱いを厳密化。

### Notes / 注意事項
- OpenAI 連携
  - 両 AI モジュール（news_nlp, regime_detector）は OpenAI の Chat Completions を想定（gpt-4o-mini, JSON mode を利用）。実行には `OPENAI_API_KEY` の設定、または api_key 引数の提供が必要。
  - レスポンスは厳密な JSON を期待しているが、冗長テキスト混入を考慮した復元ロジックもある。
  - テストのために内部の _call_openai_api を patch して外部通信をモック可能。

- データベース
  - DuckDB を主要な時系列データ格納先として利用する前提。SQL の書き方は DuckDB の仕様に合わせている（例: executemany の空リスト回避）。
  - ai_scores / market_regime 等への書き込みは冪等性を考慮（DELETE→INSERT、BEGIN/COMMIT/ROLLBACK 制御）。

- 設計上の方針
  - ルックアヘッドバイアス防止のため、datetime.today() / date.today() を直接参照しない関数設計（target_date を明示的に与える）。
  - API エラーやパース失敗に対しては例外を過度に投げず、フェイルセーフ（スコアをスキップ or 0 にフォールバック）を優先する箇所がある。ただし DB 書き込み失敗時は上位へ例外を伝播。

- 必須環境変数
  - 実行に必須な環境変数（例）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY
  - Settings._require により未設定時は ValueError が発生するため、運用環境では .env 等で設定を行ってください。

### Known limitations / 今後の改善候補
- ニュース解析の結果（ai_score）と sentiment_score は現在同値で挿入しているが、将来的に別計算や正規化を導入する余地がある。
- 一部の DuckDB バインド挙動（list バインド互換性）を避けるために executemany を利用している箇所があり、パフォーマンス改善の余地がある。
- calendar_update_job や ETL パイプラインの外部依存（jquants_client, quality）について、より詳細なエラーハンドリング・リトライ戦略を追加可能。

---

以上がバージョン 0.1.0 の主要な内容です。今後のリリースでは、テストカバレッジの拡充、運用向け監視/アラート機能の強化、AI 評価結果の説明性向上やバッチ性能の改善などを予定しています。