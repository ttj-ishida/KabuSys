# Changelog

すべての注目すべき変更を記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

現在のバージョンは [0.1.0] です — 2026-04-09

## [Unreleased]
（今後の変更をここに記載します）

---

## [0.1.0] - 2026-04-09

初期リリース。以下の主要機能と実装上の振る舞い、注意点を含みます。

### Added
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = "0.1.0"）と主要サブパッケージのエクスポート宣言。
- 環境変数 / 設定管理（src/kabusys/config.py）
  - .env および .env.local の自動ロード（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により無効化可能。
  - .env パーサーは以下に対応：
    - コメント行（#）・空行を無視
    - export KEY=val 形式のサポート
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォート無しの値でインラインコメントを適切に無視（`#` の直前が空白・タブの場合にコメント扱い）
  - 読み込み時の上書き（override）ロジックと、既存 OS 環境変数を保護する `protected` セット機構。
  - Settings クラスを提供（settings = Settings()）:
    - 必須/任意の環境変数取得メソッド（必須未設定時は ValueError を送出）
    - デフォルト値、検証（例: KABUSYS_ENV の有効値チェック、LOG_LEVEL の検証）
    - パス系設定は Path に変換して expanduser() を適用（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH など）
    - Paper Trading 用 fill_mode のバリデーション（instant/partial/never/reject）
    - CPU/MEM/DISK 閾値や PID/KILL フラグ制御等の監視設定を提供
    - 状態判定プロパティ: is_live / is_paper / is_dev

- ポートフォリオ構築（src/kabusys/portfolio/*）
  - portfolio_builder:
    - select_candidates: スコア降順、同点は signal_rank 昇順でタイブレーク。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア比率で配分。全スコアが 0 の場合は等金額にフォールバック（WARNING ログ）。
  - risk_adjustment:
    - apply_sector_cap: 既存保有のセクター比率が max_sector_pct を超える場合、当該セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数（デフォルトマップ: bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 でフォールバック（WARNING ログ）。
  - position_sizing:
    - calc_position_sizes: 各銘柄の発注株数算出ロジックを実装（allocation_method: "risk_based" | "equal" | "score"）。
    - risk_based: 許容リスク率（risk_pct）と stop_loss_pct からベース株数を算出し、単元株（lot_size）で丸め。
    - equal/score: weight と price を使って per-position 上限や aggregate cap を考慮した株数算出。
    - aggregate cap が available_cash を超える場合、スケールダウンと残差分の lot 単位での再配分を実施（端数処理と再現性を考慮）。
    - cost_buffer により手数料・スリッページを保守的に見積もり判定に反映。
    - price が取得できない場合はスキップしてログ出力。

- リサーチ / ファクター計算（src/kabusys/research/*）
  - factor_research:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を DuckDB の prices_daily テーブルから算出。MA200 未満のウィンドウでは ma200_dev を None。
    - calc_volatility: 20日 ATR（atr_20）・atr_pct・20日平均売買代金・出来高比率（volume_ratio）を算出。必要行数未満なら None を返す。
    - calc_value: raw_financials テーブルから target_date 以前の最新財務データを取得し、PER（EPS 有効時）と ROE を算出。
  - feature_exploration:
    - calc_forward_returns: target_date から指定ホライズン（デフォルト [1,5,21]）までの将来リターンを一括 SQL で取得。horizons の検証（1..252）を実施。
    - calc_ic: Spearman ランク相関（IC）を実装。有効レコードが 3 件未満なら None。
    - rank: 同順位は平均ランクを割り当てる実装（ties 検出のため値を round(v,12) で丸めて比較）。
    - factor_summary: count/mean/std/min/max/median を算出（None 値は除外）。

- AI / NLP（src/kabusys/ai/*）
  - news_nlp:
    - score_news: raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）で銘柄ごとにセンチメントを評価して ai_scores テーブルへ書き込み。
    - ニュース収集ウィンドウ: target_date の前日 15:00 JST 〜 当日 08:30 JST（内部的に UTC naive datetime で変換）。
    - バッチ処理: 最大 _BATCH_SIZE（20）銘柄を一括で送信。1銘柄あたり記事数・文字数をトリムする制御あり（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - API 呼び出しの堅牢性: 429 / ネットワーク切断 / タイムアウト / 5xx を対象に指数バックオフでリトライ。その他のエラーはスキップ。
    - レスポンスのバリデーション（JSON モードでの前後ノイズ除去、results キーの存在確認、score の数値変換、未知 code の無視）。
    - スコアは ±1.0 にクリップ。部分成功時の DB 書き込みは対象コードのみ DELETE → INSERT を行い他コードの既存スコアを保護。
    - API キーは引数 api_key または環境変数 OPENAI_API_KEY から解決。未設定だと ValueError。
    - テスト容易性のため _call_openai_api は差し替え可能（モック）。
  - regime_detector:
    - score_regime: ETF 1321（日経225 連動 ETF）の MA200 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - マクロニュースは title を _MACRO_KEYWORDS でフィルタし最大記事数で取得。記事がない場合は macro_sentiment=0.0（フォールバック）。
    - レジームスコア合成式とクリッピング、閾値に基づくラベリングを実装。DB 書き込みは BEGIN/DELETE/INSERT/COMMIT。API キー解決は news_nlp と同様。
    - API 呼び出しの堅牢性・フォールバック挙動を実装。内部で news_nlp の _call_openai_api を直接参照せず独立した実装を持つ（モジュール分離）。
- モニタリング DB（src/kabusys/monitoring/monitoring_db.py）
  - init_monitoring_db: SQLite 用の監視ログ永続化層のテーブル群（system_status, trade_logs, positions, risk_logs など）とインデックス作成を冪等に実行する関数を追加。

### Changed
- （初期リリースのため該当なし）

### Fixed
- .env パーサーおよび OpenAI レスポンスパースにおける実用的なケース（引用符内エスケープ、JSON 前後ノイズ）への耐性を強化。
- DuckDB バインド時の空 params に関する互換性対応（executemany 前に空でないことを確認）。

### Security
- OpenAI API キーは引数か環境変数から明示的に供給させる仕様。未設定時は例外を投げ処理を止めることで意図しない無条件送信を防止。

### Notes / Limitations
- 一部処理は「安全側のフォールバック」を採用（例: データ不足時の ma200_ratio=1.0、API失敗時の macro_sentiment=0.0）。これはフェイルセーフを目的とする設計決定。
- price が欠損（0.0）の場合、apply_sector_cap や position sizing のエクスポージャー算出で過少見積もりとなり得る旨を TODO コメントで記載。将来的には前日終値等のフォールバックを導入予定。
- datetime の取扱いは明示的に UTC naive な構成を用いており、JST ↔ UTC の変換を処理内で行っている（ルックアヘッドバイアス防止のため date.today()/datetime.today() を使用しない設計）。
- OpenAI 呼び出しは gpt-4o-mini と JSON Mode を期待した実装だが、将来の SDK 変更やモデル仕様変更により適宜調整が必要。
- テスト時に OpenAI 呼び出しを差し替え可能な設計（_call_openai_api のモック）を採用している。

---

参考: 詳細な実装は各モジュールの docstring / 関数コメントに記載されています。必要ならばモジュール別の変更履歴（より細かな実装ノート）も作成します。