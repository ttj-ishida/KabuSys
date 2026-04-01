CHANGELOG
=========

すべての重要な変更は Keep a Changelog の指針に従って記載しています。
リリース日付はコードベースの現状から推測して設定しています。

Unreleased
----------
（なし）

0.1.0 - 2026-04-01
------------------

Added
- パッケージ初期リリース: kabusys (version 0.1.0)
  - パッケージ公開情報: src/kabusys/__init__.py に __version__ = "0.1.0" を追加。
  - 主要サブパッケージを公開: data, research, ai, 等を __all__ でエクスポート。

- 環境設定 / 設定管理
  - .env 自動読み込み実装（プロジェクトルート判定: .git または pyproject.toml を基準）。.env と .env.local を読み込み、OS 環境変数を保護する仕組みを実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト時等で使用可能）。
  - .env パーサーの強化:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォートおよびバックスラッシュエスケープを考慮した値読み取り。
    - インラインコメントの取り扱い（クォートなしは '#' の前が空白/タブの場合のみコメント扱い）。
  - Settings クラスを追加（src/kabusys/config.py）:
    - J-Quants、kabuステーション、Slack、DB パス、監視しきい値、ログレベル、環境種別（development / paper_trading / live）などのプロパティを提供。
    - 必須環境変数未設定時は ValueError を送出する _require を実装。
    - 入力値検証: KABUSYS_ENV と LOG_LEVEL の有効値チェック。

- AI（ニュース NLP / レジーム判定）
  - ニュースセンチメントスコアリングモジュール (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini, JSON Mode）でセンチメントを算出。
    - 時間ウィンドウ計算（JST 前日 15:00 ～ 当日 08:30。DB 比較は UTC naive datetime を使用）。
    - バッチ処理（1APIコールあたり最大 _BATCH_SIZE=20 銘柄）。
    - 1銘柄あたりの記事数上限・文字数上限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）でトークン肥大化対策。
    - エクスポネンシャルバックオフによるリトライ（429、ネットワーク断、タイムアウト、5xx を対象）。
    - レスポンスの厳密バリデーション（JSON 抽出、results リスト、code と score の検証、スコアは ±1.0 にクリップ）。
    - DB 書き込みは部分失敗に備え、該当コードのみ DELETE → INSERT で置換（DuckDB の executemany 空リスト制約への対応含む）。
    - API 呼び出し箇所は _call_openai_api として分離（テストで差し替え可能）。
    - API 失敗時はフェイルセーフで該当チャンクをスキップし、他銘柄処理を継続。
  - 市場レジーム判定モジュール (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull / neutral / bear）を判定。
    - MA 計算は target_date 未満のデータのみを使用し、ルックアヘッドバイアスを排除。
    - マクロニュースは news_nlp のウィンドウ計算を利用し、キーワードでフィルタした記事タイトルを LLM に渡して JSON レスポンスを期待。
    - OpenAI 呼び出しは専用関数経由で行い、リトライ / バックオフ / 5xx ハンドリングを備える。
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実装。API 失敗時は macro_sentiment = 0.0 にフォールバックし続行。
    - レジームスコアのクリップ、閾値に基づくラベル付与を実装。

- Data（ETL / カレンダー）
  - マーケットカレンダー管理モジュール (src/kabusys/data/calendar_management.py)
    - market_calendar を基にした営業日判定 API を提供:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を実装。
    - DB データがない/未登録日については曜日ベース（土日除外）でフォールバックする一貫した挙動。
    - calendar_update_job: J-Quants API からカレンダーを差分取得し冪等に保存。バックフィルと健全性チェックを実装（未来日付の異常検出）。
  - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスを追加（取得数、保存数、品質問題、エラーの集約）。
    - 差分更新ロジック、バックフィル、品質チェック（quality モジュール連携）に基づいた処理方針を実装する設計。
    - jquants_client を利用した idempotent 保存（ON CONFLICT DO UPDATE）を想定。
    - DuckDB 互換性に配慮したテーブル存在チェック、最大日付取得ユーティリティ等を実装。
    - ETLResult を data.etl で再エクスポート。

- Research（ファクター計算 / 特徴量解析）
  - ファクター計算モジュール (src/kabusys/research/factor_research.py)
    - Momentum: mom_1m / mom_3m / mom_6m、ma200_dev（200 日 MA 乖離）。データ不足時は None を返す。
    - Volatility / Liquidity: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比（volume_ratio）。
    - Value: PER（close / EPS、EPS が 0/欠損なら None）、ROE（raw_financials から最新値を取得）。
    - DuckDB 内部 SQL とウィンドウ関数を活用した高効率実装。出力は (date, code) キーを持つ dict のリスト。
  - 特徴量探索モジュール (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算: calc_forward_returns（デフォルト horizons = [1,5,21]）。horizons 検証、単一クエリでの効率的取得。
    - IC（Information Coefficient）計算: calc_ic（Spearman ランク相関に基づく）。
    - ランク変換ユーティリティ: rank（同順位は平均ランク、丸めにより ties の誤判定を防止）。
    - 統計サマリー: factor_summary（count/mean/std/min/max/median）。
  - research パッケージの __init__ で代表的関数をエクスポート（calc_momentum, calc_value, calc_volatility, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

Changed
- 設計方針・安全策を明示的に導入
  - ルックアヘッドバイアス対策: すべてのスコアリング/算出関数は date 引数を受け取り、datetime.today()/date.today() を直接参照しない設計。
  - OpenAI 呼び出し周りは JSON mode を前提とし、レスポンスパース失敗や API エラー時にフェイルセーフで継続する方針。
  - DuckDB のバージョン差異（executemany の空リスト制約、配列バインドの不安定さ）への互換性対策を導入。

Fixed
- DB トランザクションの安全化:
  - INSERT 前に該当レコードを DELETE しておく冪等処理（calendar, ai_scores, market_regime 等）。
  - 例外発生時は ROLLBACK を試み、ROLLBACK 自体の失敗も WARN ログ出力して上位に例外を伝播。
- OpenAI API のエラー分類とハンドリング強化:
  - RateLimitError / 接続エラー / タイムアウト / 5xx をリトライ対象にし、非5xx は即座にスキップ。
  - APIError の status_code 存在に安全に対応（getattr を使用）。

Security
- （該当なし）

Removed
- （該当なし）

アップグレード・移行メモ
- 環境変数:
  - 自動 .env 読み込みはデフォルトで有効。CI / テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - 必須の環境変数（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）は未設定時に ValueError が発生します。
- DuckDB:
  - executemany に空リストを渡すと失敗するバージョン対策を入れています。ETL 実行時に空パラメータケースがある処理は既にチェック済みです。

既知の制約・注意点
- OpenAI 呼び出しは実装上 gpt-4o-mini を前提に JSON Mode を使用します。将来的なモデル/SDK 変更に対しては response_format 周りを見直す必要があります。
- news_nlp と regime_detector は意図的に内部の _call_openai_api を共有せずモジュール結合を低く保っています。ユニットテストでモック差し替えが可能です。
- ETL / Data モジュールは DuckDB を前提としています。別DB を使う場合は互換性確認が必要です。

お問い合わせ
- バグ報告・提案はリポジトリの Issue にて受け付けてください。