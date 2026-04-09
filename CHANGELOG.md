# CHANGELOG

すべての重要な変更履歴はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

## [Unreleased]

## [0.1.0] - 2026-04-09
初期リリース。日本株自動売買システムのコアユーティリティ群を実装しました。以下の主要機能を含みます。

### 追加
- パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。
  - パッケージ公開用の top-level エクスポート（data, strategy, execution, monitoring）を定義。

- 環境変数 / 設定管理 (kabusys.config)
  - プロジェクトルート自動検出機能を実装（.git または pyproject.toml を基準）。
  - .env/.env.local ファイルの自動読み込み機能（読み込み順序: OS 環境変数 > .env.local > .env）。
  - .env パーサを実装（export プレフィックス対応、クォート・エスケープ対応、インラインコメント処理など）。
  - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加（テスト用途など）。
  - Settings クラスを追加し、アプリケーションで利用する設定プロパティを提供:
    - J-Quants / kabuステーション / LINE API 関連（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, LINE_CHANNEL_ACCESS_TOKEN 等）
    - DB パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）
    - Paper Trading の設定（PAPER_FILL_MODE の検証とデフォルト "instant"）
    - 監視用パス/フラグ（PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START）
    - リソース閾値（CPU/MEMORY/DISK の閾値を float として取得）
    - 実行環境およびログレベル検証（KABUSYS_ENV: development/paper_trading/live、LOG_LEVEL の有効値検査）
    - ユーティリティプロパティ（is_live/is_paper/is_dev）

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順、同点は signal_rank 昇順でソートして上位 N を選択。
    - calc_equal_weights: 等金額配分の重みを計算。
    - calc_score_weights: スコア比率に基づく配分。全銘柄スコアが 0 の場合は等金額配分にフォールバックして WARNING ログを出力。
  - risk_adjustment:
    - apply_sector_cap: 既存ポジションのセクター別エクスポージャーに基づき、新規候補をセクター上限(max_sector_pct)で除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに基づく投下資金乗数（bull:1.0, neutral:0.7, bear:0.3）。未知レジーム時は 1.0 にフォールバックして WARNING ログを出力。
  - position_sizing:
    - calc_position_sizes: 発注株数計算（allocation_method: "risk_based" / "equal" / "score" をサポート）。
      - risk_based: 許容リスク率 (risk_pct) と損切り率 (stop_loss_pct) から算出。
      - equal/score: 重みと価格から各銘柄の目標株数を算出。
      - lot_size（単元）で丸め、ポジション上限(max_position_pct) と aggregate cap（利用可能現金）を考慮してスケールダウン。
      - cost_buffer による手数料・スリッページ保守見積りを採用。
      - aggregate スケールダウン後、端数分配を残差の大きい順に lot 単位で追加配分するロジックを実装。
      - price 欠損時はスキップする安全策を実装。
      - 将来的な拡張（銘柄別 lot_size）に関する TODO コメントを追加。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research:
    - calc_momentum: mom_1m/3m/6m と 200 日移動平均乖離率(ma200_dev) を DuckDB SQL で算出。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR / ATR 比率、20 日平均売買代金、出来高比などを算出。NULL 伝播やカウント条件に配慮。
    - calc_value: raw_financials から直近財務データを取得して PER, ROE を算出（EPS 欠損時に PER を None）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン先の将来リターンを一括クエリで取得（horizons の検証あり）。
    - calc_ic: Spearman ランク相関（IC）を実装。データ不足や非有限値へ堅牢。
    - rank: 同順位は平均ランクを与えるランク付けユーティリティ（丸めで ties 検出の安定化）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー関数。
  - research.__init__ に zscore_normalize（kabusys.data.stats から）と上記関数をエクスポート。

- AI（kabusys.ai）
  - news_nlp:
    - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）で銘柄別センチメントを評価し、ai_scores テーブルへ書き込み。
    - ニュースウィンドウ計算（JST に基づき前日 15:00 ～ 当日 08:30 を UTC に変換）を提供（calc_news_window）。
    - バッチ処理（最大 20 銘柄/回）、記事トリム（最大記事数・最大文字数）を実装。
    - OpenAI 呼び出しラッパー、レスポンスバリデーション、スコアの ±1.0 クリップ、429/ネットワーク/5xx に対する指数バックオフリトライ。
    - DuckDB への書き込みは冪等性を考慮（対象コードだけ DELETE → INSERT）し、部分失敗時に既存スコアを保護。
    - API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出。
    - フェイルセーフ設計: API/パース失敗時は該当チャンクをスキップして処理継続。
  - regime_detector:
    - ETF 1321 の 200 日移動平均乖離（ma200_ratio）とマクロニュースの LLM センチメントを合成して日次でレジーム判定（'bull'/'neutral'/'bear'）を行い、market_regime テーブルへ書き込み。
    - マクロニュースはタイトルをキーワードでフィルタして取得（キーワードリストを内部定義）。
    - マクロセンチメントが取得できない場合は 0.0 をフォールバックする設計（フェイルセーフ）。
    - OpenAI 呼び出しは独立実装（news_nlp の内部関数と共有しない）で、API のリトライ/エラー処理を実装。
    - API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError。

- 監視用 DB（kabusys.monitoring.monitoring_db）
  - init_monitoring_db: SQLite 接続に対して冪等で以下テーブル・インデックスを作成するスクリプトを実装:
    - system_status（CPU/MEM/Disk 等のサンプリング）
    - trade_logs（発注 / 約定ログ）
    - positions（現在ポジション）
    - risk_logs（リスクイベント） ほか（スクリプトは複数テーブル・インデックスを作成）

### 変更
- （初期リリースのため変更履歴なし）

### 修正
- （初期リリースのため修正履歴なし）

### セキュリティ
- OpenAI API キーは明示的に引数で渡すか環境変数 OPENAI_API_KEY を参照する設計とし、未設定時は例外を投げて明示的に扱うようにしています（安全な失敗モード）。

### 既知の制限 / TODO
- position_sizing: 将来的に銘柄別の lot_size をサポートする拡張予定（現状は全銘柄共通の lot_size 引数）。
- apply_sector_cap: price_map に 0.0（欠損）がある場合、エクスポージャーが過小評価される可能性がある旨の注記。将来的にフォールバック価格の導入を検討。
- DuckDB に対する executemany の空リストバインドの互換性考慮のため、空チェックを行っている（DuckDB バージョン差異への互換措置）。
- news_nlp / regime_detector は外部 API（OpenAI）に依存するため、ネットワーク/料金等の運用上の考慮が必要。

---

もしリリースノートの粒度（ファイル別の詳細やログ出力のサンプル、将来のマイルストーン等）をさらに細かくしたい場合は、目的に応じて追記します。