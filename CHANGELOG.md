Keep a Changelog
すべての重要な変更はこのファイルに記録します。
フォーマットは https://keepachangelog.com/ja/ に準拠します。

[Unreleased]
- なし

[0.1.0] - 2026-04-09
Added
- 基本パッケージ初期実装を追加
  - パッケージメタ情報: kabusys.__version__ = "0.1.0" を設定。
  - パッケージエクスポートを定義（data, strategy, execution, monitoring 等を想定）。
- 環境変数 / 設定管理モジュール（kabusys.config）を追加
  - .env ファイルや環境変数から設定を自動ロード（プロジェクトルートを .git / pyproject.toml で検出）。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサ実装: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行末コメント処理をサポート。
  - 環境変数読み込みの優先順位: OS 環境変数 > .env.local > .env。
  - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB /モニタリング / システム設定等のプロパティを定義（必須項目は _require でエラー）。
  - バリデーション実装: PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等の有効値チェック。
  - Path 型の設定（DuckDB / SQLite / PID / kill flag 等）は expanduser() を適用。
- ポートフォリオ構築モジュール（kabusys.portfolio）を追加
  - 銘柄選定: select_candidates（スコア降順、同点は signal_rank でタイブレーク）。
  - 配分重み計算: calc_equal_weights、calc_score_weights（スコア合計が 0 の場合は等分にフォールバックし警告ログ）。
  - リスク調整: apply_sector_cap（既存保有に基づくセクター集中制限、unknown セクターは無視）、calc_regime_multiplier（regime に応じた乗数、未知レジームはフォールバックで警告）。
  - ポジションサイジング: calc_position_sizes（risk_based / equal / score の各方式、単元株丸め、per-position/aggregate 上限、コストバッファ、スケールダウンと残差分配アルゴリズムを実装）。
- リサーチ / ファクター計算（kabusys.research）を追加
  - ファクター計算（duckdb 接続を受ける純粋関数）:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離（ウィンドウ行数不足時は None）。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比（データ不足は None）。
    - calc_value: raw_financials から最新財務を取得し PER / ROE を計算（EPS 欠損時は None）。
  - ファクター探索ユーティリティ:
    - calc_forward_returns: 指定ホライズンの将来リターンを一括取得（ホライズン検証あり）。
    - calc_ic: スピアマンランク相関（IC）計算（有効レコードが 3 未満なら None）。
    - rank: 同順位は平均ランクを返す実装（丸めによる ties 対応）。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで計算。
  - 設計方針: DuckDB の prices_daily / raw_financials のみ参照、外部ライブラリ（pandas 等）に依存しない。
  - z-score 正規化ユーティリティを kabusys.data.stats から再エクスポート。
- AI モジュール（kabusys.ai）を追加
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols から銘柄ごとに記事を集約して OpenAI（gpt-4o-mini）でセンチメント評価し ai_scores テーブルへ保存。
    - バッチ処理（最大 20 銘柄/コール）、トークン肥大対策（記事数・文字数上限）、スコアの ±1.0 クリップ。
    - 再試行ポリシー: 429 / ネットワーク断 / タイムアウト / 5xx を指数バックオフでリトライ。その他は失敗としてスキップ（フェイルセーフ）。
    - レスポンスの堅牢なバリデーション（JSON 抽出、キー/型検証、未知コードの無視）。
    - DuckDB への書き込みは部分的更新（対象コードのみ DELETE → INSERT）で部分失敗から既存データを保護。
    - テスト補助: _call_openai_api は差し替え可能（unittest.mock.patch を想定）。
    - 設計方針: datetime.today()/date.today() を直接参照しない（ルックアヘッドバイアス防止）。
  - レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の MA200 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で regime_label（bull/neutral/bear）を算出し market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出はキーワードマッチ（複数キーワード群）でタイトルを収集し LLM で評価。記事がない場合は macro_sentiment=0.0（フェイルセーフ）。
    - API 呼び出しのリトライ/エラー処理を実装。内部の OpenAI 呼び出し関数は news_nlp と意図的に別実装（モジュール結合を避ける）。
    - ルックアヘッド防止: prices_daily クエリは target_date 未満のデータのみを使用。
- モニタリング永続化（kabusys.monitoring.monitoring_db）を追加
  - SQLite を使用した監視ログ永続化層を実装。冪等に 5 テーブル + インデックス作成（system_status, trade_logs, positions, risk_logs などのスキーマを定義）。

Changed
- なし（初期リリース）

Fixed
- なし（初期リリース）

Security
- 環境変数や API キーの取り扱いに注意:
  - OpenAI API キーは関数引数で渡すか、環境変数 OPENAI_API_KEY を使用（未設定時は ValueError）。
  - .env の読み込みで OS 環境変数は保護（起動時の既存環境変数を上書かない設計）。.env.local は上書き優先。

Notes / Implementation details
- DuckDB / SQLite を前提とした実装で、各関数は DB 接続オブジェクトを外から注入する純粋関数設計を意識しています（副作用を最小化）。
- LLM（OpenAI）呼び出しに関しては、テスト時に差し替えやモックが行えるように設計されています。
- 日付・時間の扱いはルックアヘッドバイアス防止の設計方針に従い、target_date ベースの窓計算やクエリ制約を採用しています。

今後の予定（未実装/TODO）
- position_sizing: 銘柄別 lot_size をマスタから取得する拡張（現在は全銘柄共通）。
- apply_sector_cap: price 欠損時のフォールバックロジック（前日終値や取得原価など）の追加検討。
- research: PBR や 配当利回り等のバリューファクター拡張。
- テストカバレッジの強化（特に OpenAI 周りのリトライ/バリデーションケース）。

--- 
リリースノートはコード内のドキュメント文字列、ログメッセージ、設計注釈から推測して作成しました。必要があれば項目の言い回しや追加情報（例えば実際のリリース日や変更の粒度）を調整します。