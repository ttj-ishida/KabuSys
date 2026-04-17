# CHANGELOG

すべての変更は「Keep a Changelog」形式に準拠しています。  
主にコードベースの初期リリース相当の追加と設計上の注意点を、ソースコードから推測して日本語でまとめています。

## [Unreleased]
- 開発中 / ドキュメント化待ちの小規模改善や追加テストが予定されています。
- news_nlp モジュールに未完の箇所（ファイル末尾の処理切れ）が存在するため、API 呼び出し周りやエラー処理の最終確認・調整が必要です。

## [0.1.0] - 2026-04-17
初回リリース（推定）。以下の主要機能・モジュールを追加しました。

### 追加
- 全体
  - パッケージ初期バージョンを導入（kabusys.__version__ = "0.1.0"）。
  - データ保管に SQLite / DuckDB を併用する設計を採用。
  - 停止フラグ（data/stop_requested.flag）や PID ファイルによるプロセス管理に対応。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイントを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視処理は KABUSYS_ENV に依らず本番用 sqlite_path を使用する仕様。
    - プロセス優先度を起動時に設定（set_process_priority）。
    - 例外発生時はログを残して次のポーリングに継続するフェイルセーフ挙動。

  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient（BrokerClientFactory を介して）を使用し paper_trading 用の専用 SQLite DB（デフォルト data/paper_trading.db）に分離して記録。
    - エンジン起動前の停止フラグ確認、スレッドでのデーモン実行と停止フラグ検出による安全停止を実装。
    - RiskManager / OrderManager / Reconciler 等の組み立て処理を実装（リスク設定はデフォルト値を採用）。

- 設定管理
  - config.py
    - .env 自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。
    - .env / .env.local の読み込み順・上書きルールを定義。OS 環境変数を保護する protected 機能を実装。
    - export KEY=val、クォート、エスケープ、インラインコメント等を扱える .env パーサーを実装。
    - 多数の設定プロパティを提供（J-Quants / KabuAPI / LINE / DB パス / 監視閾値 / 環境区分 等）。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）や KABUSYS_ENV / LOG_LEVEL の検証を実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを提供。

- ユーティリティ
  - utils/process_priority.py
    - クロスプラットフォームでのプロセス優先度設定（Windows の priority class / POSIX の nice）を実装。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
    - 権限不足や未サポート環境では警告ログを出して安全にスキップ。

- 監視
  - monitoring データベース初期化用の init_monitoring_db を run スクリプトから呼び出すことで、監視用テーブルの冪等な保証を実装（詳細は該当モジュールに依存）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 検証指標（稼働率、注文成功率、送信率、P95 レイテンシ等）を集計して標準出力にレポート出力。
    - デフォルト閾値: 稼働率 >= 99.0%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms。
    - 日付フィルタ（--from, --to）と DB パス指定（--db）をサポート。
    - DB が未存在・テーブル欠落の場合のフェイルセーフ処理（OperationalError をハンドル）を実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（スコア降順、同点時 signal_rank でタイブレーク）。
    - 等金額配分（calc_equal_weights）とスコア加重配分（calc_score_weights、全スコア 0 の場合は等配分へフォールバック）。

  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）：既存保有のセクター比率が上限を超える場合に新規候補を除外。unknown セクターは制限対象外。
    - 市場レジームに合わせた投下資金乗数（calc_regime_multiplier）：bull/neutral/bear のマップを定義し、未知レジームは警告して 1.0 フォールバック。

  - portfolio/position_sizing.py
    - position sizing 実装（allocation_method: risk_based / equal / score）。
    - 単元（lot_size）丸め、1 銘柄上限・総投下上限の考慮、cost_buffer を用いた保守的見積り。
    - aggregate cap 超過時のスケーリング処理（割合スケール → lot 単位での再配分ロジック）を実装。
    - 将来的な拡張（銘柄別 lot_size）の TODO を明記。

- リサーチ（DuckDB ベースのファクター計算）
  - research/factor_research.py
    - Momentum、Volatility、Value ファクター計算を実装。
    - ma200_dev（200 日移動平均乖離）、mom_1m/3m/6m、ATR 20 日、20 日平均売買代金、volume_ratio、PER / ROE 等を DuckDB SQL で計算。
    - データ不足時の None 返却とログ出力を設計。

  - research/feature_exploration.py
    - 将来リターン（calc_forward_returns）、IC（calc_ic: Spearman の ρ）、ファクター統計サマリ（factor_summary）を実装。
    - pandas 等に依存せず、標準ライブラリと DuckDB のみで完結する設計。
    - rank() は同順位を平均ランクとする実装で浮動小数の丸めに注意。

  - research/__init__.py
    - 主要関数群をエクスポート（zscore_normalize は外部モジュールから取り込み）。

- AI / NLP
  - ai/news_nlp.py（ニュースの NLP スコアリング）
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）でセンチメントスコア（-1.0〜1.0）を生成して ai_scores に書き込む設計。
    - バッチ送信（最大 20 銘柄 / コール）、JSON Mode 想定、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンス検証、スコアクリップ（±1.0）、部分成功時の既存スコア保護（限定 DELETE/INSERT）等の堅牢化設計を含む。
    - タイムウィンドウ計算（JST 基準）を実装（calc_news_window）。
    - OpenAI API キー未設定時は ValueError を投げる仕様。
    - 注: ファイル末尾が途中で切れているため、記事取得や実際の API 呼び出しループの実装が未完（補完・テストが必要）。

### 変更
- .env 読み込みの動作
  - OS 環境変数保護（protected set）と .env.local による上書き挙動を明確化。
  - 自動ロードはデフォルトで有効だが KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

### 修正（既知の注意点 / TODO）
- position_sizing.calc_position_sizes
  - price が欠損（0.0）の場合にエクスポージャーが過少見積もられる可能性がある旨の TODO コメントあり。前日終値や取得原価等のフォールバックを将来的に検討。
- risk_adjustment.apply_sector_cap
  - "unknown" セクターは現在セクター上限を適用しない（意図的な挙動）。
- ai/news_nlp.py
  - ファイル終端で処理が切れており、_fetch_articles 等の内部実装呼び出し部分が未完。実運用前に実装完了と検証が必要。
- tools/paper_verification_report.py
  - P95 の算出やテーブル欠落時のフォールバックを実装しているが、DB スキーマ変化時の互換性確認が必要。

### セキュリティ
- 環境変数の取り扱いに注意: JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / OPENAI_API_KEY などのシークレットは OS 環境変数か .env ファイルで提供する設計。`.env` の読み込みはデフォルトで有効だが、運用環境では `.env` の取り扱い（権限管理）に注意してください。

## 既知の問題
- ai/news_nlp.py の未完箇所（ファイル切れ）によりニューススコアリング機能が部分実装の状態です。OpenAI へのバッチ送信・結果パース・DB 書き込みの完成と単体テストが必要です。
- 一部の TODO（position_sizing の価格フォールバック、将来の lot_size 銘柄別対応）が残っています。

---

もし CHANGELOG に含めたい詳細（例えばリリース日・担当者・追加で注記すべき設計判断など）があれば教えてください。それを反映して改訂版を作成します。