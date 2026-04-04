Changelog
=========
すべての変更は Keep a Changelog の形式に従います。  
フォーマット: https://keepachangelog.com/（日本語訳に準拠）

[Unreleased]
------------

なし

[0.1.0] - 2026-04-04
--------------------

初回リリース。

Added
- パッケージ基盤
  - kabusys パッケージを追加。バージョンは 0.1.0。パブリック API のエクスポート: data, strategy, execution, monitoring を __all__ に設定。

- 設定 / 環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数からの設定自動読み込み機能を実装。
    - プロジェクトルートを .git または pyproject.toml で探索して .env/.env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env のパースは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントなどに対応する堅牢な実装。
    - .env.local は優先上書き（OS 環境変数は保護）。
  - Settings クラスを導入し、アプリケーション設定をプロパティ経由で取得可能に。
    - J-Quants・kabu ステーション・LINE・DB パス・監視閾値・環境（development/paper_trading/live）・ログレベルの取得とバリデーションを提供。
    - 必須変数が未設定の場合は ValueError を送出し、ユーザーに .env.example を参照するよう通知。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）に JSON Mode でバッチ評価を実行して ai_scores テーブルへ書き込む。
    - チャンク処理（最大 20 銘柄/チャンク）、1 銘柄当たりの記事上限・文字数上限を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。その他エラーはスキップしてフェイルセーフに継続。
    - レスポンス検証機構を実装（JSON 抽出、results リスト検証、code の正規化、数値チェック、±1.0 でクリップ）。
    - DuckDB の executemany の空リスト問題への回避ロジック（空時は実行しない）を実装。
    - 公開関数: score_news(conn, target_date, api_key=None) — 書き込み件数を返す。api_key が未設定の場合は ValueError を送出。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、market_regime テーブルへ日次で保存。
    - マクロニュースは内部で定義したキーワード群でフィルタ（最大 20 記事）し、OpenAI（gpt-4o-mini、JSON Mode）で macro_sentiment を取得。
    - LLM 呼び出しのリトライ／エラー処理を実装（RateLimit/接続/タイムアウト/5xx の再試行、その他はフォールバック 0.0）。
    - DB への書き込みは冪等化（BEGIN / DELETE / INSERT / COMMIT）し、失敗時は ROLLBACK を試みて例外を再送出。
    - 公開関数: score_regime(conn, target_date, api_key=None) — 正常終了時に 1 を返す。api_key 未設定で ValueError。

  - テストしやすさを考慮し、OpenAI 呼び出し部分は内部の _call_openai_api を通じて実装（テスト時に patch 可能）。news_nlp と regime_detector は相互にプライベート関数を共有しない設計でモジュール結合を抑制。

- リサーチ/ファクター群 (kabusys.research)
  - factor_research:
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を計算。
    - calc_volatility(conn, target_date): 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value(conn, target_date): raw_financials から最新財務を取得して PER / ROE を計算（EPS=0/NULL は None）。
    - 実装は DuckDB 上の SQL ウィンドウ関数を多用し、外部 API へアクセスしない安全な設計。
  - feature_exploration:
    - calc_forward_returns(conn, target_date, horizons=None): 将来リターン（複数ホライズン）を一度のクエリで取得する実装。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンのランク相関（IC）を計算（有効レコード<3 の場合 None）。
    - rank(values): 同順位の平均ランク処理、丸めで ties 検出漏れを低減。
    - factor_summary(records, columns): count, mean, std, min, max, median の統計要約を返す。
  - 公開ユーティリティとエクスポートを設定。

- データプラットフォーム (kabusys.data)
  - calendar_management:
    - 市場カレンダーを扱うユーティリティ群を提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB に market_calendar がない場合は曜日（土日）ベースのフォールバックを使用。
    - next/prev/get_trading_days は _MAX_SEARCH_DAYS により無限ループを防止。
    - calendar_update_job(conn, lookahead_days): J-Quants から差分取得して market_calendar を更新（バックフィル、健全性チェックを実装）。
  - pipeline / etl:
    - ETLResult dataclass を導入して ETL 実行結果を構造化（品質チェック結果・エラーリスト等を保持）。
    - ETL パイプラインの基本方針（差分更新、バックフィル、品質チェックの継続方針等）を実装するためのインターフェースを提供。
  - jquants_client を介した取得/保存のための呼び出し点を想定（実際のクライアントは別モジュール）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- OpenAI API キーおよびその他機密情報は直接ログ出力しない設計。Settings は必須キー未設定時に明示的なエラーを投げるため、運用時の misconfiguration を早期に検出可能。

Notes / 使用上の注意
- OpenAI を利用する機能（score_news, score_regime）は OPENAI_API_KEY の設定が必要（関数引数で注入可能）。未設定時は ValueError。
- .env 自動読み込みは配布後の環境でも堅牢に動作するようプロジェクトルート探索を行いますが、テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を推奨。
- DuckDB 互換性に関する回避策（executemany の空リスト回避、list バインドの違い等）を実装済み。
- すべての時刻／日付処理は Look-ahead バイアスを避けるため date/target_date を外部から受け取り、datetime.today()/date.today() の直接参照を避ける設計。

既知の制限
- PBR・配当利回りなど一部バリューメトリクスは未実装（calc_value にて注記）。
- AI レスポンスの堅牢性は高めているが、LLM の応答フォーマットが完全に守られない場合は該当チャンクはスキップする動作。部分的にスコアを取得できる銘柄のみ DB に書き込む設計。

開発者向け情報
- テスト容易性のため OpenAI 呼び出しポイント（各モジュールの _call_openai_api）を patch してモック可能。
- ロギングは各モジュールで logger を使用。詳細なデバッグ出力は log_level の設定で制御。

--- 

履歴の記載に問題がある、補足してほしい箇所がある、またはリリースノートを英語版でも作成してほしい場合はお知らせください。