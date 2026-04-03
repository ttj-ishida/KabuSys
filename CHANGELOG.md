CHANGELOG
=========

All notable changes to this project will be documented in this file.

フォーマットは Keep a Changelog に準拠し、http://keepachangelog.com/ja/ に従います。

未リリースの変更は "Unreleased" に記載します。

Unreleased
----------

- なし

[0.1.0] - 2026-04-03
--------------------

初回公開リリース。以下の主要コンポーネントと機能を実装しました。

Added
-----

- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0 を設定。
  - パッケージ公開インターフェースに data / strategy / execution / monitoring をエクスポート。

- 環境設定管理 (kabusys.config)
  - .env / .env.local ファイルまたは OS 環境変数から設定値を読み込む自動ロード機能を実装。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサは export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応。
  - OS側の既存環境変数を保護する protected オプションをサポート（.env.local は上書きモード）。
  - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB パス / 監視閾値 / ログレベル / 実行環境（development/paper_trading/live）の取得と検証を実装。
  - 必須環境変数未設定時は明示的な ValueError を送出（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。

- AI モジュール (kabusys.ai)
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）に投げ、銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込む。
    - タイムウィンドウは前日 15:00 JST 〜 当日 08:30 JST（UTC に変換して比較）で固定。calc_news_window ユーティリティを提供。
    - バッチ処理（最大 20 銘柄/チャンク）、1 銘柄あたり最大記事数・最大文字数トリム、スコア ±1.0 クリップ。
    - JSON Mode を期待し、レスポンス検証（results 配列・code/score・数値チェック）を実装。部分失敗を許容して他銘柄データを保護する書き込み（DELETE → INSERT）戦略を採用。
    - API 失敗（429/ネットワーク/タイムアウト/5xx）は指数バックオフでリトライ。永続失敗時は該当チャンクをスキップして継続（フェイルセーフ）。
    - テスト容易性のため OpenAI 呼び出し関数は差し替え可能（unittest.mock.patch 対応）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（ウエイト 70%）とマクロ経済ニュースの LLM センチメント（ウエイト 30%）を合成して、日次で market_regime テーブルへレジーム（bull/neutral/bear）を書き込む処理を実装。
    - マクロ記事抽出はキーワードベースで titles を取得し、OpenAI（gpt-4o-mini）に送信。API 失敗時は macro_sentiment=0.0 として継続。
    - レジームスコアはクリップされ、閾値に基づきラベル付与。DB への書き込みは冪等に行う（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。
    - OpenAI 呼び出しの再試行・エラーハンドリングを実装。

- Data モジュール (kabusys.data)
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを参照して営業日判定ロジックを提供（is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days）。
    - DB データが存在しない場合は曜日ベース（土日除外）でフォールバックする一貫した挙動。
    - calendar_update_job を実装し、J-Quants API（jquants_client）から差分取得・バックフィル・保存を行う。lookahead/backfill/健全性チェックをサポート。
  - ETL パイプライン（kabusys.data.pipeline / kabusys.data.etl）
    - DataPlatform の設計に基づいた差分更新・保存・品質チェックフローを実装するための基礎を追加。
    - ETLResult dataclass を公開（kabusys.data.etl 経由で再エクスポート）。実行結果、品質検出、エラー概要などを構造化して返す。
    - 差分更新の初期日やデフォルトのバックフィル日数、品質チェックの扱い（重大度に応じたフラグ付け、ただし処理は継続）を定義。
    - DuckDB を前提としたテーブル存在チェックや最大日付取得ユーティリティを実装（パイプライン内部で使用）。

- Research モジュール (kabusys.research)
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR、相対 ATR、20日平均売買代金、出来高比率）、Value（PER, ROE）を DuckDB の prices_daily / raw_financials から計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - SQL ウィンドウ関数を用いて効率的に計算。データ不足時は None を返す挙動。
    - 出力は (date, code) ベースの dict リスト。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）：複数ホライズンのリターンを一度に取得する SQL 実装。horizon の妥当性チェックあり。
    - IC（Information Coefficient）計算（calc_ic）：ファクターと将来リターンのスピアマンランク相関を計算。3 件未満で None を返す。
    - rank / factor_summary：ランク付け（同順位は平均ランク処理）、基本統計量（count/mean/std/min/max/median）を実装。
    - zscore_normalize を data.stats から再エクスポートするためのインターフェースを用意（kabusys.research.__init__ 経由で利用可能）。

Changed
-------

- （初回リリースのため該当なし）

Fixed
-----

- （初回リリースのため該当なし）

Internal / Implementation notes
-------------------------------

- OpenAI 呼び出し部分は各モジュールで独立実装されており、モジュール間でプライベート関数を共有しない設計（テスト容易性と結合低減のため）。
- DuckDB を主要なデータストアとして想定。SQL 内での NULL / データ不足の扱いに注意しており、欠損時は明示的に None を返すかフェイルセーフ動作を実装。
- 外部 API 呼び出し（OpenAI / J-Quants）はリトライ・バックオフ・フェイルセーフを備え、部分失敗時でもシステム全体が停止しない設計。
- テスト容易性のため、OpenAI 呼び出し関数や .env 自動ロードの抑止が可能。

Acknowledgements
----------------

- DuckDB を内部データベースとして利用。
- OpenAI Chat Completions（gpt-4o-mini）をニュースセンチメント・マクロ分析に利用。

今後の予定（例）
----------------

- AI 推論結果を利用した実取引・バックテストの統合（execution / strategy の具体実装）。
- ai_scores / market_regime などの監査ログ・可視化連携。
- テストカバレッジ拡張と CI ワークフローの整備。