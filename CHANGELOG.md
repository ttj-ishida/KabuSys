# Changelog

すべての注目すべき変更を記録します。フォーマットは Keep a Changelog に準拠します。  
現在のバージョンは 0.1.0 です。

## [0.1.0] - 2026-03-28

### Added
- パッケージの初期リリース: KabuSys (バージョン 0.1.0)
  - Python パッケージエントリポイントを定義（src/kabusys/__init__.py）。
  - バージョン情報: __version__ = "0.1.0"。

- 環境設定 / ロード機能（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定値を読み込む自動ロード機構を実装。
  - プロジェクトルート検出: .git または pyproject.toml を起点に自動的にルートを探索（CWD 非依存）。
  - .env のパースは以下に対応:
    - 空行・コメント行（#）のスキップ
    - export KEY=val 形式の対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォートなしでのインラインコメント取り扱い（直前がスペース/タブ時）
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。OS 環境変数は保護（上書き禁止）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを提供し、必須変数の取得（_require）や検証を行う:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須として取得
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH にデフォルトを設定
    - KABUSYS_ENV（development / paper_trading / live）、LOG_LEVEL の妥当性検査
    - is_live / is_paper / is_dev の便利プロパティ

- AI モジュール（src/kabusys/ai）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約して銘柄ごとにニューステキストを作成
    - OpenAI（gpt-4o-mini）を JSON Mode で呼び出し、銘柄ごとのセンチメントスコア（-1.0〜1.0）を取得
    - チャンク（デフォルト最大 20 銘柄）単位でバッチ送信（トークン肥大化対策: 最大記事数/文字数でトリム）
    - リトライ戦略: 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフで再試行
    - レスポンス検証機能を実装（JSON 抽出、results キー、コードとスコアの型チェック、既知コードのみ採用、スコアのクリップ）
    - 書き込みは部分原子性を考慮: スコア取得に成功したコードのみ DELETE → INSERT（DuckDB の executemany 制約を考慮）
    - ルックアヘッドバイアス回避: target_date を明示的に渡す設計（datetime.today() を内部で参照しない）
    - テスト容易性: _call_openai_api を patch で差し替え可能
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム判定（bull / neutral / bear）
    - prices_daily / raw_news を参照し、calc_news_window を用いたウィンドウでニュースを抽出
    - OpenAI 呼び出し（gpt-4o-mini）で macro_sentiment を取得、API エラー時は 0.0 にフォールバック（フェイルセーフ）
    - レジームスコア合成式、閾値によるラベリングを実装
    - DB 書き込みは冪等: BEGIN / DELETE WHERE date = ? / INSERT / COMMIT。失敗時は ROLLBACK を試行し例外を上位へ伝播
    - テスト容易性: news_nlp とは独立した _call_openai_api 実装（モジュール結合を低く保つ）

- Research モジュール（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算（データ不足時は None）
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率を計算（データ不足時は None）
    - calc_value: raw_financials から直近財務を取得し PER / ROE を計算（EPS = 0 または欠損時は None）
    - DuckDB を用いた SQL + Python 実装、外部 API に依存しない設計
  - 特徴量解析（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 指定 horizon（営業日単位）に対する将来リターンをまとめて取得（可変 horizon、検証あり）
    - calc_ic: スピアマンランク相関（Information Coefficient）を実装（欠損や ties を考慮）
    - rank: 同順位は平均ランクで処理（丸めで ties 検出の安定化）
    - factor_summary: count/mean/std/min/max/median の計算（None を除外）
  - research パッケージの再エクスポート（__init__.py）で主要関数を公開

- Data モジュール（src/kabusys/data）
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day の提供
    - market_calendar テーブル優先だが未登録日や NULL は曜日ベース（週末）でフォールバックする一貫したロジック
    - next/prev は最大探索日数制限を設け無限ループ防止
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等保存（バックフィル、健全性チェックを実装）
  - ETL パイプライン（src/kabusys/data/pipeline.py）
    - ETLResult dataclass を実装（取得件数・保存件数・品質問題・エラーの集約）
    - 差分取得、保存、品質チェックの設計方針を反映したユーティリティ（J-Quants クライアントとの連携を想定）
    - 一部ユーティリティ関数（テーブル存在確認、最大日付取得等）を実装
  - etl モジュールで ETLResult を再エクスポート（src/kabusys/data/etl.py）
  - jquants_client と quality モジュールとの連携箇所を想定（外部 API クライアントは別実装）

- 共通設計上の配慮
  - DuckDB を主要な分析データベースとして使用する前提で SQL を最適化
  - ルックアヘッドバイアス防止: target_date を明示的に受け取り、date 未満 / 排他条件を徹底
  - DB 書き込みは冪等性・部分成功保護を重視（DELETE→INSERT のパターンや個別 executemany）
  - OpenAI 呼び出しは冪長（リトライ・バックオフ・500 系とそれ以外の扱いを区別）で堅牢化
  - テストしやすさを考慮し、API 呼び出し関数は差し替え可能（patchable）に実装

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 環境変数読み込みにおいて OS 環境変数は保護（.env による上書きをデフォルトで行わない）する仕様を導入

### Notes / Limitations
- OpenAI API キーが必要:
  - score_news / score_regime は api_key 引数または環境変数 OPENAI_API_KEY を必要とする。未設定時は ValueError を送出。
- LLM 依存部分は外部サービスに左右されるため、API 失敗時は安全側のフォールバック（スコア 0.0 やスキップ）を行う設計になっている。
- DuckDB バージョン特有の挙動（executemany の空リスト不可など）を考慮した実装になっている。
- 現フェーズでは PBR・配当利回りなど一部バリューファクターは未実装。

---

今後のリリースでは、ドキュメントの拡充、テストスイートの追加、J-Quants / kabu API クライアントの具体実装、運用監視（monitoring）・実行（execution）パッケージの実装拡張などを予定しています。