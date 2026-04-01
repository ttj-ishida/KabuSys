Keep a Changelog準拠 — 変更履歴 (日本語)
===================================

この CHANGELOG はソースコードから推測して作成しています。実装された主な機能、設計方針、注意点、移行手順などをまとめています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------
- なし

[0.1.0] - 2026-04-01
-------------------
Added
- パッケージ基礎
  - kabusys パッケージ初期リリース。公開モジュール群のエントリポイントを設定（data, strategy, execution, monitoring を __all__ に含む）。
  - バージョン: 0.1.0

- 設定・環境変数管理 (kabusys.config)
  - .env / .env.local ファイルの自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索し、CWD に依存しない）。
  - .env 読み込みのパーサ実装:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内でのバックスラッシュエスケープ対応
    - クォート無しの行でのインラインコメント処理（直前が空白/タブの場合に # をコメントと判断）
  - .env.local を .env より優先して上書きする挙動。OS 環境変数を保護するオプション（保護セット）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - Settings クラス提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須変数検査（未設定時は ValueError を送出）
    - デフォルト値 (KABU_API_BASE_URL 等) とパス（DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH）
    - 環境 (KABUSYS_ENV) とログレベル (LOG_LEVEL) の検証（許容値チェック）
    - is_live / is_paper / is_dev のユーティリティプロパティ

- AI モジュール (kabusys.ai)
  - news_nlp.score_news:
    - raw_news と news_symbols を用いて銘柄別にニュースを集約し、OpenAI (gpt-4o-mini, JSON Mode) でセンチメント (ai_score) を算出して ai_scores テーブルへ書き込む。
    - バッチ処理（最大 20 銘柄 / API コール）、トークン爆発対策（記事数最大/文字数トリム）を実装。
    - リトライ（429 / ネットワーク / タイムアウト / 5xx）を指数バックオフで実装。API 失敗時は該当チャンクをスキップ（フェイルセーフ）。
    - レスポンスの堅牢なバリデーションと JSON 復元処理（前後余計なテキストを含む場合に最外の {} を抽出）。
    - 書き込みは部分的失敗を考慮して対象コードのみ DELETE → INSERT（トランザクション）で置換。
    - タイムウィンドウ計算 (JST ベース → DB 用 UTC naive datetime) を提供 (calc_news_window)。
    - 外部依存: duckdb、openai SDK。
  - regime_detector.score_regime:
    - ETF 1321 の 200 日移動平均乖離 (重み 70%) と news_nlp ベースのマクロセンチメント (重み 30%) を合成して market_regime テーブルに日次で書き込む。
    - マクロニュースはマクロキーワードでフィルタし、OpenAI に JSON 出力を要求。API 失敗時は macro_sentiment を 0.0 として継続（フェイルセーフ）。
    - レジームスコアの閾値により 'bull' / 'neutral' / 'bear' を決定。
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）。エラー時は ROLLBACK と例外伝播。

- 研究モジュール (kabusys.research)
  - factor_research:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日 MA 乖離）を DuckDB の SQL ウィンドウ関数で算出。データ不足は None を返す。
    - calc_volatility: 20 日 ATR（true_range 計算の NULL 伝播制御）、相対 ATR、20 日平均売買代金・出来高比率を算出。
    - calc_value: raw_financials から直近の財務データを取得して PER / ROE を算出（EPS が 0/NULL の場合は None）。PBR/配当利回りは未実装。
  - feature_exploration:
    - calc_forward_returns: 指定の horizon（営業日数）に対する将来リターンを LEAD を使ってまとめて取得。horizons の検証 (1..252)。
    - calc_ic: スピアマンのランク相関（IC）を実装（同順位は平均ランク）。
    - factor_summary: count/mean/std/min/max/median を算出（None 値は除外）。
    - rank: 値 → ランク（同順位は平均ランク、丸め処理で ties 検出漏れを防止）。
  - zscore_normalize は kabusys.data.stats から再公開（research パッケージ経由で利用可能）。

- データプラットフォーム (kabusys.data)
  - calendar_management:
    - 市場カレンダーの照会・判定ユーティリティ:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - market_calendar が未取得の場合は曜日ベースのフォールバック（土日を非営業日扱い）。
    - calendar_update_job: J-Quants API (jquants_client.fetch_market_calendar) から差分取得して market_calendar を更新（バックフィル、健全性チェック、ON CONFLICT 相当の保存を想定）。
    - 最大探索日数やバックフィル・ルックアヘッド等の運用パラメータを定義。
  - pipeline (ETL):
    - ETLResult データクラスを提供（取得/保存件数、品質問題、エラー一覧など）。
    - ETL の設計方針に沿った差分取得・backfill、品質チェックの収集方針を実装するための基盤。
  - etl モジュールは ETLResult を再エクスポート。

- 実装上の設計方針（全体）
  - ルックアヘッドバイアス防止のため、datetime.today()/date.today() をスコア・計算の基準日に直接用いない（外部から target_date を注入する設計）。
  - DuckDB を主要なデータストアとして利用（大量の SQL とウィンドウ関数を活用）。
  - OpenAI 呼び出しは JSON Mode を利用し、レスポンスパースに冗長性を持たせる（失敗時フォールバック）。
  - API 呼び出しでの一時エラーは指数バックオフでリトライ。再試行上限あり。
  - DB 書き込みはトランザクションで冪等に行う（既存レコードの上書き/置換）。
  - executemany の空引数対応（DuckDB 0.10 の挙動を考慮）を行い、部分失敗時に既存データを保護。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- OpenAI API キー（OPENAI_API_KEY）や各種トークンは環境変数または引数で注入する設計。シークレットを .env に書く場合は .env.local を利用して上書きや環境差分管理を推奨。
- 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD を用意（テストや CI での意図しない読み込みを防止）。

Migration / Upgrade notes
- 必須環境変数を設定してください:
  - OPENAI_API_KEY（score_news / score_regime 実行時必須）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など（実運用機能を使う場合）
- DuckDB 上に必要なテーブルを準備してください（主なテーブル名）:
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar
  - ETL や各処理はこれらのテーブルを前提に動作します。
- テスト環境:
  - 自動 .env ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- 注意: PBR / 配当利回りなど一部指標は未実装です。strategy / execution / monitoring モジュールの実装は本リリースで一部想定のみ（パッケージエントリには含まれるが、実装の有無は環境による）。

Known limitations / Notes
- OpenAI モデルは現状 gpt-4o-mini に固定。将来的なモデル変更は API 呼び出し箇所を更新する必要あり。
- news_nlp・regime_detector の JSON パースは寛容に実装しているが、LLM 側の不正出力によりスキップや部分スコア欠落が発生する可能性あり。
- raw_financials の取得や J-Quants クライアント (kabusys.data.jquants_client) の実装は外部に依存するため別途設定と権限が必要。
- strategy / execution / monitoring の詳細実装は本コードベースに包含されていない（将来的なリリースでの追加を想定）。

Authors / Contributors
- 初期実装（コードベースから推測）。実際の貢献者情報はリポジトリのコミット履歴を参照してください。

ライセンス
- 本 CHANGELOG はコードベースから推測して作成したものであり、実際のプロジェクト README / RELEASE ノートと相違する場合があります。正式なリリースノートはリポジトリのリリースページを参照してください。