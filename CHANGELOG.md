CHANGELOG
=========

すべての重要な変更点をこのファイルに記録します。本ファイルは「Keep a Changelog」形式に準拠しています。

フォーマット:
- 変更はカテゴリ(Added, Changed, Fixed, Deprecated, Removed, Security)ごとに分類しています。
- バージョンごとに日付を付与しています。

[Unreleased]
------------

（未リリースの変更はここに記載）

[0.1.0] - 2026-03-28
-------------------

Added
- 初回公開: KabuSys 日本株自動売買システムの基本モジュール群を追加。
  - パッケージ公開情報
    - src/kabusys/__init__.py に __version__="0.1.0" を設定し、data/strategy/execution/monitoring を公開。
  - 設定・環境変数管理
    - src/kabusys/config.py
      - .env ファイルおよび環境変数から設定値を自動読込する仕組みを実装（プロジェクトルートは .git / pyproject.toml から探索）。
      - 読み込み順序: OS 環境変数 > .env.local > .env。
      - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
      - .env パーサは export 形式・クォート・エスケープ・インラインコメントに対応。
      - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 実行環境（development/paper_trading/live）等の設定取得と基本バリデーションを実装。
      - 必須環境変数未設定時には ValueError を発生させるユーティリティを提供。
  - AI（NLP）関連
    - src/kabusys/ai/news_nlp.py
      - raw_news と news_symbols を基に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）の JSON mode を用いてセンチメント（ai_score）を算出して ai_scores テーブルへ書込む機能を実装。
      - バッチ処理（最大 20 銘柄／API 呼び出し）、トークン肥大化対策（記事数・文字数制限）、レスポンス検証、スコアクリップ（±1.0）を実装。
      - ネットワーク／429／5xx エラーに対して指数バックオフによるリトライを実装。失敗時はスキップして継続（フェイルセーフ）。
      - calc_news_window(target_date) を実装（JST 基準で前日 15:00 ～ 当日 08:30 のウィンドウを UTC naive datetime で返す）。
      - テスト容易性のため OpenAI 呼び出し箇所は差し替え可能（モジュール内 private 関数を patch する想定）。
    - src/kabusys/ai/regime_detector.py
      - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、日次の市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ冪等書込する機能を実装。
      - MA200 計算はルックアヘッドを防止（target_date 未満のデータのみ利用）。マクロ記事がない場合や API エラー時は macro_sentiment = 0.0 としてフェイルセーフで継続。
      - OpenAI 呼び出しはニュース NLP と独立した private 実装（モジュール結合を避ける）。
      - API 呼び出しは再試行ロジックを含む。
  - データ処理（Data Platform）
    - src/kabusys/data/calendar_management.py
      - JPX マーケットカレンダー管理: market_calendar テーブルを用いた営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。
      - DB にカレンダーがない場合は曜日（平日）ベースでフォールバック。DB 登録値があれば優先する設計。
      - calendar_update_job: J-Quants API（jquants_client）から差分取得して冪等保存（バックフィル・健全性チェック含む）。
    - src/kabusys/data/pipeline.py, src/kabusys/data/etl.py
      - ETL パイプラインの骨組みを実装。差分取得・保存・品質チェックの方針を明文化。
      - ETLResult dataclass を導入（取得数・保存数・品質問題・エラー要約を保持するユーティリティ）。etl.py は ETLResult を再エクスポート。
    - src/kabusys/data/__init__.py（モジュール構成の準備）
  - リサーチ（Research）
    - src/kabusys/research/factor_research.py
      - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR、相対 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER、ROE）等のファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。結果は (date, code) をキーにした dict リストで返却。
      - DuckDB の SQL を活用し、データ不足時には None を返す等の堅牢性を確保。
    - src/kabusys/research/feature_exploration.py
      - 将来リターン計算（calc_forward_returns）、IC（Spearman）の計算（calc_ic）、ランク関数、統計サマリー（factor_summary）を実装。外部依存を持たず標準ライブラリと DuckDB のみで動作。
    - src/kabusys/research/__init__.py で主要関数をエクスポート。
  - テスト・運用向け設計上の考慮
    - ルックアヘッドバイアス対策: いずれの関数も内部で datetime.today()/date.today() を暗黙参照せず、target_date を明示的に受け取る設計。
    - DuckDB を主要なローカル分析 DB として採用。DB 書込みは冪等（DELETE→INSERT のパターン、BEGIN/COMMIT/ROLLBACK 制御）。
    - OpenAI レスポンスのパース失敗や API 障害時はフェイルセーフ（例外を放置せずログを残して 0.0 やスキップで継続）。
    - テスト容易性のため、内部の API 呼び出し関数を patch して差し替え可能にした箇所が多数存在。
  - ロギング・バリデーション
    - 各モジュールは詳細なログ（INFO/DEBUG/WARNING）を出力し、異常時は logger.exception/ logger.warning で理由を残す実装。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- （初回リリースのため該当なし）

注意事項（重要）
- 必須環境変数:
  - OPENAI_API_KEY（AI 機能: score_news / score_regime）
  - JQUANTS_REFRESH_TOKEN（J-Quants API）
  - KABU_API_PASSWORD（kabu ステーション API）
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（Slack 通知）
- デフォルトの DB パス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- 自動的に .env を読み込む仕組みがあるため、CI / テストで環境操作する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化可能。
- OpenAI API 呼び出し部分は gpt-4o-mini を想定した JSON Mode を利用しており、出力フォーマットに厳密性を要求するため API レスポンスの形式変更には注意が必要。
- DuckDB の executemany に空リストを渡すとエラーとなるバージョンがあるため、空チェックを行ってから実行する実装になっています。

今後の予定（例）
- strategy / execution / monitoring モジュールの具体的な取引ロジック・発注実装の追加。
- テストカバレッジ拡充（ユニットテスト・統合テスト）、CI パイプライン整備。
- OpenAI 呼び出しのオプション（モデル切替や同時実行制御）の拡充。
- J-Quants / kabu クライアントのエラーハンドリング強化やメトリクス収集。

もし CHANGELOG に追加したい項目（実装意図・リリース日・重要な TODO 等）があれば教えてください。必要に応じて日付やカテゴリ分けを調整します。