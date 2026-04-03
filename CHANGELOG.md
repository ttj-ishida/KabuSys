# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) のフォーマットに準拠します。  
このプロジェクトはセマンティックバージョニングを採用します。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-03

Added
- 基本パッケージ初期リリース (kabusys v0.1.0)
  - パッケージメタ情報: src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env / .env.local ファイルの自動読み込み機能を実装。
    - プロジェクトルート判定は .git または pyproject.toml を起点に探索するため、CWD に依存しない。
    - 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env の読み取りは UTF-8、`export KEY=val`、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いに対応。
    - OS 環境変数を保護するため保護セット(protected)をサポートし、上書き動作を制御。
  - Settings クラスを提供 (settings インスタンスを公開)：
    - J-Quants / kabustation / LINE / DB パス / 監視関連 (PID/kill flag/資源閾値) / システム設定（KABUSYS_ENV, LOG_LEVEL）等のプロパティを提供。
    - 必須環境変数取得用 _require() を実装し未設定時は ValueError を送出。
    - KABUSYS_ENV と LOG_LEVEL の値検証を実施（有効値を限定）。
    - Path 型プロパティは expanduser を適用。

- データプラットフォーム (src/kabusys/data/)
  - カレンダー管理モジュール (calendar_management.py)
    - market_calendar テーブルを用いた営業日判定ロジックを実装。
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供。
      - DB にデータがない／未登録日には曜日ベースのフォールバック（週末=休場）を一貫して使用。
      - 探索の最大範囲を設定し無限ループを防止（_MAX_SEARCH_DAYS）。
    - 夜間バッチ更新ジョブ calendar_update_job を実装。
      - J-Quants クライアント経由で差分取得→冪等保存（ON CONFLICT 相当処理）を行う。
      - バックフィル (_BACKFILL_DAYS)、先読み、健全性チェック（未来日数の異常検知）を実装。
  - ETL パイプライン基盤 (pipeline.py, etl.py)
    - ETLResult データクラスを公開（etl.py は pipeline.ETLResult を再エクスポート）。
    - 差分更新、バックフィル、品質チェック（quality モジュール呼出し）、idempotent 保存を想定した設計。
    - DuckDB に関するユーティリティ（テーブル存在確認、最大日付取得等）を実装。
    - エラー／品質問題は収集して上位での判断に委ねる（Fail-Fast ではない）。
    - DuckDB の executemany に関する空リスト制約を考慮した実装。

- 研究用分析モジュール (src/kabusys/research/)
  - factor_research.py
    - モメンタム（1M/3M/6M リターン、200日移動平均乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER、ROE）などのファクター計算関数を実装：
      - calc_momentum(conn, target_date)
      - calc_volatility(conn, target_date)
      - calc_value(conn, target_date)
    - SQL で DuckDB を直接問い合わせて計算を実行。外部 API にはアクセスしない設計（安全）。
    - データ不足時の扱い（必要数未満は None を返す）を明確に実装。
  - feature_exploration.py
    - 将来リターン計算: calc_forward_returns(conn, target_date, horizons)
      - 複数ホライズンを1クエリで取得、入力検証（horizons の範囲チェック）。
    - IC（Information Coefficient）計算: calc_ic(factor_records, forward_records, factor_col, return_col)
      - スピアマンのランク相関を実装、有効レコードが少ない場合は None を返す。
    - ランク変換ユーティリティ rank(values)（同順位は平均ランク）。
    - 統計サマリー: factor_summary(records, columns)（count/mean/std/min/max/median）。
  - research パッケージ __init__ から主要関数を再エクスポート。

- AI (src/kabusys/ai/)
  - ニュース NLP スコアリング (news_nlp.py)
    - raw_news と news_symbols から銘柄ごとにニュース集約し、OpenAI（gpt-4o-mini、JSON Mode）でバッチ評価して ai_scores テーブルへ書き込む。
    - 特徴：
      - タイムウィンドウ計算 calc_news_window(target_date)（JST ベース、UTC 変換で DB 比較）。
      - 銘柄あたり記事数・文字数上限を設けトークン肥大化を抑制（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
      - 最大 _BATCH_SIZE=20 銘柄単位でバッチ送信。
      - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。
      - レスポンス検証と JSON 整形ロバストネス（前後余分テキストから最外の {} を抽出する等）。
      - スコアは ±1.0 にクリップ。部分失敗時でも他銘柄スコアを保護するため DELETE→INSERT の差し替えを銘柄限定で実行。
      - テスト用フック: _call_openai_api を unittest.mock.patch で差し替え可能。
  - 市場レジーム判定 (regime_detector.py)
    - ETF 1321 の 200日 MA 乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を組合せて日次で market_regime テーブルに書き込む score_regime(conn, target_date, api_key=None) を実装。
    - 特徴：
      - _calc_ma200_ratio: target_date 未満のデータのみ使用してルックアヘッドを防止。データ不足は中立(1.0)扱い。
      - マクロニュース抽出（キーワードマッチ）と LLM 評価（_score_macro）。API失敗時は macro_sentiment=0.0 にフォールバック（例外としない）。
      - OpenAI 呼び出しは専用 wrapper（_call_openai_api）を使用。テストで差し替え可能。
      - レジームスコア合成後、BEGIN/DELETE/INSERT/COMMIT の冪等書き込みを行い、失敗時は ROLLBACK を試行。
      - API キー未設定時は ValueError を送出。
  - ai パッケージ __init__ から score_news を再エクスポート。

- 汎用設計・実装方針（全域）
  - ルックアヘッドバイアス防止のため datetime.today() / date.today() を多くの処理で直接参照しない設計（target_date 引数駆動）。
  - DB 書き込みはトランザクションを用いた冪等性を重視（BEGIN / DELETE / INSERT / COMMIT / ROLLBACK）。
  - OpenAI 呼び出しに関してはリトライ戦略・エラーハンドリング・レスポンスバリデーション等の安全装置を実装。
  - DuckDB に依存するクエリ・ユーティリティを多数提供。
  - ロギング（logger）・警告出力を充実させ、障害時の挙動をログに記録。

Fixed
- 初回リリースのため該当なし。

Changed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Notes
- 多くの機能が外部 API（OpenAI, J-Quants）や DuckDB 上のスキーマ（prices_daily / raw_news / market_calendar / ai_scores / market_regime / raw_financials 等）に依存します。実運用前に該当テーブルと権限／API キーの準備が必要です。
- テスト容易性のため一部内部呼び出し（OpenAI API 呼び出し等）をモック差し替え可能にしています。