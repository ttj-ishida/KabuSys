# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。  
主にコードベース（src/kabusys 以下）の機能追加・設計意図・注意点をコード内容から推測してまとめた初回リリース記録です。

なお日付は本 CHANGELOG 作成日（YYYY-MM-DD）で記載しています。

## [Unreleased]

## [0.1.0] - 2026-04-09

### Added
- 全体
  - パッケージ初期バージョンを追加。パッケージメタ情報は `kabusys.__version__ = "0.1.0"` に設定。
  - モジュール公開 API を `__all__` で整理（portfolio、research、ai など主要サブパッケージをエクスポート）。

- 環境設定 / 設定管理 (`kabusys.config`)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルートは `__file__` を起点に `.git` または `pyproject.toml` を探索して特定（CWD 非依存）。
    - 読み込み優先順位は OS 環境変数 > .env.local > .env。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト向け）。
  - `.env` パーサ実装（クォート・エスケープ・inline コメント等を考慮した堅牢なパース）。
  - Settings クラスを提供し、アプリケーションで使用する設定値をプロパティとして取得可能に：
    - J-Quants / kabuステーション / LINE / DB パス / Paper Trading 周り / 監視閾値 / ログレベル等の設定プロパティを追加。
    - 必須環境変数が未設定の場合は `_require` により `ValueError` を送出する（明示的なエラーを早期発見）。
    - `PAPER_FILL_MODE`, `KABUSYS_ENV`, `LOG_LEVEL` 等に対する入力検証と有効値チェックを実装。

- ポートフォリオ構築 (`kabusys.portfolio`)
  - 銘柄選定・重み計算（pure functions）
    - `select_candidates`: BUY シグナルをスコア降順、同点時は signal_rank でタイブレークして上位 N 件を選択。
    - `calc_equal_weights`: 等金額配分を計算。
    - `calc_score_weights`: スコア正規化による加重配分。全銘柄スコアが 0 の場合は等分配へフォールバック（WARNING ログ）。
  - リスク調整
    - `apply_sector_cap`: 既存ポジションのセクター露出を算出し、同一セクターの新規候補を上限超過時に除外（"unknown" セクターは制限しない）。
    - `calc_regime_multiplier`: market regime（bull/neutral/bear）に基づく投下資金乗数を返す（未知レジームは 1.0 でフォールバック、警告ログ）。
  - ポジションサイズ計算
    - `calc_position_sizes`: allocation_method（"risk_based" / "equal" / "score"）に応じて株数を算出。ロット丸め、1銘柄上限、aggregate cap（available_cash）を考慮。
    - risk_based 方式では許容リスク率（risk_pct）と損切り率（stop_loss_pct）から株数を計算。
    - aggregate cap 超過時はスケールダウンし、端数処理で残余キャッシュを使って lot_size 単位で再配分するアルゴリズムを実装。
    - `cost_buffer` により手数料・スリッページを保守的に見積もって判定に反映。

- リサーチ / ファクター計算 (`kabusys.research`)
  - ファクター計算モジュール（DuckDB 接続を受け取り、prices_daily / raw_financials テーブルのみを参照）
    - `calc_momentum`: 1M/3M/6M リターン、200 日移動平均乖離（MA200）を計算。データ不足時は None を返す。
    - `calc_volatility`: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率を計算。true_range の NULL 伝播制御に配慮。
    - `calc_value`: raw_financials の最新財務（target_date 以前）と当日の株価を組み合わせて PER / ROE を算出（EPS=0 の場合は None）。
  - 特徴量探索・統計 (`kabusys.research.feature_exploration`)
    - `calc_forward_returns`: 複数ホライズン（デフォルト 1,5,21 営業日）の将来リターンを一括 SQL で取得。ホライズン入力検証あり。
    - `calc_ic`: ファクターと将来リターンのスピアマンランク相関（IC）を計算。有効レコード < 3 の場合は None。
    - `rank`: 同順位は平均ランクで処理（浮動小数丸めで ties 検出誤差を軽減）。
    - `factor_summary`: count/mean/std/min/max/median を計算する統計サマリ。

  - 設計方針: research モジュールは外部 API に依存せず DuckDB クエリ + 標準ライブラリで完結する設計。

