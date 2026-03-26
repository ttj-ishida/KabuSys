# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。  
フォーマット: https://keepachangelog.com/（日本語訳を踏まえた表記）

※ バージョンはパッケージの __version__ = "0.1.0" に合わせています。

## [Unreleased]
- 今後の変更履歴をここに記載します。

## [0.1.0] - 2026-03-26
初回リリース。日本株自動売買・データ基盤・リサーチ・AI支援のコア機能を実装。

### 追加 (Added)
- パッケージ基盤
  - パッケージ名: kabusys。公開モジュールとして data, strategy, execution, monitoring を __all__ でエクスポート（src/kabusys/__init__.py）。
  - バージョン: 0.1.0。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動読込する仕組みを実装。
  - 探索ロジック: パッケージ位置を基準に .git または pyproject.toml を探してプロジェクトルートを特定し、.env/.env.local を読み込む（KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能）。
  - 独自に堅牢な .env パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントルール等に対応）。
  - Settings クラスを提供し、アプリケーション設定（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パス、環境名、ログレベル判定等）をプロパティとして取得。
  - 環境値検証（KABUSYS_ENV の有効値チェック、LOG_LEVEL の有効値チェック）と便宜的プロパティ（is_live, is_paper, is_dev）。

- データプラットフォーム（DuckDB ベース）
  - ETL パイプライン (src/kabusys/data/pipeline.py)
    - 差分取得・保存・品質チェックを想定した ETLResult データクラスを実装（取得件数、保存件数、品質問題、エラーリスト等を含む）。
    - テーブル最終日取得ユーティリティ、最小データ日などの定数を定義。
  - ETL 公開インターフェースとして ETLResult を再エクスポート (src/kabusys/data/etl.py)。
  - マーケットカレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar を用いた営業日判定機能を実装: is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days。
    - DB に登録がない日については曜日ベース（土日）でフォールバックする一貫した挙動。
    - calendar_update_job を実装し、J-Quants API から差分でカレンダーを取得して冪等に保存（バックフィル/健全性チェックを含む）。J-Quants クライアント呼び出しを jquants_client 経由で行う設計。

- AI（ニュース NLP / レジーム判定）
  - ニュースセンチメントスコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols から対象ウィンドウ（前日15:00JST〜当日08:30JST、UTC換算で前日06:00〜23:30）を抽出する calc_news_window を提供。
    - 銘柄ごとに最新記事を集約し（最大記事数・文字数でトリム）、OpenAI (gpt-4o-mini) に対して JSON Mode でバッチ（最大20銘柄）送信してセンチメントを取得。
    - API エラー（429/ネットワーク/タイムアウト/5xx）に対して指数的バックオフでリトライ。レスポンスのバリデーションとスコアの ±1.0 クリップ、取得済み銘柄のみ ai_scores テーブルへ置換（DELETE→INSERT）することで冪等性・部分失敗時の保護を実現。
    - テスト容易性: OpenAI 呼び出しを _call_openai_api で抽象化して差し替え可能。
    - 公開関数 score_news(conn, target_date, api_key=None) を提供（戻り値: 書込んだ銘柄数）。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200日移動平均乖離（重み70%）とニュース LLM（重み30%）を合成し日次で市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - prices_daily と raw_news を参照、calc_news_window で同じ時間ウィンドウを使用。OpenAI API 呼び出し時のリトライとフェイルセーフ（失敗時は macro_sentiment=0.0）を実装。
    - DB への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を行う。
    - テスト容易性のため OpenAI 呼び出しを切り替え可能に実装。

- リサーチ・ファクター群 (src/kabusys/research/)
  - factor_research.py
    - Momentum（1M/3M/6M リターン、200日MA乖離）、Volatility（20日ATR、相対ATR、平均売買代金、出来高比率）、Value（PER, ROE）を DuckDB 上で計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の None 処理、対象テーブルは prices_daily / raw_financials のみとする設計。
  - feature_exploration.py
    - 将来リターン計算 calc_forward_returns（任意ホライズン対応、入力検証あり）。
    - スピアマンランク相関による IC 計算 calc_ic（NULL/少数レコードで None を返す）。
    - ランク変換ユーティリティ rank（同順位は平均ランク）。
    - factor_summary による基本統計量集計（count/mean/std/min/max/median）。
  - research パッケージ __init__ で主要関数をエクスポート。

### 変更 (Changed)
- （初版につき過去からの変更はなし）

### 修正 (Fixed)
- （初版につきバグ修正履歴はなし）

### 注意事項 / 既知の制約
- OpenAI API を利用する機能（score_news, score_regime）は API キー（env または引数）が必須。キー未設定時は ValueError を発生。
- デフォルトの DuckDB / SQLite のパスは settings によるデフォルト値（data/kabusys.duckdb, data/monitoring.db）。必要に応じて環境変数で上書き可能。
- .env 自動読み込みはプロジェクトルート検出に依存（.git または pyproject.toml）。配布後やテスト時には KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- DuckDB の executemany に空リストを渡せない点を考慮した実装（空の場合は実行をスキップ）。
- 日付処理はルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない設計を優先している箇所がある（score_news/score_regime 等では target_date 引数必須）。

### テストサポート / フェイルセーフ
- OpenAI 呼び出しを差し替え可能に実装し、ユニットテストでのモックを想定。
- API エラー時は適切にログ出力してフェイルセーフ（多くの場合スコア 0.0 または処理スキップ）とすることで、ETL/リサーチ処理の継続を確保。
- DB 書き込みは冪等化（DELETE → INSERT、ON CONFLICT 方針）してあり、部分失敗時に既存データを不必要に上書きしない工夫がある。

---

開発上の詳細（設計方針・アルゴリズムの説明・ログ出力方針など）は各モジュールの docstring にも記載しています。必要であればリリースノートの簡易英訳や、各関数の使用例・API ドキュメント（README 追加）も作成します。ご希望があれば次版での追加項目（例: Slack 通知、より詳細なメトリクス、戦略実行フローの実装）を提案します。