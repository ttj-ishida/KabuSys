CHANGELOG
=========
すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" 準拠です。  

注意: このリポジトリの初期リリースはパッケージ内の __version__ に従い v0.1.0 として記載しています。

[Unreleased]
-------------

v0.1.0 - 2026-03-31
-------------------

Added
- 初回公開: KabuSys 日本株自動売買システムのコアライブラリ群を追加。
  - パッケージ公開情報
    - src/kabusys/__init__.py にてバージョンと主要サブパッケージ（data, strategy, execution, monitoring）を公開。
  - 設定・環境変数管理
    - src/kabusys/config.py
      - .env / .env.local ファイルの自動ロード機能（プロジェクトルートを .git または pyproject.toml から探索）。
      - export KEY=val 形式、クォートやエスケープ、インラインコメント等に対応した .env パーサ実装。
      - OS 環境変数を保護する protected オプション、override ロジック実装。
      - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
      - 必須設定取得ヘルパー _require、設定ラッパークラス Settings を提供（J-Quants、kabu API、Slack、DBパス、環境種別、ログレベル等）。
      - デフォルトの DB パス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"。
  - AI（NLP）モジュール
    - src/kabusys/ai/news_nlp.py
      - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI (gpt-4o-mini, JSON mode) を用いて銘柄単位のセンチメント（ai_score）を算出。
      - API 呼び出しはチャンク単位（デフォルト20銘柄）でバッチ処理し、1銘柄当たり記事数・文字数上限／トリムを実装。
      - レスポンスの堅牢なバリデーション（JSON 抽出、results フォーマット、未知コード無視、数値チェック、スコア ±1.0 クリップ）。
      - リトライ（429/ネットワーク/タイムアウト/5xx）を指数バックオフで実装。失敗時はスキップして継続（フェイルセーフ）。
      - DuckDB への書き込みは冪等性を考慮（該当 code の DELETE → INSERT）。空パラメータの executemany 回避（DuckDB 互換性考慮）。
      - テスト容易性のため _call_openai_api を差し替え可能に実装（unittest.mock.patch を想定）。
    - src/kabusys/ai/regime_detector.py
      - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%、news_nlp の窓集計を利用）を合成して日次の市場レジーム（bull/neutral/bear）を算出。
      - OpenAI を用いたマクロセンチメント取得（gpt-4o-mini, JSON mode）、レスポンスパースとリトライ処理を備える。
      - レジーム結果を market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時は ROLLBACK を試行して例外を伝播。
      - API 未設定時の ValueError、API 失敗時は macro_sentiment = 0.0 にフォールバックするフェイルセーフ設計。
  - Data（ETL / カレンダー / クオリティ）
    - src/kabusys/data/pipeline.py
      - ETLResult dataclass を導入（ETL 実行の集約結果、品質問題リスト、エラー等を保持）。ETL 実行結果の to_dict を実装。
      - 差分更新、バックフィル日数、品質チェック連携の設計考慮をコメントで明記（J-Quants クライアント経由での取得想定）。
    - src/kabusys/data/etl.py
      - pipeline.ETLResult を再エクスポート。
    - src/kabusys/data/calendar_management.py
      - JPX マーケットカレンダー取得 / 営業日判定ロジックを実装。
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等のユーティリティを提供。
      - market_calendar テーブルがない場合は曜日ベースでフォールバック（週末休場扱い）。DB 登録値優先・未登録日は曜日フォールバックの一貫性を確保。
      - calendar_update_job による夜間バッチ（J-Quants から差分取得、バックフィル、健全性チェック、保存）を実装。API エラーはログ記録して 0 を返す安全設計。
    - src/kabusys/data/__init__.py にてサブモジュール公開の準備。
    - jquants_client（別モジュール参照）との連携箇所を想定した実装（fetch / save 関数呼び出し）。
  - Research（ファクター / 特徴量探索）
    - src/kabusys/research/factor_research.py
      - モメンタム（1M/3M/6M リターン・200日 MA 乖離）、ボラティリティ（20日 ATR 等）、バリュー（PER/ROE）等の計算関数を実装（calc_momentum, calc_volatility, calc_value）。
      - DuckDB を使った SQL ベースの集計を採用し、データ不足時に None を返す堅牢設計。
    - src/kabusys/research/feature_exploration.py
      - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク変換（rank）、ファクター統計サマリー（factor_summary）を実装。
      - pandas 等外部ライブラリに依存せず標準ライブラリで実装。
    - src/kabusys/research/__init__.py
      - 主要関数と data.stats.zscore_normalize を公開。
  - 共通・ユーティリティ
    - DuckDB を主要なローカル分析 DB として多用する設計（関数引数に DuckDB 接続を受け取る）。
    - ロギングを随所に追加し、警告・情報ログによる状態把握を重視。
    - ルックアヘッドバイアスを避けるため、各モジュールは date 引数を必須にし、datetime.today()/date.today() に依存しない設計方針を採用。
    - OpenAI API 使用に際しては API キーを引数で注入可能（テスト容易性）かつ環境変数 OPENAI_API_KEY からも解決。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- config の .env ロードで OS 環境変数を protected として保護（.env.local による上書きも OS 環境変数は上書きされない挙動）。
- OpenAI / Slack / Kabu API の機密情報は環境変数経由で取得する設計。必須変数未設定時は明確なエラーメッセージを投げる。

Known issues / Limitations
- OpenAI 呼び出しは gpt-4o-mini + JSON mode を前提とする。API 仕様変更に伴う調整が必要になる可能性がある。
- DuckDB バインドの互換性（executemany の空リスト不可など）を回避する実装を入れているが、将来の DuckDB バージョン差分で追加対応が必要になる場合がある。
- jquants_client や外部保存関数（fetch/save）の実装は本コードの外にあり、そこへの依存性が存在する。

補足
- テスト容易性に配慮して外部 API 呼び出し箇所は差し替え可能（モック）になるよう設計されています（例: kabusys.ai.news_nlp._call_openai_api の patch）。