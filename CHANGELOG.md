# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。  

最新リリース: 0.1.0

<!-- 区切り -->
## [Unreleased]

特になし。

## [0.1.0] - 2026-03-28

初回公開リリース。日本株自動売買のためのデータ処理・研究・AI支援・環境設定ユーティリティ群を提供します。主な追加内容は以下の通りです。

### Added
- パッケージ基礎
  - パッケージ初期化とバージョン管理を追加（kabusys.__version__ = "0.1.0"）。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ に登録。

- 環境設定・ロード機能（kabusys.config）
  - .env ファイル（.env, .env.local）または OS 環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルート検出機能を実装（.git または pyproject.toml を基準）。これにより CWD に依存せず自動ロードが可能。
  - .env パーサを実装:
    - 空行・コメント行・`export KEY=val` 形式に対応。
    - シングル/ダブルクォート内でのバックスラッシュエスケープ処理をサポート。
    - クォートなしの値は、直前が空白/タブの `#` を行コメントとして扱うルールを採用。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用途に便利）。
  - Settings クラスを提供（J-Quants / kabuステーション / Slack / DB パス / 環境・ログレベル判定など）。各設定に必須チェックや値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）を実装。

- AI 支援モジュール（kabusys.ai）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp.score_news）
    - raw_news + news_symbols からターゲット時間窓の記事を集約し、OpenAI（gpt-4o-mini）にバッチ送信して銘柄ごとのセンチメント（ai_score）を ai_scores に書き込む。
    - バッチ処理（1回最大 20 銘柄）、1銘柄あたり最大記事数・最大文字数でトリム（トークン肥大対策）。
    - JSON Mode を利用、レスポンスの堅牢なバリデーションとスコアの ±1.0 クリップ。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。
    - API 失敗時は該当チャンクをスキップし、全体処理を継続する（フェイルセーフ）。
    - テストで OpenAI 呼び出しを差し替え可能（_call_openai_api を patch 可能）。
    - executemany の空リストバインド回避（DuckDB 0.10 対策）や、部分失敗時に既存スコアを消さない差し替えロジックを採用。
  - 市場レジーム判定（kabusys.ai.regime_detector.score_regime）
    - ETF 1321 の200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日別に market_regime テーブルへ書き込む。
    - マクロキーワードフィルタ／最大記事数制限／LLM の JSON レスポンスパース／リトライ処理を実装。
    - API 失敗時は macro_sentiment = 0.0 にフォールバックし、処理継続（フェイルセーフ）。
    - 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実装。
    - テスト容易性のため、OpenAI 呼び出しの差し替えを想定した分離設計。

- データ基盤（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を用いた営業日判定・前後営業日取得・期間内営業日リスト取得・SQ日判定等のユーティリティを実装。
    - DB 登録値を優先し、未登録日は曜日ベースでフォールバックする一貫したロジック。
    - calendar_update_job: J-Quants から差分でカレンダーを取得して保存する夜間バッチジョブを実装（バックフィル、健全性チェックあり）。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを公開。ETL 実行結果（取得数・保存数・品質問題・エラー）を集約。
    - 差分更新・バックフィル・品質チェックを行う設計方針を反映（jquants_client, quality モジュールと連携想定）。
    - DuckDB テーブル存在チェック、最大日付取得ユーティリティを実装。

- 研究ツール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M、ma200乖離）、Volatility（20日 ATR, 相対 ATR）、Liquidity（20日平均売買代金, 出来高比率）、Value（PER, ROE）を計算する関数を実装。
    - DuckDB 上の prices_daily / raw_financials のみを参照する純粋分析関数（取引・API 不要）。
    - データ不足時は None を返す安全設計。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）：複数ホライズンを一括で取得、horizons の検証あり。
    - IC（Information Coefficient）計算（calc_ic）：スピアマンのランク相関を実装（ties の平均ランク処理を含む）。
    - ランク変換ユーティリティ（rank）: 同順位は平均ランク。丸めによる ties 検出漏れ対策あり。
    - 統計サマリー（factor_summary）：count/mean/std/min/max/median を算出。

### Changed
- 設計方針・安全性
  - データ処理・AI モジュールにおいて、datetime.today() / date.today() を直接参照することを避け、引数で target_date を受け取る方針を徹底（ルックアヘッドバイアス回避）。
  - OpenAI 呼び出しはモジュール毎に独立したプライベート関数として実装し、モジュール間の強い結合を避けてテスト可能性を向上。

### Fixed / Robustness
- API エラー処理の強化
  - OpenAI 呼び出しに対する 429/ネットワーク/タイムアウト/5xx のリトライとフォールバック（macro_sentiment=0.0 やチャンクスキップ）を実装し、処理継続性を向上。
  - JSON レスポンスパースの堅牢化（前後余計なテキストが混じるケースのために最外の {} を抽出する復元処理を追加）。
  - APIError で status_code が存在しない場合にも安全に扱うロジックを追加。
- DB 書き込みの堅牢化
  - DuckDB に対する executemany の空リストバインド回避（DuckDB 0.10 の制約）を実装。
  - トランザクション失敗時に ROLLBACK を試行し、ROLLBACK 自体が失敗した場合は warning を出力して上位に例外を伝播するようにした。
  - DuckDB から返る日付値の取り扱いを統一するユーティリティを追加（_to_date）。
- .env 読み込みの堅牢化
  - .env ファイル読み込みでファイルオープン失敗時に警告を出し安全にスキップ。

### Security
- 環境変数保護
  - .env 自動ロード時、既存 OS 環境変数を protected として扱い、.env.local でも意図せぬ上書きを避ける仕組みを導入。

### Notes / Constraints
- OpenAI API の利用
  - news_nlp.score_news / regime_detector.score_regime は API キー（api_key 引数または環境変数 OPENAI_API_KEY）の指定が必須。未指定時は ValueError を送出します。
- DB スキーマ前提
  - 多くの関数は DuckDB 上の特定テーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等）を前提としているため、呼び出し側で適切にテーブルを準備する必要があります。
- 依存外部挙動
  - jquants_client, quality モジュール等は外部実装との連携を前提としているため、実行環境に応じて適切に注入・モックしてください。

---

今後の予定（例）
- strategy / execution / monitoring の具体的実装を追加して自動売買フローを完成させる。
- テストカバレッジ拡充（特に OpenAI 呼び出しのモック化、DuckDB 相互作用の統合テスト）。
- パフォーマンス改善（大規模データセットに対する ETL 最適化、AI バッチ処理のパラレル化検討）。

---

（本 CHANGELOG はコードベースの現状から機能・改善点・設計意図を推測して作成しています。実際のリリースノート作成時は変更の正確な履歴を確認の上、適宜編集してください。）