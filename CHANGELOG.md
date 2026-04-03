CHANGELOG
=========

このファイルは Keep a Changelog の形式に準拠して作成しています。  
フォーマット:
- Unreleased: 今後の変更
- 各バージョン: 追加 (Added) / 変更 (Changed) / 修正 (Fixed) / 破壊的変更 (Removed) など

Unreleased
----------

（現時点での未リリースの変更はありません）

0.1.0 - 2026-04-03
------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージ公開情報:
    - src/kabusys/__init__.py にて __version__ = "0.1.0"、サブパッケージを __all__ で公開（data, strategy, execution, monitoring）。

- 環境設定 / ロード
  - src/kabusys/config.py
    - .env / .env.local をプロジェクトルートから自動読み込みする仕組みを追加（.git または pyproject.toml を基準にプロジェクトルートを探索）。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env の行パーサ実装: コメント行、export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いに対応。
    - protected（OS 環境変数）を考慮した上書きロジック（.env.local は上書き、.env は既存未設定のみ設定）。
    - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB / 監視 / システム関連の設定をプロパティとして取得。必須キー未設定時は ValueError を送出。
    - KABUSYS_ENV, LOG_LEVEL 等の値検証ロジックを追加（正当な値でない場合は ValueError）。

- データプラットフォーム（DuckDB ベース）
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理 API（market_calendar）および営業日判定ユーティリティを実装:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
      - DB にデータがある場合は DB 値優先、未登録日は曜日ベースでフォールバック。
      - 検索範囲上限（_MAX_SEARCH_DAYS）や健全性チェックを実装。
    - calendar_update_job による夜間バッチ更新（J-Quants クライアント経由の差分取得、バックフィルロジック、保存の安全処理）を実装。
  - src/kabusys/data/pipeline.py / etl.py
    - ETL パイプラインの基盤を実装（差分取得、idempotent 保存、品質チェックフローの設計方針を反映）。
    - ETLResult データクラスを公開（src/kabusys/data/etl.py から再エクスポート）。ETL 実行結果および品質問題・エラーの集約をサポート。
    - DuckDB のテーブル存在確認や最大日付取得などのユーティリティ実装。
    - デフォルトのバックフィル日数、カレンダー先読み等の定数を定義。

- AI / ニュース NLP とレジーム検出
  - src/kabusys/ai/news_nlp.py
    - raw_news / news_symbols を読み、OpenAI（gpt-4o-mini, JSON mode）により銘柄別センチメント（ai_score）を算出して ai_scores テーブルへ書き込む処理を実装。
    - 処理の主な特徴:
      - JST ベースのニュース収集ウィンドウ計算（前日15:00〜当日08:30）とその UTC 対応（calc_news_window）。
      - 1 銘柄あたりの記事数・文字数のトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
      - 1 回の API 呼び出しで最大 20 銘柄をバッチ処理（_BATCH_SIZE）。
      - JSON レスポンスのバリデーション（results 配列の検証、未知コード無視、数値チェック、±1.0 にクリップ）。
      - RateLimit / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフによるリトライ。失敗時は個別チャンクをスキップして他チャンクに影響を与えないフェイルセーフ設計。
      - DuckDB executemany の空パラメータ回避（空リスト時の処理ガード）。
      - テスト容易性のため _call_openai_api の差し替え可能（unittest.mock.patch を想定）。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225 連動 ETF）の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次市場レジーム（bull / neutral / bear）を判定し market_regime テーブルへ冪等書き込みする実装。
    - 処理の主な特徴:
      - ma200_ratio の計算（ルックアヘッドバイアス回避: target_date 未満のデータのみ使用、データ不足時は中立扱い）。
      - マクロキーワードによる raw_news フィルタリングと上限記事数取得。
      - OpenAI を用いたマクロセンチメント評価（JSON mode, gpt-4o-mini）、API エラー時は macro_sentiment=0.0 にフォールバック。
      - リトライ / バックオフ、API エラーの種類に応じたロジック（5xx はリトライ、その他は即フォールバック）。
      - レジームスコアの合成・クリップ・閾値に基づくラベル付け。
      - DB 操作は BEGIN / DELETE / INSERT / COMMIT の形で冪等に実行し、例外時は ROLLBACK を試行して上位に伝播。

- リサーチ / ファクター計算
  - src/kabusys/research/factor_research.py
    - モメンタム、ボラティリティ（ATR 等）、バリュー（PER, ROE）等の定量ファクター計算を実装。
    - 特徴:
      - DuckDB 上の SQL ウィンドウ関数を活用して高速に計算。
      - 200 日移動平均や ATR のデータ不足時の扱い（None を返す、警告ロジックなど）。
      - 結果は (date, code) をキーとする dict のリストとして返す設計。
      - 研究環境向けに本番の発注系処理とは無関係で外部 API 非依存。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランキングユーティリティ（rank）、統計サマリー（factor_summary）を実装。
    - 特徴:
      - horizons の入力検証（正の整数、最大 252）。
      - Spearman 相当のランク相関を自前実装して外部依存を排除。
      - 統計量（count/mean/std/min/max/median）を標準ライブラリのみで算出。
  - src/kabusys/research/__init__.py で主要関数を再エクスポート。

- テスト / 安全性・設計上の注意点（実装内コメント）
  - ルックアヘッドバイアス防止: 各モジュール（news_nlp, regime_detector, research）で date.today()/datetime.today() を直接参照しない設計（target_date を引数で受ける）。
  - API キー注入: OpenAI API キーは引数で注入可能。未設定時は環境変数 OPENAI_API_KEY を参照し、未設定なら ValueError を送出。
  - DB 書き込みは冪等化（DELETE→INSERT、ON CONFLICT 想定など）とトランザクションで安全に実行。ロールバックの失敗は警告ログで通知。
  - エラーハンドリング: API 失敗時は例外を上位にそのまま投げるのではなく、可能な限りフェイルセーフ（スコア 0.0 / スキップ）で継続する設計（ただし DB 書き込み失敗など致命的なものは例外伝播）。
  - OpenAI 呼び出し関数はモジュール間でプライベート関数を共有しない（結合度を下げ、テストで差し替えやすく）。

Changed
- 初期リリース: 新規追加のため該当なし。

Fixed
- 初期リリース: 修正点なし。

Removed
- 初期リリース: 削除点なし。

Security
- OpenAI API キーの取り扱い:
  - キーは引数または環境変数からのみ取得。未設定の場合は明示的なエラーで通知。
  - .env ロードでは OS 環境変数を protected として保持する挙動を採用し、意図しない上書きを防止。

注記 / 将来の改善案（実装コメントに記載）
- DuckDB のバージョン差分（list 型パラメータバインドの挙動等）に注意し、executemany 周りの空配列扱いなど互換性ガードを入れている。
- OpenAI レスポンスの扱いは厳格に JSON を期待するが、実運用では LLM の不整合に備えた復元ロジック（最外側の {} 抽出など）を実装済み。
- ETL パイプラインや calendar_update_job は J-Quants クライアント側の実装（jquants_client）に依存するため、API 変更時はそこに合わせた更新が必要。

-----