- AI / ニュース NLP (`kabusys.ai`)
  - ニュースセンチメントスコアリング（OpenAI を使用）
    - `score_news`: raw_news と news_symbols を集約して銘柄ごとのテキストを OpenAI（gpt-4o-mini, JSON Mode）に送信し、ai_scores テーブルへ書き込み。
    - タイムウィンドウ計算 (`calc_news_window`) は JST ベースの固定ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を UTC に変換して使用。ルックアヘッドバイアスを避けるため内部で date.today() を参照しない設計。
    - バッチ処理（最大 20 銘柄 / API コール）とチャンク単位での再試行（429・ネットワーク断・タイムアウト・5xx を指数バックオフでリトライ）。
    - レスポンスの堅牢なバリデーション（JSON パース耐性、results 構造確認、未知銘柄無視、スコア数値変換、±1.0 にクリップ）。
    - DB 書き込みは部分置換（対象コードのみ DELETE → INSERT）で冪等かつ部分失敗時に既存データを保護。DuckDB executemany の制約を考慮して空パラメータは送らない。
    - テスト容易化のため API 呼び出し関数を切り出し（モック可能）。

  - 市場レジーム判定 (`kabusys.ai.regime_detector`)
    - `score_regime`: ETF 1321 の MA200 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で regime（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出はキーワードベースのタイトル検索（複数キーワード、最大取得数制限）。
    - API 失敗時は macro_sentiment=0.0 でフォールバック（フェイルセーフ）。
    - LLM 呼び出し実装は news_nlp と分離（モジュール間で private 関数を共有しない設計）。
    - ルックアヘッドバイアス対策として prices_daily クエリで date < target_date のみ使用。

- 監視 / Monitoring DB (`kabusys.monitoring.monitoring_db`)
  - SQLite ベースの監視ログ永続化層を実装（ビジネスロジックを持たない読み書き層）。
  - `init_monitoring_db` により以下のテーブルとインデックスを冪等的に作成：
    - system_status（CPU/メモリ/ディスク/プロセス状態）
    - trade_logs（発注・約定ログ）
    - positions（保有銘柄）
    - risk_logs（リスクイベントログ） …など（テーブル定義の一部を実装済み。ファイルは途中までの定義を含む）

### Fixed
- なし（初回リリースとして新規実装が中心。コード上にはフォールバックや堅牢化の実装多数）。

### Changed
- なし（初回リリース）。

### Deprecated
- なし。

### Removed
- なし。

### Security
- 環境変数読み込みは OS 環境を上書きしない既定動作を採用し、上書き時は OS 環境変数セットを protected として扱う実装を導入。自動ロードの無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。
- 各種 API キーは明示的に引数または環境変数で要求し、未設定時は `ValueError` を発生させ安全性を確保（OpenAI API キー等）。

---

Notes / Known limitations（コードから明示されている注意点）
- research モジュールは DuckDB のテーブル（prices_daily / raw_financials 等）に依存する。外部データ取得・前処理は別途用意する必要あり。
- news_nlp / regime_detector は OpenAI API に依存するため API 利用料およびキー管理が必要。API エラー時はフェイルセーフにより処理継続されるが、結果は空または中立値にフォールバックされる。
- position_sizing の lot_size は現状全銘柄共通（将来は銘柄毎に拡張可能）。price が欠損（0.0）の場合は一部処理がスキップされる旨の TODO が存在。
- monitoring_db のファイルは途中までの定義が含まれており、完全なスキーマはリポジトリ内の続き実装に依存。

以上がコードベースから推測して作成した CHANGELOG（初回リリース）です。必要であれば、各項目をさらに細分化したり、実装ファイルごとの変更点一覧（関数単位）に展開します。