# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
この CHANGELOG は与えられたコードベースの内容から推測して作成しています（実際のコミット履歴ではありません）。

すべての注記は日本語です。

## [Unreleased]

- （現状なし）

## [0.1.0] - 2026-04-09

初回リリース（コードベースから推測）。主要機能と実装上の注意点を以下に列挙します。

### 追加 (Added)
- 基本パッケージ情報
  - パッケージメタ情報を追加: `kabusys.__version__ = "0.1.0"`。パッケージの公開初期バージョンを定義。

- 環境変数 / 設定管理 (`src/kabusys/config.py`)
  - .env ファイル（`.env` / `.env.local`）および既存 OS 環境変数からの自動読み込みを実装。
    - プロジェクトルートは `.git` または `pyproject.toml` を基準に自動検出（CWD に依存しない）。
    - 読み込み順は OS 環境変数 > `.env.local` > `.env`。
    - 自動読み込みを無効化するための環境変数: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
    - 読み込み時の既存 OS 環境変数は保護（`.env`/`.env.local` の上書きを制御）。
  - `.env` 行パーサーは `export KEY=val` 形式、クォートとエスケープ、行内コメントの扱いをサポート。
  - 必須環境変数未設定時は `ValueError` を投げる `_require()` を提供。
  - 各種設定プロパティを提供する `Settings` クラス:
    - J-Quants: `JQUANTS_REFRESH_TOKEN`（必須）
    - kabuステーション: `KABU_API_PASSWORD`（必須）、`KABU_API_BASE_URL`（デフォルト: `http://localhost:18080/kabusapi`）
    - LINE: `LINE_CHANNEL_ACCESS_TOKEN`, `LINE_USER_ID`
    - DB パス: `DUCKDB_PATH`（default `data/kabusys.duckdb`）、`SQLITE_PATH`（default `data/monitoring.db`）、Paper Trading 用 `PAPER_TRADING_SQLITE_PATH`
    - Paper Trading 設定: `PAPER_FILL_MODE`（有効値: `"instant"|"partial"|"never"|"reject"`、デフォルト `"instant"`）
    - 監視: PID / kill flag パス、クリア挙動、閾値（CPU/メモリ/ディスク）
    - システム: `KABUSYS_ENV`（`development|paper_trading|live`）、`LOG_LEVEL`（`DEBUG|INFO|WARNING|ERROR|CRITICAL`）および論理プロパティ `is_live` / `is_paper` / `is_dev`
  - 環境値のバリデーション（不正値時は `ValueError`）。

- ポートフォリオ構築 (純粋関数群) (`src/kabusys/portfolio/*`)
  - 候補選定: `select_candidates(buy_signals, max_positions=10)` — スコア降順、同点は `signal_rank` でタイブレーク。
  - 配分重み:
    - 等金額: `calc_equal_weights(candidates)`
    - スコア加重: `calc_score_weights(candidates)`（全スコアが 0 の場合は等配分にフォールバックし WARN ログ）。
  - リスク調整:
    - セクター集中制限: `apply_sector_cap(candidates, sector_map, portfolio_value, current_positions, price_map, max_sector_pct=0.30, sell_codes=None)`（"unknown" セクターは制限対象外）
    - レジーム乗数: `calc_regime_multiplier(regime)` — `bull=1.0`, `neutral=0.7`, `bear=0.3`、未知レジームはフォールバック 1.0（警告ログ）
  - 発注株数計算:
    - `calc_position_sizes(...)` — 以下の方式をサポート:
      - `risk_based`: 許容リスク率 (`risk_pct`) / 損切り率 (`stop_loss_pct`) に基づく株数算出
      - `equal` / `score`: weight（1銘柄比率）に基づく算出
    - 単元株（lot_size、デフォルト 100）丸め、1銘柄上限 (`max_position_pct`)、投下上限（`max_utilization`）の取り扱いを実装。
    - aggregate cap（全銘柄合計コストが利用可能現金を超える場合のスケールダウン）および残差処理（lot 単位での追加配分）。
    - 手数料・スリッページ見積り用 `cost_buffer` をサポート。
    - 価格欠損時はログでスキップ。

- リサーチ（ファクター計算） (`src/kabusys/research/*`)
  - ファクター計算モジュール:
    - Momentum: `calc_momentum(conn, target_date)` — 1M/3M/6M リターン、MA200 乖離（データ不足時は None）
    - Volatility/Liquidity: `calc_volatility(conn, target_date)` — 20日 ATR、相対 ATR、20日平均売買代金、出来高比
    - Value: `calc_value(conn, target_date)` — EPS/ROE を用いた PER/ROE（raw_financials から最新レコードを取得）
  - 研究用ユーティリティ:
    - 将来リターンの計算: `calc_forward_returns(conn, target_date, horizons=[1,5,21])`
    - IC（Spearman のランク相関）: `calc_ic(factor_records, forward_records, factor_col, return_col)`
    - ランク計算: `rank(values)`（同順位は平均ランク）
    - 統計要約: `factor_summary(records, columns)`（count/mean/std/min/max/median）
  - 実装は DuckDB（`prices_daily`, `raw_financials` テーブル）を直接参照。外部 API には依存しない。
  - pandas 等に依存せず標準ライブラリと duckdb SQL で実装。

