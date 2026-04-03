CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
バージョン番号はパッケージ内の __version__（0.1.0）に基づきます。

0.1.0 - 2026-04-03
------------------

Added
- 初回公開リリース（0.1.0）。
- パッケージ基盤
  - パッケージ名: kabusys
  - エントリポイント: src/kabusys/__init__.py にて __version__ = "0.1.0"、公開サブパッケージ data, strategy, execution, monitoring を定義。
- 環境設定管理 (src/kabusys/config.py)
  - .env/.env.local の自動読み込みサポート（プロジェクトルートを .git または pyproject.toml から検出）。
  - .env パーサ実装（コメント、export プレフィックス、シングル/ダブルクォート内のエスケープ処理を考慮）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 環境変数取得ユーティリティ Settings を提供（J-Quants / kabu API / LINE / DB パス / 監視設定 / システム設定）。
  - 必須キー未設定時は ValueError を送出する _require を提供。
  - env・log_level の値検証（許容値チェック）や is_live / is_paper / is_dev のヘルパーを追加。
- データプラットフォーム関連 (src/kabusys/data)
  - ETL 結果の表現 ETLResult を公開（pipeline.ETLResult を再エクスポート）。
  - ETL パイプライン基盤 (src/kabusys/data/pipeline.py)
    - 差分取得・バックフィル・品質チェックの設計に基づく ETLResult dataclass を実装。
    - DuckDB を用いた最大日付取得・テーブル存在チェックなどのユーティリティを実装。
  - マーケットカレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar を用いた営業日判定ロジックを実装（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - JPX カレンダーの夜間差分更新ジョブ calendar_update_job を実装（J-Quants クライアント経由で取得 → 冪等保存）。
    - カレンダー未取得時の曜日ベースフォールバック、最大探索日数の制限、バックフィル・健全性チェックを導入。
- 研究用ユーティリティ (src/kabusys/research)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（EPS が 0/欠損は None）。
    - DuckDB 上で完結する SQL + Python 実装。出力は (date, code) ベースの dict リスト。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: factor と将来リターンのスピアマン IC（ランク相関）を計算。
    - rank: 同順位は平均ランクで扱うランク変換ユーティリティを実装（丸めによる ties 処理を含む）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を算出。
  - research パッケージのエクスポートを整理（zscore_normalize の再エクスポート等）。
- AI / NLP 機能 (src/kabusys/ai)
  - ニュースセンチメント (src/kabusys/ai/news_nlp.py)
    - score_news: raw_news と news_symbols を元に銘柄ごとのニュースを集約し、OpenAI (gpt-4o-mini) によりセンチメントを取得して ai_scores テーブルへ書き込み。
    - 時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を正確に扱う calc_news_window を実装。
    - バッチ送信（最大 20 銘柄/チャンク）、1銘柄あたりの記事数・文字数制限、レスポンス検証、スコアクリップ（±1.0）を実装。
    - API エラー（429、ネットワーク、タイムアウト、5xx）に対して指数バックオフリトライを実装。致命的でない場合はスキップ継続（フェイルセーフ）。
    - レスポンス JSON の耐障害的パース（前後の余計なテキストを除去して {} を抽出するロジック含む）。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - score_regime: ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出（キーワードベース）、OpenAI 呼び出し、リトライ、JSON パース、フォールバック（API 失敗時は macro_sentiment=0.0）を実装。
    - レジーム合成ロジック（スコアクリップ、閾値判定）を実装。
  - AI モジュールは OpenAI SDK（OpenAI クライアント）をラップして使う実装。テスト容易性のため _call_openai_api を patch 可能に設計。
- その他ユーティリティ
  - DuckDB を前提とした日付/テーブルユーティリティ、IDEMPOTENT な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時の ROLLBACK の扱い）を複数箇所で実装。
  - ロギングや詳細なデバッグ/警告メッセージを多数追加（データ不足、API失敗、ROLLBACK失敗等のケース）。

Changed
- 設計方針として「ルックアヘッドバイアス防止」を明示
  - 各種処理（score_news, score_regime, calc_*）で datetime.today()/date.today() を直接参照せず、target_date 引数で明示的に計算する設計に統一。
- DuckDB 互換性対応
  - executemany の空リスト回避、リスト型バインドに依存しない DELETE の実装など、DuckDB バージョン依存の問題に配慮。

Fixed
- API レスポンスパース失敗や OpenAI の一時エラーで例外を上位に伝播させないフェイルセーフ挙動を追加（運用中の単一記事・単一チャンク失敗で全体が止まらないように）。

Security
- 環境変数のオーバーライド保護機能（protected set）を実装。OS 環境変数を .env により意図せず上書きしない仕組みを導入。

Notes / 使用上の注意
- OpenAI API キー
  - news_nlp.score_news, regime_detector.score_regime は api_key 引数または環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出。
  - モデルは gpt-4o-mini を想定し、JSON Mode（response_format={"type":"json_object"}）での呼び出しを行う。
- .env 読み込み順序
  - 優先度: OS 環境 > .env.local > .env。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- DuckDB 前提
  - 多くの内部実装が DuckDB の SQL 機能（ウィンドウ関数等）に依存。実行時には DuckDB 接続を渡す必要がある。
- フォールバック挙動
  - OpenAI 呼び出し失敗時は macro_sentiment=0.0 やスコア未取得のスキップなどのフォールバックを行い、システム全体の耐障害性を優先しています。

公開 API（主な関数・クラス）
- settings: kabusys.config.Settings（settings インスタンス）
- ETLResult: kabusys.data.pipeline.ETLResult
- calendar_update_job / is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - モジュール: kabusys.data.calendar_management
- score_news / calc_news_window
  - モジュール: kabusys.ai.news_nlp
- score_regime
  - モジュール: kabusys.ai.regime_detector
- calc_momentum / calc_volatility / calc_value
  - モジュール: kabusys.research.factor_research
- calc_forward_returns / calc_ic / factor_summary / rank
  - モジュール: kabusys.research.feature_exploration

今後の予定（短期）
- strategy / execution / monitoring パッケージの具体的な実装（発注ロジック・実行監視・LINE 通知など）を充実させ、運用ワークフローを統合予定。
- テストカバレッジの拡充（特に OpenAI 呼び出し周りのモック・エラー処理）。
- J-Quants クライアント（jquants_client）と品質チェックモジュール（quality）の詳細実装強化。

もし CHANGELOG の構成を別のバージョン分け（Unreleased を追加する等）で希望があれば教えてください。