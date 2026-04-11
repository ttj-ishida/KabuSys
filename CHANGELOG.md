# CHANGELOG

すべての重要な変更は Keep a Changelog の慣例に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/

## [Unreleased]
- (今後の変更をここに記載)

## [0.1.0] - 2026-04-11
初期リリース。自動売買システム "KabuSys" のコア機能群を追加。

### 追加 (Added)
- 基本パッケージ情報
  - パッケージバージョンを src/kabusys/__init__.py にて `__version__ = "0.1.0"` として定義。

- 設定管理 (src/kabusys/config.py)
  - .env 自動読み込み機能を実装（プロジェクトルートの検出: .git / pyproject.toml を起点）。
  - .env のパース機能を強化:
    - `export KEY=val` 形式対応、クォート（シングル/ダブル）内のエスケープ処理、インラインコメント取り扱いなどに対応。
    - override / protected（OS 環境変数の保護）オプションをサポート。
  - 環境設定を扱う Settings クラスを実装し、よく使う設定をプロパティで提供（DB パス、API トークン、PID/kill フラグパス、閾値など）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードの無効化が可能。
  - 環境変数の検証を強化（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE などで不正値時に ValueError を送出）。

- 実行・監視の起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動のためのエントリポイントを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite DB を使用し、本番 DB と分離する（デフォルト: data/paper_trading.db）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/Reconciler/RiskManager を組み立て、ExecutionEngine を起動するワークフローを実装。
    - 起動時にプロセス優先度を "high" に設定。
    - DuckDB 接続を受けて分析用データにアクセス。
    - 監視テーブルの存在を保証するため init_monitoring_db を冪等に呼び出す。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計（監視データは本番 DB を参照）。

- プロセス管理ユーティリティ (src/kabusys/utils/process_priority.py)
  - クロスプラットフォームでプロセス優先度設定 (Windows の HIGH_PRIORITY_CLASS 等、POSIX の nice 値) を実装。
  - CPU affinity 設定関数 set_cpu_affinity を追加。
  - 権限不足や未対応プラットフォーム時は警告を出して安全にスキップするフォールバック実装。

- ポートフォリオ構築 (src/kabusys/portfolio/*)
  - ポートフォリオ候補選定と重み計算:
    - select_candidates: スコア降順 + signal_rank によるタイブレークで候補選定。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を提供。スコア全てが 0 の場合は等金額へフォールバックして WARNING 出力。
  - リスク調整:
    - apply_sector_cap: セクター集中上限を適用して候補をフィルタリング（"unknown" セクターは除外しない挙動）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を提供（bull/neutral/bear のマッピング、未知レジームは 1.0 でフォールバック）。
  - 株数決定・単元丸め (position_sizing.calc_position_sizes):
    - allocation_method = "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）単位で丸め、per-position 上限、aggregate cap（可用現金によるスケーリング）、cost_buffer を考慮した保守的見積り。
    - 利用可能現金を超える場合はスケールダウンし、残差処理で lot 単位の追加配分を行う再現性あるアルゴリズムを実装。

- 研究・ファクター計算 (src/kabusys/research/*)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離の計算（DuckDB SQL ベース）。
    - calc_volatility: 20 日 ATR、相対 ATR、平均出来高、出来高比率の計算。
    - calc_value: raw_financials から最新財務を取得して PER / ROE を計算。
    - いずれも DuckDB 接続を受け、prices_daily/raw_financials テーブルのみ参照する設計。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズンの将来リターンを一括クエリで取得（horizons バリデーションあり）。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装（ties は平均ランクで処理、レコード不足時は None を返す）。
    - factor_summary / rank: 基本統計量とランク変換ユーティリティを提供。
  - いずれも外部ライブラリ（pandas 等）に依存しない純粋 Python + DuckDB 実装。

- AI 関連 (src/kabusys/ai/*)
  - news_nlp:
    - raw_news / news_symbols を集約して OpenAI (gpt-4o-mini) へ送信し、銘柄別センチメント ai_score を ai_scores テーブルへ書き込む機能を実装。
    - バッチ処理（最大 20 銘柄/回）、1 銘柄あたりの記事数・文字数上限でトークン肥大化対策を導入。
    - エラーハンドリング: 429 / ネットワーク断 / タイムアウト / 5xx を対象とした指数バックオフリトライ、その他エラーはスキップ。
    - レスポンス検証ロジックを実装（JSON 抽出、results キー存在確認、コード検証、スコア数値化、±1.0 にクリップ）。
    - DuckDB への書き込みは部分失敗時に既存スコアを消さないよう、対象コードを限定して DELETE→INSERT を実行（トランザクション・ロールバック対応）。
    - タイムウィンドウ計算は target_date ベースで固定（ルックアヘッドバイアス防止）。
  - regime_detector:
    - ETF 1321 の 200 日 MA 乖離 (重み70%) とマクロニュースの LLM センチメント (重み30%) を合成して日次レジーム判定（'bull'/'neutral'/'bear'）を行う機能を実装。
    - prices_daily は target_date 未満のデータのみを使用（ルックアヘッド防止）。
    - API 失敗時は macro_sentiment=0.0 で継続するフェイルセーフ実装。
    - 判定結果を market_regime テーブルへ冪等に書き込む。

- DuckDB を分析エンジンとして採用
  - 各種計算モジュール・AI モジュール・研究機能は DuckDB 接続を受けて SQL を実行する設計。

### 変更 (Changed)
- なし（初期リリース） — ただし各モジュール内で設計方針・ログ出力を明記。

### 修正 (Fixed)
- DB 書き込み・トランザクション周りの堅牢化:
  - ai_scores 書き込みで部分失敗時に他コードの既存データを保護する実装。
  - DuckDB executemany の空リスト制約を回避する安全対策を導入。
  - regime_detector / news_nlp などで API 失敗時のデフォルト挙動（フォールバック）を明示。
- 環境変数パースの堅牢化（不正な MONITOR_POLL_INTERVAL 値や無効な PAPER_FILL_MODE 等を検出しデフォルト/例外で対処）。

### セキュリティ (Security)
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY が必須。未設定時は ValueError を送出して誤動作を防止。
- .env 読み込みは OS 環境変数を protected として上書き抑止し、意図しない上書きを防止。

---

注記:
- コード内には将来的な拡張や改善を示す TODO/設計メモが存在します（例: 銘柄別 lot_size マスタの導入、価格欠損時のフォールバック戦略など）。
- Date/Time の扱いはルックアヘッドバイアスを防ぐ方針で実装されています（target_date を明示的に受け取り datetime.today()/date.today() を直接参照しないなど）。