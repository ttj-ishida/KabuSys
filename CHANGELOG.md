# Changelog

全ての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングに従います。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-09
初回リリース。日本株のデータ取得・ETL、ファクター研究、AI ベースのニュースセンチメント、
市場レジーム判定、環境設定管理など、コア機能を実装。

### Added
- 基本パッケージ
  - パッケージ初期化: kabusys パッケージとバージョン定義（__version__ = "0.1.0"）。
  - 公開モジュール群のエクスポート設定（data, strategy, execution, monitoring）。

- 設定・環境変数管理 (kabusys.config)
  - .env / .env.local の自動ロード機能（プロジェクトルートを .git または pyproject.toml で検出）。
  - .env パーサの実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応）。
  - 自動ロード無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
  - Os 環境変数の保護（.env の上書き制御、protected set）。
  - Settings クラスによる型付き設定アクセス（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス, PAPER_FILL_MODE 等）。
  - 設定値のバリデーション（PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等）。
  - 監視用閾値（CPU/MEM/DISK）や PID / kill flag パスなどのシステム設定。

- AI ニュース・NLP モジュール (kabusys.ai.news_nlp)
  - ニュース記事を銘柄ごとに集約して OpenAI (gpt-4o-mini) に送信し、銘柄別センチメント(ai_scores)を算出して書き込む機能（score_news）。
  - ニュース収集ウィンドウ算出（前日 15:00 JST ～ 当日 08:30 JST 相当の UTC 範囲）。
  - バッチ送信（最大 20 銘柄／チャンク）、記事数・文字数トリム、レスポンス検証、スコア ±1.0 クリップ。
  - API エラー / レート制限 / タイムアウト / 5xx に対する指数バックオフとリトライ実装。
  - テスト容易化のための _call_openai_api の差し替え想定（unittest.mock.patch）。
  - DuckDB への冪等書き込み（DELETE→INSERT、executemany の empty-list 回避ロジック、トランザクション制御）。

- 市場レジーム判定 (kabusys.ai.regime_detector)
  - ETF 1321（日経225 連動）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次で判定する機能（score_regime）。
  - マクロキーワードで raw_news をフィルタし、OpenAI に投げて macro_sentiment を取得（JSON mode）。
  - API のリトライ・フェイルセーフ（失敗時は macro_sentiment=0.0）。
  - DuckDB への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT、ROLLBACK on failure）。
  - ルックアヘッドバイアス対策（date 比較は target_date 未満や calc_news_window を利用し datetime.today()/date.today() を直接参照しない設計）。

- Research/ファクター計算 (kabusys.research)
  - ファクター計算群（kabusys.research.factor_research）
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200乖離（データ不足時の None ハンドリング）。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率。
    - calc_value: raw_financials からの EPS/ROE を用いた PER / ROE 計算（target_date 以前の最新レコードを取得）。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - calc_forward_returns: 指定ホライズンの将来リターンを一括取得（デフォルト [1,5,21]）。
    - calc_ic: スピアマンランク相関（IC）計算（None/非有限値/有効レコード数チェック）。
    - rank: 同順位は平均ランクとするランク付け実装（丸めによる ties 対策）。
    - factor_summary: count/mean/std/min/max/median の集計を提供。
  - zscore_normalize を data.stats から再エクスポート。

- データ・カレンダー管理 (kabusys.data.calendar_management)
  - JPX カレンダー管理（market_calendar テーブル）と営業日判定ユーティリティ:
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
  - DB にデータがない場合は曜日ベースでフォールバックする一貫したロジック。
  - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等に保存、バックフィルと健全性チェック実装。
  - 検索範囲制限（最大探索日数）や異常検知（将来日付の健全性チェック）。

- ETL / パイプライン (kabusys.data.pipeline, kabusys.data.etl)
  - ETLResult データクラスの導入（ETL 実行結果の構造化: フェッチ数/保存数/品質問題/エラー等）。
  - pipeline モジュールの公開インターフェースとして ETLResult を再エクスポート。
  - 差分更新・バックフィル・品質チェックの設計方針を実装に反映（コメント・設計意図を明記）。

- DuckDB 互換性と安全装置
  - executemany の空リスト回避など、DuckDB バージョン差異への対応。
  - トランザクション制御（BEGIN/COMMIT/ROLLBACK）とログ出力の充実。

### Changed
- （新規リリースのため過去変更なし）

### Fixed
- （新規リリースのため過去修正なし）

### Security
- OpenAI API キーは関数引数で注入可能。また環境変数 OPENAI_API_KEY を利用。
- .env ファイル読み込みは OS 環境変数を保護する設計（protected set）で誤上書きを抑止。

### Notable design decisions / implementation notes
- ルックアヘッドバイアス防止: 各 AI / 研究処理は datetime.today()/date.today() を直接参照せず、target_date ベースでウィンドウを明示的に計算する設計。
- フェイルセーフ: LLM/API に依存する機能は API 失敗時にスコア 0.0 やスキップで継続する実装。例外は必要箇所で伝播（DB 書込み失敗などは上位へ）。
- テスト性: _call_openai_api 等を patch できるようにし、ユニットテストで外部 API 呼び出しを差し替えやすくしている。
- DuckDB との互換性を考慮した SQL 実装および executemany の扱い。

---

参照:
- パッケージバージョン: 0.1.0 (src/kabusys/__init__.py)
- 実装ファイル: src/kabusys/config.py, src/kabusys/ai/*.py, src/kabusys/research/*.py, src/kabusys/data/*.py, など

（必要であれば各モジュール毎の詳細な CHANGELOG エントリを追記します）