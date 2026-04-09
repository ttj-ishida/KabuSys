CHANGELOG
=========

すべての注目すべき変更はここに記録します。本ファイルは "Keep a Changelog" の形式に準拠しています（日本語）。

フォーマット:
- 変更はセクション（Added, Changed, Fixed, Security など）に分類しています。
- 日付は YYYY-MM-DD 形式です。

Unreleased
----------
（現在の開発ブランチ向けの未リリース変更はここに記載してください）

[0.1.0] - 2026-04-09
-------------------

初回リリース。日本株自動売買システム "KabuSys" のコア機能を実装しました。主な追加内容は以下の通りです。

Added
- パッケージ初期化
  - src/kabusys/__init__.py にてパッケージ名とバージョンを定義（バージョン: 0.1.0）。
  - パブリック API: data, strategy, execution, monitoring を __all__ で公開。

- 環境設定管理
  - src/kabusys/config.py: 環境変数/.env ファイルの自動読み込み機能を実装。
    - 読み込み優先順: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト向け）。
    - .git または pyproject.toml を起点にプロジェクトルートを検出して .env を探索（CWD 非依存）。
    - .env パーサは export プレフィックス、クォート（シングル/ダブル）、エスケープ、インラインコメント等に対応。
    - 既存 OS 環境変数を保護するため protected キーを導入（.env の上書きを制御）。
  - Settings クラスを提供:
    - J-Quants / kabu / LINE / DB パス / Paper Trading の設定取得プロパティを実装。
    - PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等の値検証（有効値チェック）を実装。
    - 各種監視用パス・閾値（PID ファイル、kill フラグ、CPU/メモリ/ディスク閾値）を設定から取得。

- AI（自然言語処理）機能
  - src/kabusys/ai/news_nlp.py:
    - raw_news + news_symbols からニュースを集約し、OpenAI（gpt-4o-mini）で銘柄ごとにセンチメントスコアを算出。
    - バッチ処理（最大 20 銘柄/コール）、1 銘柄あたり記事数・文字数制限（トークン肥大対策）。
    - リトライ（429 / ネットワーク / タイムアウト / 5xx）を指数バックオフで実装。
    - JSON Mode の応答を厳密に検証し、パース失敗時は前後の余分なテキストから JSON 部分を抽出するフォールバック。
    - バリデーションで未知コードを無視し、スコアを ±1 にクリップ。
    - 成功したスコアのみ ai_scores テーブルに置換（DELETE → INSERT）し、部分失敗時に他コード既存スコアを保護。
    - calc_news_window により JST の前日 15:00 ～ 当日 08:30 のウィンドウを適切に UTC 変換して扱う。
  - src/kabusys/ai/regime_detector.py:
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）と、ニュース由来のマクロセンチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定。
    - OpenAI でマクロセンチメント算出（gpt-4o-mini、JSON 出力期待）、API リトライとフェイルセーフ（失敗時 macro_sentiment=0.0）。
    - DuckDB を用いて冪等的に market_regime テーブルへ書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - ルックアヘッドバイアス対策: date 未満のデータのみを参照、datetime.today() 等を直接参照しない。

- データ基盤（Data）
  - src/kabusys/data/calendar_management.py:
    - JPX カレンダー（market_calendar）を用いた営業日判定ユーティリティ群を実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録がない場合は曜日ベース（土日を休業日）でフォールバック。
    - calendar_update_job 実装: J-Quants から差分取得→保存、バックフィル/健全性チェックを実施。
  - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py:
    - ETL パイプラインの骨組みと ETLResult データクラスを実装（取得件数、保存件数、品質問題、エラーの収集）。
    - デフォルトの差分単位・バックフィル方針を定義（backfill_days=3 等）。
    - quality モジュールと連携して品質チェックを行う設計（重大度を集計可能）。
  - jquants_client との連携を想定（fetch/save 関数呼び出し、例外処理を含む）。

