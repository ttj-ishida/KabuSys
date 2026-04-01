CHANGELOG
=========

すべての変更は "Keep a Changelog" の形式に従って記載しています。  
このドキュメントはコードベースの内容から推測して作成した初期リリース向けの変更履歴です。

[Unreleased]
------------

- （現時点のコードは初期リリースとしてタグ v0.1.0 を想定しています。将来の変更はこのセクションに記載してください）

[0.1.0] - 2026-04-01
--------------------

Added
- 基本パッケージとエントリポイント
  - kabusys パッケージ初期化（src/kabusys/__init__.py）。バージョン "0.1.0"、主要サブパッケージを __all__ で公開（data, strategy, execution, monitoring）。

- 設定／環境変数管理
  - src/kabusys/config.py を追加。.env ファイルおよび環境変数から設定を自動ロードする機能を実装。
    - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）によりカレントディレクトリに依存しない自動読み込み。
    - .env / .env.local の優先度処理（OS 環境変数 > .env.local > .env）および上書き保護（protected）。
    - export KEY=val、クォート、エスケープ、インラインコメント処理などの堅牢なパーサ実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト向け）。
  - Settings クラスを提供し、J-Quants・kabuステーション・Slack・DBパス・監視閾値・システム環境（development/paper_trading/live）などをプロパティで取得・検証。

- AI（LLM）関連
  - src/kabusys/ai/news_nlp.py：ニュース記事を集約して OpenAI（gpt-4o-mini、JSON Mode）へ送信し、銘柄ごとのセンチメント（ai_score）を ai_scores テーブルに書き込む処理を実装。
    - 時間ウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST）、記事トリミング（件数・文字数制限）、バッチ送信（最大 20 銘柄）を実装。
    - レスポンス検証（JSON 抽出、results の形式チェック、code/score の検証、スコアの ±1.0 クリップ）。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ、失敗時はフェイルセーフでスキップ。
    - テスト用に _call_openai_api の差し替えを想定。
  - src/kabusys/ai/regime_detector.py：ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出し、market_regime テーブルへ冪等書き込みする処理を実装。
    - マクロキーワードによる raw_news フィルタ、OpenAI 呼び出し（JSON パース）、リトライ・フェイルセーフ（API 失敗時は macro_sentiment=0.0）を備える。
    - ルックアヘッドバイアス防止の設計（date 引数ベース、DB クエリは target_date 未満のみ使用）。

- Data（データ基盤）
  - src/kabusys/data/calendar_management.py：JPX カレンダー管理と営業日判定ユーティリティを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days の提供。
    - market_calendar 未取得時は曜日ベースのフォールバック（週末非取引）を用いる設計。
    - calendar_update_job により J-Quants API から差分取得して冪等保存（バックフィル・健全性チェック付き）。
  - src/kabusys/data/pipeline.py：ETL パイプラインと ETLResult データクラスを実装。
    - 差分更新・バックフィル、jquants_client を通した idempotent 保存、品質チェック（quality モジュール）との統合を想定。
    - ETLResult により取得・保存カウント、品質問題、エラー一覧を集約し to_dict() を提供。
  - src/kabusys/data/etl.py：ETLResult の再エクスポート。

- Research（リサーチ／ファクター）
  - src/kabusys/research/factor_research.py：
    - calc_momentum / calc_volatility / calc_value を実装。prices_daily / raw_financials を用いたファクター計算（MA200 乖離、1/3/6 ヶ月リターン、ATR20、平均売買代金、PER、ROE 等）。
    - データ不足時の None ハンドリング、DuckDB のウインドウ関数を活用した実装。
  - src/kabusys/research/feature_exploration.py：
    - calc_forward_returns（任意ホライズンの将来リターン）、calc_ic（スピアマンランク相関での IC 計算）、rank（平均ランク処理）、factor_summary（基本統計量）を実装。
    - Pandas 等外部ライブラリに依存しない純 Python / DuckDB 実装。
  - src/kabusys/research/__init__.py：主要関数をエクスポート。

Changed
- 初版リリースとして設計方針や実装上の注意点（ルックアヘッド防止、冪等性、部分失敗時の保護など）が各モジュールの docstring として反映。

Fixed
- （該当なし：初期リリース）

Security
- 環境変数取得時に必須変数が未設定の場合は ValueError を投げることで明示的な失敗にし、秘密情報の取り扱いを明確にした（Settings._require）。

Deprecated
- （該当なし）

Removed
- （該当なし）

Notes / 実装上の注記
- DuckDB を主要なローカルデータストアとして利用しているため、SQL は DuckDB の動作を前提とした実装（executemany の空リスト制約や日付型の取り扱い等）になっています。DuckDB のバージョン違いで挙動差異があり得る点は認識してください。
- OpenAI（gpt-4o-mini）の呼び出しは JSON Mode を利用する前提で書かれており、レスポンスの頑健なパースとフォールバック（前後余分テキストの抽出等）処理を実装しています。
- テスト容易性のため、外部呼び出し箇所（OpenAI API 呼び出しなど）はテストで差し替え可能な設計になっています（例: unittest.mock.patch による _call_openai_api のモック）。
- 時刻／日付の扱いはルックアヘッドバイアスを避けるため target_date を明示的に受け取り、datetime.today()/date.today() への依存を最小化する方針が徹底されています（一部ジョブでのみ date.today() を使用）。
- 自動環境ロードはプロジェクトルート検出に依存するため、パッケージ配布後や CI 環境で不要なロードを避けるために KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化できます。

今後の改善候補（提案）
- OpenAI 呼び出しのインターフェース抽象化（インジェクション可能なラッパー）を進めてテスト／実稼働切替をさらに容易にする。
- ETL の品質チェック結果に基づく自動アラート（Slack 等）統合。
- DuckDB のスキーマ検証ユーティリティ追加とマイグレーション管理の整備。

--- 

（この CHANGELOG はコードの内容から推測して作成した初期リリースの要約です。実際のコミットログ／リリースノートと差異がある可能性があります）