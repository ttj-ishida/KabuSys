CHANGELOG
=========

すべての変更は Keep a Changelog 準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/

Unreleased
----------

（なし）

[0.1.0] - 2026-04-04
-------------------

Added
- 初期リリースを追加。kabusys パッケージの基本機能群を導入。
  - パッケージ構成:
    - kabusys.config: 環境変数/設定管理
    - kabusys.ai: ニュース NLP と市場レジーム検出
    - kabusys.research: ファクター計算・特徴量探索
    - kabusys.data: マーケットカレンダー管理、ETL パイプライン等
    - kabusys.data.etl: ETLResult の公開エントリポイント
  - パッケージバージョン: 0.1.0（src/kabusys/__init__.py）

- kabusys.config
  - .env ファイルの自動読み込み実装（プロジェクトルート検出: .git または pyproject.toml を探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化をサポート。
  - .env パーサ実装（export KEY=val 形式、クォート文字とバックスラッシュエスケープ、インラインコメント処理などに対応）。
  - 環境変数上書きポリシー: .env.local は上書き（override=True）、既存 OS 環境変数は保護（protected set）。
  - Settings クラスを提供（プロパティ経由で設定値取得）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
    - DUCKDB_PATH, SQLITE_PATH
    - 実行監視設定: PID/KILL ファイルパス, 閾値（CPU/MEM/DISK）、kill_flag_clear_on_start
    - 実行環境: KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL 検証
    - 便利プロパティ: is_live, is_paper, is_dev
  - 未設定必須変数に対して明示的な ValueError を送出する _require を実装。

- kabusys.ai.news_nlp (score_news)
  - raw_news / news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini, JSON mode）でセンチメント評価して ai_scores テーブルへ書き込み。
  - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC 変換で DB クエリ）。
  - バッチ処理: 最大 20 銘柄/API 呼び出し、1銘柄あたり最大 10 記事・3000 文字にトリム。
  - リトライ戦略: 429・ネットワーク断・タイムアウト・5xx を対象とした指数バックオフ（最大リトライ回数）を実装。
  - レスポンス検証: JSON 抽出・results フォーマット検証・コード照合・数値チェック・±1.0 クリップ。
  - DuckDB 互換性: executemany に空リストを渡さないガード（DuckDB 0.10 対応）。
  - フェイルセーフ: API エラー時は該当チャンクをスキップし、他銘柄への影響を最小化。
  - ロギングによる処理可視化（対象記事数・チャンク数・書込件数等）。

- kabusys.ai.regime_detector (score_regime)
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を統合し、日次で market_regime テーブルへ判定結果を冪等書き込み。
  - ma200_ratio は target_date 未満のみのデータを使用（ルックアヘッド防止）。
  - マクロニュースは raw_news からマクロキーワードでフィルタ（最大 20 件）し、OpenAI により -1.0〜1.0 のスコアを取得。
  - LLM 呼び出しのリトライ・エラー処理（API レート制限や 5xx などに対する再試行）を実装。最終的失敗時は macro_sentiment=0.0 にフォールバックして継続。
  - スコア合成後、閾値により regime_label を 'bull'/'neutral'/'bear' に判定。
  - DB 操作は BEGIN / DELETE / INSERT / COMMIT のトランザクションで冪等性を確保。失敗時は ROLLBACK を試行。

- kabusys.research
  - factor_research:
    - calc_momentum: mom_1m/3m/6m、ma200_dev（200日MA乖離）を計算。データ不足で None を返す挙動。
    - calc_volatility: 20日 ATR（true range 処理含む）、相対 ATR、20日平均売買代金、出来高比を計算。
    - calc_value: raw_financials から最新財務を結合し PER / ROE を計算（EPS が 0/NULL の場合は None）。
    - 設計により DuckDB 上の SQL ウィンドウ関数を活用し高速に処理。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。ホライズン検証（1..252）あり。
    - calc_ic: スピアマンランク相関（IC）を実装。 有効レコードが 3 未満なら None。
    - rank: 同順位は平均ランクとして扱う実装（round(..., 12) による丸めで ties の安定化）。
    - factor_summary: count/mean/std/min/max/median を算出する統計ユーティリティ。
  - research.__init__ で主要関数をエクスポート。

- kabusys.data.calendar_management
  - market_calendar を基に営業日判定・次営業日/前営業日・期間内営業日取得・SQ 判定を実装。
  - DB にカレンダー情報がない場合は曜日ベースのフォールバック（週末を非営業日扱い）。
  - calendar_update_job: J-Quants クライアント経由で差分取得 → 保存（バックフィル・正常性チェック・例外ハンドリングを含む）。
  - 最大探索日数やバックフィル・サニティチェックを導入して安全な自動更新を実現。

- kabusys.data.pipeline / ETL
  - ETLResult データクラスを導入（取得数、保存数、品質問題、エラー一覧などを保持）。
  - 差分更新の設計（最終取得日の backfill、calendar lookahead など）、品質チェック収集方針（Fail-Fast ではなく全件収集）を明記。
  - 内部ユーティリティ: テーブル存在チェック・最大日付取得の基盤実装（DuckDB 用）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。
- 実装時の互換性対策・エラーハンドリング（DuckDB executemany 空リスト回避、API 失敗時のフォールバック等）を反映。

Notes / Implementation details
- 全 AI / リサーチ処理はルックアヘッドバイアス防止のため datetime.today()/date.today() を内部で参照しない設計（target_date を引数に取る）。
- OpenAI を利用する関数は api_key 引数でキー注入可能。None の場合は環境変数 OPENAI_API_KEY を参照。未設定の場合は ValueError を送出。
- DB 書き込みは冪等化を重視（削除→挿入、ON CONFLICT 等）し、トランザクション制御と例外発生時の ROLLBACK を実装。
- ロギングを多用して実行状況と異常を記録（warning/info/debug）。
- 外部依存: DuckDB、OpenAI SDK、J-Quants クライアント（kabusys.data.jquants_client）が必要。

Migration notes / Usage hints
- AI 機能を利用するには OPENAI_API_KEY を環境変数に設定するか、関数呼び出し時に api_key を渡してください。
- 初回 ETL / カレンダー更新実行前に DuckDB 内のテーブルスキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar 等）を用意してください。
- .env/.env.local を用いる場合、プロジェクトルートに .git または pyproject.toml が存在する必要があります（自動検出に使用）。
- 開発/本番切替は KABUSYS_ENV（development/paper_trading/live）で制御します。ログレベルは LOG_LEVEL 環境変数で設定可能。

Contact / Contributing
- バグ報告・改善提案はリポジトリの Issue をご利用ください。README やドキュメントに沿ったテスト、特に DuckDB と OpenAI 呼び出し周りのモック/スタブを活用したユニットテストが重要です。