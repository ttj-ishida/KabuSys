# Changelog

すべての変更は Keep a Changelog の慣例に従って記載しています。  
このファイルはソースコードの内容から推測して作成した初期リリース向けの変更履歴です。

全般的な注意
- 日付は本 CHANGELOG 作成日（2026-04-03）を使用しています。実際のリリース日付は適宜調整してください。
- 記載はコード内の実装・ docstring・定数・設計方針等から推測した機能・設計決定に基づきます。

## [Unreleased]

（次リリース向けの変更はここに記載）

## [0.1.0] - 2026-04-03

初回公開リリース。

### Added
- パッケージ基盤
  - kabusys パッケージを追加。バージョンは `0.1.0`。
  - パッケージ公開インターフェースとして `data`, `strategy`, `execution`, `monitoring` を __all__ に設定。

- 設定管理（kabusys.config）
  - .env ファイルおよび OS 環境変数から設定を自動読み込みする仕組みを実装。
    - 自動読み込みの優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルートは .git または pyproject.toml を基準に探索（CWD に依存しない）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを無効化可能（テスト向け）。
  - .env パーサーは export 形式、引用符、エスケープ、インラインコメント等に対応。
  - `Settings` クラスを提供し、アプリケーション設定をプロパティで取得可能。
    - J-Quants / kabuステーション / LINE / DB パス / 監視閾値 / ログレベル等の主要設定をカバー。
    - 必須変数未設定時は明示的なエラー（ValueError）を発生。
    - `KABUSYS_ENV` と `LOG_LEVEL` の入力検証（許容値セット）を実装。
    - パス系は Path オブジェクトとして返却（~ 展開）。

- データ層（kabusys.data）
  - ETL 用インターフェース公開（ETLResult の再エクスポート）。
  - calendar_management モジュールを実装
    - JPX マーケットカレンダー管理（market_calendar テーブル）と営業日判定ユーティリティを提供。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装。
    - DB 登録データが無い場合は曜日（土日）ベースでフォールバックする設計。
    - calendar_update_job により J-Quants API から差分取得して冪等的に保存（バックフィル・健全性チェックあり）。
  - pipeline / etl モジュールを実装
    - ETLResult データクラスを定義（ETL の取得数・保存数・品質問題・エラー一覧などを保持）。
    - ETL の差分取得・保存・品質チェックを行う設計（jquants_client と quality モジュールを利用）。
    - デフォルトのバックフィル動作やカレンダー先読みなどの運用向け設定を持つ。
    - DuckDB との互換性を考慮した実装（空の executemany を避ける等）。

- AI 関連（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を用いて銘柄別にニュースを集約し、OpenAI（gpt-4o-mini、JSON mode）でセンチメントを算出。
    - バッチ処理（最大 20 銘柄／チャンク）、銘柄あたりの記事数・文字数上限を実装（トークン肥大化対策）。
    - 再試行（429・ネットワーク・タイムアウト・5xx を対象）と指数バックオフを実装。
    - レスポンスの厳密なバリデーション（JSON 抽出、results 配列、code/score の検査）を実装。
    - スコアは ±1.0 にクリップ、取得成功分のみ ai_scores テーブルへ（DELETE → INSERT の冪等書き込み）。
    - テスト容易性のため OpenAI 呼び出し関数を差し替え可能（内部で _call_openai_api を使用）。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window として提供。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225 連動）200 日移動平均乖離（重み 70％）と、マクロニュースの LLM センチメント（重み 30％）を合成して日次の市場レジーム（bull / neutral / bear）を算出。
    - OpenAI（gpt-4o-mini、JSON mode）を用いたマクロセンチメント評価を実装。API エラー時はフォールバックで macro_sentiment=0.0。
    - レジームスコア合成・閾値判定・market_regime への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - ルックアヘッドバイアス対策（datetime.today()/date.today() を直接参照しない、prices_daily に date < target_date を明示）。
    - マクロキーワードセットやリトライ、最大記事数といった定数を設定可能。
    - OpenAI 呼び出しはテスト用に差し替え可能（内部関数経由）。
  - ai パッケージの __init__ で score_news を公開。

- Research（kabusys.research）
  - factor_research モジュール
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER、ROE）を DuckDB の SQL で計算する関数を実装。
    - データ不足時の None 処理や結果を (date, code) ベースの dict リストで返却する仕様。
  - feature_exploration モジュール
    - 将来リターン計算（calc_forward_returns）を実装。horizons のバリデーションあり。
    - IC 計算（calc_ic）: スピアマンのランク相関を独自実装し ties を平均ランクで処理。
    - ランキング関数 rank、統計サマリー factor_summary（count/mean/std/min/max/median）を提供。
    - pandas 等の外部ライブラリに依存しない実装方針。
  - research パッケージの __init__ で主な関数群をまとめてエクスポート。

- その他
  - DuckDB を用いたローカル分析基盤を前提（各種関数は DuckDB 接続を受け取る）。
  - ロギング箇所を適宜追加。重要な処理は INFO/DEBUG/WARNING/EXCEPTION で記録。

### Changed
- 初回リリースのため該当なし（今後のバージョンで追加予定）。

### Fixed
- 初回リリースのため該当なし。

### Security
- OpenAI API キーは関数引数で注入可能。未設定時は環境変数 OPENAI_API_KEY を参照。未提供時は ValueError を発生させることで誤った運用を防止。

### Notes / Implementation choices（重要な設計上の注意点）
- ルックアヘッドバイアス対策:
  - AI 評価やファクター計算は target_date を明示的に受け取り、内部で date.today() を参照しない方針を徹底。
  - prices_daily 等のクエリは date < target_date や date BETWEEN を適切に使い、未来データ参照を避ける。
- フェイルセーフ:
  - OpenAI 呼び出し失敗やパースエラーは例外を上位へ波及させず、スコアを中立（0.0 または None）にして処理を継続する設計が多く採用されている。
- 冪等書き込み:
  - DB 書き込みは BEGIN/DELETE/INSERT/COMMIT（例: market_regime）や DELETE → INSERT（ai_scores）で冪等性を確保。
  - DuckDB の executemany 空リスト制約に配慮した実装（空の executemany を呼ばないガード）。
- テスト容易性:
  - OpenAI API 呼び出し部は内部ヘルパー経由でまとめており、ユニットテスト時に patch/モックしやすい構造。
  - api_key を引数で注入できる関数設計でテスト環境でのキー取り扱いを容易にしている。

---

今後の予定（推測）
- strategy / execution / monitoring パッケージの実装（現状は __all__ に名前があるが詳細は未提示）。
- jquants_client や quality モジュールの詳細実装・テストケース充実化。
- ドキュメント（運用手順、.env.example、DB スキーマ）や CI / テスト整備。

必要であれば、上記 CHANGELOG を英語版や別形式（例: リリースノート向けの短い要約）に変換します。