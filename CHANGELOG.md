# Changelog

すべての注目すべき変更を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

現在のバージョン: 0.1.0 — 初回リリース

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-09

### 追加
- 全体
  - 初回リリース。パッケージメタ情報を src/kabusys/__init__.py にてバージョン "0.1.0" として定義。

- 設定 / 環境変数管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数からの設定読み込みを実装。プロジェクトルートは .git / pyproject.toml を基準に自動検出し、CWD に依存しない方式で読み込む。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により無効化可能。
  - .env パースの堅牢化:
    - コメント、export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメントの扱いなどを考慮。
  - 環境変数アクセス用 Settings クラスを提供（settings インスタンスをエクスポート）。以下の主要キーを扱う:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID
    - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH（パスは expanduser で解決）
    - PAPER_FILL_MODE（instant/partial/never/reject のバリデーション）
    - PID / KILL フラグパス、KILL_FLAG_CLEAR_ON_START フラグ
    - CPU / メモリ / ディスク閾値（数値変換）
    - KABUSYS_ENV（development / paper_trading / live のバリデーション）および LOG_LEVEL の検証
    - is_live / is_paper / is_dev ヘルパー

- ポートフォリオ構築（src/kabusys/portfolio/*）
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順、同点は signal_rank の小さい方を優先して上位 N を選択。
    - calc_equal_weights: 等金額配分（1/N）を計算。
    - calc_score_weights: スコア比率に基づく配分。全銘柄のスコアが 0 の場合は等金額配分へフォールバックし WARNING を出力。
  - risk_adjustment:
    - apply_sector_cap: 既存保有のセクター比率が閾値を超える場合、そのセクターの新規候補を除外（"unknown" セクターは対象外）。当日売却予定銘柄を除外して計算可能。
    - calc_regime_multiplier: 市場レジーム ('bull'/'neutral'/'bear') に応じた投下資金乗数を返す（フォールバックや警告あり）。
  - position_sizing:
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に対応した株数決定ロジックを実装。
      - risk_based: 許容リスク率、損切り率に基づく計算（単元丸め、1銘柄上限などを考慮）。
      - equal/score: 重み・ポートフォリオ価値・max_utilization、lot_size に基づく株数算出。
      - aggregate cap 処理: 合計コストが利用可能現金を超える場合にスケールダウンし、端数は lot_size 単位で残差に基づき再配分。
      - cost_buffer によりスリッページ・手数料を保守的に見積もる。

- リサーチ / ファクター計算（src/kabusys/research/*）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターンおよび MA200 乖離を DuckDB 上で計算。必要行数が不足する場合は None を返す。
    - calc_volatility: 20日 ATR（true range を適切に扱う）/ 相対 ATR / 20日平均売買代金 / 出来高比率を計算。
    - calc_value: raw_financials から直近財務データを取得し PER / ROE を計算（EPS 欠損や 0 の取り扱いあり）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズンの将来リターンをまとめて DuckDB クエリで取得（入力検証あり）。
    - calc_ic: スピアマンのランク相関（IC）を純 Python で計算（None/不足データの除外、3 件未満で None）。
    - rank: 同順位は平均ランク化（浮動小数点誤差対策に round(v, 12) を利用）。
    - factor_summary: count/mean/std/min/max/median を計算する軽量集計ユーティリティ。
  - research パッケージは zscore_normalize（kabusys.data.stats）を再エクスポート。

- AI（OpenAI）関連（src/kabusys/ai/*）
  - news_nlp:
    - score_news: raw_news + news_symbols から銘柄単位で記事を集約し、OpenAI (gpt-4o-mini) を JSON Mode で呼び出して銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込む。
    - 特徴:
      - ニュースウィンドウ計算（JST を UTC に変換、ルックアヘッドバイアスを避ける設計）。
      - 1銘柄あたり記事数と文字数上限でトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
      - 最大バッチサイズ: 20 銘柄／API 呼び出し。
      - 429/ネットワーク/タイムアウト/5xx を対象とした指数バックオフリトライ実装（最大試行回数制御）。
      - レスポンスの堅牢なバリデーション（JSON 抽出、results リスト、各要素の code/score 検証、スコアのクリップ）。
      - DuckDB への書き込みは部分消去（該当 code の DELETE）→ INSERT の冪等パターン。DuckDB executemany の空パラメータ制約を回避。
      - API キー未設定時は ValueError を送出。
  - regime_detector:
    - score_regime: ETF 1321 の MA200 乖離（70%）とマクロニュースの LLM センチメント（30%）を合成して日次レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出はキーワードベースでタイトルを取得、最大件数制限あり。LLM 呼び出しの失敗時は macro_sentiment を 0.0 にフォールバック（フェイルセーフ）。
    - LLM 呼び出しは JSON Mode を利用し、リトライロジック・ステータスコードに応じた扱いを実装。
    - API キー未設定時は ValueError を送出。

- 監視ログ永続化（src/kabusys/monitoring/monitoring_db.py）
  - init_monitoring_db: SQLite 接続に対して 5 テーブルと関連インデックスを冪等作成するスクリプトを提供（system_status, trade_logs, positions, risk_logs など。インデックス含む）。

### 変更
- 該当なし（初回リリース）

### 修正（既知の安全性・堅牢化）
- 環境変数・.env のパースロジックを強化し、クォート内エスケープや export 形式、インラインコメントの扱いなどに対応。これにより .env の柔軟な記述に対応。
- AI モジュールではレスポンスパース失敗／API エラー時に例外を許容せずフォールバックやログ出力で継続する設計とし、部分失敗時の DB 保護（該当コードのみ書き換え）を導入。
- DuckDB クエリはルックアヘッドバイアス対策（target_date 未満／指定範囲の厳格な使用）を考慮。

### 既知の制約 / 注意点
- news_nlp / regime_detector は OpenAI API（gpt-4o-mini）の JSON Mode を利用するため、実行環境で API キー（OPENAI_API_KEY）または明示的な api_key 引数が必要。未設定時は ValueError を返す。
- calc_position_sizes の lot_size は現状全銘柄共通（デフォルト 100）。将来的に銘柄別単元対応が TODO として残る。
- apply_sector_cap の価格欠損（price_map が 0.0）を考慮していない箇所に TODO コメントあり（過少見積りの可能性）。
- DuckDB executemany は空リストを受け付けない点を考慮した実装を行っている（互換性対策）。
- 一部ファイル・機能は設計ドキュメント（PortfolioConstruction.md, StrategyModel.md など）に依存する旨のコメントがあるが、ドキュメント自体は本パッケージに含まれていない可能性あり。

### セキュリティ
- OpenAI API キーは引数または環境変数で供給する方式。キー未設定時には明示的にエラーを出すことで誤動作を防止。
- .env 自動ロードは明示的に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

---

（この CHANGELOG はコードベースの内容から推測して作成しています。実際の変更履歴やドキュメントと差異がある場合はそちらを優先してください。）