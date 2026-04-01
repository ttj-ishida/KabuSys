# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
このプロジェクトはセマンティックバージョニング (SemVer) を使用しています。

※ このファイルはコードベースから推測して作成した変更履歴です。実際のコミット履歴やリリースノートと差異がある場合があります。

## [Unreleased]

- なし

---

## [0.1.0] - 2026-04-01

Initial release — 日本株自動売買 / 研究用プラットフォームの初期実装。

### 追加 (Added)
- パッケージ初期構成
  - パッケージ名: kabusys
  - パッケージバージョン: 0.1.0

- 環境設定 / 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能
    - プロジェクトルートは .git または pyproject.toml から探索（CWD 非依存）
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env パーサ実装（export 先頭、クォート、エスケープ、コメント処理対応）
  - 必須環境変数アクセス用ユーティリティ Settings クラス
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等
    - パス設定（DuckDB / SQLite / PID ファイル）
    - 監視閾値（CPU / メモリ / ディスク）
    - 環境種別バリデーション（development / paper_trading / live）
    - ログレベルの検証

- AI モジュール (kabusys.ai)
  - ニュースセンチメント分析 (kabusys.ai.news_nlp)
    - raw_news と news_symbols から銘柄ごとに記事を集約して OpenAI（gpt-4o-mini, JSON Mode）でセンチメントを算出
    - バッチ処理（最大 20 銘柄/リクエスト）、トークン過膨張対策（記事数・文字数制限）
    - リトライ（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）、レスポンスバリデーション、スコアクリップ（±1.0）
    - ai_scores テーブルへの置換（DELETE→INSERT、部分失敗時に他銘柄を保護）
    - calc_news_window ユーティリティ（JST ベースのニュース窓を UTC naive datetime で計算）
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を組み合わせて日次レジームを判定（bull/neutral/bear）
    - DuckDB からのデータ取得、OpenAI 呼び出し、スコア合成、market_regime テーブルへの冪等書き込み
    - API キー注入可能（引数経由 or OPENAI_API_KEY 環境変数）
    - API エラー時はマクロセンチメントを 0.0 にフォールバック（フェイルセーフ）
    - 内部でルックアヘッドバイアスを避ける設計（date.today() 参照回避・SQL に date < target_date 条件）

- データプラットフォーム (kabusys.data)
  - マーケットカレンダー管理 (kabusys.data.calendar_management)
    - market_calendar テーブルを基にした営業日判定 / 翌前営業日検索 / 期間内営業日列挙 / SQ 判定
    - DB データがない場合は曜日ベースのフォールバック（週末を休場とみなす）
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新。バックフィル・健全性チェックを実装
  - ETL パイプライン (kabusys.data.pipeline / etl)
    - ETLResult データクラスの実装（取得数・保存数・品質問題・エラーの集約）
    - 差分更新・バックフィル方針（最終取得日の数日前から再取得）、品質チェックの集約設計
    - jquants_client との連携想定（fetch/save 関数を呼び出すフロー）
    - パイプラインのユーティリティ（テーブル存在チェック、最大日付取得等）
  - jquants_client の再利用を想定した設計（外部クライアントモジュール経由）

- 研究 / ファクター (kabusys.research)
  - factor_research
    - Momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）
    - Volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比
    - Value: PER（EPS ベース）、ROE（raw_financials から最新の財務データを結合）
    - DuckDB を用いた SQL ベースの計算（prices_daily / raw_financials 参照）
  - feature_exploration
    - 将来リターン計算（calc_forward_returns、任意ホライズン）
    - IC（Information Coefficient）計算（Spearman の ρ、ランク変換は平均ランク tie 処理）
    - 統計サマリー（count/mean/std/min/max/median）
    - 純標準ライブラリのみで実装（pandas などに依存しない）
  - 研究用ユーティリティの公開（zscore_normalize 等を data.stats から再利用）

- モジュール公開インターフェース
  - kabusys.__all__ に data, strategy, execution, monitoring を含むエクスポート（パッケージ構成の想定）
  - 各サブパッケージの主要関数を __all__ で公開（例: kabusys.ai.__all__ = ["score_news"]、kabusys.research.__all__ に研究関数群）

### 変更 (Changed)
- 設計上の安全性と互換性を重視した実装方針
  - DuckDB の executemany に対する互換性注意（空リストを渡さないガードを追加）
  - API 呼び出しのリトライ戦略は 429/ネットワーク/タイムアウト/5xx に限定し、それ以外は非リトライ（明示的にログを残してスキップ）
  - 日時取り扱いはすべて date / naive datetime で統一しタイムゾーン混入を避ける
  - ルックアヘッドバイアス防止のためコード内で date.today() / datetime.today() を直接参照しない方針を明記

### 修正 (Fixed)
- 初期リリース相当の実装安定化（データ不足時のフォールバック、例外発生時のロールバック処理等）
  - market_regime / ai_scores の書き込みを冪等化（BEGIN / DELETE / INSERT / COMMIT、ROLLBACK のログ）
  - レスポンスパース失敗時はフェイルセーフで 0.0 や空スコアにフォールバックし、パイプライン全体を停止させない

### 既知の問題 / 注意事項 (Known issues / Notes)
- OpenAI を利用する機能（news_nlp / regime_detector）は API キーが必須
  - 関数引数で api_key を渡すか、環境変数 OPENAI_API_KEY を設定する必要がある
- 環境変数の必須項目が満たされていない場合、Settings のプロパティアクセスで ValueError を送出
  - 必要な環境変数例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- DuckDB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials 等）を事前に用意しておくこと
- gpt-4o-mini の JSON Mode を前提にレスポンスパース処理を行っているため、API レスポンス形式が変わると影響を受ける
- News window は JST ベースで実装されており、calc_news_window が UTC naive datetime を返す点に注意
- calendar_update_job は J-Quants クライアント（jquants_client）に依存し、その実装／ネットワークにより処理結果が左右される

### マイグレーション / 使用上のリマインダ (Migration / Upgrade notes)
- 自動 .env ロードを無効化したい環境（テスト等）では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください
- OpenAI 関連処理は外部ネットワークに依存するため、テストでは _call_openai_api をモックすることを想定しています（ユニットテストで差し替え可能）
- DuckDB を使用するため、複数プロセスからの同時アクセスやバージョン依存（executemany の挙動等）に対して運用側での確認を推奨します

---

（このファイルはコードベースからの推測に基づいて作成されています。実際のリリースノートや履歴はリポジトリのコミットログに基づいて作成してください。）