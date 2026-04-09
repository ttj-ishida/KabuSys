# Changelog

すべての注目する変更をここに記録します。フォーマットは「Keep a Changelog」に準拠します。

現在のバージョン: 0.1.0 — 2026-04-09

---

## [0.1.0] - 2026-04-09

### 追加
- 全体
  - プロジェクト初期リリース。パッケージ名: kabusys、バージョン `0.1.0` を導入。
  - パッケージエクスポートの整理（kabusys.__init__ の __all__ に主要サブパッケージを追加）。

- 設定 / 環境変数管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機能を実装（プロジェクトルートは .git または pyproject.toml を探索して検出）。
  - .env パーサは以下をサポート:
    - コメント行（#）、空行を無視。
    - `export KEY=val` 形式のサポート。
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - インラインコメント判定（クォート外・前がスペース/タブの '#' をコメントと扱う）。
  - 自動ロードの挙動:
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - 既存 OS 環境変数を保護するため protected set を使用して上書きを制御。
  - 設定プロパティ（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）、パス系は Path に変換して expanduser を適用。
  - 一部の設定値は検証を実施（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL など）。無効値は ValueError を送出。

- ポートフォリオ構築（src/kabusys/portfolio/*）
  - portfolio_builder:
    - select_candidates: buy シグナルをスコア降順（同点は signal_rank 昇順）でソートし上位 N を返す。
    - calc_equal_weights: 等金額配分の重みを計算。
    - calc_score_weights: スコア比率で重みを計算。全銘柄スコアが 0 の場合は等金額にフォールバックし WARNING を出力。
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限をチェックし、超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime（'bull'/'neutral'/'bear'）に応じた投下資金乗数を返す。未知レジームは Warn を出して 1.0 にフォールバック。
  - position_sizing:
    - calc_position_sizes: 各銘柄の発注株数を計算（allocation_method: "risk_based" / "equal" / "score" をサポート）。
    - リスクベースの株数算出、単元株（lot_size）で丸め、1銘柄上限（max_position_pct）、投下資金上限（available_cash）に対する aggregate スケールダウンロジックを実装。
    - cost_buffer を用いた約定コストの保守的見積り、スケールダウン後の端数処理で残余キャッシュを再配分するアルゴリズムを導入。
    - lot_size は将来的な拡張を見据えて引数化（現在は共通単元を想定）。

- リサーチ / ファクター計算（src/kabusys/research/*）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を DuckDB の prices_daily を用いて計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務データを取得し PER・ROE を計算（EPS が 0/欠損のとき PER は None）。
    - 全関数は DuckDB 接続を受け取り、DB のテーブルのみ参照する純粋関数群として実装。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括 SQL で取得。
    - calc_ic: スピアマンランク相関（IC）の計算（ランク同着は平均ランク）。有効レコード < 3 の場合は None を返す。
    - rank, factor_summary: ランク付けユーティリティ・ファクター統計サマリー（count/mean/std/min/max/median）。
    - 外部ライブラリに依存せず標準ライブラリと DuckDB のみで実装。

- AI 関連（src/kabusys/ai/*）
  - news_nlp:
    - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）にバッチ送信し、銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込む処理を実装。
    - バッチサイズ、記事数/文字数上限、スコアの ±1.0 クリップ、429/ネットワーク/5xx に対する指数バックオフリトライを実装。
    - レスポンスの厳密なバリデーション（JSON 抽出、results 配列、code と score、既知コードフィルタ、数値チェック）。失敗時は該当チャンクをスキップして継続（フェイルセーフ）。
    - 書き込みは部分失敗に備え、対象 code のみ DELETE → INSERT で置換（DuckDB executemany の制約を考慮）。
  - regime_detector:
    - ETF 1321 の ma200 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し日次でレジーム（bull/neutral/bear）を判定して market_regime テーブルへ冪等書き込みを行う。
    - マクロニュースはタイトルをキーワードでフィルタ、最大件数・API 呼び出しは記事がある場合のみ実行。API 失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - LLM 呼び出しは内部で独立した実装（news_nlp と内部実装を共有しない設計）。

- 監視ログ永続化（src/kabusys/monitoring/monitoring_db.py）
  - SQLite を用いた監視用 DB 初期化処理を実装（system_status, trade_logs, positions, risk_logs などのテーブルとインデックスを作成する SQL スクリプト。注: ファイル末尾が部分表示だが基本的なテーブル作成ロジックを実装）。

### 変更
- （初回リリースのため過去からの変更履歴は無し）

### 修正
- （初回リリースのため過去からの修正履歴は無し）

### 既知の制限・設計上の注意（ドキュメント / TODO）
- risk_adjustment.apply_sector_cap:
  - price_map に price が欠損（0.0）の場合、エクスポージャーが過少見積りされる可能性があり、将来的に前日終値や取得原価でのフォールバックを検討する旨の TODO コメントあり。
- position_sizing:
  - 将来的に銘柄別 lot_size（単元）をサポートする設計を想定しているが、現状は全銘柄共通の単元を前提。
- AI モジュール:
  - OpenAI API に依存するため、API キーが無い場合は明確に ValueError を投げる実装。API の失敗は「部分的にスコア取得しない」・「macro_sentiment を 0 にフォールバック」等のフェイルセーフで対処するが、運用時は API 呼び出しの可用性に留意すること。
- 環境変数ロード:
  - プロジェクトルート検出に失敗した場合は自動 .env ロードをスキップするため、配布後は明示的に環境変数を設定する必要がある場合がある。

### セキュリティ
- .env の自動ロードはデフォルトで有効。ただし KABUSYS_DISABLE_AUTO_ENV_LOAD によって無効化可能。既存 OS 環境変数は保護して上書きされない設計。

---

今後のリリース候補（例）
- .env パーサの追加テストケース強化（複雑なエスケープ/ネストケース）
- position_sizing の銘柄別 lot_size 対応
- apply_sector_cap の価格フォールバック実装
- AI 呼び出しのモック容易化のためのインターフェース抽出（テストカバレッジ向上）
- monitoring_db の完全実装レビュー（現在ソース末尾が断片的に表示）

---

（注）本 CHANGELOG は提供されたコードベースの内容から推測して作成しています。リリースノートの正確な言い回しや日付はリポジトリ管理者の運用方針に合わせて調整してください。