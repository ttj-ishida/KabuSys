CHANGELOG
=========

すべての変更は Keep a Changelog の方針に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

[0.1.0] - 2026-04-01
--------------------

Added
- 初回リリース。KabuSys のコアモジュールを追加。
  - パッケージ情報: kabusys.__init__ (バージョン 0.1.0, export 設定)
- 環境設定管理 (kabusys.config)
  - .env ファイルまたは OS 環境変数から設定を自動読み込みする機能を実装。
  - プロジェクトルート検出: .git または pyproject.toml を基準に自動検出（CWD 非依存）。
  - .env のパース機能強化:
    - コメント行 / 空行無視、export KEY=val 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応。
    - クォートなし値のインラインコメント処理（直前が空白/タブのみコメントと認識）。
  - .env 読み込み順序: OS 環境変数 > .env.local > .env（.env.local は上書き）
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD を用意（テスト等で使用可能）。
  - 保護された OS 環境変数の上書き防止ロジックを実装。
  - Settings クラスを提供し、以下の設定プロパティを公開:
    - J-Quants / kabuステーション / Slack / データベース（DuckDB/SQLite）パス
    - 監視用 PID ファイルパス、CPU/メモリ/ディスクの閾値
    - 環境(KABUSYS_ENV) とログレベル(LOG_LEVEL) のバリデーション
    - is_live / is_paper / is_dev ヘルパー
- AI モジュール (kabusys.ai)
  - news_nlp.score_news:
    - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini / JSON Mode）へバッチ送信してセンチメント（-1.0〜1.0）を算出し、ai_scores テーブルへ書き込む。
    - 機能: タイムウィンドウ計算 (calc_news_window)、チャンク処理（最大 20 銘柄/チャンク）、トークン肥大対策（記事数/文字数トリム）、レスポンス検証、スコアクリップ、DuckDB 互換性のための executemany 空リスト回避。
    - エラー耐性: 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ・リトライ、その他はスキップして継続（フェイルセーフ）。
    - レスポンスの JSON パース復元（余分な前後テキストが混ざる場合に最外の {} を抽出）等の堅牢性向上。
  - regime_detector.score_regime:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等的に書き込む。
    - マクロキーワードで raw_news をフィルタして LLM へ送信。API 呼び出し失敗時は macro_sentiment=0.0 で継続（フェイルセーフ）。
    - OpenAI 呼び出しは news_nlp 側と別実装にしてモジュール結合を避ける設計。
    - 冪等性: BEGIN / DELETE / INSERT / COMMIT を用いた上書き処理、失敗時に ROLLBACK 試行。
- Data モジュール (kabusys.data)
  - calendar_management:
    - JPX カレンダー管理: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。
    - DB に market_calendar が無い場合は曜日ベース（単純に土日除外）でフォールバックする一貫したロジック。
    - next/prev の探索範囲上限 (_MAX_SEARCH_DAYS) を設定して無限ループを防止。
    - calendar_update_job: J-Quants API から差分取得し、バックフィル（直近 _BACKFILL_DAYS 日）を含めて market_calendar を冪等的に更新。健全性チェック（将来日付異常検出）を実装。
  - pipeline / etl:
    - ETLResult データクラスを追加して ETL 実行結果（取得数・保存数・品質問題・エラー）を構造化。
    - ETL モジュール設計（差分更新・品質チェック・id_token 注入対応など）を実装（pipeline, etl の骨組み）。
    - DuckDB テーブル存在チェック・最大日付取得等のユーティリティを実装。
- Research モジュール (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 偏差（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算。
    - calc_value: raw_financials から最新財務を取得し PER / ROE を計算（EPS が 0/欠損の場合は None）。
    - 全関数とも DuckDB の prices_daily / raw_financials のみ参照、ルックアヘッド対策済みの SQL を使用。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得する実装。
    - calc_ic: ファクター値と将来リターンの Spearman ランク相関（IC）計算。記録不足（<3）で None を返す。
    - rank / factor_summary: ランク化（同順位は平均ランク）と列の要約統計量（count/mean/std/min/max/median）を実装。
- エクスポート整理:
  - 各サブパッケージの __all__ を整備して公開 API を明示（research, ai など）。

Changed
- （初回リリースにつき該当なし）

Fixed
- （初回リリースにつき該当なし）

Notes / Implementation details
- ルックアヘッドバイアス対策:
  - AI / research の各処理は date.today() / datetime.today() を内部参照せず、必ず引数で target_date を受け取る設計。
  - DB クエリは target_date 未満 / 以前の排他条件を適用して将来情報を参照しないようにしている。
- OpenAI 関連:
  - gpt-4o-mini を使用、JSON Mode を利用（response_format={"type":"json_object"}）。
  - レスポンスの厳格な JSON 出力を期待するが、パース失敗時には復元処理やフェイルセーフとしてスコア 0.0 / スキップを行う。
  - テスト容易性のため、_call_openai_api をモック可能に設計。
- DuckDB 互換性:
  - executemany に空リストを渡すと失敗するバージョンを考慮して、空パラメータ時は実行をスキップするガードを追加。
- .env 読み込みの保護:
  - OS 環境変数は保護（protected set）され、.env/.env.local による上書きを必要に応じて制御。
- ロギング:
  - 主要処理で情報/警告/例外ログを出力するように実装しており、異常検出時に詳細を残す。

Known issues / Limitations
- OpenAI の仕様変更（例: 例外クラスや status_code の取り扱い）に対しては getattr を使うなどで互換性を確保しているが、将来の SDK 変更に注意が必要。
- raw_financials の PBR・配当利回り等は未実装（今後拡張予定）。
- calendar_update_job は J-Quants クライアント (kabusys.data.jquants_client) に依存しており、外部 API の可用性に依存する。

References
- 各モジュールの docstring に設計方針・処理フローが記載されています。各機能の詳細は該当モジュールのソースコードを参照してください。