# Changelog

すべての変更は「Keep a Changelog」仕様に準拠しています。  
リリースは SemVer に従います。

## [Unreleased]

## [0.1.0] - 2026-04-09

Added
- 初回リリース。KabuSys のコア機能群を追加。
- パッケージ公開情報
  - パッケージバージョンを `src/kabusys/__init__.py` にて `0.1.0` として定義。
  - `__all__` に主要サブパッケージをエクスポート（data, strategy, execution, monitoring）。
- 環境変数 / 設定管理 (`src/kabusys/config.py`)
  - .env ファイル（`.env` / `.env.local`）および OS 環境変数から設定を自動ロード。
  - 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に探索。ルートが見つからない場合は自動ロードをスキップ。
  - `.env` パーサ実装:
    - 空行・コメント行（#）・`export KEY=val` 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープを考慮したパース。
    - クォートなしの場合はインラインコメントを適切に除外。
  - 自動ロードの無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート（テスト等で使用）。
  - 必須キー取得ユーティリティ `_require` を実装（未設定時は ValueError）。
  - 各種設定プロパティを提供（J-Quants、kabu API、LINE、DBパス、監視閾値、システム環境等）。
  - 入力検証:
    - PAPER_FILL_MODE の有効値チェック（instant/partial/never/reject）。
    - KABUSYS_ENV の有効値チェック（development/paper_trading/live）。
    - LOG_LEVEL の有効値チェック。
- ポートフォリオ構築 (`src/kabusys/portfolio/*`)
  - 候補選定・重み計算 (`portfolio_builder.py`)
    - select_candidates: score 降順、同点は signal_rank 昇順で上位 N 件を選択。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア比率による加重配分。全銘柄スコアが 0 の場合は等配分へフォールバックし WARNING を出力。
  - セクター制約・レジーム乗数 (`risk_adjustment.py`)
    - apply_sector_cap: 既存保有のセクター比率が閾値を超える場合、新規候補の同セクター銘柄を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知レジームは 1.0 でフォールバック（警告ログ）。
  - 株数決定・資金配分 (`position_sizing.py`)
    - risk_based / equal / score の割当方式を実装。
    - 単元（lot_size）丸め、1 銘柄最大割合、cost_buffer による保守的なコスト見積り。
    - aggregate cap を超える場合はスケールダウンし、小数端数は lot_size 単位で残差順に再配分するロジックを実装。
- 研究・ファクター計算 (`src/kabusys/research/*`)
  - ファクター計算 (`factor_research.py`)
    - モメンタム: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）。DuckDB の Window 関数で実装。データ不足時は None を返す。
    - ボラティリティ/流動性: 20日 ATR、ATR 相対値、20日平均売買代金、出来高比率。true_range の NULL 伝播を厳密に扱う。
    - バリュー: raw_financials から直近財務データを取得し PER/ROE を計算（EPS が 0/欠損時は PER=None）。
    - 全関数は DuckDB 接続を受け取り prices_daily / raw_financials を参照する純粋関数。
  - 特徴量探索 (`feature_exploration.py`)
    - 将来リターン: calc_forward_returns にて任意ホライズン（デフォルト [1,5,21]）の将来リターンを一括 SQL で取得。horizons の検証あり。
    - IC（Information Coefficient）計算: calc_ic により Spearman の順位相関を実装。同順位は平均ランク、丸めによる ties 対策あり。有効レコードが 3 未満なら None。
    - 基本統計量集計: factor_summary にて count/mean/std/min/max/median を算出。
  - research パッケージの public API を __init__ でエクスポート（zscore_normalize を含む）。
- AI 関連 (`src/kabusys/ai/*`)
  - ニュース NLP（銘柄ごとのセンチメント） (`news_nlp.py`)
    - raw_news と news_symbols を用いてターゲットウィンドウ（前日 15:00 JST ～ 当日 08:30 JST 相当の UTC 範囲）で記事を収集・銘柄別に集約。
    - 記事トリム（最大記事数・文字数）を行い、最大 20 銘柄ずつ OpenAI（gpt-4o-mini）へバッチ送信。
    - API 呼び出しに対して 429・接続エラー・タイムアウト・5xx を対象に指数バックオフでリトライ。その他のエラーはスキップ。
    - レスポンスのバリデーションとスコアのクリップ（±1.0）。JSON mode を扱い、余計な前後テキストが混入した場合の復元を試みる。
    - 成功スコアのみ ai_scores テーブルに対して冪等的（DELETE → INSERT）に書き込み。部分失敗でも既存のスコアを残す設計。
    - OpenAI クライアント呼び出し部分はテスト差し替えしやすいように分離。
  - 市場レジーム判定 (`regime_detector.py`)
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）の合成でレジーム（bull/neutral/bear）判定。
    - prices_daily は target_date 未満のデータのみを利用してルックアヘッドを防止。データ不足時は中立（ma200_ratio=1.0）でフォールバック。
    - マクロニュースはキーワード検索で抽出、LLM 呼び出しは失敗時に 0.0 としてフォールバック（フェイルセーフ）。
    - 判定結果を market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
  - ai パッケージは score_news を公開。
- 監視データ永続化 (`src/kabusys/monitoring/monitoring_db.py`)
  - SQLite 接続を受け取り監視用テーブル群（system_status, trade_logs, positions, risk_logs ...）とインデックスを冪等的に作成する init_monitoring_db を実装（スキーマ作成ロジックを含む）。

Changed
- N/A（初回リリースのため過去バージョンからの変更点はなし）。

Fixed
- N/A（初回リリースのため過去バージョン不具合修正はなし）。

Security
- 環境変数の自動ロードでは OS 環境変数を保護する仕組み（読み込み時の protected set）を実装し、.env.local による上書きを制御。

Notes / Caveats
- DuckDB / SQLite への executemany に関する互換性注意点（空リストを許容しないバージョンへの対策）を考慮して実装されている箇所がある（news_nlp）。
- 一部関数（例: apply_sector_cap 内の price が欠損した場合の挙動）に TODO コメントが残っており、今後の改善余地がある。
- OpenAI API を利用する機能は API キーの設定が必須（引数または OPENAI_API_KEY 環境変数）。失敗時は安全なフォールバック処理を行う設計。

--- 

（備考）上記はソースコード内の実装・コメントから推測してまとめた CHANGELOG です。リリース日・バージョンは現在のコード状態に基づき記載しています。