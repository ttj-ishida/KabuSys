CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティック バージョニングを採用します。

[Unreleased]
------------

（現在のリポジトリはバージョン 0.1.0 が最初の公開リリースとして含まれます。以降の変更はここに記載します。）

0.1.0 - 2026-04-02
------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージトップ:
    - package version を src/kabusys/__init__.py にて定義（__version__ = "0.1.0"）。
    - 公開モジュール一覧を __all__ で定義（data, strategy, execution, monitoring）。
- 設定 / 環境変数管理 (src/kabusys/config.py)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git / pyproject.toml を起点に探索）。
  - .env パーサは以下に対応:
    - コメント行、export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、
    - インラインコメント（クォート外で直前が空白/タブの場合のみ）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。既存 OS 環境変数は保護（上書き除外）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを公開（settings）:
    - J-Quants / kabuステーション / Slack / DB / 監視 / システム関連のプロパティを提供。
    - 必須 env チェック（_require）や値検証（KABUSYS_ENV, LOG_LEVEL）の実装。
    - デフォルト値（例: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH 等）。
- ニュース NLP（AI） (src/kabusys/ai/news_nlp.py)
  - raw_news と news_symbols を用い銘柄別に記事を集約し OpenAI（gpt-4o-mini）でセンチメント評価。
  - 主な機能:
    - タイムウィンドウ（JST 前日 15:00 〜 当日 08:30）計算（calc_news_window）。
    - 1 銘柄あたり最大記事数・文字数制限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - 銘柄単位を最大 _BATCH_SIZE（20）でチャンク化してバッチ API 呼び出し。
    - OpenAI JSON Mode を使用し、レスポンスバリデーション（results リスト・code/score 等）を実装。
    - スコア ±1.0 にクリップして ai_scores テーブルへ冪等書き込み（DELETE→INSERT のトランザクション）。
    - ネットワーク/429/5xx/タイムアウトは指数バックオフでリトライ。失敗時は該当チャンクをスキップして継続（フェイルセーフ）。
    - テスト容易性: API 呼び出しは _call_openai_api を patch して差し替え可能。
- 市場レジーム判定（AI） (src/kabusys/ai/regime_detector.py)
  - ETF 1321（日経225 連動 ETF）の 200 日移動平均乖離（重み 70%）とマクロニュース由来の LLM センチメント（重み 30%）を合成して daily レジーム判定（bull/neutral/bear）。
  - 主な機能:
    - ma200_ratio 計算（target_date 未満のデータのみ使用、データ不足時は中立 1.0 を採用）。
    - マクロキーワードで raw_news をフィルタしてタイトルを取得（最大 20 記事）。
    - OpenAI（gpt-4o-mini）で JSON を返すようプロンプトを構成、結果から macro_sentiment を抽出。
    - API 呼び出しのリトライ・エラー時は macro_sentiment=0.0 にフォールバック（例外を上げない）。
    - 合成スコアをクリップしラベル化。market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時 ROLLBACK）。
    - API キーは引数で注入可能（api_key）で、未指定時は環境変数 OPENAI_API_KEY を参照。未設定なら ValueError。
- データ基盤 - カレンダー管理 (src/kabusys/data/calendar_management.py)
  - JPX カレンダーの夜間バッチ更新ジョブ（calendar_update_job）を実装:
    - market_calendar の最終取得日を確認し J-Quants API から差分取得、冪等保存（jq.fetch_market_calendar / jq.save_market_calendar を利用）。
    - バックフィル、先読み、健全性チェック（未来日差分が大きすぎる場合のスキップ）を実装。
  - 営業日関連ユーティリティを提供:
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days（DB 値優先、未登録は曜日ベースでフォールバック）。
    - 最大探索日数制限で無限ループを防止。
- データ基盤 - ETL パイプライン (src/kabusys/data/pipeline.py, etl.py)
  - ETLResult データクラスを公開（src/kabusys/data/etl.py 経由で再エクスポート）。
    - ETL 実行結果の構造化（取得数、保存数、品質問題、エラー等）と to_dict() を実装。
  - 差分取得・保存・品質チェックの設計に基づくユーティリティ実装（jq クライアント / quality モジュールと連携を前提）。
  - DB 存入時は冪等性を重視（ON CONFLICT/DELETE→INSERT パターン）し、DuckDB の executemany の仕様を考慮。
- リサーチ / ファクター計算 (src/kabusys/research/)
  - factor_research.py:
    - calc_momentum: mom_1m/3m/6m, ma200_dev（データ不足時は None）を prices_daily から計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務を取得して PER / ROE を計算（EPS が 0/欠損の際は None）。
    - 全関数は DuckDB と prices_daily / raw_financials のみ参照（副作用なし）。
  - feature_exploration.py:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを一括 SQL で計算。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算、3 件未満で None。
    - rank / factor_summary: ランク付け（同順位平均）と基本統計量（count/mean/std/min/max/median）を提供。
  - リサーチ API は外部の取引/発注 API にアクセスしない方針を明記。
- モジュール構成のエクスポート
  - ai パッケージに score_news / score_regime（score_regime は regime_detector 内、score_news は news_nlp）を用意。
  - research パッケージから主なリサーチ関数を集約して公開。

Changed
- 初期リリースのため当該バージョンでは「Changed」は無し。

Fixed
- 初期リリースのため当該バージョンでは「Fixed」は無し。

Security
- 初期リリースのため当該バージョンでは「Security」は無し。

Notes / 実装上の重要ポイント
- ルックアヘッドバイアス対策:
  - AI スコアリングやレジーム判定の全関数は内部で datetime.today()/date.today() を直接参照せず、外部から target_date を渡す設計。
  - DB クエリは target_date より前のデータのみ参照するよう配慮。
- フェイルセーフ設計:
  - OpenAI の API エラーやパースエラー時は例外を投げず安全値（macro_sentiment=0.0 やチャンクスキップ）で継続する箇所が多数存在。
  - DB 書き込みは明示的トランザクション（BEGIN/COMMIT/ROLLBACK）で保護。
- テスト容易性:
  - OpenAI 呼び出しを行う内部関数（各モジュールの _call_openai_api）や API キー注入により unittest.mock.patch / DI による差し替えを想定。
- 外部依存:
  - OpenAI SDK（OpenAI クライアント / gpt-4o-mini を想定）。
  - DuckDB（DuckDBPyConnection 型で DB 操作）。
  - jquants_client（データ取得 / 保存用クライアントを data.jquants_client として想定）。
- 環境変数（主なもの）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY
  - LOG_LEVEL, KABUSYS_ENV（development/paper_trading/live）、KABUSYS_DISABLE_AUTO_ENV_LOAD
  - DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, CPU/MEMORY/DISK 閾値

Upgrade / Migration notes
- 初回リリースのためマイグレーションは無し。今後 DB スキーマ変更がある場合は別セクションに記載します。
- OpenAI キーがない場合、score_news / score_regime は ValueError を送出するため、CI/実行環境での env 設定を忘れずに。

Authors
- 初期実装（コードベースに基づく推測ドキュメント生成）。

（以降のバージョンは本 CHANGELOG の [Unreleased] セクションに記載してください。）