CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" の形式に準拠しており、すべての公開変更を記録します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------
（なし）

0.1.0 - 2026-03-28
------------------

Added
- 基本パッケージ
  - パッケージ名: kabusys、バージョン 0.1.0 をリリース。
  - パッケージ公開 API: __all__ に data, strategy, execution, monitoring を定義。

- 設定 / 環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数の自動読み込みを実装。読み込み優先順は OS 環境変数 > .env.local > .env。
  - プロジェクトルートの検出は __file__ の親ディレクトリを辿り .git または pyproject.toml を基準に判定（CWD 非依存）。
  - .env パーサを実装:
    - コメント行、export プレフィックス対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱い、クォートなしでの # コメント判定などをサポート。
  - 自動ロードを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを導入し、必須変数取得時に未設定だと ValueError を送出するユーティリティを提供。
  - 設定項目: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV（development/paper_trading/live 検証）, LOG_LEVEL（DEBUG/INFO/... 検証）、および is_live/is_paper/is_dev のプロパティを提供。

- データプラットフォーム (kabusys.data)
  - calendar_management:
    - market_calendar を利用した営業日判定ロジックを提供。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装。
    - market_calendar 未取得時には曜日ベース（土日を非営業日）でフォールバック。
    - calendar_update_job を実装（J-Quants から差分取得 → 保存、バックフィル、健全性チェックを含む）。
  - pipeline:
    - ETLResult データクラスを公開し、ETL 実行結果の構造化（取得件数、保存件数、品質問題、エラー等）を提供。
    - 差分取得・バックフィル・品質チェックを行う設計方針を採用。
  - etl モジュールは pipeline.ETLResult を再エクスポート。

- AI モジュール (kabusys.ai)
  - news_nlp:
    - 指定ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）に基づいて raw_news と news_symbols を集約し、銘柄ごとのニュースを OpenAI（gpt-4o-mini, JSON mode）へバッチ送信してセンチメント（-1.0〜1.0）を算出。
    - バッチ処理: 最大 20 銘柄 / リクエスト、1 銘柄あたりの記事数・文字数制限（記事数最大 10、文字数最大 3000）。
    - 再試行戦略: 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ。
    - レスポンスの厳密バリデーション（JSON 抽出、results 配列存在チェック、コード照合、スコア数値化、有限性チェック）、スコアは ±1.0 にクリップ。
    - 書き込みは冪等性を考慮し、該当コードのみ DELETE → INSERT（DuckDB の executemany 空リスト制約に配慮）。
    - テストの容易性のため、内部の OpenAI 呼び出しポイント（_call_openai_api）をモック可能に設計。
  - regime_detector:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、ニュース NLP によるマクロセンチメント（重み 30%）を合成し日次で市場レジーム（bull / neutral / bear）を判定。
    - ma200_ratio 計算は target_date 未満のデータのみ使用し、データ不足時は中立（1.0）を採用してフェイルセーフ化。
    - マクロニュースは news_nlp の calc_news_window を利用して窓を決定し、OpenAI を呼び出して JSON で macro_sentiment を取得。API 失敗時は macro_sentiment=0.0 にフォールバック。
    - スコア合成後、market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時には ROLLBACK を試行して例外を伝播。

- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最近の財務データを取得して PER/ROE を計算（EPS が 0 または欠損時は None）。
    - SQL とウィンドウ関数を組み合わせた実装で、prices_daily / raw_financials のみ参照。外部 API にはアクセスしない。
  - feature_exploration:
    - calc_forward_returns: 将来リターン（任意ホライズン、デフォルト [1,5,21]）を計算。
    - calc_ic: スピアマンのランク相関（IC）を計算。有効レコードが 3 件未満の場合は None。
    - factor_summary: 指定カラムの基本統計量（count/mean/std/min/max/median）を算出。
    - rank: 同順位は平均ランクとするランク付けユーティリティ（丸めによる ties 対策あり）。

- テスト性 / 実運用配慮
  - モジュール設計で lookahead バイアスを避けるため datetime.today()/date.today() の直接参照を避けている（target_date を明示的に受け取る設計）。
  - OpenAI 呼び出し箇所は内部関数を通しており、unittest.mock.patch による差し替えが可能。
  - DuckDB のバージョン依存の挙動（executemany に空リストを渡せない等）に配慮した実装。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- OpenAI API キーが未設定の場合は明示的に ValueError を返す（news_nlp / regime_detector の両方）。
- 環境変数読み込みにおいて OS 環境変数を保護する protected セットを導入（override 処理時に上書きを防止）。

Notes / Known limitations
- AI モデルとして gpt-4o-mini を想定しており、将来のモデル変更や OpenAI SDK の API 仕様変更により実装の調整が必要になる可能性がある。
- DuckDB のバージョン差異（特にリストバインドや executemany の挙動）に注意。現実装は互換性を確保するための回避策を含む。
- 一部計算（ファクター算出や ETL の差分取得）は DB 内のデータ品質に依存するため、quality モジュールでの検出に基づく運用ルールが必要。

---

今後のリリースでは次の点を検討予定:
- Strategy / Execution 層の実装と実売買連携（kabu API 経由）。
- ai モジュールの評価精度改善、プロンプト最適化。
- モニタリング・アラート機能（Slack 経由通知等）。
- ユニットテストと CI の整備（OpenAI モック・DuckDB テストデータの自動化）。

README やリリースノートに追加してほしい項目があればお知らせください。