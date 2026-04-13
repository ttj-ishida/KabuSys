# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
主なバージョンはパッケージの __version__ に合わせて 0.1.0 としています（初回公開相当のまとめ）。

記載はソースコードから推測できる機能追加・設計上の注意点・重要な挙動を基にしています。

## [Unreleased]

（現在なし）

## [0.1.0] - 2026-04-13

### 追加
- 全体
  - 初回リリース相当のコアモジュール群を追加。
  - パッケージメタ情報を src/kabusys/__init__.py にて version=0.1.0 として公開。

- 設定管理（kabusys.config）
  - .env 自動読み込み機能を追加（プロジェクトルートを .git または pyproject.toml から判定）。
  - .env と .env.local の読み込み順序と上書きルールを実装（OS 環境変数の保護）。
  - 複数の環境設定プロパティを提供（DB パス、PID ファイルパス、KABUSYS_ENV 検証、LOG_LEVEL 検証 等）。
  - PAPER_FILL_MODE の検証（"instant"|"partial"|"never"|"reject"）を実装。
  - Paper Trading 用 DB パス（PAPER_TRADING_SQLITE_PATH）を分離して提供。
  - 環境変数未設定時に明示的エラーを投げる _require() を追加（必須トークン等の早期検出）。

- 実行/監視起動スクリプト
  - 実行エンジン起動スクリプト: src/kabusys/run_execution.py を追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用して本番 DB と完全分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine の起動処理を実装。
    - RiskManager のデフォルトパラメータ（max_position_pct, max_utilization 等）を設定し、初期ポートフォリオ値を broker.get_available_cash() で取得。
  - 監視ループ起動スクリプト: src/kabusys/run_monitoring.py を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。0 以下や不正値はデフォルトにフォールバックし警告を出力。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計（監視データは常に本番 DB に記録）。
    - SystemMonitor の単回チェック loop（例外はログ出力して継続、KeyboardInterrupt による終了処理を実装）。
  - 両スクリプトとも起動時にプロセス優先度を "high" に設定する処理を組み込み。

- プロセス制御ユーティリティ（kabusys.utils.process_priority）
  - クロスプラットフォームでプロセス優先度（Windows: HIGH_PRIORITY_CLASS 等、POSIX: nice 値）を設定する set_process_priority を実装。
  - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装。
  - 権限不足や非対応プラットフォーム時は警告を出して安全にスキップする挙動。

- ポートフォリオ構築（kabusys.portfolio）
  - 銘柄選定: select_candidates（スコア降順、同点は signal_rank でタイブレーク）。
  - 重み計算: calc_equal_weights（等金額）、calc_score_weights（スコア正規化。全スコアが 0 の場合は等金額にフォールバックし WARNING を出力）。
  - セクター集中制限: apply_sector_cap（既存ポジションによるセクターエクスポージャーを計算し、上限超過セクターの新規候補を除外）。
  - レジーム乗数: calc_regime_multiplier（"bull"/"neutral"/"bear" に応じた乗数、未知レジームは警告して 1.0 にフォールバック）。
  - 株数決定: calc_position_sizes（allocation_method="risk_based"|"equal"|"score" をサポート）。
    - 単元（lot_size）丸め、per-stock 上限・aggregate cap（available_cash）によるスケーリング、cost_buffer による保守的見積り、スケール後の端数配分ロジックを実装。
    - 価格欠損や無効価格時はスキップしてログ出力。

- リサーチ/ファクター（kabusys.research）
  - ファクター計算: calc_momentum、calc_volatility、calc_value（DuckDB を利用し prices_daily/raw_financials を参照）。
    - Momentum: 1m/3m/6m リターン、200 日移動平均乖離（データ不足時は None）。
    - Volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比。
    - Value: PER/ROE（raw_financials から最新の報告を結合）。
  - 特徴量探索: calc_forward_returns（複数ホライズン対応、入力検証あり）、calc_ic（Spearman ランク相関：IC）、rank（同順位は平均ランク）、factor_summary（count/mean/std/min/max/median）。
  - 実装方針として外部ライブラリに依存せず、DuckDB と標準ライブラリのみで完結する設計。

- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を集約し OpenAI (gpt-4o-mini) を用いて銘柄ごとのセンチメント（-1.0〜1.0）を算出、ai_scores テーブルへ書き込む処理を実装。
  - バッチ処理（最大 20 銘柄/コール）、1銘柄あたりの記事数・文字数上限（トークン肥大化対策）を実装。
  - OpenAI API 呼び出しに対する 429/ネットワーク/5xx 等のリトライ（指数バックオフ）を実装。
  - レスポンスバリデーション（JSON 構造・既知コード・数値チェック）、スコアの ±1.0 クリップ、部分失敗時の DB 保護（対象コードに絞って置換）を設計。
  - OpenAI API キー未設定時に ValueError を送出。

- ツール（kabusys.tools.paper_verification_report）
  - Paper Trading の検証レポート生成スクリプトを追加（CLI 対応: --from/--to/--db）。
  - system_status/trade_logs/risk_logs テーブルから稼働率・注文成功率・送信率・レイテンシ（avg/max/P95）等を集計し、閾値判定（PASS/FAIL）を行う。
  - P95 計算、日付フィルタの SQL パラメータ化、DB 存在チェック、OperationalError に対するフォールバックを実装。
  - レポート書式で可読性高く出力。

### 変更
- なし（初期追加のため該当項目なし）

### 修正 / ハードニング（補足）
- 設定値や入力に対する堅牢性を強化:
  - KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE のバリデーションを追加し、不正値は ValueError で早期検出。
  - MONITOR_POLL_INTERVAL の不正値（0、負数、非数）をデフォルトにフォールバックして警告。
  - プロセス優先度・CPU affinity の設定で権限不足や未サポート環境を例外ではなく警告で扱い、処理を継続。
  - DuckDB の executemany に関する制約（空パラメータの送信回避）を考慮した実装注意書き。

### 既知の注意点 / TODO
- portfolio.risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされ、除外が回避される可能性がある旨の TODO コメント。将来的に前日終値や取得原価でのフォールバックが検討される。
- position_sizing:
  - lot_size を現在は全銘柄共通の引数で扱っているが、将来的に銘柄別 lot_map を受け取る拡張を想定。
- news_nlp:
  - OpenAI 呼び出し部はレート制限や API の細かな挙動に依存するため、運用時にさらなるエラーハンドリングやメトリクス観測が望ましい。
- 設定自動ロード:
  - プロジェクトルートが特定できない場合は .env 自動ロードをスキップ（CI/配布時に注意）。

### セキュリティ
- 環境変数に依存する API キーやトークン（OpenAI, J-Quants, kabu API パスワード 等）については .env/.env.local または OS 環境変数での管理を想定。README/運用手順での秘匿管理を推奨。

---

参考:
- 各モジュールはドキュメント文字列（docstring）やコード内コメントで意図・設計方針が明確に示されているため、実装詳細や運用上の前提はソースコードを参照してください。必要であればリリースノートを拡張して個別関数のユースケースや CLI 実行例を追加します。