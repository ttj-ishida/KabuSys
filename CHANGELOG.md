# Changelog

すべての注目すべき変更点を記録します。本ファイルは Keep a Changelog 準拠の形式で記載しています。

フォーマット:
- Unreleased — 次回リリース用の未リリース変更
- 各リリースは日付付きで記載

## [Unreleased]
- （現在未リリースの変更はありません）

## [0.1.0] - 2026-04-09
初期リリース。

### 追加 (Added)
- パッケージ全体
  - 基本モジュール構成を追加（kabusys パッケージ）。
  - __version__ = "0.1.0" を設定。

- 環境変数 / 設定管理 (src/kabusys/config.py)
  - .env / .env.local の自動読み込み機能を実装。
    - プロジェクトルートは .git または pyproject.toml を起点に探索（CWD に依存しない）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env のパースは export プレフィックス・クォート・コメント処理・エスケープに対応。
    - OS 環境変数を保護するため既存キーを protected として扱う。
  - Settings クラスを追加し、アプリケーション設定をプロパティ経由で取得可能に。
    - J-Quants / kabu API / LINE / DB パス / Paper Trading / 監視設定 / システム設定等のプロパティを提供。
    - 必須環境変数未設定時は _require が ValueError を送出する（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
    - KABUSYS_ENV のバリデーション（development/paper_trading/live）。
    - LOG_LEVEL のバリデーション（DEBUG/INFO/WARNING/ERROR/CRITICAL）。

- ポートフォリオ構築 (src/kabusys/portfolio/)
  - portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で選出（同点は signal_rank でブレーク）。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア加重配分を計算。全スコアが 0 の場合は等配分へフォールバック（WARNING ログ）。
  - risk_adjustment.py
    - apply_sector_cap: 既存保有比率に基づくセクター集中上限チェック（unknown セクターは制限対象外）。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull=1.0／neutral=0.7／bear=0.3、未知はフォールバック1.0）。
  - position_sizing.py
    - calc_position_sizes: 指定方式に基づき発注株数を算出（allocation_method: risk_based, equal, score）。
    - risk_based: risk_pct, stop_loss_pct から株数算定。lot_size 単位で丸め。
    - equal/score: weight と max_utilization 等を考慮して配分。
    - aggregate cap: available_cash を超える場合はスケーリングし、lot_size 単位で残差を再配分（再現性のため安定ソート）。
    - cost_buffer による手数料・スリッページの保守的見積り。
    - 将来的な拡張点として銘柄別 lot_size を想定する TODO を記載。

  - package エクスポートを追加（kabusys.portfolio: select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier）。

- リサーチ / ファクター計算 (src/kabusys/research/)
  - factor_research.py
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離を DuckDB クエリで計算。必要データ不足時は None を返す設計。
    - calc_volatility: 20日 ATR、ATR 比率、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播を適切に制御。
    - calc_value: raw_financials から最新財務データを取得し PER・ROE を計算（EPS 欠損/0 の場合は None）。
  - feature_exploration.py
    - calc_forward_returns: 指定ホライズン先の将来リターンを一括クエリで取得。horizons の検証あり。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。十分な有効レコードが無い場合は None。
    - rank: 同順位は平均ランクを与える安定ランク関数（丸めによる ties 漏れ対策）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリ。
  - research パッケージは zscore_normalize を kabusys.data.stats から再エクスポート。

  - 設計方針として DuckDB 接続を受け取り、外部ライブラリ（pandas 等）に依存せず純粋関数として実装。

- AI / ニュース NLP (src/kabusys/ai/)
  - news_nlp.py
    - raw_news テーブルからニュースを銘柄別に集約し、OpenAI（gpt-4o-mini）で銘柄ごとにセンチメント（-1.0〜1.0）を算出して ai_scores テーブルへ書き込む機能を実装。
    - 設計・実装の特徴:
      - タイムウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）を calc_news_window で計算し、UTC として比較。
      - 1チャンクで最大 _BATCH_SIZE（20）銘柄を API に送信。1銘柄あたり最大記事数/文字数でトリム。
      - OpenAI クライアントは OpenAI(api_key=...) を使用。デフォルトモデルは gpt-4o-mini。
      - レート制限（429）、ネットワーク断、タイムアウト、5xx を対象に指数バックオフでリトライ（最大回数設定あり）。
      - JSON Mode を前提としたレスポンス検証処理（前後余分なテキストが混入する場合の補正ロジック含む）。
      - スコアは ±1.0 にクリップ。
      - DuckDB への書き込みは部分失敗に備え、対象コードを限定して DELETE → INSERT を実行（executemany を使用。DuckDB 0.10 の制約を考慮）。
      - API キー未設定時は ValueError を送出。
      - テスト容易性: _call_openai_api をパッチ差替え可能。
  - regime_detector.py
    - ETF 1321 の ma200 乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ書き込む機能を実装。
    - 設計・実装の特徴:
      - ルックアヘッドバイアス防止: prices_daily クエリは date < target_date を使用。
      - マクロニュースはキーワードでフィルタ（複数キーワード、ILIKE）。
      - LLM 呼び出しは失敗時に macro_sentiment=0.0 でフォールバック（フェイルセーフ）。
      - レジーム出力は -1.0〜1.0 の regime_score を clip し、閾値で label を決定（閾値は定数化）。
      - API キー未設定時は ValueError を送出。
      - テスト容易性: _call_openai_api をパッチ差替え可能、_score_macro は sleep 関数の差替えを受け入れる設計。

  - ai パッケージは score_news を外部にエクスポート（kabusys.ai.score_news）。

- 監視データベース (src/kabusys/monitoring/monitoring_db.py)
  - SQLite ベースの監視ログ永続化層を実装。
  - init_monitoring_db 関数で以下のテーブル（およびインデックス）を冪等に作成:
    - system_status（CPU/メモリ/ディスク/プロセス状態）
    - trade_logs（発注・約定ログ）
    - positions（保有ポジション）
    - risk_logs（※ファイル末尾の続き実装あり）
  - ビジネスロジックを持たない純粋な読み書き層として設計。

### 変更 (Changed)
- 初版のため該当なし。

### 修正 (Fixed)
- 初版のため該当なし。

### 既知の制約・注意点 (Known issues / Notes)
- .env 読み込み:
  - .env ファイルから読み込む際、クォート内のバックスラッシュエスケープに対応しているが、複雑なシェル展開（$(...) 等）はサポートしない。
- apply_sector_cap:
  - price_map に 0.0（欠損）を与えた場合、エクスポージャーが過少見積もられブロックが外れる可能性がある旨を TODO コメントで指摘。将来的にフォールバック価格の導入を検討。
- position_sizing:
  - lot_size は現状グローバル共通。将来的に銘柄別 lot_size を受け取る拡張を想定（TODO）。
- research:
  - DuckDB を使う設計で、テーブル名（prices_daily, raw_financials 等）に依存。スキーマ・データ準備が必要。
- AI 系:
  - OpenAI SDK のレスポンス仕様変化やステータスコードの扱いに対して耐性を持つように実装されているが、将来 SDK の大幅変更が入ると影響を受ける可能性がある。
  - API 呼び出しは外部ネットワークを使用するため実行環境での API キー管理に注意が必要。

### セキュリティ (Security)
- 初版のため該当なし。

---

備考:
- 各モジュールの docstring に動作方針や設計上の注意点が記載されています。実運用前に .env の設定、DuckDB / SQLite の初期データ準備、OpenAI API キーの管理を行ってください。