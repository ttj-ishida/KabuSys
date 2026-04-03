CHANGELOG
=========
この CHANGELOG は "Keep a Changelog" の形式に従い、日本語で本リポジトリの変更点をまとめたものです。

フォーマット:
- 変更はセクションごとに "Added / Changed / Fixed / Security / Internal" 等で分類しています。
- バージョンはパッケージの __version__ (src/kabusys/__init__.py = 0.1.0) を基準として作成しています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-03
--------------------

Added
- 初回リリース: kabusys パッケージ (バージョン 0.1.0)
  - パッケージエントリポイントを追加（src/kabusys/__init__.py）。
- 環境設定管理
  - src/kabusys/config.py
    - .env / .env.local の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から自動検出）。
    - export 形式やクォート・エスケープ・インラインコメントを考慮した .env パーサを実装。
    - 環境変数取得用 Settings クラスを提供（J-Quants, kabuステーション, LINE, DB パス, 監視閾値, ログレベル等のプロパティ）。
    - 自動ロード無効化用フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - 必須環境変数未設定時に ValueError を送出する _require 関数を実装。
- AI モジュール
  - src/kabusys/ai/news_nlp.py
    - ニュース記事を銘柄ごとに集約して OpenAI (gpt-4o-mini) にバッチ送信し、銘柄ごとのセンチメント（ai_score）を ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ計算 (前日15:00 JST ～ 当日08:30 JST 相当) を calc_news_window で提供。
    - バッチサイズ、記事・文字数上限、リトライ（429/ネットワーク/5xx に対する指数バックオフ）等の堅牢化を実装。
    - JSON レスポンス検証・数値変換・スコアクリップ（±1.0）を行うバリデーション機能を実装。
    - API キー注入可能でテスト容易性を考慮（OpenAI クライアントの呼び出し箇所は差し替え可能）。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を計算し、market_regime テーブルへ冪等書き込みする機能を実装。
    - マクロニュース抽出、OpenAI 呼び出し、リトライ・フォールバック（API 失敗時は macro_sentiment=0.0）を含むフローを実装。
    - LLM 呼び出しはモジュール間の結合を避けるため独自実装（テストでのモックが容易）。
- データプラットフォーム（Data）
  - src/kabusys/data/pipeline.py
    - ETL パイプラインの枠組みを実装（差分取得、保存、品質チェックの統合を想定）。
    - ETLResult データクラスを公開（ETL の各種統計・品質問題・エラー収集を保持）。
    - DuckDB を用いたテーブル存在確認や最大日付取得等のユーティリティを実装の下地。
  - src/kabusys/data/etl.py
    - pipeline.ETLResult を再エクスポート。
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理（market_calendar）の取得・保存・営業日判定ユーティリティを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の API を提供。
    - DB 登録値優先、未登録日は曜日ベースのフォールバック、最大探索日数の制限等を実装。
    - カレンダー夜間更新ジョブ calendar_update_job を実装（J-Quants から差分取得・バックフィル・健全性チェック）。
- リサーチ（Research）
  - src/kabusys/research/factor_research.py
    - ファクター計算関数: calc_momentum, calc_volatility, calc_value を実装（prices_daily / raw_financials を参照）。
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR、相対 ATR、出来高比等）、Value（PER, ROE）を計算。
    - DuckDB SQL とウィンドウ関数を活用した再現性のある実装。
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns（将来リターン）、calc_ic（Spearman IC）、rank（同順位は平均ランク）、factor_summary（統計サマリー）を実装。
    - pandas に依存しない純標準ライブラリ + DuckDB 実装。
  - src/kabusys/research/__init__.py で主要関数を公開。
- パッケージ公開インターフェース
  - __all__ に data, strategy, execution, monitoring を含める（トップレベルの公開方針を明示）。

Internal / Design notes
- 全モジュールでルックアヘッドバイアスを防ぐため datetime.today() / date.today() を直接参照しない設計方針を採用（target_date を明示的に受け取る）。
- DB 書き込みは冪等性を考慮（DELETE→INSERT、BEGIN/COMMIT/ROLLBACK 管理等）。
- OpenAI 呼び出しにおいては JSON Mode を用いたパースとレスポンス検証を行い、パース失敗や API 障害時にシステム全体が停止しないようフォールバックを実装。
- 単体テスト容易性のため、内部の API 呼び出し関数は差し替え（patch）可能な形で実装。

Changed
- 該当なし（初回リリース）

Fixed
- 該当なし（初回リリース）

Security
- 該当なし（初回リリース）

注意事項 / 既知の制約
- DuckDB の executemany に空リストを渡せないバージョン制約（0.10）を踏まえたガードコードを含む。
- OpenAI API キーは関数引数または環境変数 OPENAI_API_KEY で供給する必要がある（未設定時は ValueError を送出）。
- .env の自動読み込みはプロジェクトルート検出に依存するため、配布後や環境によっては KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効化可能。

貢献・報告
- バグ報告や改善提案は issue にてお願いします。README / ドキュメントには各モジュールの使用法・サンプルを追記予定です。