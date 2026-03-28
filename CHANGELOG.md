CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに準拠して記載しています。  
主要なバージョンは semver を想定しています。

[Unreleased]
------------

- （今後の変更をここに記載）

[0.1.0] - 2026-03-28
-------------------

Added
- 初回公開: KabuSys 0.1.0 を追加。
  - パッケージ全体のエントリポイント（kabusys.__init__）を導入。公開サブパッケージ: data, strategy, execution, monitoring。
- 環境設定管理（kabusys.config）を追加。
  - .env / .env.local 自動ロード（プロジェクトルート判定: .git または pyproject.toml を探索）。
  - 行パーサはコメント・export プレフィックス・クォート・エスケープを考慮。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 必須変数取得ヘルパー _require、Settings クラスで環境変数による設定値取得を提供（J-Quants、kabuステーション、Slack、DBパス、環境・ログレベル検証など）。
- ニュースNLP（kabusys.ai.news_nlp）を追加。
  - raw_news / news_symbols を元にニュースを銘柄ごとに集約し、OpenAI（gpt-4o-mini）の JSON mode を用いてセンチメント（-1.0〜1.0）を算出。
  - バッチ処理（最大 20 銘柄 / リクエスト）、記事数・文字数の上限、JSON バリデーション、スコアのクリップ処理を実装。
  - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ、API失敗時はフォールバック（失敗したチャンクは空スコアにして継続）。
  - ai_scores テーブルへ冪等的（DELETE → INSERT）に書き込むロジックを提供。
  - タイムウィンドウ計算ユーティリティ calc_news_window を公開。
- 市場レジーム判定（kabusys.ai.regime_detector）を追加。
  - ETF 1321（Nikkei 225 連動ETF）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull / neutral / bear）を判定。
  - prices_daily / raw_news を参照し、計算結果を market_regime テーブルへ冪等書き込み。
  - LLM 呼び出しは独立実装。API失敗時は macro_sentiment=0.0 のフェイルセーフを適用。
  - リトライ・バックオフ・JSON パースエラーハンドリングあり。
- Data モジュール（kabusys.data）に ETL / カレンダー管理機能を追加。
  - pipeline.ETLResult: ETL 実行結果を表す dataclass を公開（取得数・保存数・品質問題・エラー集約・辞書化ユーティリティを含む）。
  - pipeline: 差分取得、バックフィル、品質チェックのためのユーティリティを実装（J-Quants client 経由での取得を想定）。
  - calendar_management:
    - JPX カレンダー取得用の夜間バッチ (calendar_update_job) を実装。バックフィル・健全性チェック・J-Quants からの差分取得を考慮。
    - 営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB にカレンダーが無い場合は曜日（平日）ベースのフォールバックを使用。
    - _MAX_SEARCH_DAYS による探索上限、エラー時の安全な挙動を保証。
- Research モジュール（kabusys.research）を追加。
  - factor_research:
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、相対 ATR、出来高関連）、Value（PER, ROE）等のファクター計算を実装。
    - DuckDB 上の prices_daily / raw_financials を参照し、(date, code) キーの辞書リストを返す。
    - データ不足時に None を返す安全設計。
  - feature_exploration:
    - 将来リターン計算 calc_forward_returns（任意ホライズン、検証済み入力制約）。
    - IC（Information Coefficient）計算 calc_ic（Spearman の ρ をランクで計算、最小サンプルチェックあり）。
    - ランク化ユーティリティ rank（同順位は平均ランク）。
    - 統計サマリー factor_summary（count/mean/std/min/max/median）。
  - research.__init__ で主要ユーティリティを再公開（zscore_normalize は data.stats 由来）。
- 内部実装の設計上の配慮・フェイルセーフ等（全体的な設計指針としてドキュメント化）。
  - ルックアヘッドバイアス防止: datetime.today()/date.today() をモデルの中心処理で直接参照しない（関数へ target_date を渡す設計）。
  - DuckDB を主要なオンディスクデータベースとして採用し、SQL と Python のハイブリッドで集計処理を実装。
  - 外部 API 呼び出し（OpenAI, J-Quants 等）は明示的な API キー注入・例外処理・リトライ戦略を実装し、API 失敗時に処理全体が致命的に停止しない設計。
  - DB 書き込みは可能な限り冪等性を担保（DELETE→INSERT、ON CONFLICT 相当の保存を想定）。
  - テスト容易性: OpenAI 呼び出し箇所は内部ヘルパーを通して差し替え可能（unittest.mock.patch を想定）。

Fixed
- （初回リリースのため該当なし）

Changed
- （初回リリースのため該当なし）

Security
- OpenAI API キーや各種シークレットは Settings 経由で必須チェックを行う。自動 .env ロード時にも OS 環境変数を保護する仕組み（protected set）を導入。

注記（実装上の重要点）
- OpenAI のレスポンスは JSON mode を利用する想定だが、実運用では SDK/API の仕様変更に伴う例外が発生する可能性があるためパースの堅牢化（前後テキストの切り出し等）を施しています。
- DuckDB の executemany に空リストを渡せない制約に対するガードがあるため、書き込み前に params が空でないかを確認しています。
- calendar_update_job 等で日付の健全性チェックを行い、極端に未来日が検出された場合には安全のため処理をスキップします。
- デフォルト設定や閾値（バッチサイズ、ウィンドウ、重みなど）はソースコード内の定数として定義されており、将来的に設定化が可能です。

今後の予定（候補）
- strategy / execution / monitoring サブパッケージの実装（本リリースではインターフェースのみ公開）。
- 設定の外部化（ YAML/JSON ）やより細かなログ出力設定、メトリクス収集の追加。
- 単体テスト・統合テストの充実（特に外部 API のモックを用いた回帰テスト）。
- OpenAI の利用に関するコスト最適化（圧縮プロンプト、キャッシュ、より軽量モデルの検討）。

---  
（この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノートとして用いる場合は必要に応じて調整してください。）