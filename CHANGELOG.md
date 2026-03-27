Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。  

[Unreleased]
------------

（現時点でのリリースは 0.1.0 のみ。今後の変更はここに記載されます。）

[0.1.0] - 2026-03-27
--------------------

Added
- 基礎パッケージ構成を追加
  - パッケージ名: kabusys
  - __version__ = 0.1.0、公開サブモジュール: data, strategy, execution, monitoring

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を探索して判定）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env/.env.local の読み込み順・上書きルールを実装（OS 環境変数を protected として保護）。
  - シェル形式の export KEY=val とクォート付き値、行内コメントの扱い（エスケープ対応）をサポートするパーサを実装。
  - 必須環境変数取得用の _require、Settings クラスを提供（J-Quants・kabu API・Slack・DB パス・環境種別・ログレベル等）。
  - KABUSYS_ENV と LOG_LEVEL の入力検証（許容値チェック）を導入。
  - 設定値の Path 化（duckdb/sqlite のパス等）と環境フラグ（is_live/is_paper/is_dev）を提供。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を基に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini, JSON Mode）でセンチメントを査定して ai_scores テーブルへ保存する処理を実装。
    - タイムウィンドウ（JST 前日15:00〜当日08:30）計算ユーティリティ calc_news_window を実装。
    - バッチ処理（最大 20 銘柄/リクエスト）、1 銘柄あたりの最大記事数・最大文字数トリム、JSON レスポンスのバリデーション、スコアクリップ（±1.0）等を備える。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。失敗時は安全にスキップして処理継続（フェイルセーフ）。
    - レスポンスパース時の余計な前後テキストの扱い（最外側の {} を抽出）や整数コードの文字列化など、実運用での LLM の揺らぎに対する耐性を組み込む。
    - DuckDB の executemany に対する互換性を考慮し、空パラメータの場合は実行しないガードを実装。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（Nikkei-225 連動 ETF）の 200 日移動平均乖離（重み70%）と、マクロ経済ニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等書き込みする処理を実装。
    - マクロニュースフィルタ用キーワード群、最大記事数、OpenAI 呼び出し（gpt-4o-mini）を実装。
    - OpenAI API 呼び出しの再試行ロジック、API 失敗時の macro_sentiment=0.0 でのフォールバック、レスポンス JSON のパース、安全なスコアクリップ処理を実装。
    - ルックアヘッドバイアス防止のため datetime.today()/date.today() を参照しない設計、prices_daily クエリに date < target_date を使う等の実装方針を順守。

- Data モジュール（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを用いた営業日判定ユーティリティを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にデータが無い場合は曜日ベース（土日非営業）でフォールバックする堅牢な設計。
    - next/prev/get_trading_days は最大探索日数の上限を設け無限ループを防止。
    - calendar_update_job: J-Quants API から JPX カレンダーを差分取得し、バックフィル（直近数日を再取得）・健全性チェック（極端な future date の検出）・冪等保存を行う実装を提供。
    - jquants_client を介した fetch/save の分離、エラー時のハンドリングとログ出力を実装。

  - ETL パイプライン（kabusys.data.pipeline, kabusys.data.etl）
    - 差分更新の方針（最終取得日の算出、バックフィル、_MIN_DATA_DATE による初期化）に従った ETLResult データクラスを実装。
    - jquants_client を使った取得・保存、quality モジュールによる品質検査の枠組みを用意。
    - ETLResult による実行結果の集約（取得件数・保存件数・品質問題・エラーなど）と to_dict() によるシリアライズを提供。
    - テーブル存在チェックや最大日付取得ユーティリティを実装。

- Research モジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER, ROE）などの計算関数を実装。
    - DuckDB を用いた SQL ベースの計算、必要なデータ不足時の None 返却、結果は (date, code) キーの dict リストで返す設計。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns、任意の horizon をサポート）、IC（Information Coefficient）計算（calc_ic）、ランク変換ユーティリティ（rank）、統計サマリー（factor_summary）を実装。
    - pandas など外部ライブラリに依存せず標準ライブラリと DuckDB のみで動作する設計。
  - 研究用ユーティリティの再公開（zscore_normalize の再エクスポート等）。

Changed
- （初回リリースのため該当なし）

Fixed
- トランザクション処理の堅牢化
  - market_regime / ai_scores 書き込みで BEGIN → DELETE → INSERT → COMMIT のパターンを採用。例外時には ROLLBACK を行い、ROLLBACK 失敗時は警告ログを出すようにした。

- DuckDB 互換性の考慮
  - executemany に空リストを渡さない保護（DuckDB 0.10 の制約回避）を追加。

Security
- 環境変数の扱いに注意
  - OS 環境変数は .env の自動上書きから保護（protected set）。
  - OpenAI API キー未設定時は明確な ValueError を投げて早期検出。

Notes / Implementation choices
- ルックアヘッドバイアス対策
  - 全てのバッチ / スコアリング関数は内部で date.today()/datetime.today() を直接参照しない（必ず target_date を引数で与える）。
  - DB クエリは target_date 未満 / 以前 など適切に排他・包含を制御。

- OpenAI（LLM）呼び出し
  - gpt-4o-mini を想定、JSON Mode を利用して厳密な JSON 出力を期待するが、現実的な揺らぎ（前後テキスト等）へはパース救済処理を実装。
  - ネットワーク/レート/サーバエラーに対してはリトライ（指数バックオフ）、それ以外は安全にスキップする方針。

- ロギング
  - 重要処理（スコア算出、ETL、カレンダー更新等）には情報・警告・例外ログを挿入し運用時のトラブルシュートを支援。

Removed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Acknowledgements
- 本バージョンは DuckDB を主要な分析 DB とし、OpenAI（gpt-4o-mini）による NLP を組み合わせた研究・運用向けの日本株自動売買支援基盤の初期実装です。今後、テストカバレッジ・エラーハンドリング・メトリクス出力の強化、外部 API クライアント抽象化等を予定しています。