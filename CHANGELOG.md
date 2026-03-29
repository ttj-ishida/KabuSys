CHANGELOG
=========

すべての注目すべき変更点をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の原則に従います。

フォーマット:
- 変更はセクション（Added / Changed / Fixed / ...）で分類しています。
- 日付はリリース日を示します。

Unreleased
----------

（現時点ではなし）

[0.1.0] - 2026-03-29
--------------------

Added
- 初期リリース: KabuSys — 日本株自動売買・データ分析プラットフォームの基礎機能を実装。
  - パッケージメタ:
    - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。公開モジュールは data, research, ai, 等を想定。
  - 環境設定:
    - src/kabusys/config.py を追加。
      - .env / .env.local ファイルまたは OS 環境変数から設定を読み込む自動ロード機能を実装（パッケージルートを .git / pyproject.toml で検出）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
      - export KEY=val 形式、クォート文字・バックスラッシュエスケープ、インラインコメントの取り扱いをサポートする .env パーサを実装。
      - 環境変数の上書きポリシー（OS環境変数保護）を実装。
      - Settings クラスを提供（J-Quants / kabu API / Slack / DB パス / 実行環境 / ログレベルなどのアクセサ）。
      - KABUSYS_ENV / LOG_LEVEL の検証ロジック（許容値チェック）を実装。
  - AI（NLP）:
    - src/kabusys/ai/news_nlp.py を追加。
      - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）に対して銘柄ごとのセンチメントをバッチで要求。
      - JST ベースのニュース収集ウィンドウ計算（前日15:00～当日08:30 JST）を実装（calc_news_window）。
      - バッチサイズ制限、記事数/文字数トリム、JSON Mode 応答バリデーション、スコア ±1.0 クリップ、部分書き換え（DELETE→INSERT）による冪等保存を実装。
      - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフのリトライ、失敗時はそのチャンクをスキップするフェイルセーフ方針。
      - テスト容易性のため OpenAI 呼び出し部分を差し替え可能（内部 _call_openai_api をパッチ可）。
    - src/kabusys/ai/regime_detector.py を追加。
      - ETF 1321（Nikkei 連動ETF）の 200日移動平均乖離（重み70%）と、マクロニュース（LLM によるセンチメント、重み30%）を合成して市場レジーム（bull/neutral/bear）を日次で判定。
      - prices_daily / raw_news / market_regime テーブル操作のための DuckDB 統合、OpenAI API 呼び出し（リトライ等）と冪等な DB 書き込みを実装。
      - API失敗時のフォールバック（macro_sentiment = 0.0）やルックアヘッドバイアスを避ける設計（target_date 未満のデータのみ使用）等の安全策を実装。
  - データプラットフォーム（Data）:
    - src/kabusys/data/calendar_management.py を追加。
      - JPX カレンダー管理（market_calendar）用ユーティリティ群（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。
      - DB に登録済みのカレンダー値を優先し、未登録日は曜日ベースのフォールバックを提供。最大探索日数の上限や健全性チェックを実装。
      - calendar_update_job により J-Quants から差分取得→冪等保存（バックフィル、健全性チェック含む）を実装（jquants_client を想定）。
    - src/kabusys/data/pipeline.py を追加。
      - ETL 処理の骨格（差分取得、保存、品質チェック）を実装。ETLResult データクラスを定義。
      - DuckDB のテーブル存在チェック、最大日付取得、バックフィル方針等を実装。
      - ETLResult.to_dict() により品質問題を辞書化して監査ログに使えるようにした。
    - src/kabusys/data/etl.py で pipeline.ETLResult を再エクスポート。
  - Research（因子・特徴探索）:
    - src/kabusys/research/factor_research.py を追加。
      - Momentum / Volatility / Value 系の定量ファクター計算を実装（prices_daily / raw_financials を参照）。
      - 1M/3M/6M リターン、200日MA乖離、20日ATR、20日平均売買代金などを計算。
      - SQL（DuckDB）中心の実装で、結果を (date, code) キーの dict リストで返す。
    - src/kabusys/research/feature_exploration.py を追加。
      - 将来リターン計算（任意ホライズン）、IC（Spearman の ρ）計算、rank 関数、ファクター統計サマリを実装。
      - 外部ライブラリに依存せず標準ライブラリのみで実装。
    - src/kabusys/research/__init__.py で関数群を再エクスポート。
  - その他ユーティリティ:
    - DuckDB を主要なローカル DB として採用。executemany の空リストバインド制約に対する対策を導入。
    - ロギング（各モジュールで logger を使用）を充実させ、失敗時に警告/例外ログを残すように設計。

Changed
- （初版のため、過去バージョンからの変更点はなし）

Fixed
- （初版のため、過去バージョンのバグ修正履歴はなし）
  - ただし各モジュールでフェイルセーフ動作や例外時の ROLLBACK 処理、API レスポンスパース失敗時の安全フォールバック等を積極的に実装していることを明記。

Notes / 設計上の留意点
- ルックアヘッドバイアス回避:
  - news_nlp / regime_detector は内部で datetime.today() や date.today() を参照せず、呼び出し元から target_date を受け取る設計。
  - DB クエリでは target_date 未満や半開区間などの明確な境界を使う。
- OpenAI 統合:
  - gpt-4o-mini を想定。JSON Mode を使った厳密な JSON 出力を期待するが、JSON パースに失敗した場合のフォールバックや前後テキスト除去ロジックを実装。
  - 重要なリクエストはリトライ（指数バックオフ）し、最終的に失敗してもシステム全体は継続するフェイルセーフを採用。
  - テスト容易性: _call_openai_api を patch して API 呼び出しを模擬できる。
- DB 書き込みの冪等性:
  - market_regime / ai_scores / market_calendar 等への書き込みは、対象日やコードを限定して既存データを削除してから挿入するなど、部分失敗時に既存データを不必要に消さない実装。
  - トランザクション（BEGIN/COMMIT/ROLLBACK）を適切に使用。
- 環境変数読み込み:
  - .env と .env.local の優先順位を実装し、OS 環境変数はデフォルトで保護（上書き不可）する仕組みを採用。
  - 不正な設定値に対しては明示的な ValueError を送出（早期検出）。

Breaking Changes
- 初期リリースのため該当なし。

Security
- OpenAI API キー等の機密情報は環境変数で管理することを推奨。コード自体にベタ書きしないこと。

作者注
- このリリースは初期実装として、データ取得・ストレージ・解析・AI によるスコア付けの基盤を提供します。  
- 実際の運用（特に発注やライブトレード）に投入する前に、テスト・監査・安全策（レート制限、バックテスト、モニタリング、ロールバック手順等）の追加を推奨します。