- リサーチ / ファクター計算
  - src/kabusys/research/factor_research.py:
    - モメンタム（1M/3M/6M）、200 日 MA 乖離、ATR（20 日）、流動性（20 日平均売買代金・出来高比）、Value（PER / ROE）等のファクターを DuckDB SQL で実装。
    - データ不足時の None 処理、ルックアヘッド回避、DuckDB の window 関数を利用した実装。
  - src/kabusys/research/feature_exploration.py:
    - 将来リターン計算（複数ホライズン、デフォルトは [1,5,21]）、IC（Spearman のランク相関）計算、rank（同順位は平均ランク）、factor_summary（count/mean/std/min/max/median）を実装。
    - pandas 等に依存せず標準ライブラリと DuckDB で実装。
  - src/kabusys/research/__init__.py による主要関数の公開。

- パッケージ公開
  - ai.__init__.py, research.__init__.py にて主要関数を再エクスポートしている（score_news 等）。

Changed
- （初回リリースのため過去変更なし）

Fixed
- （初回リリースのため過去修正なし）

Security
- 環境変数の必須チェックを実装（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等は _require による検証で不足時に ValueError を発生）。
- .env の自動ロード時に OS 環境変数を上書きしない保護機構を導入（protected set）。

Notes / Implementation details / 制約事項
- OpenAI API
  - news_nlp / regime_detector は OpenAI の Chat Completions 機能（gpt-4o-mini, JSON Mode 想定）を使用。API キーは引数 api_key で注入可能、引数が None の場合は環境変数 OPENAI_API_KEY を参照する。未設定時は ValueError を送出する。
  - テスト容易性のために _call_openai_api をモック可能（unittest.mock.patch を想定）。
  - API レスポンスの不確実性に備え、JSON パースや形式エラー時はスコアを無効化してフェイルセーフで継続する実装。
- DuckDB
  - 多くの処理は DuckDB 接続を前提としている（prices_daily / raw_news / news_symbols / raw_financials / ai_scores / market_regime / market_calendar 等のテーブルが必要）。
  - executemany に空リストを渡せない DuckDB の制約（特に 0.10 系）に配慮した分岐処理あり。
- ルックアヘッドバイアス対策
  - すべての日時関連処理は target_date を明示的に受け取り、datetime.today()/date.today() を直接参照しない設計思想を採用（ETL・スコアリングの再現性確保）。
- Paper Trading
  - PAPER_FILL_MODE の有効値は instant/partial/never/reject。無効値が設定された場合は ValueError を送出。
  - Paper Trading 用 SQLite パスは環境変数で上書き可能（PAPER_TRADING_SQLITE_PATH）。
- ロギングとトランザクション
  - DB 書き込みは冪等性を考慮した BEGIN / DELETE / INSERT / COMMIT のパターン、例外時は ROLLBACK を試行して警告ログを出力。

Known limitations / TODO
- strategy / execution / monitoring の詳細実装（パッケージトップで __all__ にあるが本リリースのコードスニペットでは詳細は未掲載）。
- ai_score と sentiment_score は現フェーズで同値として扱っているが、将来的に差別化を検討。
- 外部 API（J-Quants, Kabu API, OpenAI）に依存するため、環境ごとのセットアップ手順（.env.example 等）が必要。

Migration / Upgrade notes
- 既存のユーザーが本リリースに移行する際は以下を確認してください:
  - 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY など）を設定すること。
  - DuckDB スキーマ（prices_daily, raw_news, ai_scores, market_regime, market_calendar 等）が本実装の期待と一致していること。
  - 自動 .env ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください（テスト目的など）。

開発者向けメモ
- テストでは OpenAI 呼び出しを _call_openai_api を patch してスタブ化することを推奨。
- .env のパースは多くのケース（エスケープ、クォート、コメント）を扱うため、実運用での .env フォーマットに注意すること。

----------

フィードバックや誤りの報告、改善案は README や issue を通じてお願いします。