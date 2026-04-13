# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載します。  
安定版のバージョンはパッケージの __version__ に合わせて記載しています。

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- 非推奨 (Deprecated)
- セキュリティ (Security)

## [Unreleased]
- 細かなロギングやドキュメント補足などのマイナー改善を予定。

## [0.1.0] - 2026-04-13
初回リリース。日本株自動売買システム「KabuSys」の基本コンポーネントを実装。

### Added
- 基本パッケージとバージョン設定
  - パッケージ初期化ファイルにてバージョン 0.1.0 を定義（src/kabusys/__init__.py）。
- 環境変数 / 設定管理
  - Settings クラスを実装し、.env / .env.local の自動読み込み機能を追加（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml から探索して自動ロード。
    - .env の解析は引用符・エスケープ・コメント・export 形式に対応。
    - OS 環境変数を保護する protected 上書きロジックを実装。
  - 多数の設定プロパティを提供（DB パス、PID/kill フラグ、閾値、環境判定、Paper Trading 関連など）。
  - 環境変数検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）を実装し、不正値は例外で通知。

- 実行用スクリプト / ランナー
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）を追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite DB を使用し、本番 DB と完全分離。
    - BrokerClientFactory を利用してブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 起動直後にプロセス優先度を "high" に設定。
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下はデフォルトへフォールバック）。
    - 監視処理は環境にかかわらず本番 sqlite_path を参照する設計（監視 DB は常に本番パス）。
    - SystemMonitor の一回チェックを例外捕捉してループ継続する堅牢な実装。
    - 起動直後にプロセス優先度を "high" に設定。

- 監視 DB 初期化ユーティリティ
  - init_monitoring_db を利用して監視用テーブルが存在することを冪等に保証（used by run scripts）。

- プロセス管理ユーティリティ
  - プロセス優先度・CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX（Linux, Darwin, FreeBSD）間の差分を吸収。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。
    - 権限不足や未対応プラットフォームでは警告を出して安全にフォールバック。

- ポートフォリオ構築関連（純粋関数群）
  - 銘柄選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順 + tie-breaker を実装。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（スコア全0 の場合のフォールバック実装）。
  - セクター制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: セクター別エクスポージャーを計算し、上限超過セクターの新規候補を除外。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear）を実装。未知レジームは警告の上フォールバック。
  - ポジションサイズ計算（src/kabusys/portfolio/position_sizing.py）
    - 複数の allocation_method に対応（risk_based / equal / score）。
    - 単元株（lot_size）丸め、per-stock 上限、aggregate キャップ（available_cash）に応じたスケーリング、cost_buffer（手数料・スリッページ想定）を実装。
    - 精緻なスケールダウンと余剰キャッシュを用いた再配分ロジックを実装。

- 研究（Research）モジュール
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum / Volatility / Value ファクターを DuckDB を用いて計算。
    - 各種窓長（1M/3M/6M、MA200、ATR20 等）・欠損時の None 戻し・効率的な SQL 実装。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（複数ホライズンに対応、入力検証あり）。
    - IC（スピアマンρ）計算、ランク付けユーティリティ、ファクター統計サマリを実装。
  - research パッケージ __all__ に必要 API を公開（zscore_normalize の re-export も含む）。

- AI / ニュース NLP
  - news_nlp モジュール（src/kabusys/ai/news_nlp.py）を追加。
    - raw_news と news_symbols からニュースを銘柄ごとに集約し、OpenAI (gpt-4o-mini) にバッチで投げてセンチメント（-1.0〜1.0）を算出。
    - スコアは ±1.0 にクリップ。
    - API レート制限や 5xx、ネットワークエラーに対して指数バックオフでリトライ（上限あり）。
    - 処理単位は最大 20 銘柄／チャンク、1 銘柄あたりの最大記事数・文字数を制限。
    - 結果は ai_scores テーブルへ差分更新（部分失敗時に他コードのスコアを保護する設計）。
    - OPENAI_API_KEY の未設定時は明示的にエラー。

- ツール
  - Paper Trading 検証レポート生成ツール（src/kabusys/tools/paper_verification_report.py）
    - 稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数などを算出してレポート出力。
    - 日付フィルタ（--from/--to）、DB パス指定（--db / 環境変数）に対応。
    - P95 計算、各種 SQL 集計、閾値による PASS/FAIL 判定を実装。
    - DB が存在しない/テーブルがない場合は graceful に N/A を表示。

- モジュールのエクスポート整理
  - portfolio / research パッケージの __all__ を整備し、主要関数を公開。

### Changed
- （初回リリースのため過去変更なし）プロジェクト設計は以下の方針に従う:
  - DuckDB を解析用 DB として採用（prices_daily / raw_financials 等の参照専用）。
  - SQLite はモニタリング / paper_trading の軽量永続ストレージとして利用。
  - 実行時の副作用（実際の API 呼び出し等）は ExecutionEngine / BrokerClient 経由で分離。

### Fixed
- 環境値の堅牢化
  - MONITOR_POLL_INTERVAL が不正値（整数変換失敗や 0 以下）の場合、警告を出してデフォルトにフォールバックするように実装（run_monitoring）。
  - PAPER_FILL_MODE の検証を実装し、不正な文字列の場合に ValueError を投げる（config）。
  - CPU affinity / priority 設定で権限不足や未対応プラットフォームが発生した場合に警告を出して処理を継続するように安全化（utils/process_priority）。

### Deprecated
- なし（初回リリース）。

### Security
- OpenAI API キーは明示的に引数または環境変数 OPENAI_API_KEY で渡すように実装。キー未設定時は例外を投げることで秘匿漏洩のリスクを減らす設計（news_nlp）。

---

参考: 各ファイルの実装詳細、使用例、設計メモはソース内ドキュメント（docstring / コメント）を参照してください。