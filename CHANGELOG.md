# CHANGELOG

すべての重要な変更は Keep a Changelog の方針に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

注: 本 CHANGELOG はソースコードから推測して作成した初期リリースの変更履歴です。

## [0.1.0] - 2026-03-31

### 追加
- 初期リリース。KabuSys 日本株自動売買システムのコアライブラリを追加。
- パッケージ公開情報
  - src/kabusys/__init__.py にバージョン `0.1.0` を設定。
  - __all__ に data, strategy, execution, monitoring をエクスポート。

- 環境設定管理
  - src/kabusys/config.py
    - .env ファイルまたは環境変数から設定を自動ロード（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env / .env.local の読み込み順序（OS環境変数 > .env.local > .env）と、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
    - export KEY=val 形式やシングル/ダブルクォート、エスケープシーケンス、インラインコメントなどを考慮した堅牢な1行パーサを実装。
    - 環境変数保護（protected set）により OS 環境変数を .env で上書きしない挙動に対応。
    - Settings クラスを提供し、アプリケーション設定に型付きプロパティを用意（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
    - デフォルト値とバリデーション:
      - KABUSYS_ENV は "development" / "paper_trading" / "live" のみ許容。
      - LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL に制限。
      - データベースのデフォルトパス: duckdb: data/kabusys.duckdb, sqlite: data/monitoring.db。

- AI モジュール（OpenAI 統合）
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を用いて銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルに書き込む処理を実装。
    - JST ベースのニュースウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window として提供。
    - バッチ処理（最大 20 銘柄 / チャンク）、1銘柄あたり記事数上限（10 件）および文字数上限（3000 文字）を採用し、API 呼び出しの肥大化を抑制。
    - OpenAI の JSON Mode を利用して厳格な JSON を期待。レスポンス検証ロジック（results 配列・code/score の型チェック・スコアの ±1.0 クリップ）を実装。
    - レート制限(429)、ネットワーク断、タイムアウト、5xx に対する指数バックオフでのリトライを実装。再試行上限を設定。
    - テスト容易性のため _call_openai_api を patch 可能に設計。
    - 部分失敗に備え、取得できた銘柄のみを DELETE → INSERT で置換することで既存スコア保護（冪等性）を確保。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定する機能を追加。
    - prices_daily と raw_news を参照し、ma200_ratio の算出、マクロキーワードでフィルタした記事を LLM に投げて macro_sentiment を取得、スコア合成、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - OpenAI クライアント生成は OpenAI(api_key=...) を使用。API 失敗時は macro_sentiment=0.0 をフェイルセーフとして継続。
    - API 呼び出しのリトライ / バックオフ処理、およびレスポンス JSON パースの堅牢性を実装。
    - 設定可能な定数: 重み、閾値、モデル名（gpt-4o-mini）、リトライ回数等。

- データ処理・研究モジュール
  - src/kabusys/data/pipeline.py, src/kabusys/data/etl.py
    - ETL パイプラインのインターフェース実装。ETLResult データクラスを導入し、取得件数・保存件数・品質問題・エラーの集約を行う。
    - 差分更新、バックフィル、品質チェックの方針をドキュメント化。
    - DuckDB を利用したテーブル存在チェックや最大日付取得ユーティリティを実装。

  - src/kabusys/data/calendar_management.py
    - JPX カレンダー（market_calendar）に対する夜間更新ジョブ calendar_update_job を実装。J-Quants クライアント経由で差分取得し冪等保存。
    - 営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を提供。DB データがない場合は曜日ベース（平日は営業日、土日は休日）でフォールバック。
    - lookahead / backfill / 健全性チェック (_SANITY_MAX_FUTURE_DAYS) を実装。

  - src/kabusys/research
    - src/kabusys/research/factor_research.py
      - ファクター計算（Momentum／Value／Volatility／Liquidity）の実装:
        - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
        - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率を計算。
        - calc_value: raw_financials から最新財務データを取得し PER, ROE を算出。
      - DuckDB 上で SQL とウィンドウ関数を中心に高効率に計算する設計。データ不足時の None 扱いなどの安全策を実装。

    - src/kabusys/research/feature_exploration.py
      - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）に対する将来リターンを一括取得する汎用クエリを実装。
      - calc_ic: Spearman ランク相関（Information Coefficient）をランク化ユーティリティとともに実装。データ不足時は None を返す。
      - rank: 同順位は平均ランクとする安定したランク化実装（丸め処理による ties 検出安定化）。
      - factor_summary: 基本統計量（count/mean/std/min/max/median）を計算するユーティリティ。

- モジュール再エクスポート
  -研究・AI・データの __init__.py で主要関数を外部に公開（score_news, score_regime, calc_momentum 等）。

### 変更（設計上の決定・実装ポリシーの記載）
- 全体設計方針（ドキュメント的な変更）
  - ルックアヘッドバイアス対策: 各モジュール（news_nlp, regime_detector, research の関数等）は datetime.today()/date.today() に依存せず、呼び出し側から target_date を明示的に渡す設計。
  - 外部 API 失敗時は基本的に例外で止めずにフォールバック（0.0 やスキップ）して継続するフェイルセーフ方針を採用（ただし DB 書き込み失敗時は上位に例外伝播）。
  - DuckDB に依存するクエリ実装を中心にし、外部ライブラリ（pandas 等）に依存しない実装方針。

### 修正（バグ修正 / 安定化）
- トランザクション処理時の例外安全化:
  - score_regime / score_news 等の DB 書き込みで try/except により ROLLBACK を試行し、ROLLBACK 失敗時は警告ログを出力するように実装（冪等性と障害耐性強化）。
- OpenAI レスポンスのパース強化:
  - JSON Mode でも前後の余計なテキストが混入するケースに備えて最外の {} を抽出してパースを試みる実装を追加。
- レート制限・サーバエラー時のリトライロジックを各 AI 呼び出しで厳密に実装（429/ネットワーク断/タイムアウト/5xx の扱いを明確化）。

### 既知の注意点 / 制約
- OpenAI API キー必須:
  - score_news と score_regime は api_key 引数または環境変数 OPENAI_API_KEY のいずれかが必須。未設定時は ValueError を送出する。
- DuckDB バージョン互換性:
  - DuckDB の executemany に空リストを渡せない挙動（0.10 系など）を考慮して、空リストチェックを行ってから executemany を呼び出している。
- デフォルトで OpenAI モデル gpt-4o-mini を使用する設計。
- news_nlp のチャンクサイズや最大記事数・文字数は現状の定数で固定されている（将来変数化の余地あり）。
- calendar_update_job は jquants_client を使用（外部 API 呼び出し）。API 例外発生時は 0 を返して安全に終了する。

### セキュリティ
- 環境変数の自動ロードはデフォルトで有効だが、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 によって無効化可能。テスト環境などで明示的に制御できるよう配慮。

---

今後のリリースでは以下を想定:
- strategy / execution / monitoring の実装拡充（現在は名前のみエクスポート）。
- OpenAI モデルやバッチ設定の外部設定化（設定ファイル / env 経由）。
- より詳細な品質チェックの導入と監視・アラート機能の強化。