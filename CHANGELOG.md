# Changelog

すべての重要な変更は Keep a Changelog の方針に従って記載します。  
日付はコードベースから推測可能な最新のリリース日として記載しています。

## [Unreleased]

- 現時点で未リリースの変更はありません。

## [0.1.0] - 2026-04-09

初回リリース。以下の主要機能・モジュールを含みます。

### 追加 (Added)

- 基本メタ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 環境設定 / ロード機能 (src/kabusys/config.py)
  - プロジェクトルート（.git または pyproject.toml）を起点に .env / .env.local を自動読み込みする機能を追加。CWD に依存せず動作。
  - .env 行パーサを実装（コメント、export プレフィックス、クォートとエスケープ、インラインコメントの扱いに対応）。
  - .env 読み込み時の上書き制御（override 引数）および OS 環境変数保護（protected）をサポート。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - 必須環境変数取得用ヘルパ `_require()` を実装（未設定時は ValueError を投げる）。
  - 各種設定プロパティを提供（J-Quants / kabuステーション / LINE / DB パス / Paper Trading 設定 / 監視閾値 / 環境・ログレベル検証等）。`PAPER_FILL_MODE` や `KABUSYS_ENV`、`LOG_LEVEL` のバリデーション実装。

- ポートフォリオ構築 (src/kabusys/portfolio)
  - 銘柄選定・重み計算（pure functions）
    - select_candidates: buy シグナルをスコア降順／タイブレークでソートして上位 N 件選択。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア加重配分を計算。全銘柄スコアが 0 の場合は等配分にフォールバックして WARNING を出力。
  - リスク調整（セクター上限・レジーム乗数）
    - apply_sector_cap: 既存保有のセクター別エクスポージャーを計算し、上限超過セクターの候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime（'bull'/'neutral'/'bear'）に応じた投下資金乗数を返す。未知レジームは 1.0 にフォールバック（WARNING）。
  - ポジションサイジング
    - calc_position_sizes: risk_based / equal / score の割当方式をサポートし、単元株（lot_size）で丸めた発注株数を算出。各種制約（per-stock 上限、aggregate cap、cost_buffer）を実装。利用可能現金を超える場合のスケーリングと残差処理（lot 単位での再配分）を行う。

- リサーチ / ファクター計算 (src/kabusys/research)
  - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率の計算（DuckDB の prices_daily を使用）。
  - calc_volatility: 20日 ATR、ATR 比率、20日平均売買代金、出来高変化率を計算。
  - calc_value: raw_financials と prices_daily を結合して PER / ROE を計算（最新財務レコードの取得ロジックを含む）。
  - calc_forward_returns: 指定ホライズンの将来リターンを一括で取得（SQL で LEAD を利用）。
  - calc_ic, rank, factor_summary: IC（スピアマンのランク相関）計算、ランク付けユーティリティ、統計サマリーを標準ライブラリのみで実装。小規模データや ties を考慮した実装。

- AI（LLM）連携 (src/kabusys/ai)
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約し、銘柄ごとに記事をトリムして OpenAI（gpt-4o-mini）へバッチ送信しセンチメント（ai_score）を ai_scores テーブルへ書き込む。
    - バッチサイズ、最大記事数/文字数制限、JSON レスポンス検証、±1.0 クリップ、部分的書き込み（DELETE→INSERT で対象コードのみに対して行い、部分失敗で既存データを残す）を実装。
    - API 呼び出しは 429 / 接続断 / タイムアウト / 5xx を対象に指数バックオフでリトライ。その他エラーはフェイルセーフによりスキップ。
    - テスト用に _call_openai_api をモック可能。
    - 日時ウィンドウ計算（JST→UTC 変換）のユーティリティを提供（ルックアヘッドバイアス回避のため datetime.today() を参照しない設計）。
  - レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の ma200 乖離（70%）とマクロニュースの LLM センチメント（30%）を合成して日次で regime_label を判定し market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出、LLM 呼び出し、スコア合成、閾値判定、DB トランザクション制御（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - API 失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。

- 監視ログ永続化 (src/kabusys/monitoring/monitoring_db.py)
  - SQLite を用いた MonitoringDB 初期化関数を実装（冪等で複数テーブルとインデックスを作成）。（system_status, trade_logs, positions, risk_logs 等のテーブル定義を含む）

- パッケージ公開インターフェース
  - kabusys パッケージの __all__ 定義および各サブモジュールの __all__ 整備により主要関数を外部公開。

### 修正 / 防御的実装 (Fixed / Hardening)

- .env パーサやファイル読み込みでの堅牢性向上
  - クォート内のバックスラッシュエスケープ処理や export プレフィックス対応、スペース付きのインラインコメント判定などを実装。
  - .env 読み込みでファイルオープン失敗時に warnings.warn を出して処理を継続。

- データ欠損時の安全策
  - ファクター計算やポジションサイズ計算でデータ欠損（価格・ATR 等）を検出した際にスキップし、過度に失敗しないようログ出力のうえ安全にフォールバックする実装を追加。
  - calc_score_weights は全スコアが 0 の場合に等配分へフォールバックして警告を出す。

- AI コール周りの堅牢化
  - レスポンスの JSON パース失敗時に「外側の {} を抽出して再パース」する復元処理を実装。
  - レスポンス形式のバリデーション（results キーの存在、要素の型、code の正規化、score の数値変換と有限性チェック）を行い、妥当性がない場合は対象を無視して継続。
  - executemany に空リストを渡せない DuckDB の制約に対応して、空チェックをしてから executemany を呼ぶ実装。

### 既知の制約 / 注意点

- settings の一部プロパティは必須（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。未設定時は ValueError を送出するため、実行前に .env または環境変数を用意する必要があります。
- position_sizing の lot_size は現状グローバル固定（デフォルト 100）。将来的に銘柄別 lot_map での拡張を想定している旨の TODO コメントあり。
- apply_sector_cap は price_map に 0.0 を与えた銘柄があるとエクスポージャーを過少見積りする可能性がある旨の注記あり（将来的にフォールバック価格を検討）。
- Regime 判定のしきい値や重みはコード内定数で定義されている（必要に応じて調整が可能）。

### 破壊的変更 (Breaking Changes)

- 初回リリースのため破壊的変更はありません。

### セキュリティ (Security)

- OpenAI API キーは引数か環境変数 OPENAI_API_KEY で供給する設計。コード内に直接キーを埋め込まない運用を想定。
- .env 自動読み込みは無効化できる（KABUSYS_DISABLE_AUTO_ENV_LOAD）のでテスト環境でのキー漏洩リスク緩和が可能。

---

（注）本 CHANGELOG は与えられたコード内容から実装意図・挙動を推測して作成しています。実際のコミット履歴や追加の変更（ドキュメント、テスト、CI 設定等）がある場合は適宜追記してください。