CHANGELOG
=========

すべての重要な変更履歴をここに記録します。  
フォーマットは "Keep a Changelog" に準拠します。  

注: 以下の変更内容はリポジトリ内のソースコードから推測して記載しています。

Unreleased
----------

- 予定・検討中:
  - monitoring モジュールの実装追加（__all__ に含まれているため将来的に公開機能を追加予定）
  - AI モデル設定やバッチサイズ等のチューニング項目のパラメータ化（現状は定数）
  - テスト・CI 向けのモック用ヘルパーや型注釈の強化
  - DuckDB のバージョン差分に対する互換性テストとドキュメント整備

0.1.0 - 2026-03-28
------------------

Added
- パッケージ初期リリースを公開
  - パッケージメタ情報:
    - src/kabusys/__init__.py にて __version__ = "0.1.0"、公開サブパッケージを __all__ で定義（data, strategy, execution, monitoring）。
- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダを実装。
  - プロジェクトルート検出: .git または pyproject.toml を基準にルートを自動検索（CWD に依存しない実装）。
  - .env パーサ実装: コメント、export 形式、クォート内のエスケープ処理、行内コメントの扱い等に対応。
  - 自動ロードの制御: KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。
  - 保護された既存 OS 環境変数を上書きしない仕組み（.env の上書き可否と protected set）。
  - Settings クラスを提供し、必要な環境変数をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等を必須として検証。
    - DB パス（DUCKDB_PATH, SQLITE_PATH）のデフォルト設定と Path 型変換。
    - KABUSYS_ENV と LOG_LEVEL の検証（許容値チェック）と便利プロパティ（is_live / is_paper / is_dev）。
- AI モジュール (src/kabusys/ai)
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news / news_symbols を用いて銘柄ごとに記事を集約し、OpenAI (gpt-4o-mini) に JSON mode で送信してセンチメントを取得。
    - チャンク処理（_BATCH_SIZE=20）、記事・文字数トリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）を実装。
    - 再試行ロジック（429 / ネットワーク断 / タイムアウト / 5xx）を指数バックオフで実装。
    - レスポンスの厳密なバリデーションと数値クリップ（±1.0）。
    - DuckDB 用の安全な書き換え処理（部分成功時に既存データを保護するため DELETE→INSERT を個別実行）。
    - テストしやすさのため _call_openai_api を内部に定義し置換可能に設計。
    - calc_news_window により JST 基準のタイムウィンドウ計算を実装（UTC naive datetime で DB 比較）。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF(1321) の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を組み合わせて日次で 'bull' / 'neutral' / 'bear' を判定。
    - LLM（gpt-4o-mini）呼び出しは retry/バックオフを実装、API 失敗時は macro_sentiment=0.0 でフェイルセーフ。
    - MA200 計算は target_date 未満のデータのみを使用し、データ不足時は中立(1.0)を返す等ルックアヘッドバイアス対策を徹底。
    - 判定結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）で保存。
    - テスト用に _call_openai_api をモック可能にしている（news_nlp と意図的に独立実装）。
- データプラットフォーム (src/kabusys/data)
  - ETL パイプライン (src/kabusys/data/pipeline.py)
    - ETLResult dataclass を定義し ETL 実行結果、品質検査結果、エラー収集を一元管理。
    - 差分更新、バックフィル、品質チェック（quality モジュール参照）を行う設計を反映。
    - DuckDB のテーブル存在チェック、最大日付取得ユーティリティを実装。
  - ETL 再公開 (src/kabusys/data/etl.py)
    - pipeline.ETLResult をパッケージ外へ再エクスポート。
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar テーブルを基に営業日判定・次/前営業日取得・期間内営業日列挙などのユーティリティを実装。
    - DB データが無い/未登録日の場合は曜日ベース（週末除外）でフォールバックするポリシー。
    - calendar_update_job を実装し、J-Quants クライアント経由で差分取得→保存（バックフィル、健全性チェック付き）。
    - 最大探索日数やバックフィル期間等の安全パラメータを定義して無限ループや異常データ発生時の挙動を制御。
  - jquants_client と quality への連携を想定した設計（fetch/save 関数を利用）。
- リサーチ・ファクター (src/kabusys/research)
  - factor_research.py
    - Momentum（1M/3M/6M）、200 日 MA 乖離、Volatility（20 日 ATR）、Liquidity（20日平均売買代金・出来高比率）、Value（PER/ROE）などのファクター計算を実装。
    - DuckDB のウィンドウ関数を用いて効率的に集計し、データ不足時には None を返す堅牢な実装。
    - すべての関数は prices_daily / raw_financials のみ参照し、本番の発注等には接続しない安全設計。
  - feature_exploration.py
    - 将来リターン calc_forward_returns（可変ホライズン対応、入力検証あり）。
    - ランク相関による IC（calc_ic）計算（Spearman 相関をランクに変換して算出）。
    - rank ユーティリティ（同順位を平均ランクとする実装、浮動小数誤差に備え丸め処理あり）。
    - factor_summary で基本統計量（count/mean/std/min/max/median）を計算。

Changed
- 設計方針を明記:
  - 全ての分析・研究関数は datetime.today()/date.today() を直接参照せず、呼び出し元が target_date を渡す設計（ルックアヘッドバイアス防止）。
  - 外部 API 呼び出し失敗時は例外で処理を止めず、フォールバック（スコア=0.0 など）や部分成功を許容するフェイルセーフ設計を採用。
  - DuckDB の executemany に関する互換性問題（空リスト不可）に対するワークアラウンドを実装。
  - OpenAI 呼び出しに対しては JSON mode を利用し厳密な出力を期待しつつ、パース失敗時の復元ロジック（最外側の {} を抽出）を実装。

Fixed
- 複数の堅牢性改良（コード中のログに記載・実装済み）:
  - .env 読み取り失敗時に警告を出して処理続行（IOError/ OSError を捕捉）。
  - OpenAI API 呼び出しにおける様々な例外（RateLimit, Connection, Timeout, 5xx）を扱い、リトライ/フォールバックを明示。
  - DB 書き込み失敗時は ROLLBACK を試行し、ROLLBACK 失敗時に警告ログを出力。
  - 入力検証の強化（KABUSYS_ENV / LOG_LEVEL / horizons 引数 等の不正値チェック）。

Security
- 環境変数の扱い:
  - OS 環境変数を上書きしないデフォルト動作と、.env.local による上書きを許可する設計。
  - 必須シークレット（OpenAI, Slack, Kabu パスワード 等）を明示し、未設定時は ValueError を発生させることで安全に停止。

Notes
- テスト性:
  - OpenAI 呼び出し部分はモジュール内部で抽象化（_call_openai_api）してあり、unittest.mock.patch による差し替えが容易。
  - API キーは関数引数で注入可能（api_key）であり、環境変数依存を緩めている。
- DuckDB 前提:
  - 各モジュールは DuckDB 接続（duckdb.DuckDBPyConnection）を受け取り、SQL と純粋な Python で処理を行う想定。
  - DuckDB の日付型や executemany の仕様差分に配慮した実装あり。

今後の改善案（候補）
- monitoring サブパッケージの実装（__all__ にあるが未実装のため追加予定）。
- AI モデル・プロンプトの A/B テスト用フラグや設定ファイル化。
- 性能計測と大規模データでの最適化（DuckDB クエリのインデックス/分割等）。
- エンドツーエンドの統合テスト、CI ワークフロー、ドキュメント補強。

--- 

（この CHANGELOG はリポジトリ内ソースからの推測に基づく要約です。実際のコミット履歴やリリースログがある場合はそちらを優先してください。）