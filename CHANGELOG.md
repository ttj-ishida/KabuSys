# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。

## [Unreleased]

## [0.1.0] - 2026-04-09
初回リリース。

### 追加
- パッケージ基盤
  - パッケージバージョンを設定（kabusys.__version__ = "0.1.0"）し、主要サブパッケージをエクスポートする初期構成を導入。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルートは __file__ を起点に `.git` または `pyproject.toml` から検出（配布後も動作するよう CWD に依存しない設計）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パーサはコメント、export プレフィックス、クォート（シングル／ダブル）とバックスラッシュエスケープ、インラインコメントの扱いなどに対応。
    - .env ファイル読み込み時の I/O エラーは警告として処理。
    - OS 環境変数を保護する protected 機構を実装。
  - Settings クラスを追加し、アプリケーション設定値をプロパティ経由で取得可能に。
    - J-Quants / kabuステーション / LINE / DB（DuckDB/SQLite） / 監視設定 / システム設定など主要設定を扱う。
    - 必須キー未設定時は _require() により ValueError を送出（利用者に .env.example を提示するメッセージ）。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）や KABUSYS_ENV と LOG_LEVEL の許容値チェックを実装。
    - パス設定は expanduser() 対応。

- ポートフォリオ構築 (kabusys.portfolio)
  - 銘柄選定と重み計算の純粋関数群を追加。
    - select_candidates: score 降順、同点は signal_rank の昇順で上位 N 件を選択。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア比率で正規化。全銘柄スコアが 0 の場合は等金額配分にフォールバックし警告を出力。
  - リスク調整ルーチンを追加。
    - apply_sector_cap: 既存ポジションのセクター時価総額を集計し、1セクター上限 (max_sector_pct) を超過するセクターの新規候補を除外。unknown セクターは除外対象外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull:1.0, neutral:0.7, bear:0.3）。未知レジームは警告ログを出して 1.0 でフォールバック。
  - ポジションサイジングを追加。
    - calc_position_sizes: allocation_method("risk_based" / "equal" / "score") に応じて発注株数を算出。
      - risk_based: 許容リスク率 (risk_pct) と損切り幅 (stop_loss_pct) から目標株数を算出し、単元 (lot_size) に丸める。
      - equal/score: 重みに基づいて per-position 上限や aggregate cap を考慮して計算。
      - aggregate cap を超える場合はスケールダウンし、端数は lot_size 単位で分配するアルゴリズムを実装。
      - cost_buffer による保守的なコスト見積り（スリッページ・手数料の見積り）を考慮。
      - 価格欠損 (None/<=0) はスキップし、ログ出力で通知。
      - 将来拡張（銘柄別 lot_size 等）を見据えた TODO コメントあり。

- リサーチ / ファクター計算 (kabusys.research)
  - ファクター計算モジュールを追加（DuckDB 接続受け取り、prices_daily / raw_financials を参照）。
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率（MA200）の算出。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率を算出。true_range の NULL 伝播を注意深く扱う実装。
    - calc_value: raw_financials の最新財務データと当日株価から PER / ROE を計算（EPS が 0 または欠損時は PER を None）。
  - 特徴量探索ユーティリティを追加。
    - calc_forward_returns: 各ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD を使って一括取得。horizons の検証あり。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。有効レコードが 3 未満の場合は None。
    - rank: 同順位は平均ランクとして扱う。浮動小数誤差対策のため round(..., 12) で丸めて比較。
    - factor_summary: count/mean/std/min/max/median を計算。None は除外。
  - research パッケージは zscore_normalize を kabusys.data.stats から再エクスポート。

- AI / ニュース NLP (kabusys.ai)
  - ニュースセンチメント評価 (news_nlp.score_news)
    - raw_news と news_symbols を集約して銘柄ごとに記事を連結・トリムし、OpenAI (gpt-4o-mini) にバッチ送信して銘柄別スコアを取得。
    - リトライ戦略: 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ。その他のエラーはスキップ。
    - レスポンスの厳密なバリデーション実装（JSON 抽出、results リスト、code/score の型チェック、既知コードのみ採用、数値性・有限性チェック）。
    - スコアは ±1.0 にクリップ。
    - 書き込みは部分失敗を考慮して対象コードのみ DELETE → INSERT（トランザクション、DuckDB executemany の空リスト制約に配慮）。
    - API キー解決: api_key 引数または環境変数 OPENAI_API_KEY。未設定時は ValueError を送出。
    - calc_news_window により JST ベースのニュース収集ウィンドウを UTC naive datetime で算出（前日 15:00 JST ～ 当日 08:30 JST）。
    - テスト用に _call_openai_api の差し替え（patch）を想定。
  - 市場レジーム判定 (ai.regime_detector.score_regime)
    - ETF 1321（日経連動 ETF）の直近 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム ('bull'/'neutral'/'bear') を判定。
    - マクロニュース抽出はキーワードベース（複数キーワード）でタイトルを取得し、LLM でセンチメント評価。
    - レジームスコア合成: clip(0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment, -1,1)、閾値によりラベル判定。
    - API 失敗時は macro_sentiment=0.0 でフォールバック（フェイルセーフ）。
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実装。
    - API キー解決は news_nlp と同様で、未設定時は ValueError。
    - news_nlp._call_openai_api とは別実装で、モジュール間のプライベート関数共有を避ける設計。

- 監視ログ永続化 (kabusys.monitoring.monitoring_db)
  - SQLite を用いた監視ログ層を追加。
    - init_monitoring_db により system_status / trade_logs / positions / risk_logs などのテーブルとインデックスを作成（冪等）。
    - （ファイル途中で切れているが、監視用永続化テーブル群を用意していることが明記されている。）

### 既知の制約・注意点
- OpenAI API の呼び出し部分は外部サービスに依存しており、API キー未設定時は ValueError を送出する（フェイルセーフとしては API 呼び出し失敗時にスコアを 0.0 とする挙動を導入している箇所がある）。
- .env の自動ロードはプロジェクトルートが検出できない場合にスキップされる。パッケージ配布後やテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD による制御を推奨。
- DuckDB / SQLite に関する互換性や executemany の振る舞い（空リスト）に注意して実装している。特に DuckDB バージョン差異に伴う挙動に配慮している。
- 位置決め・サイズ計算では lot_size を全銘柄共通とした設計になっている（将来的な拡張ポイントとして銘柄別 lot_map の導入を想定）。
- 一部の関数（例: apply_sector_cap）では価格欠損時にエクスポージャーが過少見積になる可能性がある旨が TODO として記載されている。

### 将来の改善案（コードコメント等に記載）
- position_sizing: 銘柄別単元情報（lot_size）のサポート。
- apply_sector_cap: 価格欠損時のフォールバック（前日終値や取得原価など）導入。
- ニュース / LLM 呼び出し回りのロギング・メトリクスの強化や再試行ポリシーの細分化。

---

今後のリリースではバグ修正、性能改善、外部サービスへの依存低減（ローカルフェールバック等）、および銘柄別設定の拡張を予定しています。