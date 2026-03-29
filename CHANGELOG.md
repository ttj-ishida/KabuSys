# Changelog

すべての重要な変更点をこのファイルに記録します。
このプロジェクトでは "Keep a Changelog" の規約に従い、変更履歴を日本語で記載しています。

※ バージョン番号はパッケージ内定義（kabusys.__version__ = "0.1.0"）に基づきます。

[Unreleased]

[0.1.0] - 2026-03-29
--------------------

Added
- パッケージ初回リリース: kabusys v0.1.0
  - パッケージ公開モジュール:
    - kabusys.data, kabusys.research, kabusys.ai, kabusys.config などの基本モジュール群を追加。
  - バージョン情報: src/kabusys/__init__.py に __version__ = "0.1.0" を定義。

- 環境設定 / ロード機能（src/kabusys/config.py）
  - .env/.env.local ファイルおよび OS 環境変数から設定を自動読み込みするロジックを実装。
  - プロジェクトルートの自動検出（.git または pyproject.toml を起点）により、CWD に依存しない読み込みを実現。
  - .env パーサーにおける以下の対応:
    - コメント行・空行を無視
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォートなし行のインラインコメント扱いは直前が空白/タブのみ認識
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - Settings クラスを提供（J-Quants / kabuAPI / Slack / DB パス / 環境フラグ等）
  - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）
  - デフォルトの DB パス（DUCKDB_PATH, SQLITE_PATH）の設定

- ニュース NLP モジュール（src/kabusys/ai/news_nlp.py）
  - raw_news / news_symbols を集約して銘柄単位のニュースを作成し、OpenAI（gpt-4o-mini）の JSON Mode を用いてセンチメントスコア（-1.0〜1.0）を計算。
  - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window() で実装。
  - バッチ処理（最大 20 銘柄／リクエスト）、記事数・文字数トリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
  - API リトライ（429・ネットワーク断・タイムアウト・5xx）を指数バックオフで実装。失敗時はスキップして継続（フェイルセーフ）。
  - レスポンスの堅牢なバリデーション（JSON 抽出、results リスト/型チェック、未知コード無視、数値チェック、スコアの ±1 のクリップ）。
  - DuckDB への冪等的書き込み（DELETE → INSERT、空パラメータの回避対応）。
  - テスト用フック: _call_openai_api() をモック可能（unittest.mock.patch）。

- 市場レジーム判定モジュール（src/kabusys/ai/regime_detector.py）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
  - ma200_ratio 計算でルックアヘッドを防止（target_date 未満のデータのみ使用）。データ不足時は中立(1.0)にフォールバック。
  - マクロニュース抽出（キーワードリスト _MACRO_KEYWORDS、最大記事数制限）。
  - OpenAI 呼び出しに対する再試行とエラー分類（429/ネットワーク/タイムアウト/5xx をリトライ、それ以外はフォールバック）。
  - レスポンス JSON の安全なパースとフェイルセーフ（失敗時 macro_sentiment=0.0）。
  - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時に ROLLBACK）。

- 研究用ファクター & 特徴量モジュール（src/kabusys/research/）
  - factor_research.py:
    - calc_momentum(): 1M/3M/6M リターン、200 日 MA 乖離などを DuckDB で計算。
    - calc_volatility(): 20 日 ATR（真のレンジ）、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value(): raw_financials と prices_daily から PER/ROE を算出。
    - 設計方針により外部 API にはアクセスせず、prices_daily / raw_financials のみ参照。
  - feature_exploration.py:
    - calc_forward_returns(): 将来リターン（任意ホライズン）を一括取得する効率的クエリ。
    - calc_ic(): ファクター値と将来リターンのスピアマンランク相関（IC）を実装。レコード不足時は None を返却。
    - rank(): 同順位は平均ランクで処理（数値丸め調整あり）。
    - factor_summary(): count/mean/std/min/max/median を標準ライブラリのみで計算。
  - これらは研究環境向けで、本番発注等にはアクセスしない設計。

- データプラットフォーム関連（src/kabusys/data/）
  - calendar_management.py:
    - JPX カレンダー管理（market_calendar テーブル）と営業日判定ユーティリティを実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB にカレンダーがない場合は曜日（平日）ベースのフォールバック。
    - 夜間バッチ更新 job (calendar_update_job) を実装（J-Quants から差分取得、バックフィル、健全性チェック）。
    - 最大探索範囲制限、NULL 値時の警告ログなど堅牢性を考慮。
  - pipeline.py:
    - ETL パイプラインの骨子（差分取得・保存・品質チェックフロー）を実装。
    - ETLResult データクラス（target_date、取得/保存件数、品質問題、エラー一覧、ヘルパーメソッド）を追加。
    - _get_max_date/_table_exists 等の内部ユーティリティを提供。
  - etl.py:
    - pipeline.ETLResult を再エクスポート。

Changed
- 初回リリースのため「変更」は該当なし。

Fixed
- 初回リリースのため「修正」は該当なし。

Security
- 初回リリースのため「セキュリティ修正」は該当なし。

Notes / 補足
- ルックアヘッドバイアス対策:
  - いずれのスコア計算 / ウィンドウ算出でも datetime.today() / date.today() の直接参照を避け、関数引数の target_date を基準に処理する設計。
- OpenAI 呼び出し:
  - news_nlp/regime_detector ともに独立した _call_openai_api 実装を持ち、モジュール間でプライベート関数を共有しない（モジュール結合を低減）。
  - テスト容易性のためモック差替えを想定。
- DuckDB 互換性:
  - executemany の空リスト回避等、DuckDB のバージョン差を考慮した実装上の配慮が多数ある。
- 環境設定の上書き挙動:
  - .env と .env.local の読み込み順序（OS 環境変数 > .env.local > .env）、.env.local は上書き（override=True）。
  - protected 引数により起動時の OS 環境変数は保護される。

今後の予定（例）
- 監視・実行モジュール（execution, monitoring）や、jquants_client の詳細実装・テストの充実。
- スコア集計のパフォーマンス改善や追加ファクターの実装。

[0.1.0]: v0.1.0

-----------------------------------------------------------------------------
（注）本 CHANGELOG は提供されたコードベースの内容から推測して作成しています。実際のリリースノートや運用ポリシーに合わせて適宜修正してください。