- AI / LLM 統合 (`src/kabusys/ai/*`)
  - ニュース NLP (`news_nlp.py`)
    - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）の JSON Mode を用いてセンチメントスコア（-1.0〜1.0）を算出。
    - バッチ処理（最大 20 銘柄/コール）、トークン肥大対策（記事数・文字数トリム）、リトライ（429/ネットワーク/5xx で指数バックオフ）を実装。
    - レスポンス検証（JSON 抽出、results 配列、code/score 型チェック、既知コード確認、スコア有限性）を行い、±1.0 でクリップ。
    - 結果を `ai_scores` テーブルへ冪等的に書き込む（対象コードのみ DELETE → INSERT）。部分失敗時にも他コードの既存データを保護する設計。
    - public API: `score_news(conn, target_date, api_key=None)`（`OPENAI_API_KEY` または引数で API キー供給が必要。未設定時は ValueError）
    - 時間ウィンドウ計算: JST ベースの前日 15:00 〜 当日 08:30（内部は UTC naive datetime を返す）を提供する `calc_news_window(target_date)`。
    - フェイルセーフ: API 失敗時はスキップ・ログ出力で継続（例外を上位に投げない設計）。
  - レジーム判定 (`regime_detector.py`)
    - ETF 1321 の MA200 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して `bull|neutral|bear` を日次判定。
    - マクロ記事抽出はタイトルベースのキーワードマッチング（複数キーワードリストを持つ）。
    - スコア合成: clip(0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment, -1,1) で算出。閾値によりラベル化（閾値は定数化）。
    - LLM 呼び出し失敗時は macro_sentiment=0.0 を使う（フェイルセーフ）。
    - DB へ冪等書き込み: `market_regime` テーブルへ BEGIN / DELETE / INSERT / COMMIT。
    - public API: `score_regime(conn, target_date, api_key=None)`（`OPENAI_API_KEY` または引数で API キー供給が必要。未設定時は ValueError）

- 監視ログ永続化層 (`src/kabusys/monitoring/monitoring_db.py`)
  - SQLite を使った監視ログ DB 初期化ユーティリティ: `init_monitoring_db(conn)` を実装。
  - 作成するテーブル（冪等）:
    - system_status（CPU/Memory/Disk 比率等）
    - trade_logs（イベントログ、client_order_id インデックス）
    - positions（保有ポジション）
    - risk_logs（リスクイベント）
    - （スニペット末尾に続きがある想定。コードは途中まで提示されている）

- public API エクスポート
  - `kabusys.portfolio` モジュールで主要関数を __all__ で公開
  - `kabusys.research` で主要ファクター/ユーティリティを公開
  - `kabusys.ai` で `score_news` をエクスポート

### 変更 (Changed)
- 該当なし（初回リリース相当のため）。

### 修正 (Fixed)
- 該当なし（初回リリース相当のため）。

### 既知の制限・注意点 (Notes / Known issues / TODOs)
- .env パーサーの挙動
  - クォートありの値でバックスラッシュエスケープを独自実装している（複雑なケースは注意）。
  - クォートなしのコメント除去は「# の直前がスペースまたはタブの場合」にのみコメントとみなす（意図的な挙動）。
- price 欠損時の扱い
  - sector exposure 計算や position sizing 内で price が 0.0 / 欠損の場合、過少見積りやスキップにつながる旨の TODO コメントあり。将来的に前日終値や取得原価などのフォールバック導入を検討。
- DuckDB / SQLite 互換性
  - DuckDB のバージョン依存（例: executemany の空リストバインド）を考慮した回避策をとっている。DB バージョンによっては挙動差異があり得る。
- LLM 呼び出し
  - news_nlp と regime_detector はそれぞれ独立で OpenAI API 呼び出しを持ち、テスト時は内部関数を patch して差し替える設計。
  - API 使用時は `OPENAI_API_KEY` の提供が必須。失敗時のフォールバックが実装されているが、精度保証はない。
- テスト用フラグ
  - 自動 .env ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能（テストでの isolation を想定）。

### セキュリティ (Security)
- 機密情報 (API キーやパスワード) は環境変数を通じて管理する設計。`.env.local` を使って上書き可能。
- `.env` 自動ロードの既存 OS 環境変数保護機構あり（OS 環境変数を上書かない／保護する）。

---

今後のリリース案（推奨）
- 0.2.0: テスト追加（単体テスト / 統合テスト）、価格フォールバック処理、銘柄別 lot_size サポート、異常系のカバレッジ強化
- 0.3.0: LLM モデル差し替え対応、batching の最適化、monitoring 周りの完全スキーマ公開

（この CHANGELOG はコードのコメント・実装から推測して作成しています。実際の変更履歴と差異がある可能性があります。）