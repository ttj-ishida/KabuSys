# CHANGELOG

すべての重要な変更はこのファイルに記録します。形式は「Keep a Changelog」に準拠しています。

現在日付: 2026-04-09

## [Unreleased]

## [0.1.0] - 2026-04-09
初回リリース。プロジェクトの基本機能・モジュールを実装しました。

### 追加 (Added)
- パッケージ基礎
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - 公開 API を整理して __all__ を設定（data, strategy, execution, monitoring 等のトップレベル想定）。

- 環境変数／設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env 読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。OS 環境変数は保護され、.env の上書き対象外にできる。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト用途）。
  - .env パース機能を強化（export 句対応、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理）。
  - 各種設定プロパティを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, LINE_* 系、DB パス、監視閾値など）。
  - バリデーション実装:
    - PAPER_FILL_MODE の有効値チェック（instant, partial, never, reject）。不正値は ValueError。
    - KABUSYS_ENV の有効値チェック（development, paper_trading, live）。不正値は ValueError。
    - LOG_LEVEL の有効値チェック（DEBUG, INFO, WARNING, ERROR, CRITICAL）。不正値は ValueError。
  - 必須値未設定時に明示的エラーを出す _require() を実装。

- ポートフォリオ構築 (src/kabusys/portfolio/)
  - 銘柄選定・配分計算モジュールを追加。
    - select_candidates: スコア降順で上位 N 件を選定（同点は signal_rank でタイブレーク）。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア比率で配分を計算。全スコアが 0 の場合は等配分にフォールバックし WARNING を出力。
  - リスク調整モジュールを追加。
    - apply_sector_cap: 既存ポジションのセクター露出が閾値を超える場合、新規候補を除外（"unknown" セクターは除外しない）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear、未知はフォールバックと警告）。
  - 株数決定（position sizing）を追加。
    - calc_position_sizes: allocation_method による株数算出（risk_based / equal / score）。
    - 単元株（lot_size）で丸め、1銘柄上限・aggregate cap（available_cash）を適用。
    - cost_buffer を考慮した保守的見積り、スケーリング時の余剰配分ロジックを実装。
    - 価格欠損時のスキップとデバッグログを実装。

- リサーチ（ファクター計算） (src/kabusys/research/)
  - ファクター計算モジュールを追加。
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を計算。データ不足は None を返す。
    - calc_volatility: 20日 ATR、ATR/close、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播を制御。
    - calc_value: raw_financials から直近の財務値を取得し PER / ROE を計算（EPS欠損は None）。
  - 特徴量探索ユーティリティを追加。
    - calc_forward_returns: 指定ホライズンの将来リターンを一括クエリで取得。入力検証あり（horizons の範囲制限）。
    - calc_ic: スピアマンランク相関（IC）を計算。データ不足や分散ゼロ時は None を返す。
    - rank: 同順位は平均ランクで扱うランク化ユーティリティ（浮動小数丸め対策あり）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリーを実装。
  - DuckDB 接続を受け取り SQL と組み合わせて計算する設計（外部 API 不使用）。

- AI 関連 (src/kabusys/ai/)
  - ニュース NLP（score_news）を追加 (news_nlp.py)。
    - raw_news + news_symbols から対象記事を集約し、OpenAI（gpt-4o-mini）で銘柄ごとにセンチメントを算出。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄／呼び出し）、1銘柄あたり記事・文字数上限でトリム。
    - エラー時のエクスポネンシャルバックオフ（429/ネットワーク/タイムアウト/5xx をリトライ）。その他のエラーはスキップ。
    - レスポンス検証を実装（JSON モードの微妙なケース対応、results リスト／型チェック、未知コードは無視、スコアを ±1.0 にクリップ）。
    - 書き込みは期間・コードを限定して DELETE → INSERT（部分失敗時に既存スコアを保護）。DuckDB executemany の空リスト制約に配慮。
    - テスト容易性のため _call_openai_api を分離し patch 可能に。
    - API キー未設定時は明示的 error（ValueError）。
    - ルックアヘッドバイアス防止（日付関係処理で datetime.today()/date.today() を参照しない）。
  - レジーム検出（regime_detector.py）を追加。
    - ETF 1321 の ma200 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で 'bull'/'neutral'/'bear' を判定。
    - raw_news のマクロキーワードによるフィルタ、最大記事件数制限、LLM 評価、スコア合成と閾値判定を実装。
    - API コール失敗時は macro_sentiment=0.0 として継続（フェイルセーフ）。
    - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - _call_openai_api は news_nlp と意図的に別実装（モジュール結合を避ける）。
  - ai パッケージの公開 API として score_news をエクスポート。

- 監視ログ永続化層 (src/kabusys/monitoring/monitoring_db.py)
  - SQLite ベースの監視 DB 初期化関数 init_monitoring_db を追加。system_status / trade_logs / positions / risk_logs 等のテーブルとインデックスを作成（冪等）。

### 変更 (Changed)
- モジュール設計
  - 外部 API 呼び出し箇所（OpenAI）をラップし、テスト時に差し替え可能にして単体テストを容易化。
  - DuckDB 操作は基本的に SQL で完結させ、executemany 周りで互換性問題に配慮した実装に（空配列での executemany を避けるガード）。

### 修正 (Fixed)
- バリデーション強化
  - 複数の設定値（PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL）の不正値検出を追加し、早期に ValueError を返すようにして誤設定の発見を容易に。

- 耐障害性の向上
  - AI モジュールでの API エラーに対してフェイルセーフ（部分失敗時に他データを保護、macro_sentiment のフォールバック 0.0、空レスポンスの扱い）を実装。
  - DB 書込み失敗時に ROLLBACK を試み、ROLLBACK 自体が失敗した場合は警告をログに出力。

### 既知の問題 / 注意点 (Known issues / Notes)
- .env パーサは多くのケースをカバーするが、極端に複雑なシェル式（変数展開やコマンド置換等）はサポートしていません。
- position_sizing の注記: price が欠損（0.0）の場合、エクスポージャーや株数計算が過少見積りとなる可能性があり、将来的にフォールバック価格（前日終値や取得原価）を導入する予定。
- DuckDB / SQLite のバージョン依存の挙動（特に executemany の空リストなど）に対して実行時互換性の配慮を行っていますが、運用環境での事前検証を推奨します。
- OpenAI SDK（将来のバージョン差分）に起因する status_code の有無などに対して保険的な実装（getattr）を行っています。

### 開発メモ
- 単体テスト容易化のため、OpenAI 呼び出し箇所はモジュール内でラップしており unittest.mock.patch による差し替えが可能です。
- 日付処理はルックアヘッドバイアス防止を重視しており、target_date を明示的に受け取る設計になっています。

---
今後の予定（例）
- ファクター正規化・統合パイプラインの追加（zscore_normalize の利用拡張）。
- 単元株数の銘柄別対応（stocks マスタによる lot_size マップ）。
- 監視・運用向けの CLI / サービス化スクリプトの追加。