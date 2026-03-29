# Changelog

すべての注目すべき変更はここに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。セマンティックバージョニングを採用します。

フォーマット:
- Added: 新機能
- Changed: 変更
- Deprecated: 廃止予定
- Removed: 削除
- Fixed: 修正
- Security: セキュリティ関連

Unreleased
----------
（なし）

[0.1.0] - 2026-03-29
--------------------
初回リリース。以下の主要機能を実装・公開。

Added
- パッケージ基盤
  - src/kabusys/__init__.py にてパッケージメタ情報と公開モジュールを定義（version=0.1.0, data/strategy/execution/monitoring を公開）。
- 設定・環境変数管理（src/kabusys/config.py）
  - .env/.env.local ファイルと OS 環境変数からの自動読み込み機能を実装（プロジェクトルートは .git / pyproject.toml を起点に探索）。
  - 読み込み優先度: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート。
  - .env パース器（export 形式、クォート内エスケープ、行内コメント処理等）を実装。
  - Settings クラスを提供し、必要な設定値（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等）をプロパティ経由で取得。値検証（KABUSYS_ENV, LOG_LEVEL 等）を実装。
  - duckdb/sqlite のデフォルトパス設定（DUCKDB_PATH/SQLITE_PATH）をサポート。
- AI（自然言語処理）機能（src/kabusys/ai/）
  - news_nlp モジュール（src/kabusys/ai/news_nlp.py）
    - raw_news／news_symbols を用いて銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）の JSON モードでセンチメントスコアを付与して ai_scores テーブルに書き込む処理を実装。
    - タイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST）とバッチ処理（最大20銘柄/チャンク）を実装。
    - トークン肥大化対策（記事数上限・文字数トリム）実装。
    - エラー時の再試行（429 / ネットワーク / タイムアウト / 5xx）を指数バックオフで処理。レスポンスバリデーション（JSON整形、resultsフィールド、スコア検査）を実装。
    - DuckDB への冪等書き込み（DELETE→INSERT、トランザクション）を実装し、部分失敗時に既存データを保護する設計。
    - テストしやすさのため OpenAI 呼び出し箇所を差し替え可能（内部 _call_openai_api をモック可）。
  - regime_detector モジュール（src/kabusys/ai/regime_detector.py）
    - ETF 1321（Nikkei225 連動型）200日移動平均乖離（重み70%）とニュース由来のマクロセンチメント（重み30%）を合成し、日次で市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ書き込む処理を実装。
    - prices_daily からの MA200 乖離計算、raw_news によるマクロキーワード抽出、OpenAI によるマクロセンチメントスコア算出（JSON返却期待）、スコア合成、冪等DB書き込みを実装。
    - API 失敗時は macro_sentiment を 0.0 にフォールバックするフェイルセーフを提供。
    - モジュール内での OpenAI 呼び出しは news_nlp と独立実装（モジュール結合を避ける）。
- 研究（Research）機能（src/kabusys/research/）
  - factor_research.py
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR、相対ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER, ROE）を prices_daily / raw_financials を使って計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の None 処理や営業日ベースでのウィンドウ取り扱い、DuckDB を活用した SQL ベース実装。
  - feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（スピアマンランク相関: calc_ic）、ランク変換ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - Pandas 等に依存せず標準ライブラリでの実装。
  - research パッケージの __init__.py で主要 API を再公開。
- データプラットフォーム（src/kabusys/data/）
  - calendar_management.py
    - market_calendar を用いた営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。DB がない場合は曜日（週末）ベースのフォールバックを提供。
    - JPX カレンダー夜間バッチ更新ジョブ（calendar_update_job）を実装し、J-Quants クライアント経由で差分取得→保存（冪等）を行う。バックフィル、健全性チェックを備える。
  - pipeline.py / ETLResult（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETL の統一インターフェースと結果を表す ETLResult dataclass を実装。差分取得・保存・品質チェックの枠組みを想定。
  - jquants_client 経由のデータ取得・保存連携を想定した設計（fetch/save 系は jquants_client に委譲）。
- その他
  - テスト容易性の導入点（各所で内部 API 呼び出し箇所をモック可能に設計）。
  - DuckDB を主要なローカル分析用 DB として採用し、SQL+Python のハイブリッド実装で高パフォーマンスを志向。
  - ロギング出力（logger）を各モジュールに実装し、状況通知やフェイルセーフを明示。

Changed
- （初回リリースのため変更履歴なし）

Fixed
- （初回リリースのため修正履歴なし）

Deprecated
- （初回リリースのためなし）

Removed
- （初回リリースのためなし）

Security
- 環境変数読み込み時に OS 環境変数を保護する仕組み（protected set）を導入。override=False の場合は既存の OS 環境変数を上書きしない。
- .env ファイル読み込み失敗時は警告を出して処理継続（明示的に例外は投げない）。

Notes / 設計上の注意点
- ルックアヘッドバイアス回避:
  - 多くの関数（news のウィンドウ計算、regime/ai scoring、research の計算など）は datetime.today()/date.today() を内部参照しない設計（呼び出し側が target_date を渡す）。
- DuckDB の互換性:
  - executemany に空リストを渡すと失敗するバージョンや list 型バインドの挙動に依存する箇所で防護策を講じている（空チェック）。
- OpenAI 呼び出し:
  - JSON Mode を期待したレスポンス処理を行うが、余計な前後テキスト混入に対する復元ロジックも実装。
  - リトライ/バックオフ戦略や 5xx に対する扱いを明確化。
- テスト痕跡:
  - _call_openai_api 等を patch してユニットテストで差し替え可能。
- 既知の未実装/制約:
  - Strategy/Execution/Monitoring パッケージの詳細な実装は本リリース範囲外（公開はパッケージ初期エクスポートに留める）。
  - PBR・配当利回り等のバリューファクターは未実装。
  - jquants_client の具体的実装は外部依存（このコードベースは連携設計を含むが、API クライアント本体は別モジュールを想定）。

開発者向け補足
- 環境変数の自動読み込みはパッケージ import 時に走るため、テスト時には KABUSYS_DISABLE_AUTO_ENV_LOAD を設定するか、環境変数を制御してください。
- OpenAI の API キーは関数呼び出し引数で注入可能（api_key 引数）で、None の場合は環境変数 OPENAI_API_KEY を参照します。
- トランザクション処理は BEGIN/DELETE/INSERT/COMMIT のスタイルで冪等化しているため、部分失敗時は ROLLBACK 後に例外を上位に伝搬します。

---

今後のリリース案（例）
- 0.2.0: Strategy と Execution の初実装、実際の発注ロジック・監視（monitoring）機能の追加。
- 0.1.x: バグ修正、OpenAI レスポンスのバリデーション強化、jquants_client 連携テスト追加。