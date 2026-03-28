# CHANGELOG

すべての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

現在のバージョン: 0.1.0 (初版)

## [Unreleased]

(なし)

## [0.1.0] - 2026-03-28

### Added
- パッケージ初版リリース。モジュール群を実装し公開。
  - パッケージ管理
    - パッケージメタ情報: `kabusys.__version__ = "0.1.0"`、主要サブパッケージを `__all__` で公開。
  - 設定管理
    - `kabusys.config`:
      - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。プロジェクトルートは `.git` または `pyproject.toml` を基準に探索（CWD 非依存）。
      - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
      - `.env` パース機能を強化:
        - `export KEY=val` 形式対応。
        - シングル/ダブルクォートされた値内のバックスラッシュエスケープ対応。
        - クォートなし値のインラインコメント判定（直前がスペース/タブの `#` をコメント扱い）。
      - `.env.local` を優先して上書き（OS 環境変数は保護）。
      - 必須キー取得用ヘルパー `_require()` とアプリ設定ラッパ `Settings` を提供（J-Quants / kabu / Slack / DB パス / 環境種別 / ログレベル等）。
      - `KABUSYS_ENV` / `LOG_LEVEL` の入力検証（許容値チェック）と `is_live`/`is_paper`/`is_dev` の便利プロパティ。
  - AI（自然言語処理）
    - `kabusys.ai.news_nlp`:
      - raw_news と news_symbols を集約して銘柄ごとのニュースを OpenAI（gpt-4o-mini）へバッチ送信し、センチメントスコアを `ai_scores` テーブルへ書き込む `score_news()` を実装。
      - JST ベースのニュースウィンドウ定義（前日 15:00 JST 〜 当日 08:30 JST）を UTC naive datetime で計算する `calc_news_window()` を提供。
      - バッチ処理: 最大 20 銘柄ごとに処理、1銘柄あたり記事数上限（既定 10 件）、文字数トリム（既定 3000 文字）。
      - OpenAI 呼び出しのエクスポネンシャルバックオフ／リトライ（429、接続断、タイムアウト、5xx を対象）。
      - レスポンス検証ロジック（JSON モードのパース耐性、結果スキーマ検査、未知コードの除外、数値チェック、スコア ±1 クリップ）。
      - DuckDB 互換性の考慮（executemany に空リストを渡さない等）。
    - `kabusys.ai.regime_detector`:
      - ETF 1321（Nikkei 225 連動型）200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成し、日次で市場レジーム（`bull` / `neutral` / `bear`）を判定する `score_regime()` を実装。
      - マクロニュース抽出は `news_nlp.calc_news_window` を利用し、マクロキーワードリストでフィルタ。
      - OpenAI 呼び出しのリトライ/フェイルセーフ戦略（失敗時は macro_sentiment=0.0）。
      - レジーム算出後は `market_regime` テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を行う。
      - モジュール間の結合を避けるため、OpenAI 呼び出しは `news_nlp` と別実装。
  - Data（データ基盤）
    - `kabusys.data.calendar_management`:
      - JPX カレンダー管理・営業日判定ロジックを実装。
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day といったユーティリティを提供。
      - calendar_update_job により J-Quants API から差分取得し `market_calendar` に冪等保存（バックフィル、健全性チェック含む）。
      - カレンダーデータが不足する場合の曜日ベースのフォールバック、最大探索日数制限で安全対策。
    - `kabusys.data.pipeline` / `kabusys.data.etl`:
      - ETL パイプラインの基盤を実装。差分更新、J-Quants クライアント経由の保存、品質チェック呼び出しを想定。
      - ETL 実行結果を表す dataclass `ETLResult` を実装し、`to_dict()` による品質問題のシリアライズを提供。
      - 内部ユーティリティ: テーブル存在確認、最大日付取得、トレーディング日調整など。
    - `kabusys.data.__init__` で ETLResult の再エクスポート等の公開インターフェースを準備。
  - Research（リサーチ）
    - `kabusys.research.factor_research`:
      - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（20日 ATR）、バリュー（PER, ROE）等のファクター計算関数 `calc_momentum`, `calc_volatility`, `calc_value` を実装。いずれも DuckDB 上の `prices_daily` / `raw_financials` を参照し副作用なしで結果を返す設計。
      - 計算に使用するスキャン幅やウィンドウ／欠損ハンドリングのポリシーを明確化。
    - `kabusys.research.feature_exploration`:
      - 将来リターン計算 `calc_forward_returns`（horizons の柔軟指定、入力検証）、IC（Spearman ρ）計算 `calc_ic`、値をランクに変換する `rank`、ファクター統計要約 `factor_summary` を実装。
      - pandas 等への依存を避け、標準ライブラリと DuckDB で実装。
    - `kabusys.research.__init__` で主要関数を公開。
  - 互換性とテスト容易性
    - OpenAI 呼び出し箇所は内部関数（`_call_openai_api`）に切り出し、ユニットテストで差し替え（patch）可能に実装。
    - 日付参照について、ルックアヘッドバイアス防止のためモジュール内部で `date.today()` や `datetime.today()` を直接参照しない設計方針を明記（関数呼び出し側から `target_date` を渡す形）。

### Changed
- 初版のため該当なし。

### Fixed
- 初版のため該当なし。

### Deprecated
- 初版のため該当なし。

### Removed
- 初版のため該当なし。

### Security
- OpenAI API キーは引数で注入可能（テスト容易性）かつ環境変数 `OPENAI_API_KEY` を使用。キー未設定時は明示的に ValueError を発生させて misuse を防止。

### Notes / Implementation details
- DuckDB 互換性: executemany に空リストを渡せない制約を考慮し、書き込み前に空チェックを行う実装。
- OpenAI とのやり取りは JSON Mode を想定しつつ、「前後に余計なテキストが混ざった場合でも最外の `{}` を抽出してパースを試みる」など実運用での耐性を高めている。
- マクロキーワードや各種閾値（例: MA 重み、閾値、バッチサイズ、リトライ回数等）はソース中の定数として定義されており、将来的に環境変数や設定に移行する余地あり。

---

今後の予定（非網羅）
- モジュール間のドキュメント整備、API レベルの安定化、設定の外部化（config による細かいチューニング）、CI 用のユニットテスト拡充。