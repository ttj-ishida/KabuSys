# Changelog

すべての注目すべき変更はこのファイルに記載します。  
このプロジェクトは Keep a Changelog の慣例に従って管理しています。

全般
- 初期バージョン: 0.1.0（リリース日: 2026-03-26）
- パッケージ名: kabusys
- 概要: 日本株自動売買システムのコアライブラリ。データETL、マーケットカレンダー管理、ファクター計算、研究用ユーティリティ、LLMを用いたニュース/マクロ評価などを含む。

## [0.1.0] - 2026-03-26

### Added
- パッケージ基盤
  - src/kabusys/__init__.py によりパッケージ公開: data, strategy, execution, monitoring を主要サブパッケージとしてエクスポート。
  - パッケージバージョンを __version__ = "0.1.0" として定義。

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイルおよび環境変数からの自動ロード機構を実装。プロジェクトルートの特定は .git または pyproject.toml を基準とするため、CWDに依存しない読み込みを実現。
  - .env と .env.local の優先順位をサポート（.env.local が上書き）。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサ実装: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いなどを考慮した堅牢なパーサを提供。
  - 環境変数取得ユーティリティ Settings を追加（J-Quants / kabu ステーション / Slack / DBパス / システム設定などのプロパティを公開）。入力値チェック（KABUSYS_ENV, LOG_LEVEL の有効値検証）とユーティリティプロパティ（is_live, is_paper, is_dev）を提供。

- データ関連（kabusys.data）
  - ETL パイプライン基盤を追加（kabusys.data.pipeline の ETLResult とユーティリティ関数）。
  - calendar_management:
    - JPX カレンダー管理ロジックを実装。is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティを提供。
    - calendar_update_job により J-Quants からの差分取得・バックフィル・保存処理を実装（保存は冪等性を考慮）。
    - DB未取得時の曜日ベースフォールバック、最大探索幅の上限、健全性チェック（将来日付の異常検出）などを実装。
  - ETL:
    - ETLResult データクラスを導入し、ETL 実行結果・品質問題・エラーメッセージ等を構造化して返却可能に。
    - DuckDB に対するテーブル存在チェック、最大日付取得ユーティリティを実装。

- AI / NLP（kabusys.ai）
  - news_nlp:
    - raw_news と news_symbols を集約して銘柄ごとにニュースを束ね、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄別センチメント（-1.0〜1.0）を評価する score_news を実装。
    - バッチ処理（1リクエストあたり最大20銘柄）、1銘柄あたりの記事数・文字数上限のトリム、リトライ（429/ネットワーク/5xx の指数バックオフ）を実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列構造検証、コード照合、数値検証）と ±1.0 クリップを実装。
    - DuckDB への書き込みは部分失敗に耐える設計（対象コードのみ DELETE → INSERT）で互換性のため executemany の空リストガードを追加。
    - calc_news_window を提供し、JST ベースでのニュース収集ウィンドウ計算を実装（テスト容易性のため日時関数のハード参照を避ける設計）。
  - regime_detector:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - MA200 の計算は target_date 未満のデータのみを使用してルックアヘッドバイアスを排除。
    - マクロニュース抽出（キーワードフィルタ）、OpenAI 呼び出し（gpt-4o-mini）での macro_sentiment 評価、リトライ、フェイルセーフ（API失敗時は macro_sentiment=0.0）を実装。
    - 結果は市場レジームテーブルへ冪等に書き込み（BEGIN/DELETE/INSERT/COMMIT）される。

- 研究用ユーティリティ（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離などのモメンタムファクターを計算。
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比等のボラティリティ／流動性指標を計算。
    - calc_value: raw_financials を用いた PER / ROE の算出。
    - いずれも DuckDB 上の SQL を駆使して効率的に計算し、(date, code) をキーとする辞書リストを返却。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン計算を実装（LEAD を使用）。
    - calc_ic: スピアマンランク相関（Information Coefficient）を実装（同順位は平均ランク扱い）。
    - rank, factor_summary: ランク変換と統計サマリーのユーティリティを実装。
  - research パッケージ内の主要関数を __all__ で再エクスポート。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは関数引数で注入可能（テスト容易性）で、引数未指定時は環境変数 OPENAI_API_KEY を参照。キーの未設定時は明示的に ValueError を発生させ、安全に失敗させる仕様。

---

注記 / 実装上の重要な設計方針
- ルックアヘッドバイアス対策として、いずれの AI / スコアリング関数も datetime.today() / date.today() を内部参照せず、必ず外部から target_date を受け取る設計になっています。
- OpenAI 呼び出し部分はテスト時に差し替え可能（ユニットテスト用のパッチフックが組み込まれています）。
- DuckDB の互換性を考慮して executemany に空リストを渡さない等の実装上の注意を入れています。
- DB 書き込みはできるだけ冪等・部分失敗耐性を持たせる（DELETE → INSERT、対象コードで絞る等）。

今後の予定（例）
- モデル検証・パフォーマンスチューニング、strategy / execution / monitoring の具体実装と連携
- ドキュメント整備（API 使用例、運用手順、テストカバレッジ）
- セキュリティ監査と運用時のシークレット管理強化

もし CHANGELOG に追加したい詳細（例: 発行日をリポジトリコミット日時に合わせる、未記載のサブモジュールの変更点を明記する等）があれば教えてください。