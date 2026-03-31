CHANGELOG
=========
すべての重要な変更をここに記載します。  
このファイルは Keep a Changelog のフォーマットに準拠しています。  

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Deprecated: 非推奨
- Removed: 削除
- Security: セキュリティ修正

0.1.0 - 2026-03-31
-----------------

Added
- パッケージ初版リリース (kabusys v0.1.0)
- パッケージ公開情報
  - パッケージ名 / モジュール初期化（src/kabusys/__init__.py）にバージョン "0.1.0" を定義。
  - パッケージの公開 API として data, strategy, execution, monitoring をエクスポート。

- 環境設定 / .env 自動読み込み（src/kabusys/config.py）
  - プロジェクトルートを .git または pyproject.toml を起点に検出し、.env / .env.local を自動読み込み。
  - export プレフィックス、クォートされた値、インラインコメントに対応した独自の .env パーサ実装。
  - 読み込み優先順: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化可能。
  - 必須環境変数取得ヘルパー _require と Settings クラスを提供。環境値の検証（KABUSYS_ENV, LOG_LEVEL 等）を実施。
  - データベースパス設定（DUCKDB_PATH, SQLITE_PATH）を Path 型で取得。

- AI（自然言語処理）関連（src/kabusys/ai）
  - ニュースセンチメントスコアリング（news_nlp.score_news）
    - raw_news / news_symbols / ai_scores を対象に、指定時間ウィンドウのニュースを銘柄ごとに集約して OpenAI（gpt-4o-mini）へ送信し、銘柄ごとのスコアを ai_scores テーブルへ書込む。
    - バッチ処理（最大20銘柄/回）、記事トリム（最大記事数・最大文字数）を実装。
    - JSON Mode レスポンスのバリデーション・パース処理と、前後ノイズを含む JSON 抽出のフォールバック。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフによるリトライを実装。致命的でない失敗はスキップして継続（フェイルセーフ）。
    - DuckDB への書き込みは冪等（DELETE → INSERT）で実施し、部分失敗時に既存データを過度に消さない設計。
    - タイムウィンドウは JST ベース（前日15:00〜当日08:30）で計算し、DB は UTC naive datetime で比較。

  - 市場レジーム判定（regime_detector.score_regime）
    - 日次で ETF 1321（Nikkei 225 連動型）について 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して市場レジーム（bull/neutral/bear）を判定。
    - prices_daily からの MA 計算、raw_news からマクロキーワードによるタイトル抽出、OpenAI 呼び出しによるマクロセンチメント算出を実装。
    - API 呼び出し失敗時は macro_sentiment = 0.0 にフォールバックし処理継続。
    - DuckDB への書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等に行い、例外時は ROLLBACK を試行。

  - 共通設計
    - OpenAI 呼び出しは JSON モードを用い、専用の _call_openai_api を各モジュールで定義（モジュール間での private 関数共有を避ける）。
    - API エラー処理、リトライ、ログ出力を丁寧に実装。

- データ（DataPlatform）関連（src/kabusys/data）
  - ETL パイプライン（pipeline.ETLResult / data.etl 再エクスポート）
    - ETL 実行結果を表す dataclass (ETLResult) を提供。取得件数、保存件数、品質チェック結果、エラー一覧などを格納。
    - DB 最終取得日取得ユーティリティ、テーブル存在チェック等を実装。

  - カレンダー管理（calendar_management）
    - market_calendar テーブルを参照して営業日判定（is_trading_day）、SQ判定（is_sq_day）、前後営業日取得（next_trading_day / prev_trading_day）、期間内営業日取得（get_trading_days）を提供。
    - DB にカレンダー情報がない場合は曜日ベース（土日除外）でフォールバック。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等に更新する夜間ジョブを実装。バックフィル・健全性チェックを内包。
    - 最大探索日数制限やバックフィルの実装により無限ループや過度の再取得を回避。

  - jquants_client と quality モジュールを利用する ETL ワークフロー設計に準拠（差分更新、idempotent 保存、品質チェックの収集）。

- リサーチ/ファクター計算（src/kabusys/research）
  - factor_research
    - Momentum（1M/3M/6M リターン、200日MA乖離）、Volatility（20日 ATR、相対 ATR、出来高比等）、Value（PER, ROE）を DuckDB 上の SQL と Python 組合せで計算。
    - データ不足時の None 処理、ログ出力、営業日・スキャン範囲のバッファ設計を実装。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算（Spearman ランク相関）、ランク付けユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等の外部依存を使わず標準ライブラリ + duckdb で完結する実装方針。

- 共通 / 実装上の注意点
  - ルックアヘッドバイアス対策: datetime.today() / date.today() を直接参照しない設計（関数呼び出し時に target_date を明示的に渡す）。
  - DuckDB を主要な永続層として利用（transactions / executemany の互換性考慮など）。
  - ロギングを各所で実装し、警告・情報を出力する。

Changed
- 初版のため該当なし。

Fixed
- 初版のため該当なし。

Deprecated
- 初版のため該当なし。

Removed
- 初版のため該当なし。

Security
- 初版のため該当なし。

注記 (Notes)
- OpenAI API の利用には OPENAI_API_KEY が必要。各 AI 関数は api_key 引数を受け取り、未指定時は環境変数を参照する。
- .env の自動読み込みはテスト時などに副作用を避けるため KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により抑止可能。
- DuckDB の executemany はバージョンごとの挙動差があるため、空パラメータの処理等で保護コードを追加している（互換性重視）。
- AI のレスポンスパース失敗や API エラーは基本的に例外を外に出さずフォールバック（0.0）やスキップを行う設計。運用上はログや監視で検出することを推奨。

今後の改善候補（コードから推測）
- テスト用のモック / DI を拡張して OpenAI クライアントや外部 API を差し替えやすくする。
- エラーメトリクスや監視（Sentry / Prometheus など）との統合強化。
- 処理パフォーマンス改善のための非同期化や並列処理の検討（AI バッチ呼び出しの最適化）。
- ai_scores / market_regime などのテーブルスキーマ・インデックス運用に関するドキュメント追加。