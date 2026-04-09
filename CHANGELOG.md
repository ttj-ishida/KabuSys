CHANGELOG
=========

すべての重大な変更履歴はここに記録します。本ファイルは「Keep a Changelog」準拠の形式で記載しています。

Unreleased
----------
- （なし）

[0.1.0] - 2026-04-09
--------------------
追加:
- パッケージ初期リリース。モジュール群を追加。
  - kabusys.config
    - .env ファイルおよび環境変数から設定を読み込む自動ローダを実装。
    - プロジェクトルート検出: __file__ を起点に親ディレクトリを探索し、.git または pyproject.toml を基準に自動検出。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - 高機能な .env パーサ実装: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理。
    - Settings クラスを提供（J-Quants / kabuステーション / LINE / DB パス / 監視設定 / システム設定等）。必須キー未設定時は ValueError を送出する _require() を採用。
    - 設定値検証: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等の有効値チェックを実装。
  - kabusys.portfolio
    - portfolio_builder: select_candidates（スコア降順選定、signal_rank によるタイブレーク）、calc_equal_weights、calc_score_weights（スコア合計が 0 の場合は等配分へフォールバックと WARNING ログ）。
    - risk_adjustment: apply_sector_cap（既存保有のセクターエクスポージャーに基づく候補除外、unknown セクターは除外しない挙動）、calc_regime_multiplier（regime による投下資金乗数、未知レジームはフォールバックと Warning）。
    - position_sizing: calc_position_sizes（risk_based / equal / score の allocation_method に対応）、単元株（lot_size）丸め、per-position 上限・aggregate キャップ（available_cash）でのスケールダウン、cost_buffer による保守的見積り、許容リスク / 損切り率等のパラメータ化。
  - kabusys.research
    - factor_research: DuckDB 接続を受け取り prices_daily / raw_financials を用いてファクター計算を実装。
      - モメンタム: 1M/3M/6M リターン、MA200 乖離（データ不足時は None）
      - ボラティリティ/流動性: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率（データ不足は None）
      - バリュー: PER・ROE（raw_financials の最新報告を結合）
    - feature_exploration: 将来リターン（任意ホライズン）計算、Spearman ランク相関での IC 計算（rank ユーティリティ含む）、ファクター統計サマリー（count/mean/std/min/max/median）。
    - 設計方針として、外部 API 呼び出しを行わず DuckDB のみ参照する実装。
  - kabusys.ai
    - news_nlp: raw_news を OpenAI（gpt-4o-mini）へバッチ送信して銘柄別のセンチメント ai_score を算出・ai_scores テーブルへ書込み。
      - ニュースウィンドウ計算（JST 基準、UTC に変換）を提供（calc_news_window）。
      - 1 銘柄あたり記事数・文字数上限を設けてプロンプト肥大化を抑止（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
      - 最大 20 銘柄/チャンクでバッチ処理、429/ネットワーク/タイムアウト/5xx を対象とした指数バックオフによるリトライ実装。
      - API レスポンスの堅牢なバリデーション（JSON パース、results キー、型チェック、既知コードチェック、数値チェック）とスコアの ±1.0 クリップ。
      - 部分成功に配慮した書込みロジック（対象コードのみ DELETE → INSERT を実行）を採用し、部分失敗時に既存スコアを保護。
      - フェイルセーフ: API が使えない/失敗した場合はスキップまたはデフォルトで継続（例外の抑制箇所あり）。
    - regime_detector: ETF(1321) の MA200 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の market_regime を判定・書込み。
      - マクロニュースはキーワードフィルタリングで抽出、LLM 呼び出しは記事がある場合のみ実行。
      - レジームスコアの合成と閾値判定により 'bull' / 'neutral' / 'bear' を算出。API 失敗時は macro_sentiment=0.0 でフォールバック。
      - DB 書込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実装。
  - kabusys.monitoring
    - monitoring_db: SQLite ベースの監視ログ永続化層。system_status, trade_logs, positions, risk_logs 等のテーブルとインデックスを作成する init_monitoring_db を追加。

設計上の注意点・フェイルセーフ:
- research モジュールは外部 API に依存せず DuckDB のみを参照する方針。
- AI 関連は API 失敗時に安全側のデフォルト（0.0 など）で継続する実装となっており、部分失敗があっても他データを破壊しないよう配慮している。
- 日付関連処理は datetime.today()/date.today() を参照せず、与えられた target_date に基づいて計算することでルックアヘッドバイアスを防止。
- テスト容易性のため OpenAI 呼び出しは内部で別関数化しており、unittest.mock.patch により差し替え可能。

既知の制約 / TODO:
- position_sizing._max_per_stock にて price が欠損（0.0）の場合、エクスポージャーや数量算出が過少/誤算される可能性があるため将来的にフォールバック価格（前日終値や取得原価）を検討する TODO。
- lot_size は現状グローバル固定（引数で指定可能）だが、将来的に銘柄毎の単元サイズをマスタで持たせる拡張を想定。
- OpenAI SDK のレスポンス仕様や DuckDB バインドのバージョンに依存する箇所があり、将来的な外部依存ライブラリのバージョン変更に注意が必要。

（本リリースは初期実装のため、今後の運用で観測された不具合や改善点に基づき細かな修正・最適化を行う予定です。）